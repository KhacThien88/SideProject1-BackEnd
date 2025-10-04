"""
DynamoDB models cho CV data storage
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, UTCDateTimeAttribute, 
    ListAttribute, MapAttribute, BooleanAttribute, JSONAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from app.core.config import settings
from app.models.cv import CVAnalysis, CVContent


class CVStorageIndex(GlobalSecondaryIndex):
    """GSI cho CV storage queries"""
    class Meta:
        index_name = 'user_id-index'
        read_capacity_units = 5
        write_capacity_units = 5
        projection = AllProjection()
    
    user_id = UnicodeAttribute(hash_key=True)
    created_at = UTCDateTimeAttribute(range_key=True)


class CVSkillsIndex(GlobalSecondaryIndex):
    """GSI cho skills-based queries"""
    class Meta:
        index_name = 'skills-index'
        read_capacity_units = 5
        write_capacity_units = 5
        projection = AllProjection()
    
    skill_name = UnicodeAttribute(hash_key=True)
    skill_level = UnicodeAttribute(range_key=True)


class CVExperienceIndex(GlobalSecondaryIndex):
    """GSI cho experience-based queries"""
    class Meta:
        index_name = 'experience-index'
        read_capacity_units = 5
        write_capacity_units = 5
        projection = AllProjection()
    
    experience_years = NumberAttribute(hash_key=True)
    job_title = UnicodeAttribute(range_key=True)


class CVEducationIndex(GlobalSecondaryIndex):
    """GSI cho education-based queries"""
    class Meta:
        index_name = 'education-index'
        read_capacity_units = 5
        write_capacity_units = 5
        projection = AllProjection()
    
    education_level = UnicodeAttribute(hash_key=True)
    degree = UnicodeAttribute(range_key=True)


class CVLocationIndex(GlobalSecondaryIndex):
    """GSI cho location-based queries"""
    class Meta:
        index_name = 'location-index'
        read_capacity_units = 5
        write_capacity_units = 5
        projection = AllProjection()
    
    location = UnicodeAttribute(hash_key=True)
    created_at = UTCDateTimeAttribute(range_key=True)


class CVTable(Model):
    """DynamoDB table cho CV storage"""
    
    class Meta:
        table_name = settings.cv_storage_table_name
        region = settings.aws_region
        aws_access_key_id = settings.aws_access_key_id
        aws_secret_access_key = settings.aws_secret_access_key
        read_capacity_units = 10
        write_capacity_units = 10
    
    # Primary key
    cv_id = UnicodeAttribute(hash_key=True)
    user_id = UnicodeAttribute()
    
    # File information
    filename = UnicodeAttribute()
    file_size = NumberAttribute()
    file_type = UnicodeAttribute()
    s3_key = UnicodeAttribute()
    s3_url = UnicodeAttribute()
    
    # Analysis data
    analysis_result = JSONAttribute()
    raw_content = JSONAttribute()
    
    # Metadata
    status = UnicodeAttribute(default="uploaded")  # uploaded, processing, analyzed, failed
    textract_job_id = UnicodeAttribute(null=True)
    analysis_timestamp = UTCDateTimeAttribute(null=True)
    created_at = UTCDateTimeAttribute(default=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default=datetime.utcnow)
    
    # Searchable fields for GSI
    skill_name = UnicodeAttribute(null=True)
    skill_level = UnicodeAttribute(null=True)
    experience_years = NumberAttribute(null=True)
    job_title = UnicodeAttribute(null=True)
    education_level = UnicodeAttribute(null=True)
    degree = UnicodeAttribute(null=True)
    location = UnicodeAttribute(null=True)
    
    # Indexes
    user_id_index = CVStorageIndex()
    skills_index = CVSkillsIndex()
    experience_index = CVExperienceIndex()
    education_index = CVEducationIndex()
    location_index = CVLocationIndex()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'cv_id': self.cv_id,
            'user_id': self.user_id,
            'filename': self.filename,
            'file_size': self.file_size,
            'file_type': self.file_type,
            's3_key': self.s3_key,
            's3_url': self.s3_url,
            'analysis_result': self.analysis_result,
            'raw_content': self.raw_content,
            'status': self.status,
            'textract_job_id': self.textract_job_id,
            'analysis_timestamp': self.analysis_timestamp.isoformat() if self.analysis_timestamp else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'skill_name': self.skill_name,
            'skill_level': self.skill_level,
            'experience_years': self.experience_years,
            'job_title': self.job_title,
            'education_level': self.education_level,
            'degree': self.degree,
            'location': self.location
        }
    
    def update_analysis(self, analysis: CVAnalysis, content: CVContent, textract_job_id: Optional[str] = None):
        """Update CV với analysis result"""
        self.analysis_result = analysis.dict()
        self.raw_content = content.dict()
        self.status = "analyzed"
        self.textract_job_id = textract_job_id
        self.analysis_timestamp = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        # Update searchable fields
        if analysis.personal_info and analysis.personal_info.contact_info:
            self.location = analysis.personal_info.contact_info.location
        
        if analysis.work_experience:
            # Get total experience years
            total_years = 0
            for exp in analysis.work_experience:
                if exp.date_range and exp.date_range.start_date and exp.date_range.end_date:
                    years = (exp.date_range.end_date - exp.date_range.start_date).days / 365.25
                    total_years += years
            self.experience_years = int(total_years)
            
            # Get latest job title
            if analysis.work_experience:
                latest_exp = analysis.work_experience[0]
                self.job_title = latest_exp.title
        
        if analysis.education:
            # Get highest education level
            highest_education = analysis.education[0]
            self.education_level = highest_education.degree
            self.degree = highest_education.degree
        
        if analysis.skills:
            # Get primary skill
            primary_skill = analysis.skills[0]
            self.skill_name = primary_skill.name
            self.skill_level = primary_skill.level


class CVSearchTable(Model):
    """DynamoDB table cho CV search và analytics"""
    
    class Meta:
        table_name = settings.cv_search_table_name
        region = settings.aws_region
        aws_access_key_id = settings.aws_access_key_id
        aws_secret_access_key = settings.aws_secret_access_key
        read_capacity_units = 5
        write_capacity_units = 5
    
    # Primary key
    search_id = UnicodeAttribute(hash_key=True)
    user_id = UnicodeAttribute()
    
    # Search criteria
    search_criteria = JSONAttribute()
    search_results = JSONAttribute()
    
    # Metadata
    created_at = UTCDateTimeAttribute(default=datetime.utcnow)
    result_count = NumberAttribute(default=0)
    search_type = UnicodeAttribute()  # skills, experience, education, location, combined


class CVAnalyticsTable(Model):
    """DynamoDB table cho CV analytics và statistics"""
    
    class Meta:
        table_name = settings.cv_analytics_table_name
        region = settings.aws_region
        aws_access_key_id = settings.aws_access_key_id
        aws_secret_access_key = settings.aws_secret_access_key
        read_capacity_units = 5
        write_capacity_units = 5
    
    # Primary key
    analytics_id = UnicodeAttribute(hash_key=True)
    user_id = UnicodeAttribute()
    
    # Analytics data
    total_cvs = NumberAttribute(default=0)
    analyzed_cvs = NumberAttribute(default=0)
    average_completeness = NumberAttribute(default=0.0)
    average_quality = NumberAttribute(default=0.0)
    skill_distribution = JSONAttribute()
    experience_distribution = JSONAttribute()
    education_distribution = JSONAttribute()
    
    # Metadata
    created_at = UTCDateTimeAttribute(default=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default=datetime.utcnow)
