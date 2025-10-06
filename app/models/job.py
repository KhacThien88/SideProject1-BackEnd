from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import uuid


class JobType(str, Enum):
    """Job type enumeration"""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"
    REMOTE = "remote"
    HYBRID = "hybrid"


class ExperienceLevel(str, Enum):
    """Experience level enumeration"""
    ENTRY = "entry"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"


class CompanySize(str, Enum):
    """Company size enumeration"""
    STARTUP = "startup"  # 1-10 employees
    SMALL = "small"      # 11-50 employees
    MEDIUM = "medium"    # 51-200 employees
    LARGE = "large"      # 201-1000 employees
    ENTERPRISE = "enterprise"  # 1000+ employees


class Location(BaseModel):
    """Location model with geographic data"""
    city: str = Field(..., description="City name")
    state: Optional[str] = Field(None, description="State or province")
    country: str = Field(..., description="Country name")
    postal_code: Optional[str] = Field(None, description="Postal/ZIP code")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    is_remote: bool = Field(False, description="Whether this is a remote position")
    
    @validator('latitude')
    def validate_latitude(cls, v):
        if v is not None and not (-90 <= v <= 90):
            raise ValueError('Latitude must be between -90 and 90')
        return v
    
    @validator('longitude')
    def validate_longitude(cls, v):
        if v is not None and not (-180 <= v <= 180):
            raise ValueError('Longitude must be between -180 and 180')
        return v


class Salary(BaseModel):
    """Salary information model"""
    min_amount: Optional[float] = Field(None, description="Minimum salary amount")
    max_amount: Optional[float] = Field(None, description="Maximum salary amount")
    currency: str = Field("USD", description="Currency code")
    period: str = Field("annual", description="Salary period (annual, monthly, hourly)")
    is_negotiable: bool = Field(False, description="Whether salary is negotiable")
    includes_equity: bool = Field(False, description="Whether compensation includes equity")
    
    @validator('min_amount', 'max_amount')
    def validate_amount(cls, v):
        if v is not None and v < 0:
            raise ValueError('Salary amount must be positive')
        return v
    
    @validator('currency')
    def validate_currency(cls, v):
        valid_currencies = ['USD', 'EUR', 'GBP', 'VND', 'JPY', 'CAD', 'AUD']
        if v.upper() not in valid_currencies:
            raise ValueError(f'Currency must be one of: {valid_currencies}')
        return v.upper()


class JobRequirements(BaseModel):
    """Job requirements model"""
    required_skills: List[str] = Field(default_factory=list, description="Required technical skills")
    preferred_skills: List[str] = Field(default_factory=list, description="Preferred skills")
    experience_years: Optional[int] = Field(None, description="Required years of experience")
    experience_level: Optional[ExperienceLevel] = Field(None, description="Experience level")
    education_level: Optional[str] = Field(None, description="Required education level")
    certifications: List[str] = Field(default_factory=list, description="Required certifications")
    languages: List[str] = Field(default_factory=list, description="Required languages")
    
    @validator('experience_years')
    def validate_experience_years(cls, v):
        if v is not None and v < 0:
            raise ValueError('Experience years must be non-negative')
        return v


class JobBenefits(BaseModel):
    """Job benefits model"""
    health_insurance: bool = Field(False, description="Health insurance provided")
    dental_insurance: bool = Field(False, description="Dental insurance provided")
    vision_insurance: bool = Field(False, description="Vision insurance provided")
    retirement_plan: bool = Field(False, description="Retirement plan provided")
    paid_time_off: Optional[int] = Field(None, description="Paid time off days")
    sick_leave: Optional[int] = Field(None, description="Sick leave days")
    flexible_hours: bool = Field(False, description="Flexible working hours")
    work_from_home: bool = Field(False, description="Work from home option")
    professional_development: bool = Field(False, description="Professional development support")
    gym_membership: bool = Field(False, description="Gym membership provided")
    other_benefits: List[str] = Field(default_factory=list, description="Other benefits")


class Company(BaseModel):
    """Company model with organization details"""
    company_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique company ID")
    name: str = Field(..., description="Company name")
    description: Optional[str] = Field(None, description="Company description")
    website: Optional[str] = Field(None, description="Company website URL")
    industry: Optional[str] = Field(None, description="Industry sector")
    size: Optional[CompanySize] = Field(None, description="Company size")
    founded_year: Optional[int] = Field(None, description="Year company was founded")
    headquarters: Optional[Location] = Field(None, description="Company headquarters location")
    logo_url: Optional[str] = Field(None, description="Company logo URL")
    social_media: Dict[str, str] = Field(default_factory=dict, description="Social media links")
    
    @validator('founded_year')
    def validate_founded_year(cls, v):
        if v is not None and (v < 1800 or v > datetime.now().year):
            raise ValueError('Founded year must be between 1800 and current year')
        return v


