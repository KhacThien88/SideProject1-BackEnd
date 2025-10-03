"""
Repository layer cho CV storage operations
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from app.models.cv_storage import CVTable, CVSearchTable, CVAnalyticsTable
from app.models.cv import CVAnalysis, CVContent
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CVStorageRepository:
    """Repository cho CV storage operations"""
    
    def __init__(self):
        self.cv_table = CVTable
        self.search_table = CVSearchTable
        self.analytics_table = CVAnalyticsTable
    
    async def create_cv_record(
        self, 
        cv_id: str, 
        user_id: str, 
        filename: str, 
        file_size: int, 
        file_type: str, 
        s3_key: str, 
        s3_url: str
    ) -> Dict[str, Any]:
        """Tạo CV record mới"""
        try:
            cv_record = CVTable(
                cv_id=cv_id,
                user_id=user_id,
                filename=filename,
                file_size=file_size,
                file_type=file_type,
                s3_key=s3_key,
                s3_url=s3_url,
                status="uploaded"
            )
            cv_record.save()
            
            logger.info(f"Created CV record: {cv_id} for user: {user_id}")
            return cv_record.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to create CV record: {str(e)}")
            raise
    
    async def get_cv_by_id(self, cv_id: str) -> Optional[Dict[str, Any]]:
        """Lấy CV theo ID"""
        try:
            cv_record = CVTable.get(cv_id)
            return cv_record.to_dict()
        except CVTable.DoesNotExist:
            logger.warning(f"CV not found: {cv_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get CV: {str(e)}")
            raise
    
    async def get_user_cvs(self, user_id: str, limit: int = 50, last_key: Optional[str] = None) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Lấy danh sách CV của user"""
        try:
            query_kwargs = {
                'user_id': user_id,
                'limit': limit,
                'scan_index_forward': False  # Sort by created_at desc
            }
            
            if last_key:
                query_kwargs['last_evaluated_key'] = last_key
            
            response = CVTable.user_id_index.query(**query_kwargs)
            
            cvs = [item.to_dict() for item in response]
            next_key = response.last_evaluated_key.get('cv_id') if response.last_evaluated_key else None
            
            return cvs, next_key
            
        except Exception as e:
            logger.error(f"Failed to get user CVs: {str(e)}")
            raise
    
    async def update_cv_analysis(
        self, 
        cv_id: str, 
        analysis: CVAnalysis, 
        content: CVContent, 
        textract_job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cập nhật CV với analysis result"""
        try:
            cv_record = CVTable.get(cv_id)
            cv_record.update_analysis(analysis, content, textract_job_id)
            cv_record.save()
            
            logger.info(f"Updated CV analysis: {cv_id}")
            return cv_record.to_dict()
            
        except CVTable.DoesNotExist:
            logger.warning(f"CV not found: {cv_id}")
            raise ValueError(f"CV not found: {cv_id}")
        except Exception as e:
            logger.error(f"Failed to update CV analysis: {str(e)}")
            raise
    
    async def update_cv_status(self, cv_id: str, status: str, error_message: Optional[str] = None) -> Dict[str, Any]:
        """Cập nhật status của CV"""
        try:
            cv_record = CVTable.get(cv_id)
            cv_record.status = status
            cv_record.updated_at = datetime.utcnow()
            
            if error_message:
                cv_record.analysis_result = {"error": error_message}
            
            cv_record.save()
            
            logger.info(f"Updated CV status: {cv_id} -> {status}")
            return cv_record.to_dict()
            
        except CVTable.DoesNotExist:
            logger.warning(f"CV not found: {cv_id}")
            raise ValueError(f"CV not found: {cv_id}")
        except Exception as e:
            logger.error(f"Failed to update CV status: {str(e)}")
            raise
    
    async def delete_cv(self, cv_id: str, user_id: str) -> bool:
        """Xóa CV"""
        try:
            cv_record = CVTable.get(cv_id)
            
            # Verify ownership
            if cv_record.user_id != user_id:
                raise ValueError("Unauthorized: CV does not belong to user")
            
            cv_record.delete()
            
            logger.info(f"Deleted CV: {cv_id}")
            return True
            
        except CVTable.DoesNotExist:
            logger.warning(f"CV not found: {cv_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete CV: {str(e)}")
            raise
    
    async def search_cvs_by_skills(
        self, 
        skills: List[str], 
        skill_level: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Tìm CV theo skills"""
        try:
            cvs = []
            
            for skill in skills:
                query_kwargs = {
                    'skill_name': skill,
                    'limit': limit
                }
                
                if skill_level:
                    query_kwargs['skill_level'] = skill_level
                
                response = CVTable.skills_index.query(**query_kwargs)
                cvs.extend([item.to_dict() for item in response])
            
            # Remove duplicates
            unique_cvs = {cv['cv_id']: cv for cv in cvs}.values()
            
            return list(unique_cvs)
            
        except Exception as e:
            logger.error(f"Failed to search CVs by skills: {str(e)}")
            raise
    
    async def search_cvs_by_experience(
        self, 
        min_years: int, 
        max_years: Optional[int] = None,
        job_title: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Tìm CV theo experience"""
        try:
            cvs = []
            
            # Query by experience years
            for years in range(min_years, (max_years or min_years + 1) + 1):
                query_kwargs = {
                    'experience_years': years,
                    'limit': limit
                }
                
                if job_title:
                    query_kwargs['job_title'] = job_title
                
                response = CVTable.experience_index.query(**query_kwargs)
                cvs.extend([item.to_dict() for item in response])
            
            # Remove duplicates
            unique_cvs = {cv['cv_id']: cv for cv in cvs}.values()
            
            return list(unique_cvs)
            
        except Exception as e:
            logger.error(f"Failed to search CVs by experience: {str(e)}")
            raise
    
    async def search_cvs_by_education(
        self, 
        education_level: str, 
        degree: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Tìm CV theo education"""
        try:
            query_kwargs = {
                'education_level': education_level,
                'limit': limit
            }
            
            if degree:
                query_kwargs['degree'] = degree
            
            response = CVTable.education_index.query(**query_kwargs)
            cvs = [item.to_dict() for item in response]
            
            return cvs
            
        except Exception as e:
            logger.error(f"Failed to search CVs by education: {str(e)}")
            raise
    
    async def search_cvs_by_location(
        self, 
        location: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Tìm CV theo location"""
        try:
            response = CVTable.location_index.query(
                location=location,
                limit=limit
            )
            cvs = [item.to_dict() for item in response]
            
            return cvs
            
        except Exception as e:
            logger.error(f"Failed to search CVs by location: {str(e)}")
            raise
    
    async def get_cv_analytics(self, user_id: str) -> Dict[str, Any]:
        """Lấy analytics cho user"""
        try:
            # Get user CVs
            user_cvs, _ = await self.get_user_cvs(user_id, limit=1000)
            
            if not user_cvs:
                return {
                    'total_cvs': 0,
                    'analyzed_cvs': 0,
                    'average_completeness': 0.0,
                    'average_quality': 0.0,
                    'skill_distribution': {},
                    'experience_distribution': {},
                    'education_distribution': {}
                }
            
            # Calculate analytics
            total_cvs = len(user_cvs)
            analyzed_cvs = len([cv for cv in user_cvs if cv['status'] == 'analyzed'])
            
            completeness_scores = []
            quality_scores = []
            skills = {}
            experience_years = {}
            education_levels = {}
            
            for cv in user_cvs:
                if cv['status'] == 'analyzed' and cv['analysis_result']:
                    analysis = cv['analysis_result']
                    
                    # Scores
                    if 'completeness_score' in analysis:
                        completeness_scores.append(analysis['completeness_score'])
                    if 'quality_score' in analysis:
                        quality_scores.append(analysis['quality_score'])
                    
                    # Skills
                    if 'skills' in analysis:
                        for skill in analysis['skills']:
                            skill_name = skill.get('name', 'Unknown')
                            skills[skill_name] = skills.get(skill_name, 0) + 1
                    
                    # Experience
                    if 'experience_years' in cv and cv['experience_years']:
                        years = cv['experience_years']
                        experience_years[years] = experience_years.get(years, 0) + 1
                    
                    # Education
                    if 'education_level' in cv and cv['education_level']:
                        level = cv['education_level']
                        education_levels[level] = education_levels.get(level, 0) + 1
            
            return {
                'total_cvs': total_cvs,
                'analyzed_cvs': analyzed_cvs,
                'average_completeness': sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0.0,
                'average_quality': sum(quality_scores) / len(quality_scores) if quality_scores else 0.0,
                'skill_distribution': skills,
                'experience_distribution': experience_years,
                'education_distribution': education_levels
            }
            
        except Exception as e:
            logger.error(f"Failed to get CV analytics: {str(e)}")
            raise
    
    async def save_search_result(
        self, 
        search_id: str, 
        user_id: str, 
        search_criteria: Dict[str, Any], 
        search_results: List[Dict[str, Any]], 
        search_type: str
    ) -> Dict[str, Any]:
        """Lưu search result"""
        try:
            search_record = CVSearchTable(
                search_id=search_id,
                user_id=user_id,
                search_criteria=search_criteria,
                search_results=search_results,
                search_type=search_type,
                result_count=len(search_results)
            )
            search_record.save()
            
            logger.info(f"Saved search result: {search_id}")
            return search_record.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to save search result: {str(e)}")
            raise
    
    async def get_recent_searches(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Lấy recent searches của user"""
        try:
            # This would require a GSI on user_id and created_at
            # For now, we'll use scan with filter
            response = CVSearchTable.scan(
                CVSearchTable.user_id == user_id,
                limit=limit
            )
            
            searches = [item.to_dict() for item in response]
            searches.sort(key=lambda x: x['created_at'], reverse=True)
            
            return searches
            
        except Exception as e:
            logger.error(f"Failed to get recent searches: {str(e)}")
            raise
