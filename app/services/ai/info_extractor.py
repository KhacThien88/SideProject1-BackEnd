import boto3
import os
import json
import re
import numpy as np
from pdf2image import convert_from_path
import warnings
warnings.filterwarnings("ignore", message=".*pin_memory.*MPS.*")
from dotenv import load_dotenv
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from s3_utils import download_from_s3, upload_to_s3, file_exists_in_s3
from PIL import Image
import cv2
import time
import logging
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import io

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def measure_pipeline_time(func):
    """Hàm decorator để đo thời gian thực hiện toàn bộ pipeline"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time
            minutes, seconds = divmod(execution_time, 60)
            logger.info(f"Pipeline completed in {int(minutes)}m {seconds:.2f}s")
            return result
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            minutes, seconds = divmod(execution_time, 60)
            logger.error(f"Pipeline failed after {int(minutes)}m {seconds:.2f}s: {e}")
            raise
    return wrapper

class OCRProcessor:
    def __init__(self, region_name='ap-southeast-2'):
        self.client = boto3.client('textract', region_name=region_name)

    def process(self, path):
        ocr_text = ''
        if path.lower().endswith('.pdf'):
            # Giảm DPI để ảnh nhẹ hơn, xử lý nhanh hơn
            images = convert_from_path(path, dpi=200)
            
            # Hàm để xử lý một ảnh với Textract
            def ocr_image(image):
                # Chuyển PIL.Image sang bytes
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                
                response = self.client.detect_document_text(
                    Document={'Bytes': img_byte_arr}
                )
                
                text = ''
                for item in response['Blocks']:
                    if item['BlockType'] == 'LINE':
                        text += item['Text'] + '\n'
                return text.strip()

            # Sử dụng ThreadPoolExecutor để chạy OCR song song trên các trang
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Gửi tất cả các ảnh vào pool để xử lý
                future_to_text = {executor.submit(ocr_image, img): i for i, img in enumerate(images)}
                
                # Thu thập kết quả theo đúng thứ tự trang
                page_texts = ["" for _ in images]
                for future in concurrent.futures.as_completed(future_to_text):
                    index = future_to_text[future]
                    try:
                        page_texts[index] = future.result()
                    except Exception as exc:
                        print(f'Trang {index+1} tạo ra lỗi: {exc}')

                ocr_text = "\n".join(page_texts)
        else:
            # Xử lý cho file ảnh đơn
            with open(path, 'rb') as image_file:
                img_byte_arr = image_file.read()
                
            response = self.client.detect_document_text(
                Document={'Bytes': img_byte_arr}
            )
            
            for item in response['Blocks']:
                if item['BlockType'] == 'LINE':
                    ocr_text += item['Text'] + '\n'
            
        return ocr_text.strip()

class BedrockExtractor:
    def __init__(self, model_arn, region_name='ap-southeast-2'):
        if not model_arn:
            raise ValueError("Model ARN is required")
        self.model_arn = model_arn
        self.region_name = region_name
        self.client = boto3.client('bedrock-runtime', region_name=region_name)

    def extract(self, raw_txt, prompt_template):
        prompt = prompt_template + "\n" + raw_txt
        try:
            response = self.client.converse(
                modelId=self.model_arn,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": 2000, "temperature": 0.1, "topP": 0.9}
            )
            response_text = response["output"]["message"]["content"][0]["text"].strip()
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").strip()
            if response_text.endswith("```"):
                response_text = response_text.rstrip("```").strip()
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON", "raw_output": response_text}
        except Exception as e:
            return {"error": f"Bedrock invocation failed: {str(e)}"}

class S3Handler:
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name

    def download_file(self, s3_key, local_path):
        download_from_s3(self.bucket_name, s3_key, local_path)

    def upload_file(self, local_path, s3_key):
        upload_to_s3(local_path, self.bucket_name, s3_key)
        
@measure_pipeline_time
def main():
    load_dotenv()
    
    bucket_name = os.getenv("S3_BUCKET_NAME")
    input_s3_prefix = os.getenv("INPUT_S3_PREFIX")
    output_s3_prefix = os.getenv("OUTPUT_S3_PREFIX")
    local_input_path = os.getenv("LOCAL_INPUT_DATA_DIR")
    local_output_path = os.getenv("LOCAL_OUTPUT_DATA_DIR")
    model_arn = os.getenv("BEDROCK_MODEL_ARN")
    region_name = os.getenv("S3_REGION")
    
    os.makedirs(local_input_path, exist_ok=True)
    os.makedirs(local_output_path, exist_ok=True)

    # Khởi tạo OCR
    ocr_processor = OCRProcessor()
    bedrock_extractor = BedrockExtractor(model_arn, region_name)
    s3_handler = S3Handler(bucket_name)
    
    # Prompt templates
    cv_prompt_template = f"""
    You are an expert at extracting structured information from unstructured text.
    Do not make up any information.
    Extract the following information from the resume text below:
    1. Role
    2. Full Name
    3. Email Address
    4. Phone Number
    5. Location
    6. Skills (list of skills)
    7. Work Experience (list of job titles and companies)
    8. Education (list of degrees and institutions)
    9. Certifications (list of certifications)
    10. Languages (list of languages spoken)
    11. Projects (list of notable projects with full detailed descriptions, duration and technologys used)
    12. Summary (a brief summary of the candidate)
    13. LinkedIn Profile (URL of the LinkedIn profile)
    14. GitHub Profile (URL of the GitHub profile)
    15. Portfolio Website (URL of the portfolio website)
    16. References (list of references if available)
    Format the output as a JSON object with the above fields. If any information is not available, use "Not Available" as the value.
    The JSON format must adhere to the following structure:
    {{
    "role": "string",
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
    
    file_name = "2aa9c768-7e13-432c-a33f-8476964e7965_CV_Huan_Developer.pdf"
    file_base_name = os.path.splitext(file_name)[0]

    input_key = f"{input_s3_prefix.rstrip('/')}/{file_name}"
    output_key = f"{output_s3_prefix.rstrip('/')}/{file_base_name}.json"
    local_input_file = os.path.join(local_input_path, file_name)
    local_output_file = os.path.join(local_output_path, f"{file_base_name}.json")

    try:
        # Step 1: Download file from S3
        s3_handler.download_file(input_key, local_input_file)
        # Step 2: Perform OCR
        raw_text = ocr_processor.process(local_input_file)
        # Change the prompt template based on the type of document (CV or Job Description)
        if "cv" in file_base_name.lower() or "resume" in file_base_name.lower():
            prompt_template = cv_prompt_template
        else:
            prompt_template = job_prompt_template
        # Step 3: Extract information
        extracted_info = bedrock_extractor.extract(raw_text, prompt_template)
        # Step 4: Save extracted information to a JSON file
        with open(local_output_file, 'w') as json_file:
            json.dump(extracted_info, json_file, indent=4)
        # Step 5: Upload JSON file to S3
        s3_handler.upload_file(local_output_file, output_key)
    except Exception as e:
        print(f"Error in processing: {e}")

if __name__ == "__main__":  
    main()