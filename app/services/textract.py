"""
AWS Textract Service
Comprehensive text extraction từ CV documents với async processing và error handling
"""

import boto3
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, BinaryIO
from botocore.exceptions import ClientError, WaiterError
from botocore.config import Config

from app.core.config import settings
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
        document_type: str = "cv"
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
            
            # Detect document type và choose appropriate method
            file_extension = s3_key.lower().split('.')[-1]
            
            if file_extension == 'pdf':
                # Use synchronous API for PDFs
                result = await self._extract_text_sync(s3_key)
            else:
                # Use asynchronous API for other formats
                result = await self._extract_text_async(s3_key)
            
            if result["success"]:
                # Process extracted text
                processed_text = await self._process_extracted_text(
                    result["text"], 
                    document_type
                )
                
                logger.info(f"Text extraction completed for {s3_key}")
                
                return {
                    "success": True,
                    "text": processed_text["processed_text"],
                    "raw_text": result["text"],
                    "confidence": result.get("confidence", 0.0),
                    "document_type": document_type,
                    "extraction_method": result.get("method", "unknown"),
                    "processing_metadata": processed_text["metadata"],
                    "extraction_timestamp": datetime.utcnow().isoformat()
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
                logger.error(f"Textract sync error: {str(e)}")
                return {
                    "success": False,
                    "error": f"Textract error: {str(e)}"
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
            
            # Wait for job completion
            waiter = self.textract_client.get_waiter('text_detection_job_complete')
            waiter.wait(JobId=job_id)
            
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
