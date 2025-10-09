"""
AWS Textract Service
Comprehensive text extraction từ CV documents với async processing và error handling
"""

import boto3
import asyncio
import uuid
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, BinaryIO
from botocore.exceptions import ClientError, WaiterError
from botocore.config import Config

from app.core.config import settings
from app.core.database import get_dynamodb_resource
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TextractService:
    """Service để extract text từ documents sử dụng AWS Textract"""
    
    def __init__(self):
        """Initialize Textract service với proper configuration"""
        try:
            # Textract client configuration
            config = Config(
                region_name=settings.aws_region,
                retries={'max_attempts': 3, 'mode': 'adaptive'},
                max_pool_connections=50
            )
            
            self.textract_client = boto3.client(
                'textract',
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                config=config
            )
            
            self.s3_client = boto3.client(
                's3',
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                config=config
            )
            
            self.bucket_name = settings.s3_bucket_name
            self.region = settings.aws_region
            
            logger.info("TextractService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize TextractService: {str(e)}")
            raise
    
    async def extract_text_from_s3(
        self, 
        s3_key: str, 
        document_type: str = "cv",
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Extract text từ document trong S3
        
        Args:
            s3_key: S3 object key
            document_type: Type of document (cv, resume, etc.)
            
        Returns:
            Dict với extraction result
        """
        try:
            logger.info(f"Starting text extraction for {s3_key}")

            # Try reuse from S3 + DynamoDB if not forced
            source_user_id: Optional[str] = None
            source_file_id: Optional[str] = None
            source_etag: Optional[str] = None
            source_last_modified: Optional[str] = None

            try:
                head = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
                md = head.get('Metadata', {})
                source_user_id = md.get('user_id')
                source_file_id = md.get('file_id')
                source_etag = head.get('ETag', '').strip('"')
                lm = head.get('LastModified')
                source_last_modified = lm.isoformat() if lm else None
            except Exception:
                # If we can't head the object, proceed with extraction attempt (will fail later accordingly)
                pass

            # Determine potential extract key path
            extract_key: Optional[str] = None
            if source_user_id and source_file_id:
                extract_folder = "Textract/CV_extract" if document_type == "cv" else "Textract/JD_extract"
                extract_key = f"{extract_folder}/{source_user_id}/{source_file_id}.txt"

            if not force and extract_key:
                # Optional DynamoDB validation with stored etag
                etag_matches = True
                try:
                    dynamodb = get_dynamodb_resource()
                    if dynamodb:
                        table = dynamodb.Table(settings.cv_uploads_table_name)
                        item_resp = table.get_item(Key={'file_id': source_file_id})
                        item = item_resp.get('Item')
                        if item and item.get('source_etag') and source_etag:
                            etag_matches = (item.get('source_etag') == source_etag)
                except Exception:
                    # If dynamodb check fails, fallback to relying on S3 presence
                    etag_matches = True

                # If we consider cache valid, try to load cached extract from S3
                if etag_matches:
                    try:
                        cached_obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=extract_key)
                        cached_text_bytes = cached_obj['Body'].read()
                        cached_text = cached_text_bytes.decode('utf-8', errors='ignore')
                        processed_text = await self._process_extracted_text(cached_text, document_type)

                        # Try to build structured JSON even from cache
                        structured_json: Optional[Dict[str, Any]] = None
                        processed_key: Optional[str] = None
                        try:
                            structured_json = await self._extract_structured_json(
                                raw_text=cached_text,
                                document_type=document_type
                            )
                        except Exception as e:
                            logger.warning(f"Structured extraction (cache) failed: {str(e)}")

                        # Persist structured JSON if available
                        if structured_json and source_user_id and source_file_id:
                            try:
                                processed_folder = "Processed/CV_Json" if document_type == "cv" else "Processed/JD_Json"
                                processed_key = f"{processed_folder}/{source_user_id}/{source_file_id}.json"
                                self.s3_client.put_object(
                                    Bucket=self.bucket_name,
                                    Key=processed_key,
                                    Body=json.dumps(structured_json, ensure_ascii=False, indent=2).encode("utf-8"),
                                    ContentType="application/json; charset=utf-8",
                                    Metadata={
                                        "user_id": source_user_id,
                                        "file_id": source_file_id,
                                        "source_key": s3_key,
                                        "document_type": document_type
                                    }
                                )
                            except Exception as e:
                                logger.warning(f"Failed to persist structured JSON (cache) to S3: {str(e)}")

                            # Update DynamoDB mapping as well if possible
                            try:
                                dynamodb = get_dynamodb_resource()
                                if dynamodb and source_file_id:
                                    table = dynamodb.Table(settings.cv_uploads_table_name)
                                    table.update_item(
                                        Key={'file_id': source_file_id},
                                        UpdateExpression="SET processed_json_key = :pjk, last_extracted_at = :ts",
                                        ExpressionAttributeValues={
                                            ':pjk': processed_key,
                                            ':ts': datetime.utcnow().isoformat()
                                        }
                                    )
                            except Exception as e:
                                logger.warning(f"Failed to update DynamoDB mapping (cache) for {source_file_id}: {str(e)}")

                        return {
                            "success": True,
                            "text": processed_text["processed_text"],
                            "raw_text": cached_text,
                            "confidence": 0.0,
                            "document_type": document_type,
                            "extraction_method": "cache",
                            "processing_metadata": processed_text["metadata"],
                            "extraction_timestamp": datetime.utcnow().isoformat(),
                            "structured_json": structured_json,
                            "structured_json_s3_key": processed_key
                        }
                    except ClientError as e:
                        if e.response['Error']['Code'] != 'NoSuchKey':
                            logger.warning(f"Failed to reuse cached extract {extract_key}: {str(e)}")
                        # else: no cache, proceed to extract

            # Use asynchronous API for all document types
            # Some PDF formats are not supported by sync API but work with async API
            result = await self._extract_text_async(s3_key)

            if result["success"]:
                # Process extracted text
                processed_text = await self._process_extracted_text(
                    result["text"], 
                    document_type
                )

                # Try extract structured JSON via Bedrock (non-fatal on failure)
                structured_json: Optional[Dict[str, Any]] = None
                try:
                    structured_json = await self._extract_structured_json(
                        raw_text=result["text"],
                        document_type=document_type
                    )
                except Exception as e:
                    logger.warning(f"Structured extraction failed: {str(e)}")

                # Persist extract to S3 for future reuse if we have identifiers
                if extract_key:
                    try:
                        content_bytes = processed_text["processed_text"].encode("utf-8")
                        self.s3_client.put_object(
                            Bucket=self.bucket_name,
                            Key=extract_key,
                            Body=content_bytes,
                            ContentType="text/plain; charset=utf-8",
                            Metadata={
                                "user_id": source_user_id or "",
                                "file_id": source_file_id or "",
                                "source_key": s3_key,
                                "document_type": document_type,
                                "original_etag": source_etag or ""
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to persist Textract output to {extract_key}: {str(e)}")

                # Persist structured JSON if available and identifiers present
                processed_key: Optional[str] = None
                if structured_json and source_user_id and source_file_id:
                    try:
                        processed_folder = "Processed/CV_Json" if document_type == "cv" else "Processed/JD_Json"
                        processed_key = f"{processed_folder}/{source_user_id}/{source_file_id}.json"
                        self.s3_client.put_object(
                            Bucket=self.bucket_name,
                            Key=processed_key,
                            Body=json.dumps(structured_json, ensure_ascii=False, indent=2).encode("utf-8"),
                            ContentType="application/json; charset=utf-8",
                            Metadata={
                                "user_id": source_user_id,
                                "file_id": source_file_id,
                                "source_key": s3_key,
                                "document_type": document_type
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to persist structured JSON to S3: {str(e)}")

                # Update DynamoDB mapping for future reuse
                try:
                    dynamodb = get_dynamodb_resource()
                    if dynamodb and source_file_id:
                        table = dynamodb.Table(settings.cv_uploads_table_name)
                        update_expr = "SET source_etag = :etag, source_last_modified = :lm, extract_key = :ek, last_extracted_at = :ts, document_type = :dt"
                        expr_vals = {
                            ':etag': source_etag or '',
                            ':lm': source_last_modified or '',
                            ':ek': extract_key or '',
                            ':ts': datetime.utcnow().isoformat(),
                            ':dt': document_type
                        }
                        # Also store processed_json_key if we created one
                        if structured_json and source_user_id and source_file_id:
                            processed_folder = "Processed/CV_Json" if document_type == "cv" else "Processed/JD_Json"
                            processed_key = f"{processed_folder}/{source_user_id}/{source_file_id}.json"
                            update_expr += ", processed_json_key = :pjk"
                            expr_vals[':pjk'] = processed_key
                        table.update_item(
                            Key={'file_id': source_file_id},
                            UpdateExpression=update_expr,
                            ExpressionAttributeValues=expr_vals
                        )
                except Exception as e:
                    logger.warning(f"Failed to update DynamoDB mapping for {source_file_id}: {str(e)}")

                logger.info(f"Text extraction completed for {s3_key}")

                return {
                    "success": True,
                    "text": processed_text["processed_text"],
                    "raw_text": result["text"],
                    "confidence": result.get("confidence", 0.0),
                    "document_type": document_type,
                    "extraction_method": result.get("method", "unknown"),
                    "processing_metadata": processed_text["metadata"],
                    "extraction_timestamp": datetime.utcnow().isoformat(),
                    "structured_json": structured_json,
                    "structured_json_s3_key": processed_key
                }
            else:
                return result

        except Exception as e:
            logger.error(f"Text extraction failed for {s3_key}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "s3_key": s3_key
            }

    async def _extract_structured_json(self, raw_text: str, document_type: str) -> Optional[Dict[str, Any]]:
        """Extract structured JSON using Bedrock. Returns None on failure.
        This is best-effort and should not block the main Textract flow.
        """
        model_arn = getattr(settings, 'bedrock_model_arn', None) or os.getenv("BEDROCK_MODEL_ARN")
        if not model_arn:
            return None
        region = getattr(settings, 'aws_region', 'ap-southeast-2')

        if document_type == 'cv':
            prompt_template = (
                "You are an expert at extracting structured information from resume text. "
                "Do not fabricate. Return strict JSON with keys: full_name, email_address, phone_number, location, "
                "summary, linkedin_profile, github_profile, portfolio_website, skills (array), work_experience "
                "(array of objects: job_title, company, duration, description), education (array of objects: degree, "
                "institution, graduation_year), certifications (array), languages (array), projects (array), references (array)."
            )
        else:
            prompt_template = (
                "Extract structured info from job description as strict JSON with keys: job_title, company_name, "
                "location, job_type, salary_range, company_website, posting_date, contact_information, responsibilities (array), "
                "requirements (array), benefits (array), application_instructions, required_certifications (array), preferred_languages (array)."
            )
        try:
            client = boto3.client(
                'bedrock-runtime',
                region_name=region,
                aws_access_key_id=getattr(settings, 'aws_access_key_id', None),
                aws_secret_access_key=getattr(settings, 'aws_secret_access_key', None)
            )
            prompt = f"{prompt_template}\n{raw_text}"
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
            parsed = json.loads(response_text)
            if isinstance(parsed, dict):
                return parsed
            return None
        except Exception as e:
            logger.warning(f"Bedrock structured extraction error: {str(e)}")
            return None
    
    async def extract_text_from_bytes(
        self, 
        file_content: bytes, 
        file_name: str,
        document_type: str = "cv"
    ) -> Dict[str, Any]:
        """
        Extract text từ file content trực tiếp
        
        Args:
            file_content: File content as bytes
            file_name: Original filename
            document_type: Type of document
            
        Returns:
            Dict với extraction result
        """
        try:
            # Upload file to S3 temporarily
            temp_s3_key = f"temp-extraction/{uuid.uuid4()}_{file_name}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=temp_s3_key,
                Body=file_content,
                ContentType=self._get_content_type(file_name)
            )
            
            try:
                # Extract text
                result = await self.extract_text_from_s3(temp_s3_key, document_type)
                
                return result
                
            finally:
                # Clean up temporary file
                try:
                    self.s3_client.delete_object(
                        Bucket=self.bucket_name,
                        Key=temp_s3_key
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_s3_key}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Text extraction from bytes failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _extract_text_sync(self, s3_key: str) -> Dict[str, Any]:
        """Extract text sử dụng synchronous API"""
        try:
            response = self.textract_client.detect_document_text(
                Document={
                    'S3Object': {
                        'Bucket': self.bucket_name,
                        'Name': s3_key
                    }
                }
            )
            
            # Extract text từ response
            text_blocks = []
            confidence_scores = []
            
            for block in response.get('Blocks', []):
                if block['BlockType'] == 'LINE':
                    text_blocks.append(block['Text'])
                    confidence_scores.append(block.get('Confidence', 0))
            
            extracted_text = '\n'.join(text_blocks)
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            return {
                "success": True,
                "text": extracted_text,
                "confidence": avg_confidence,
                "method": "sync",
                "blocks_count": len(text_blocks)
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'InvalidParameterException':
                return {
                    "success": False,
                    "error": "Invalid document format or corrupted file"
                }
            elif error_code == 'AccessDeniedException':
                return {
                    "success": False,
                    "error": "Access denied to S3 object"
                }
            else:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_message = str(e)
                
                if error_code == 'UnsupportedDocumentException':
                    logger.error(f"Unsupported document format: {error_message}")
                    return {
                        "success": False,
                        "error": "Document format not supported by Textract. Please ensure the file is a valid PDF or image.",
                        "error_code": error_code
                    }
                elif error_code == 'InvalidS3ObjectException':
                    logger.error(f"S3 object not accessible: {error_message}")
                    return {
                        "success": False,
                        "error": "Cannot access file in S3. Check file permissions and region settings.",
                        "error_code": error_code
                    }
                else:
                    logger.error(f"Textract sync error: {error_message}")
                    return {
                        "success": False,
                        "error": f"Textract processing failed: {error_message}",
                        "error_code": error_code
                    }
        except Exception as e:
            logger.error(f"Sync extraction error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _extract_text_async(self, s3_key: str) -> Dict[str, Any]:
        """Extract text sử dụng asynchronous API"""
        try:
            # Start async job
            response = self.textract_client.start_document_text_detection(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': self.bucket_name,
                        'Name': s3_key
                    }
                }
            )
            
            job_id = response['JobId']
            logger.info(f"Started async text extraction job: {job_id}")
            
            # Wait for job completion using polling
            import time
            max_wait_time = 300  # 5 minutes
            wait_interval = 5    # 5 seconds
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                try:
                    status_response = self.textract_client.get_document_text_detection(JobId=job_id)
                    job_status = status_response.get('JobStatus', 'UNKNOWN')
                    
                    if job_status == 'SUCCEEDED':
                        result_response = status_response
                        break
                    elif job_status == 'FAILED':
                        error_message = status_response.get('StatusMessage', 'Job failed')
                        raise Exception(f"Textract job failed: {error_message}")
                    elif job_status in ['IN_PROGRESS', 'SUBMITTED']:
                        logger.info(f"Job {job_id} status: {job_status}, waiting...")
                        time.sleep(wait_interval)
                        elapsed_time += wait_interval
                    else:
                        raise Exception(f"Unknown job status: {job_status}")
                        
                except ClientError as e:
                    if e.response.get('Error', {}).get('Code') == 'InvalidJobIdException':
                        # Job not ready yet, continue waiting
                        time.sleep(wait_interval)
                        elapsed_time += wait_interval
                    else:
                        raise
            
            if elapsed_time >= max_wait_time:
                raise Exception("Textract job timed out")
            
            # Get results
            result_response = self.textract_client.get_document_text_detection(JobId=job_id)
            
            # Extract text từ results
            text_blocks = []
            confidence_scores = []
            
            for block in result_response.get('Blocks', []):
                if block['BlockType'] == 'LINE':
                    text_blocks.append(block['Text'])
                    confidence_scores.append(block.get('Confidence', 0))
            
            extracted_text = '\n'.join(text_blocks)
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            return {
                "success": True,
                "text": extracted_text,
                "confidence": avg_confidence,
                "method": "async",
                "job_id": job_id,
                "blocks_count": len(text_blocks)
            }
            
        except WaiterError as e:
            logger.error(f"Textract job timeout: {str(e)}")
            return {
                "success": False,
                "error": "Text extraction job timed out"
            }
        except ClientError as e:
            logger.error(f"Textract async error: {str(e)}")
            return {
                "success": False,
                "error": f"Textract error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Async extraction error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _process_extracted_text(
        self, 
        raw_text: str, 
        document_type: str
    ) -> Dict[str, Any]:
        """
        Process extracted text để clean và structure
        
        Args:
            raw_text: Raw extracted text
            document_type: Type of document
            
        Returns:
            Dict với processed text và metadata
        """
        try:
            # Basic text cleaning
            cleaned_text = self._clean_text(raw_text)
            
            # Extract sections
            sections = self._extract_sections(cleaned_text)
            
            # Extract key information
            key_info = self._extract_key_information(cleaned_text, document_type)
            
            # Calculate text quality metrics
            quality_metrics = self._calculate_text_quality(cleaned_text)
            
            return {
                "processed_text": cleaned_text,
                "sections": sections,
                "key_information": key_info,
                "quality_metrics": quality_metrics,
                "metadata": {
                    "original_length": len(raw_text),
                    "processed_length": len(cleaned_text),
                    "sections_count": len(sections),
                    "processing_timestamp": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Text processing error: {str(e)}")
            return {
                "processed_text": raw_text,
                "sections": {},
                "key_information": {},
                "quality_metrics": {},
                "metadata": {
                    "processing_error": str(e)
                }
            }
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        import re
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might be OCR artifacts
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\{\}\@\#\$\%\&\*\+\=\<\>\|\~\`\'\"]', '', text)
        
        # Fix common OCR errors
        text = text.replace('|', 'I')  # Common OCR error
        text = text.replace('0', 'O')  # In certain contexts
        
        # Remove multiple spaces
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    
    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract document sections"""
        import re
        
        sections = {}
        
        # Common CV section headers
        section_patterns = {
            'personal_info': r'(?:personal\s+information|contact\s+information|about\s+me)',
            'experience': r'(?:work\s+experience|professional\s+experience|employment\s+history)',
            'education': r'(?:education|academic\s+background|qualifications)',
            'skills': r'(?:skills|technical\s+skills|competencies)',
            'projects': r'(?:projects|portfolio|key\s+projects)',
            'certifications': r'(?:certifications|certificates|licenses)',
            'languages': r'(?:languages|language\s+skills)',
            'interests': r'(?:interests|hobbies|activities)'
        }
        
        text_lower = text.lower()
        
        for section_name, pattern in section_patterns.items():
            match = re.search(pattern, text_lower)
            if match:
                # Extract content after the section header
                start_pos = match.end()
                next_section = None
                
                # Find next section
                for other_pattern in section_patterns.values():
                    if other_pattern != pattern:
                        next_match = re.search(other_pattern, text_lower[start_pos:])
                        if next_match:
                            if next_section is None or next_match.start() < next_section:
                                next_section = next_match.start()
                
                if next_section:
                    section_content = text[start_pos:start_pos + next_section].strip()
                else:
                    section_content = text[start_pos:].strip()
                
                if section_content:
                    sections[section_name] = section_content
        
        return sections
    
    def _extract_key_information(self, text: str, document_type: str) -> Dict[str, Any]:
        """Extract key information từ text"""
        import re
        
        key_info = {}
        
        # Email extraction
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            key_info['emails'] = list(set(emails))
        
        # Phone number extraction
        phone_pattern = r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        phones = re.findall(phone_pattern, text)
        if phones:
            key_info['phones'] = [f"({match[0]}) {match[1]}-{match[2]}" for match in phones]
        
        # Years of experience (rough estimate)
        year_pattern = r'(?:19|20)\d{2}'
        years = re.findall(year_pattern, text)
        if years:
            years = [int(year) for year in years if 1950 <= int(year) <= 2030]
            if years:
                key_info['years_mentioned'] = sorted(list(set(years)))
        
        # Skills/keywords extraction
        common_skills = [
            'python', 'java', 'javascript', 'react', 'node.js', 'sql', 'aws', 'docker',
            'kubernetes', 'git', 'linux', 'machine learning', 'data analysis',
            'project management', 'leadership', 'communication', 'teamwork'
        ]
        
        found_skills = []
        text_lower = text.lower()
        for skill in common_skills:
            if skill in text_lower:
                found_skills.append(skill)
        
        if found_skills:
            key_info['skills_mentioned'] = found_skills
        
        return key_info
    
    def _calculate_text_quality(self, text: str) -> Dict[str, Any]:
        """Calculate text quality metrics"""
        import re
        
        # Basic metrics
        word_count = len(text.split())
        char_count = len(text)
        line_count = len(text.split('\n'))
        
        # Calculate readability metrics (simplified)
        sentences = re.split(r'[.!?]+', text)
        sentence_count = len([s for s in sentences if s.strip()])
        
        avg_words_per_sentence = word_count / sentence_count if sentence_count > 0 else 0
        avg_chars_per_word = char_count / word_count if word_count > 0 else 0
        
        # Estimate confidence based on text characteristics
        confidence_indicators = 0
        total_indicators = 0
        
        # Check for common OCR artifacts
        if not re.search(r'[a-zA-Z]', text):
            confidence_indicators += 1
        total_indicators += 1
        
        # Check for reasonable word length
        words = text.split()
        reasonable_words = sum(1 for word in words if 2 <= len(word) <= 20)
        if words:
            confidence_indicators += reasonable_words / len(words)
        total_indicators += 1
        
        # Check for proper capitalization
        proper_caps = sum(1 for word in words if word[0].isupper() and word[1:].islower())
        if words:
            confidence_indicators += proper_caps / len(words)
        total_indicators += 1
        
        estimated_confidence = (confidence_indicators / total_indicators) * 100 if total_indicators > 0 else 0
        
        return {
            "word_count": word_count,
            "char_count": char_count,
            "line_count": line_count,
            "sentence_count": sentence_count,
            "avg_words_per_sentence": round(avg_words_per_sentence, 2),
            "avg_chars_per_word": round(avg_chars_per_word, 2),
            "estimated_confidence": round(estimated_confidence, 2)
        }
    
    def _get_content_type(self, filename: str) -> str:
        """Determine content type from filename"""
        import mimetypes
        
        content_type, _ = mimetypes.guess_type(filename)
        
        if content_type:
            return content_type
        
        # Fallback based on extension
        ext = filename.lower().split('.')[-1]
        content_type_map = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'txt': 'text/plain',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png'
        }
        
        return content_type_map.get(ext, 'application/octet-stream')
    
    async def get_extraction_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status của async extraction job
        
        Args:
            job_id: Textract job ID
            
        Returns:
            Dict với job status
        """
        try:
            response = self.textract_client.get_document_text_detection(JobId=job_id)
            
            status = response.get('JobStatus', 'UNKNOWN')
            
            return {
                "success": True,
                "job_id": job_id,
                "status": status,
                "progress": response.get('Progress', 0),
                "status_message": response.get('StatusMessage', ''),
                "completion_time": response.get('CompletionTime'),
                "creation_time": response.get('CreationTime')
            }
            
        except ClientError as e:
            logger.error(f"Failed to get extraction status: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Status check error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
textract_service = TextractService()
