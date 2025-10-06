from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from decimal import Decimal

from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute, UTCDateTimeAttribute, MapAttribute, ListAttribute, BooleanAttribute
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

from app.core.config import settings
from app.models.job import JobMatch, JobApplication
from app.utils.helpers import convert_decimals

logger = logging.getLogger(__name__)


class JobMatchIndex(GlobalSecondaryIndex):
    """Global Secondary Index for querying job matches by user_id"""
    class Meta:
        index_name = 'user_id-index'
        read_capacity_units = 5
        write_capacity_units = 5
        projection = AllProjection()
    
    user_id = UnicodeAttribute(hash_key=True)
    matched_at = UTCDateTimeAttribute(range_key=True)


class JobMatchModel(Model):
    """DynamoDB model for job matches"""
    class Meta:
        table_name = f"{settings.dynamodb_table_prefix}-job-matches"
        region = settings.aws_region
        host = settings.dynamodb_host
    
    # Primary key
    match_id = UnicodeAttribute(hash_key=True)
    
    # Attributes
    cv_id = UnicodeAttribute()
    job_id = UnicodeAttribute()
    user_id = UnicodeAttribute()
    match_score = NumberAttribute()
    skill_match_score = NumberAttribute()
    experience_match_score = NumberAttribute()
    location_match_score = NumberAttribute()
    salary_match_score = NumberAttribute()
    company_match_score = NumberAttribute()
    matching_criteria = MapAttribute()
    matched_at = UTCDateTimeAttribute()
    is_viewed = BooleanAttribute(default=False)
    is_applied = BooleanAttribute(default=False)
    
    # GSI
    user_id_index = JobMatchIndex()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return convert_decimals({
            'match_id': self.match_id,
            'cv_id': self.cv_id,
            'job_id': self.job_id,
            'user_id': self.user_id,
            'match_score': self.match_score,
            'skill_match_score': self.skill_match_score,
            'experience_match_score': self.experience_match_score,
            'location_match_score': self.location_match_score,
            'salary_match_score': self.salary_match_score,
            'company_match_score': self.company_match_score,
            'matching_criteria': self.matching_criteria,
            'matched_at': self.matched_at.isoformat() if self.matched_at else None,
            'is_viewed': self.is_viewed,
            'is_applied': self.is_applied
        })