class JobPosting(BaseModel):
    """Core job posting model"""
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique job ID")
    title: str = Field(..., description="Job title")
    description: str = Field(..., description="Job description")
    company: Company = Field(..., description="Company information")
    location: Location = Field(..., description="Job location")
    job_type: JobType = Field(..., description="Type of employment")
    salary: Optional[Salary] = Field(None, description="Salary information")
    requirements: JobRequirements = Field(default_factory=JobRequirements, description="Job requirements")
    benefits: JobBenefits = Field(default_factory=JobBenefits, description="Job benefits")
    posted_date: datetime = Field(default_factory=datetime.utcnow, description="Date job was posted")
    application_deadline: Optional[datetime] = Field(None, description="Application deadline")
    is_active: bool = Field(True, description="Whether job posting is active")
    application_url: Optional[str] = Field(None, description="External application URL")
    internal_notes: Optional[str] = Field(None, description="Internal notes for recruiters")
    
    @validator('application_deadline')
    def validate_deadline(cls, v, values):
        if v is not None and 'posted_date' in values:
            if v < values['posted_date']:
                raise ValueError('Application deadline cannot be before posted date')
        return v


class JobMatch(BaseModel):
    """Job match model with scoring information"""
    match_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique match ID")
    cv_id: str = Field(..., description="CV ID that was matched")
    job_id: str = Field(..., description="Job ID that was matched")
    user_id: str = Field(..., description="User ID who owns the CV")
    match_score: float = Field(..., description="Overall match score (0.0 - 1.0)")
    skill_match_score: float = Field(..., description="Skills matching score")
    experience_match_score: float = Field(..., description="Experience matching score")
    location_match_score: float = Field(..., description="Location matching score")
    salary_match_score: float = Field(..., description="Salary matching score")
    company_match_score: float = Field(..., description="Company matching score")
    matching_criteria: Dict[str, Any] = Field(default_factory=dict, description="Detailed matching criteria")
    matched_at: datetime = Field(default_factory=datetime.utcnow, description="When match was created")
    is_viewed: bool = Field(False, description="Whether user has viewed this match")
    is_applied: bool = Field(False, description="Whether user has applied to this job")
    
    @validator('match_score', 'skill_match_score', 'experience_match_score', 
              'location_match_score', 'salary_match_score', 'company_match_score')
    def validate_scores(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError('Match scores must be between 0.0 and 1.0')
        return v


class JobApplication(BaseModel):
    """Job application model"""
    application_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique application ID")
    job_id: str = Field(..., description="Job ID being applied to")
    cv_id: str = Field(..., description="CV ID used for application")
    user_id: str = Field(..., description="User ID making the application")
    cover_letter: Optional[str] = Field(None, description="Cover letter text")
    application_status: str = Field("submitted", description="Application status")
    applied_at: datetime = Field(default_factory=datetime.utcnow, description="When application was submitted")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="When application was last updated")
    recruiter_notes: Optional[str] = Field(None, description="Recruiter notes")
    interview_scheduled: Optional[datetime] = Field(None, description="Interview date if scheduled")
    
    @validator('application_status')
    def validate_status(cls, v):
        valid_statuses = ['submitted', 'under_review', 'interview_scheduled', 'rejected', 'accepted']
        if v not in valid_statuses:
            raise ValueError(f'Application status must be one of: {valid_statuses}')
        return v


class JobSearchRequest(BaseModel):
    """Job search request model"""
    keywords: List[str] = Field(default_factory=list, description="Search keywords")
    location: Optional[str] = Field(None, description="Location filter")
    radius_km: float = Field(50.0, description="Search radius in kilometers")
    salary_min: Optional[float] = Field(None, description="Minimum salary")
    salary_max: Optional[float] = Field(None, description="Maximum salary")
    currency: str = Field("USD", description="Salary currency")
    job_types: List[JobType] = Field(default_factory=list, description="Job types to include")
    experience_level: Optional[ExperienceLevel] = Field(None, description="Experience level")
    required_skills: List[str] = Field(default_factory=list, description="Required skills")
    company_size: Optional[CompanySize] = Field(None, description="Company size filter")
    posted_within_days: Optional[int] = Field(None, description="Jobs posted within N days")
    sort_by: str = Field("relevance", description="Sort criteria")
    sort_order: str = Field("desc", description="Sort order (asc/desc)")
    limit: int = Field(20, description="Number of results to return")
    offset: int = Field(0, description="Pagination offset")
    
    @validator('radius_km')
    def validate_radius(cls, v):
        if v <= 0:
            raise ValueError('Search radius must be positive')
        return v
    
    @validator('limit')
    def validate_limit(cls, v):
        if v <= 0 or v > 100:
            raise ValueError('Limit must be between 1 and 100')
        return v
    
    @validator('offset')
    def validate_offset(cls, v):
        if v < 0:
            raise ValueError('Offset must be non-negative')
        return v


class JobSearchResponse(BaseModel):
    """Job search response model"""
    total_results: int = Field(..., description="Total number of matching jobs")
    jobs: List[JobPosting] = Field(..., description="List of job postings")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")
    search_metadata: Dict[str, Any] = Field(..., description="Search metadata")
    applied_filters: Dict[str, Any] = Field(..., description="Applied filter criteria")
