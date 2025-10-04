import boto3
import os
import json
import re
import numpy as np
from pdf2image import convert_from_path
import easyocr
import warnings
warnings.filterwarnings("ignore", message=".*pin_memory.*MPS.*")
from dotenv import load_dotenv
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from s3_utils import download_from_s3, upload_to_s3, file_exists_in_s3


load_dotenv()

def ocr_doc(path, ocr_langs=['en']):
    ocr_text = ''
    reader = easyocr.Reader(ocr_langs)
    if path.endswith('.pdf'):
        images = convert_from_path(path)
        ocr_result = []
        for image in images:
            ocr_result.extend(reader.readtext(np.array(image)))
    else:
        ocr_result = reader.readtext(path)
    for res in ocr_result:
        ocr_text += res[1] + '\n'
    return ocr_text.strip()

def extract_info_with_bedrock(raw_txt, prompt_template, model_arn, region_name='ap-southeast-2'):
    if model_arn is None:
        return {"error": "Model ARN is required"}

    prompt = prompt_template + "\n" + raw_txt
    client = boto3.client('bedrock-runtime', region_name=region_name)

    try:
        response = client.converse(
            modelId=model_arn,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 2000, "temperature": 0.1, "topP": 0.9}
        )
        response_text = response["output"]["message"]["content"][0]["text"].strip()
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "").strip()
        if response_text.endswith("```"):
            response_text = response_text.rstrip("```").strip()
        try:
            extracted_json = json.loads(response_text)
        except json.JSONDecodeError:
            extracted_json = {"error": "Failed to parse JSON", "raw_output": response_text}
        return extracted_json
    except Exception as e:
        return {"error": f"Bedrock invocation failed: {str(e)}"}

def main():
    # S3 bucket and file details
    bucket_name = os.getenv("S3_BUCKET_NAME")
    input_s3_prefix = os.getenv("INPUT_S3_PREFIX") 
    output_s3_prefix = os.getenv("OUTPUT_S3_PREFIX")
    local_input_path = os.getenv("LOCAL_INPUT_DATA_DIR")
    local_output_path = os.getenv("LOCAL_OUTPUT_DATA_DIR")
    
    os.makedirs(local_input_path, exist_ok=True)
    os.makedirs(local_output_path, exist_ok=True)

    # AWS Bedrock model details
    model_arn = os.getenv("BEDROCK_MODEL_ARN")
    region_name = os.getenv("S3_REGION")
    

    # Prompt template for extraction
    cv_prompt_template = f"""
    You are an expert at extracting structured information from unstructured text.
    Do not make up any information.
    Extract the following information from the resume text below:
    1. Full Name
    2. Email Address
    3. Phone Number
    4. Location
    5. Skills (list of skills)
    6. Work Experience (list of job titles and companies)
    7. Education (list of degrees and institutions)
    8. Certifications (list of certifications)
    9. Languages (list of languages spoken)
    10. Projects (list of notable projects with descriptions and duration)
    11. Summary (a brief summary of the candidate)
    12. LinkedIn Profile (URL of the LinkedIn profile)
    13. GitHub Profile (URL of the GitHub profile)
    14. Portfolio Website (URL of the portfolio website)
    15. References (list of references if available)
    Format the output as a JSON object with the above fields. If any information is not available, use "Not Available" as the value.
    The JSON format must adhere to the following structure:
    {{
    "full_name": "string",
    "email_address": "string",
    "phone_number": "string",
    "location": "string",
    "summary": "string",
    "linkedin_profile": "URL string or null",
    "github_profile": "URL string or null",
    "portfolio_website": "URL string or null",
    "skills": ["string", "string", "..."],
    "work_experience": [
        {{
        "job_title": "string",
        "company": "string",
        "duration": "string",
        "description": "string"
        }}
    ],
    "education": [
        {{
        "degree": "string",
        "institution": "string",
        "graduation_year": "string"
        }}
    ],
    "certifications": ["string", "string", "..."],
    "languages": ["string", "string", "..."],
    "projects": ["string", "string", "..."],
    "references": ["string", "string", "..."]
    }}
    Here is the resume text:
    """

    job_prompt_template = f"""
    You are an expert at extracting structured information from unstructured text.
    Do not make up any information.
    Extract the following information from the job description text below:
    1. Job Title
    2. Company Name
    3. Location
    4. Job Type (e.g., full-time, part-time, remote)
    5. Salary Range
    6. Responsibilities (list of key responsibilities)
    7. Requirements (list of required skills, education, and experience)
    8. Benefits (list of benefits offered)
    9. Application Instructions (how to apply)
    10. Contact Information (email or phone if available)
    11. Company Website (URL if available)
    12. Posting Date (date the job was posted if available)
    13. Required Certifications (list if any)
    14. Preferred Languages (list if any)
    Format the output as a JSON object with the above fields. If any information is not available, use "Not Available" as the value.
    The JSON format must adhere to the following structure:
    {{
    "job_title": "string",
    "company_name": "string",
    "location": "string",
    "job_type": "string",
    "salary_range": "string",
    "company_website": "URL string or null",
    "posting_date": "string",
    "contact_information": "string",
    "responsibilities": ["string", "string", "..."],
    "requirements": ["string", "string", "..."],
    "benefits": ["string", "string", "..."],
    "application_instructions": "string",
    "required_certifications": ["string", "string", "..."],
    "preferred_languages": ["string", "string", "..."]
    }}
    Here is the job description text:
    """
    
    file_name = "0.png"
    input_key = f"{input_s3_prefix.rstrip('/')}/{file_name}"
    output_key = f"{output_s3_prefix.rstrip('/')}/{file_name.replace('.png', '.json')}"
    local_input_path = os.path.join(local_input_path, file_name)
    local_output_path = os.path.join(local_output_path, file_name.replace(".png", ".json"))
    

    try:
        # Step 1: Download file from S3
        download_from_s3(bucket_name, input_key, local_input_path)
        # Step 2: Perform OCR
        raw_text = ocr_doc(local_input_path)
        # Step 3: Extract information
        extracted_info = extract_info_with_bedrock(raw_text, cv_prompt_template, model_arn, region_name)
        # Step 4: Save extracted information to a JSON file
        with open(local_output_path, 'w') as json_file:
            json.dump(extracted_info, json_file, indent=4)
        # Step 5: Upload JSON file to S3
        upload_to_s3(local_output_path, bucket_name, output_key)

    except Exception as e:
        print(f"Error in processing: {e}")

if __name__ == "__main__":  
    main()