class JobApplicationModel(Model):
    """DynamoDB model for job applications"""
    class Meta:
        table_name = f"{settings.dynamodb_table_prefix}-job-applications"
        region = settings.aws_region
        host = settings.dynamodb_host
    
    # Primary key
    application_id = UnicodeAttribute(hash_key=True)
    
    # Attributes
    job_id = UnicodeAttribute()
    cv_id = UnicodeAttribute()
    user_id = UnicodeAttribute()
    cover_letter = UnicodeAttribute(null=True)
    application_status = UnicodeAttribute()
    applied_at = UTCDateTimeAttribute()
    last_updated = UTCDateTimeAttribute()
    recruiter_notes = UnicodeAttribute(null=True)
    interview_scheduled = UTCDateTimeAttribute(null=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return convert_decimals({
            'application_id': self.application_id,
            'job_id': self.job_id,
            'cv_id': self.cv_id,
            'user_id': self.user_id,
            'cover_letter': self.cover_letter,
            'application_status': self.application_status,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'recruiter_notes': self.recruiter_notes,
            'interview_scheduled': self.interview_scheduled.isoformat() if self.interview_scheduled else None
        })


class JobMatchRepository:
    """Repository for job match data operations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_job_match(self, job_match: JobMatch) -> bool:
        """
        Create a new job match record
        
        Args:
            job_match: JobMatch object to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Creating job match: {job_match.match_id}")
            
            match_model = JobMatchModel(
                match_id=job_match.match_id,
                cv_id=job_match.cv_id,
                job_id=job_match.job_id,
                user_id=job_match.user_id,
                match_score=Decimal(str(job_match.match_score)),
                skill_match_score=Decimal(str(job_match.skill_match_score)),
                experience_match_score=Decimal(str(job_match.experience_match_score)),
                location_match_score=Decimal(str(job_match.location_match_score)),
                salary_match_score=Decimal(str(job_match.salary_match_score)),
                company_match_score=Decimal(str(job_match.company_match_score)),
                matching_criteria=job_match.matching_criteria,
                matched_at=job_match.matched_at,
                is_viewed=job_match.is_viewed,
                is_applied=job_match.is_applied
            )
            
            match_model.save()
            self.logger.info(f"Job match created successfully: {job_match.match_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating job match: {e}")
            return False
    
    def get_job_matches_by_cv(self, cv_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get job matches for a specific CV
        
        Args:
            cv_id: CV ID to get matches for
            limit: Maximum number of matches to return
            offset: Pagination offset
            
        Returns:
            List of job match dictionaries
        """
        try:
            self.logger.info(f"Getting job matches for CV: {cv_id}")
            
            # Query by CV ID (this would need a GSI on cv_id for better performance)
            matches = []
            for match in JobMatchModel.scan():
                if match.cv_id == cv_id:
                    matches.append(match.to_dict())
            
            # Apply pagination
            start_idx = offset
            end_idx = offset + limit
            paginated_matches = matches[start_idx:end_idx]
            
            self.logger.info(f"Found {len(paginated_matches)} matches for CV {cv_id}")
            return paginated_matches
            
        except Exception as e:
            self.logger.error(f"Error getting job matches for CV {cv_id}: {e}")
            return []
    
    def get_job_matches_by_user(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get job matches for a specific user
        
        Args:
            user_id: User ID to get matches for
            limit: Maximum number of matches to return
            offset: Pagination offset
            
        Returns:
            List of job match dictionaries
        """
        try:
            self.logger.info(f"Getting job matches for user: {user_id}")
            
            # Query using GSI
            matches = []
            for match in JobMatchModel.user_id_index.query(user_id, limit=limit):
                matches.append(match.to_dict())
            
            self.logger.info(f"Found {len(matches)} matches for user {user_id}")
            return matches
            
        except Exception as e:
            self.logger.error(f"Error getting job matches for user {user_id}: {e}")
            return []
    
    def update_match_status(self, match_id: str, is_viewed: bool = None, is_applied: bool = None) -> bool:
        """
        Update job match status
        
        Args:
            match_id: Match ID to update
            is_viewed: Whether match has been viewed
            is_applied: Whether user has applied to the job
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Updating match status: {match_id}")
            
            match = JobMatchModel.get(match_id)
            
            if is_viewed is not None:
                match.is_viewed = is_viewed
            if is_applied is not None:
                match.is_applied = is_applied
            
            match.save()
            self.logger.info(f"Match status updated successfully: {match_id}")
            return True
            
        except JobMatchModel.DoesNotExist:
            self.logger.warning(f"Job match not found: {match_id}")
            return False
        except Exception as e:
            self.logger.error(f"Error updating match status: {e}")
            return False
    
    def get_match_history(self, cv_id: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        Get match history for a CV
        
        Args:
            cv_id: CV ID to get history for
            limit: Maximum number of records to return
            offset: Pagination offset
            
        Returns:
            Dictionary containing history data and metadata
        """
        try:
            self.logger.info(f"Getting match history for CV: {cv_id}")
            
            matches = self.get_job_matches_by_cv(cv_id, limit, offset)
            
            # Calculate summary statistics
            total_searches = len(matches)
            avg_score = sum(match['match_score'] for match in matches) / total_searches if total_searches > 0 else 0
            
            # Get most common job types (would need job data for this)
            most_common_job_types = []
            
            history_data = {
                'cv_id': cv_id,
                'total_records': total_searches,
                'history': matches,
                'pagination': {
                    'limit': limit,
                    'offset': offset,
                    'has_more': len(matches) == limit
                },
                'summary': {
                    'total_searches': total_searches,
                    'avg_matches_per_search': avg_score,
                    'most_common_job_types': most_common_job_types,
                    'search_frequency': 'daily'
                }
            }
            
            self.logger.info(f"Retrieved match history for CV {cv_id}: {total_searches} records")
            return history_data
            
        except Exception as e:
            self.logger.error(f"Error getting match history for CV {cv_id}: {e}")
            return {
                'cv_id': cv_id,
                'total_records': 0,
                'history': [],
                'pagination': {'limit': limit, 'offset': offset, 'has_more': False},
                'summary': {'total_searches': 0, 'avg_matches_per_search': 0, 'most_common_job_types': [], 'search_frequency': 'daily'}
            }
    
    def create_job_application(self, application: JobApplication) -> bool:
        """
        Create a new job application
        
        Args:
            application: JobApplication object to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Creating job application: {application.application_id}")
            
            app_model = JobApplicationModel(
                application_id=application.application_id,
                job_id=application.job_id,
                cv_id=application.cv_id,
                user_id=application.user_id,
                cover_letter=application.cover_letter,
                application_status=application.application_status,
                applied_at=application.applied_at,
                last_updated=application.last_updated,
                recruiter_notes=application.recruiter_notes,
                interview_scheduled=application.interview_scheduled
            )
            
            app_model.save()
            self.logger.info(f"Job application created successfully: {application.application_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating job application: {e}")
            return False
    
    def get_applications_by_user(self, user_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get job applications for a specific user
        
        Args:
            user_id: User ID to get applications for
            limit: Maximum number of applications to return
            offset: Pagination offset
            
        Returns:
            List of job application dictionaries
        """
        try:
            self.logger.info(f"Getting job applications for user: {user_id}")
            
            applications = []
            for app in JobApplicationModel.scan():
                if app.user_id == user_id:
                    applications.append(app.to_dict())
            
            # Apply pagination
            start_idx = offset
            end_idx = offset + limit
            paginated_applications = applications[start_idx:end_idx]
            
            self.logger.info(f"Found {len(paginated_applications)} applications for user {user_id}")
            return paginated_applications
            
        except Exception as e:
            self.logger.error(f"Error getting job applications for user {user_id}: {e}")
            return []
    
    def cleanup_old_matches(self, days_old: int = 90) -> int:
        """
        Clean up old job matches based on data retention policy
        
        Args:
            days_old: Number of days after which matches should be deleted
            
        Returns:
            Number of matches deleted
        """
        try:
            self.logger.info(f"Cleaning up job matches older than {days_old} days")
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            deleted_count = 0
            
            for match in JobMatchModel.scan():
                if match.matched_at and match.matched_at < cutoff_date:
                    match.delete()
                    deleted_count += 1
            
            self.logger.info(f"Cleaned up {deleted_count} old job matches")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old matches: {e}")
            return 0


# Global instance
job_match_repository = JobMatchRepository()
