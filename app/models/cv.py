"""
CV Analysis Models
Comprehensive Pydantic models cho CV data structure với validation và serialization
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator, root_validator
import re


# Quality score calculation constants
QUALITY_SCORE_CONTACT_INFO = 20
QUALITY_SCORE_PER_WORK_EXPERIENCE = 10
QUALITY_SCORE_WORK_EXPERIENCE_MAX = 40
QUALITY_SCORE_PER_SKILL = 2
QUALITY_SCORE_SKILLS_MAX = 20
QUALITY_SCORE_PER_EDUCATION = 10
QUALITY_SCORE_EDUCATION_MAX = 20
QUALITY_SCORE_MAX = 100

# Validation constants
MIN_RAW_TEXT_LENGTH = 10


class DocumentType(str, Enum):
    """Document types"""
    CV = "cv"
    RESUME = "resume"
    COVER_LETTER = "cover_letter"
    PORTFOLIO = "portfolio"


class ExperienceLevel(str, Enum):
    """Experience levels"""
    ENTRY = "entry"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"


class EducationLevel(str, Enum):
    """Education levels"""
    HIGH_SCHOOL = "high_school"
    ASSOCIATE = "associate"
    BACHELOR = "bachelor"
    MASTER = "master"
    DOCTORATE = "doctorate"
    CERTIFICATE = "certificate"


class SkillCategory(str, Enum):
    """Skill categories"""
    TECHNICAL = "technical"
    SOFT = "soft"
    LANGUAGE = "language"
    CERTIFICATION = "certification"
    TOOL = "tool"


class ContactInfo(BaseModel):
    """Contact information model"""
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number") 
    address: Optional[str] = Field(None, description="Physical address")
    city: Optional[str] = Field(None, description="City")
    country: Optional[str] = Field(None, description="Country")
    linkedin: Optional[str] = Field(None, description="LinkedIn profile")
    github: Optional[str] = Field(None, description="GitHub profile")
    website: Optional[str] = Field(None, description="Personal website")
    
    @validator('email')
    def validate_email(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        if v:
            digits = re.sub(r'\D', '', v)
            if len(digits) < 7 or len(digits) > 15:
                raise ValueError('Phone number must be between 7 and 15 digits')
        return v


class PersonalInfo(BaseModel):
    """Personal information model"""
    full_name: Optional[str] = Field(None, description="Full name")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    title: Optional[str] = Field(None, description="Professional title")
    summary: Optional[str] = Field(None, description="Professional summary")
    contact: Optional[ContactInfo] = Field(None, description="Contact information")
    date_of_birth: Optional[date] = Field(None, description="Date of birth")
    nationality: Optional[str] = Field(None, description="Nationality")
    
    @validator('full_name')
    def validate_full_name(cls, v):
        if v and len(v.strip()) < 2:
            raise ValueError('Full name must be at least 2 characters')
        return v.strip() if v else v


class Skill(BaseModel):
    """Skill model"""
    name: str = Field(..., description="Skill name")
    category: SkillCategory = Field(..., description="Skill category")
    level: Optional[str] = Field(None, description="Skill level (beginner, intermediate, advanced)")
    years_experience: Optional[float] = Field(None, ge=0, le=50, description="Years of experience")
    confidence: Optional[float] = Field(None, ge=0, le=100, description="Confidence level (0-100)")
    keywords: Optional[List[str]] = Field(None, description="Related keywords")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Skill name must be at least 2 characters')
        return v.strip()


class Education(BaseModel):
    """Education model"""
    institution: str = Field(..., description="Institution name")
    degree: Optional[str] = Field(None, description="Degree name")
    field_of_study: Optional[str] = Field(None, description="Field of study")
    level: EducationLevel = Field(..., description="Education level")
    start_date: Optional[date] = Field(None, description="Start date")
    end_date: Optional[date] = Field(None, description="End date")
    gpa: Optional[float] = Field(None, ge=0, le=4, description="GPA")
    location: Optional[str] = Field(None, description="Location")
    description: Optional[str] = Field(None, description="Additional description")
    is_current: bool = Field(False, description="Currently studying")
    
    @validator('institution')
    def validate_institution(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Institution name must be at least 2 characters')
        return v.strip()
    
    @root_validator(skip_on_failure=True)
    def validate_dates(cls, values):
        start_date = values.get('start_date')
        end_date = values.get('end_date')
        
        if start_date and end_date and not values.get('is_current', False):
            if start_date > end_date:
                raise ValueError('Start date must be before end date')
        
        return values


class WorkExperience(BaseModel):
    """Work experience model"""
    company: str = Field(..., description="Company name")
    position: str = Field(..., description="Job position")
    department: Optional[str] = Field(None, description="Department")
    start_date: Optional[date] = Field(None, description="Start date")
    end_date: Optional[date] = Field(None, description="End date")
    is_current: bool = Field(False, description="Currently working")
    location: Optional[str] = Field(None, description="Work location")
    description: Optional[str] = Field(None, description="Job description")
    achievements: Optional[List[str]] = Field(None, description="Key achievements")
    skills_used: Optional[List[str]] = Field(None, description="Skills used")
    team_size: Optional[int] = Field(None, ge=1, description="Team size")
    reporting_to: Optional[str] = Field(None, description="Reporting manager")
    
    @validator('company')
    def validate_company(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Company name must be at least 2 characters')
        return v.strip()
    
    @validator('position')
    def validate_position(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Position must be at least 2 characters')
        return v.strip()
    
    @root_validator(skip_on_failure=True)
    def validate_dates(cls, values):
        start_date = values.get('start_date')
        end_date = values.get('end_date')
        
        if start_date and end_date and not values.get('is_current', False):
            if start_date > end_date:
                raise ValueError('Start date must be before end date')
        
        return values


class Project(BaseModel):
    """Project model"""
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    start_date: Optional[date] = Field(None, description="Start date")
    end_date: Optional[date] = Field(None, description="End date")
    is_current: bool = Field(False, description="Currently working on")
    technologies: Optional[List[str]] = Field(None, description="Technologies used")
    team_size: Optional[int] = Field(None, ge=1, description="Team size")
    role: Optional[str] = Field(None, description="Role in project")
    url: Optional[str] = Field(None, description="Project URL")
    achievements: Optional[List[str]] = Field(None, description="Key achievements")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Project name must be at least 2 characters')
        return v.strip()


class Certification(BaseModel):
    """Certification model"""
    name: str = Field(..., description="Certification name")
    issuer: str = Field(..., description="Issuing organization")
    issue_date: Optional[date] = Field(None, description="Issue date")
    expiry_date: Optional[date] = Field(None, description="Expiry date")
    credential_id: Optional[str] = Field(None, description="Credential ID")
    url: Optional[str] = Field(None, description="Verification URL")
    is_current: bool = Field(True, description="Currently valid")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Certification name must be at least 2 characters')
        return v.strip()
    
    @validator('issuer')
    def validate_issuer(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Issuer name must be at least 2 characters')
        return v.strip()


class Language(BaseModel):
    """Language model"""
    name: str = Field(..., description="Language name")
    proficiency: str = Field(..., description="Proficiency level")
    is_native: bool = Field(False, description="Native language")
    certifications: Optional[List[str]] = Field(None, description="Language certifications")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Language name must be at least 2 characters')
        return v.strip()
    
    @validator('proficiency')
    def validate_proficiency(cls, v):
        valid_levels = ['beginner', 'elementary', 'intermediate', 'upper-intermediate', 'advanced', 'native', 'fluent']
        if v.lower() not in valid_levels:
            raise ValueError(f'Proficiency must be one of: {", ".join(valid_levels)}')
        return v.lower()


class CVAnalysis(BaseModel):
    """Main CV analysis model"""
    # Basic information
    document_type: DocumentType = Field(..., description="Type of document")
    personal_info: Optional[PersonalInfo] = Field(None, description="Personal information")
    
    # Professional information
    experience_level: Optional[ExperienceLevel] = Field(None, description="Overall experience level")
    total_years_experience: Optional[float] = Field(None, ge=0, le=50, description="Total years of experience")
    work_experience: Optional[List[WorkExperience]] = Field(None, description="Work experience")
    
    # Education
    education: Optional[List[Education]] = Field(None, description="Education background")
    highest_education: Optional[EducationLevel] = Field(None, description="Highest education level")
    
    # Skills and competencies
    skills: Optional[List[Skill]] = Field(None, description="Skills")
    projects: Optional[List[Project]] = Field(None, description="Projects")
    certifications: Optional[List[Certification]] = Field(None, description="Certifications")
    languages: Optional[List[Language]] = Field(None, description="Languages")
    
    # Analysis metadata
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")
    confidence_score: Optional[float] = Field(None, ge=0, le=100, description="Overall confidence score")
    quality_score: Optional[float] = Field(None, ge=0, le=100, description="Document quality score")
    completeness_score: Optional[float] = Field(None, ge=0, le=100, description="Information completeness score")
    
    # Raw data
    raw_text: Optional[str] = Field(None, description="Raw extracted text")
    sections: Optional[Dict[str, str]] = Field(None, description="Extracted sections")
    key_information: Optional[Dict[str, Any]] = Field(None, description="Key information extracted")
    
    # File information
    file_id: Optional[str] = Field(None, description="Original file ID")
    s3_key: Optional[str] = Field(None, description="S3 key of original file")
    file_type: Optional[str] = Field(None, description="Original file type")
    file_size: Optional[int] = Field(None, description="Original file size")
    
    @validator('work_experience')
    def validate_work_experience(cls, v):
        if v:
            # Sort by start date (most recent first)
            return sorted(v, key=lambda x: x.start_date or date.min, reverse=True)
        return v
    
    @validator('education')
    def validate_education(cls, v):
        if v:
            # Sort by end date (most recent first)
            return sorted(v, key=lambda x: x.end_date or date.min, reverse=True)
        return v
    
    @root_validator(skip_on_failure=True)
    def calculate_scores(cls, values):
        """Calculate completeness và quality scores based on available data"""
        try:
            # Calculate completeness score
            required_fields = ['personal_info', 'work_experience', 'education', 'skills']
            completeness = sum(1 for field in required_fields if values.get(field))
            values['completeness_score'] = (completeness / len(required_fields)) * 100
            
            # Calculate quality score based on data richness
            quality = 0
            if values.get('personal_info') and values.get('personal_info').contact:
                quality += QUALITY_SCORE_CONTACT_INFO
            if work_exp := values.get('work_experience'):
                quality += min(
                    len(work_exp) * QUALITY_SCORE_PER_WORK_EXPERIENCE,
                    QUALITY_SCORE_WORK_EXPERIENCE_MAX
                )
            if skills := values.get('skills'):
                quality += min(
                    len(skills) * QUALITY_SCORE_PER_SKILL,
                    QUALITY_SCORE_SKILLS_MAX
                )
            if education := values.get('education'):
                quality += min(
                    len(education) * QUALITY_SCORE_PER_EDUCATION,
                    QUALITY_SCORE_EDUCATION_MAX
                )
            
            values['quality_score'] = min(quality, QUALITY_SCORE_MAX)
            
        except Exception:
            values['completeness_score'] = 0
            values['quality_score'] = 0
        
        return values


class CVUpload(BaseModel):
    """CV upload model"""
    file_id: str = Field(..., description="Unique file ID")
    user_id: str = Field(..., description="User ID")
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="File type")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    s3_key: str = Field(..., description="S3 key")
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Upload timestamp")
    status: str = Field("pending", description="Processing status")
    analysis_id: Optional[str] = Field(None, description="Analysis ID")
    
    @validator('filename')
    def validate_filename(cls, v):
        if not v or len(v.strip()) < 1:
            raise ValueError('Filename cannot be empty')
        return v.strip()


class CVContent(BaseModel):
    """CV content model for raw text storage"""
    file_id: str = Field(..., description="File ID")
    raw_text: str = Field(..., description="Raw extracted text")
    sections: Dict[str, str] = Field(default_factory=dict, description="Extracted sections")
    key_information: Dict[str, Any] = Field(default_factory=dict, description="Key information")
    quality_metrics: Dict[str, Any] = Field(default_factory=dict, description="Quality metrics")
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Extraction timestamp")
    confidence_score: Optional[float] = Field(None, ge=0, le=100, description="Extraction confidence")
    
    @validator('raw_text')
    def validate_raw_text(cls, v):
        if not v or len(v.strip()) < MIN_RAW_TEXT_LENGTH:
            raise ValueError(
                f'Raw text must be at least {MIN_RAW_TEXT_LENGTH} characters'
            )
        return v.strip()


class CVAnalysisSummary(BaseModel):
    """CV analysis summary for quick overview"""
    file_id: str = Field(..., description="File ID")
    user_id: str = Field(..., description="User ID")
    name: Optional[str] = Field(None, description="Candidate name")
    title: Optional[str] = Field(None, description="Professional title")
    experience_level: Optional[ExperienceLevel] = Field(None, description="Experience level")
    total_experience: Optional[float] = Field(None, description="Total years of experience")
    skills_count: int = Field(0, description="Number of skills")
    education_count: int = Field(0, description="Number of education entries")
    projects_count: int = Field(0, description="Number of projects")
    confidence_score: Optional[float] = Field(None, description="Analysis confidence")
    quality_score: Optional[float] = Field(None, description="Document quality")
    completeness_score: Optional[float] = Field(None, description="Information completeness")
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")
    
    @validator('skills_count', 'education_count', 'projects_count')
    def validate_counts(cls, v):
        if v < 0:
            raise ValueError('Counts cannot be negative')
        return v


class CVSearchFilters(BaseModel):
    """CV search filters model"""
    experience_level: Optional[List[ExperienceLevel]] = Field(None, description="Experience levels")
    education_level: Optional[List[EducationLevel]] = Field(None, description="Education levels")
    skills: Optional[List[str]] = Field(None, description="Required skills")
    location: Optional[str] = Field(None, description="Location")
    min_experience: Optional[float] = Field(None, ge=0, description="Minimum years of experience")
    max_experience: Optional[float] = Field(None, ge=0, description="Maximum years of experience")
    has_certifications: Optional[bool] = Field(None, description="Has certifications")
    languages: Optional[List[str]] = Field(None, description="Required languages")
    
    @root_validator(skip_on_failure=True)
    def validate_experience_range(cls, values):
        min_exp = values.get('min_experience')
        max_exp = values.get('max_experience')
        
        if min_exp is not None and max_exp is not None:
            if min_exp > max_exp:
                raise ValueError('Minimum experience cannot be greater than maximum experience')
        
        return values


class CVMatchScore(BaseModel):
    """CV match score model"""
    cv_id: str = Field(..., description="CV ID")
    job_id: str = Field(..., description="Job ID")
    overall_score: float = Field(..., ge=0, le=100, description="Overall match score")
    skills_match: float = Field(..., ge=0, le=100, description="Skills match score")
    experience_match: float = Field(..., ge=0, le=100, description="Experience match score")
    education_match: float = Field(..., ge=0, le=100, description="Education match score")
    location_match: float = Field(..., ge=0, le=100, description="Location match score")
    missing_skills: Optional[List[str]] = Field(None, description="Missing skills")
    matching_skills: Optional[List[str]] = Field(None, description="Matching skills")
    score_breakdown: Optional[Dict[str, Any]] = Field(None, description="Detailed score breakdown")
    match_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Match timestamp")
    
    @validator('overall_score', 'skills_match', 'experience_match', 'education_match', 'location_match')
    def validate_scores(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('Scores must be between 0 and 100')
        return v
