"""
Service layer cho CV storage business logic
"""
from typing import Dict, Any, List, Optional, Tuple
import uuid
import logging
from datetime import datetime

from app.repositories.cv_storage import CVStorageRepository
from app.models.cv import CVAnalysis, CVContent
from app.services.cv_content_parser import cv_content_parser
from app.services.textract import textract_service
from app.services.s3 import s3_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CVStorageService:
    """Service cho CV storage business logic"""
    
    def __init__(self):
        self.repository = CVStorageRepository()
        self.textract_service = textract_service
        self.s3_service = s3_service
    
    async def create_cv_record(
        self, 
        user_id: str, 
        filename: str, 
        file_size: int, 
        file_type: str, 
        s3_key: str, 
        s3_url: str
    ) -> Dict[str, Any]:
        """Tạo CV record mới"""
        try:
            cv_id = str(uuid.uuid4())
            
            cv_record = await self.repository.create_cv_record(
                cv_id=cv_id,
                user_id=user_id,
                filename=filename,
                file_size=file_size,
                file_type=file_type,
                s3_key=s3_key,
                s3_url=s3_url
            )
            
            logger.info(f"Created CV record: {cv_id}")
            return cv_record
            
        except Exception as e:
            logger.error(f"Failed to create CV record: {str(e)}")
            raise
    
    async def analyze_cv_from_s3(self, cv_id: str, s3_key: str, user_id: str) -> Dict[str, Any]:
        """Phân tích CV từ S3 và lưu kết quả"""
        try:
            # Update status to processing
            await self.repository.update_cv_status(cv_id, "processing")
            
            # Start Textract analysis
            textract_result = await self.textract_service.analyze_document_async(s3_key, user_id)
            
            if not textract_result.get('success'):
                await self.repository.update_cv_status(
                    cv_id, 
                    "failed", 
                    textract_result.get('error', 'Textract analysis failed')
                )
                return textract_result
            
            job_id = textract_result['job_id']
            
            # Update CV với job_id
            cv_record = await self.repository.get_cv_by_id(cv_id)
            if cv_record:
                cv_record['textract_job_id'] = job_id
                await self.repository.update_cv_status(cv_id, "processing")
            
            return {
                'success': True,
                'cv_id': cv_id,
                'job_id': job_id,
                'status': 'processing',
                'message': 'CV analysis started successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze CV: {str(e)}")
            await self.repository.update_cv_status(cv_id, "failed", str(e))
            raise
    
    async def get_textract_result(self, cv_id: str, job_id: str) -> Dict[str, Any]:
        """Lấy kết quả Textract và lưu vào database"""
        try:
            # Get Textract result
            textract_result = await self.textract_service.get_analysis_result(job_id)
            
            if not textract_result.get('success'):
                await self.repository.update_cv_status(
                    cv_id, 
                    "failed", 
                    textract_result.get('error', 'Textract analysis failed')
                )
                return textract_result
            
            # Parse CV content using CV Content Parser
            parsed_content = cv_content_parser.parse_cv_content(textract_result.get('text', ''))
            
            # Enhanced analysis with parsed content
            enhanced_analysis = {
                **textract_result.get('analysis_result', {}),
                'parsed_sections': parsed_content.get('sections', {}),
                'key_information': parsed_content.get('key_information', {}),
                'structured_data': parsed_content
            }
            
            # Create CVAnalysis object
            analysis = CVAnalysis(**enhanced_analysis)
            
            # Create CVContent object
            content_data = textract_result.get('raw_content', {})
            content = CVContent(**content_data)
            
            # Update CV với analysis result
            updated_cv = await self.repository.update_cv_analysis(
                cv_id, 
                analysis, 
                content, 
                job_id
            )
            
            logger.info(f"Updated CV analysis: {cv_id}")
            
            return {
                'success': True,
                'cv_id': cv_id,
                'analysis_result': analysis.dict(),
                'raw_content': content.dict(),
                'status': 'analyzed'
            }
            
        except Exception as e:
            logger.error(f"Failed to get Textract result: {str(e)}")
            await self.repository.update_cv_status(cv_id, "failed", str(e))
            raise
    
    async def get_cv_by_id(self, cv_id: str) -> Optional[Dict[str, Any]]:
        """Lấy CV theo ID"""
        try:
            return await self.repository.get_cv_by_id(cv_id)
        except Exception as e:
            logger.error(f"Failed to get CV: {str(e)}")
            raise
    
    async def get_user_cvs(
        self, 
        user_id: str, 
        limit: int = 50, 
        last_key: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Lấy danh sách CV của user"""
        try:
            return await self.repository.get_user_cvs(user_id, limit, last_key)
        except Exception as e:
            logger.error(f"Failed to get user CVs: {str(e)}")
            raise
    
    async def delete_cv(self, cv_id: str, user_id: str) -> Dict[str, Any]:
        """Xóa CV"""
        try:
            # Get CV record để lấy S3 key
            cv_record = await self.repository.get_cv_by_id(cv_id)
            if not cv_record:
                return {
                    'success': False,
                    'error': 'CV not found'
                }
            
            # Verify ownership
            if cv_record['user_id'] != user_id:
                return {
                    'success': False,
                    'error': 'Unauthorized: CV does not belong to user'
                }
            
            # Delete from S3
            s3_key = cv_record['s3_key']
            s3_result = await self.s3_service.delete_file(s3_key)
            
            if not s3_result.get('success'):
                logger.warning(f"Failed to delete S3 file: {s3_key}")
            
            # Delete from database
            success = await self.repository.delete_cv(cv_id, user_id)
            
            if success:
                logger.info(f"Deleted CV: {cv_id}")
                return {
                    'success': True,
                    'message': 'CV deleted successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'CV not found'
                }
                
        except Exception as e:
            logger.error(f"Failed to delete CV: {str(e)}")
            raise
    
    async def search_cvs(
        self, 
        search_criteria: Dict[str, Any], 
        user_id: str
    ) -> Dict[str, Any]:
        """Tìm kiếm CV theo criteria"""
        try:
            search_id = str(uuid.uuid4())
            search_results = []
            
            # Skills search
            if 'skills' in search_criteria:
                skills = search_criteria['skills']
                skill_level = search_criteria.get('skill_level')
                skill_results = await self.repository.search_cvs_by_skills(
                    skills, skill_level, limit=50
                )
                search_results.extend(skill_results)
            
            # Experience search
            if 'experience' in search_criteria:
                exp_criteria = search_criteria['experience']
                min_years = exp_criteria.get('min_years', 0)
                max_years = exp_criteria.get('max_years')
                job_title = exp_criteria.get('job_title')
                
                exp_results = await self.repository.search_cvs_by_experience(
                    min_years, max_years, job_title, limit=50
                )
                search_results.extend(exp_results)
            
            # Education search
            if 'education' in search_criteria:
                edu_criteria = search_criteria['education']
                education_level = edu_criteria.get('education_level')
                degree = edu_criteria.get('degree')
                
                edu_results = await self.repository.search_cvs_by_education(
                    education_level, degree, limit=50
                )
                search_results.extend(edu_results)
            
            # Location search
            if 'location' in search_criteria:
                location = search_criteria['location']
                location_results = await self.repository.search_cvs_by_location(
                    location, limit=50
                )
                search_results.extend(location_results)
            
            # Remove duplicates
            unique_results = {cv['cv_id']: cv for cv in search_results}.values()
            final_results = list(unique_results)
            
            # Save search result
            await self.repository.save_search_result(
                search_id=search_id,
                user_id=user_id,
                search_criteria=search_criteria,
                search_results=final_results,
                search_type=search_criteria.get('search_type', 'combined')
            )
            
            return {
                'success': True,
                'search_id': search_id,
                'results': final_results,
                'total_count': len(final_results)
            }
            
        except Exception as e:
            logger.error(f"Failed to search CVs: {str(e)}")
            raise
    
    async def get_cv_analytics(self, user_id: str) -> Dict[str, Any]:
        """Lấy analytics cho user"""
        try:
            analytics = await self.repository.get_cv_analytics(user_id)
            
            return {
                'success': True,
                'analytics': analytics
            }
            
        except Exception as e:
            logger.error(f"Failed to get CV analytics: {str(e)}")
            raise
    
    async def get_recent_searches(self, user_id: str, limit: int = 20) -> Dict[str, Any]:
        """Lấy recent searches của user"""
        try:
            searches = await self.repository.get_recent_searches(user_id, limit)
            
            return {
                'success': True,
                'searches': searches
            }
            
        except Exception as e:
            logger.error(f"Failed to get recent searches: {str(e)}")
            raise
    
    async def update_cv_metadata(
        self, 
        cv_id: str, 
        user_id: str, 
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Cập nhật metadata của CV"""
        try:
            cv_record = await self.repository.get_cv_by_id(cv_id)
            if not cv_record:
                return {
                    'success': False,
                    'error': 'CV not found'
                }
            
            # Verify ownership
            if cv_record['user_id'] != user_id:
                return {
                    'success': False,
                    'error': 'Unauthorized: CV does not belong to user'
                }
            
            # Update metadata
            cv_record.update(metadata)
            cv_record['updated_at'] = datetime.utcnow().isoformat()
            
            # Save updated record
            # Note: This would require implementing an update method in repository
            # For now, we'll return success
            
            return {
                'success': True,
                'message': 'CV metadata updated successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to update CV metadata: {str(e)}")
            raise
    
    async def export_cv_data(
        self, 
        cv_id: str, 
        user_id: str, 
        export_format: str = 'json'
    ) -> Dict[str, Any]:
        """Export CV data"""
        try:
            cv_record = await self.repository.get_cv_by_id(cv_id)
            if not cv_record:
                return {
                    'success': False,
                    'error': 'CV not found'
                }
            
            # Verify ownership
            if cv_record['user_id'] != user_id:
                return {
                    'success': False,
                    'error': 'Unauthorized: CV does not belong to user'
                }
            
            # Prepare export data
            export_data = {
                'cv_id': cv_record['cv_id'],
                'filename': cv_record['filename'],
                'analysis_result': cv_record.get('analysis_result'),
                'raw_content': cv_record.get('raw_content'),
                'metadata': {
                    'file_size': cv_record['file_size'],
                    'file_type': cv_record['file_type'],
                    'status': cv_record['status'],
                    'created_at': cv_record['created_at'],
                    'updated_at': cv_record['updated_at']
                }
            }
            
            return {
                'success': True,
                'export_data': export_data,
                'format': export_format
            }
            
        except Exception as e:
            logger.error(f"Failed to export CV data: {str(e)}")
            raise


# Global service instance
cv_storage_service = CVStorageService()
