from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.models.job import (
    JobPosting, JobMatch, JobApplication, JobSearchRequest, JobSearchResponse,
    JobType, ExperienceLevel, CompanySize, Location, Salary, JobRequirements, JobBenefits, Company
)


class JobPostingResponse(BaseModel):
    """Job posting response model for API"""
    job_id: str
    title: str
    description: str
    company: Company
    location: Location
    job_type: JobType
    salary: Optional[Salary]
    requirements: JobRequirements
    benefits: JobBenefits
    posted_date: datetime
    application_deadline: Optional[datetime]
    is_active: bool
    application_url: Optional[str]
    
    class Config:
        from_attributes = True


class JobMatchResponse(BaseModel):
    """Job match response model for API"""
    match_id: str
    cv_id: str
    job_id: str
    user_id: str
    match_score: float
    skill_match_score: float
    experience_match_score: float
    location_match_score: float
    salary_match_score: float
    company_match_score: float
    matching_criteria: Dict[str, Any]
    matched_at: datetime
    is_viewed: bool
    is_applied: bool
    
    class Config:
        from_attributes = True


class JobApplicationResponse(BaseModel):
    """Job application response model for API"""
    application_id: str
    job_id: str
    cv_id: str
    user_id: str
    cover_letter: Optional[str]
    application_status: str
    applied_at: datetime
    last_updated: datetime
    recruiter_notes: Optional[str]
    interview_scheduled: Optional[datetime]
    
    class Config:
        from_attributes = True


class JobMatchRequest(BaseModel):
    """Request model for job matching"""
    cv_id: str = Field(..., description="CV ID to match against jobs")
    filters: Optional[Dict[str, Any]] = Field(None, description="Optional filter criteria")
    limit: int = Field(20, le=100, description="Number of matches to return")
    offset: int = Field(0, ge=0, description="Pagination offset")


class JobApplicationRequest(BaseModel):
    """Request model for job application"""
    job_id: str = Field(..., description="Job ID to apply to")
    cv_id: str = Field(..., description="CV ID to use for application")
    cover_letter: Optional[str] = Field(None, description="Cover letter text")


class JobMatchHistoryResponse(BaseModel):
    """Response model for job match history"""
    cv_id: str
    total_records: int
    history: List[JobMatchResponse]
    pagination: Dict[str, Any]
    summary: Dict[str, Any]


class JobMatchAnalyticsResponse(BaseModel):
    """Response model for job match analytics"""
    cv_id: str
    analytics_period: str
    metrics: Dict[str, Any]
    insights: Dict[str, Any]
    generated_at: datetime


class CompanyResponse(BaseModel):
    """Company response model for API"""
    company_id: str
    name: str
    description: Optional[str]
    website: Optional[str]
    industry: Optional[str]
    size: Optional[CompanySize]
    founded_year: Optional[int]
    headquarters: Optional[Location]
    logo_url: Optional[str]
    social_media: Dict[str, str]
    
    class Config:
        from_attributes = True


class LocationResponse(BaseModel):
    """Location response model for API"""
    city: str
    state: Optional[str]
    country: str
    postal_code: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    is_remote: bool
    
    class Config:
        from_attributes = True


class SalaryResponse(BaseModel):
    """Salary response model for API"""
    min_amount: Optional[float]
    max_amount: Optional[float]
    currency: str
    period: str
    is_negotiable: bool
    includes_equity: bool
    
    class Config:
        from_attributes = True


class JobRequirementsResponse(BaseModel):
    """Job requirements response model for API"""
    required_skills: List[str]
    preferred_skills: List[str]
    experience_years: Optional[int]
    experience_level: Optional[ExperienceLevel]
    education_level: Optional[str]
    certifications: List[str]
    languages: List[str]
    
    class Config:
        from_attributes = True


class JobBenefitsResponse(BaseModel):
    """Job benefits response model for API"""
    health_insurance: bool
    dental_insurance: bool
    vision_insurance: bool
    retirement_plan: bool
    paid_time_off: Optional[int]
    sick_leave: Optional[int]
    flexible_hours: bool
    work_from_home: bool
    professional_development: bool
    gym_membership: bool
    other_benefits: List[str]
    
    class Config:
        from_attributes = True
