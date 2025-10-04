"""
CV Schemas
Pydantic schemas cho CV API requests và responses
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.models.cv import (
    DocumentType, ExperienceLevel, EducationLevel, SkillCategory,
    CVAnalysis, CVUpload, CVContent, CVAnalysisSummary, CVSearchFilters, CVMatchScore
)


class CVUploadRequest(BaseModel):
    """Request schema cho CV upload"""
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="File type")
    file_size: int = Field(..., ge=0, description="File size in bytes")


class CVUploadResponse(BaseModel):
    """Response schema cho CV upload"""
    success: bool = Field(..., description="Upload success status")
    message: str = Field(..., description="Response message")
    file_id: str = Field(..., description="Unique file ID")
    s3_key: str = Field(..., description="S3 key")
    file_url: Optional[str] = Field(None, description="Pre-signed URL")
    upload_timestamp: datetime = Field(..., description="Upload timestamp")


class TextExtractionRequest(BaseModel):
    """Request schema cho text extraction"""
    file_id: str = Field(..., description="File ID")
    document_type: DocumentType = Field(default=DocumentType.CV, description="Document type")


class TextExtractionResponse(BaseModel):
    """Response schema cho text extraction"""
    success: bool = Field(..., description="Extraction success status")
    message: str = Field(..., description="Response message")
    extraction_id: str = Field(..., description="Extraction ID")
    text: str = Field(..., description="Extracted text")
    confidence: float = Field(..., description="Extraction confidence")
    sections: Dict[str, str] = Field(default_factory=dict, description="Extracted sections")
    key_information: Dict[str, Any] = Field(default_factory=dict, description="Key information")
    quality_metrics: Dict[str, Any] = Field(default_factory=dict, description="Quality metrics")
    processing_time: float = Field(..., description="Processing time in seconds")
    extraction_timestamp: datetime = Field(..., description="Extraction timestamp")


class CVAnalysisRequest(BaseModel):
    """Request schema cho CV analysis"""
    file_id: str = Field(..., description="File ID")
    analysis_type: str = Field(default="full", description="Analysis type")
    include_raw_text: bool = Field(default=False, description="Include raw text in response")


class CVAnalysisResponse(BaseModel):
    """Response schema cho CV analysis"""
    success: bool = Field(..., description="Analysis success status")
    message: str = Field(..., description="Response message")
    analysis_id: str = Field(..., description="Analysis ID")
    analysis: CVAnalysis = Field(..., description="CV analysis data")
    processing_time: float = Field(..., description="Processing time in seconds")
    analysis_timestamp: datetime = Field(..., description="Analysis timestamp")


class CVListResponse(BaseModel):
    """Response schema cho CV list"""
    success: bool = Field(..., description="Request success status")
    cvs: List[CVAnalysisSummary] = Field(..., description="List of CV summaries")
    total_count: int = Field(..., description="Total number of CVs")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")
    has_more: bool = Field(..., description="Has more pages")


class CVSearchRequest(BaseModel):
    """Request schema cho CV search"""
    filters: CVSearchFilters = Field(..., description="Search filters")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Page size")
    sort_by: str = Field(default="relevance", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order")


class CVSearchResponse(BaseModel):
    """Response schema cho CV search"""
    success: bool = Field(..., description="Search success status")
    results: List[CVAnalysisSummary] = Field(..., description="Search results")
    total_count: int = Field(..., description="Total matching CVs")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")
    has_more: bool = Field(..., description="Has more pages")
    search_time: float = Field(..., description="Search time in seconds")


class CVMatchRequest(BaseModel):
    """Request schema cho CV matching"""
    cv_id: str = Field(..., description="CV ID")
    job_id: str = Field(..., description="Job ID")
    match_criteria: Optional[Dict[str, Any]] = Field(None, description="Custom match criteria")


class CVMatchResponse(BaseModel):
    """Response schema cho CV matching"""
    success: bool = Field(..., description="Match success status")
    message: str = Field(..., description="Response message")
    match_score: CVMatchScore = Field(..., description="Match score data")
    recommendations: Optional[List[str]] = Field(None, description="Improvement recommendations")
    match_timestamp: datetime = Field(..., description="Match timestamp")


class CVUpdateRequest(BaseModel):
    """Request schema cho CV update"""
    analysis_id: str = Field(..., description="Analysis ID")
    updates: Dict[str, Any] = Field(..., description="Fields to update")
    reason: Optional[str] = Field(None, description="Update reason")


class CVUpdateResponse(BaseModel):
    """Response schema cho CV update"""
    success: bool = Field(..., description="Update success status")
    message: str = Field(..., description="Response message")
    analysis_id: str = Field(..., description="Analysis ID")
    updated_fields: List[str] = Field(..., description="Updated fields")
    update_timestamp: datetime = Field(..., description="Update timestamp")


class CVDeleteRequest(BaseModel):
    """Request schema cho CV deletion"""
    file_id: str = Field(..., description="File ID")
    delete_analysis: bool = Field(default=True, description="Delete analysis data")
    reason: Optional[str] = Field(None, description="Deletion reason")


class CVDeleteResponse(BaseModel):
    """Response schema cho CV deletion"""
    success: bool = Field(..., description="Deletion success status")
    message: str = Field(..., description="Response message")
    file_id: str = Field(..., description="Deleted file ID")
    deleted_analysis: bool = Field(..., description="Analysis data deleted")
    deletion_timestamp: datetime = Field(..., description="Deletion timestamp")


class CVStatsResponse(BaseModel):
    """Response schema cho CV statistics"""
    success: bool = Field(..., description="Request success status")
    total_cvs: int = Field(..., description="Total number of CVs")
    total_analyses: int = Field(..., description="Total number of analyses")
    avg_quality_score: float = Field(..., description="Average quality score")
    avg_completeness_score: float = Field(..., description="Average completeness score")
    top_skills: List[Dict[str, Any]] = Field(..., description="Most common skills")
    experience_distribution: Dict[str, int] = Field(..., description="Experience level distribution")
    education_distribution: Dict[str, int] = Field(..., description="Education level distribution")
    stats_timestamp: datetime = Field(..., description="Statistics timestamp")


class CVExportRequest(BaseModel):
    """Request schema cho CV export"""
    file_id: str = Field(..., description="File ID")
    export_format: str = Field(default="json", description="Export format")
    include_raw_text: bool = Field(default=False, description="Include raw text")
    include_analysis: bool = Field(default=True, description="Include analysis data")


class CVExportResponse(BaseModel):
    """Response schema cho CV export"""
    success: bool = Field(..., description="Export success status")
    message: str = Field(..., description="Response message")
    file_id: str = Field(..., description="File ID")
    export_url: str = Field(..., description="Export file URL")
    export_format: str = Field(..., description="Export format")
    file_size: int = Field(..., description="Export file size")
    expires_at: datetime = Field(..., description="Export URL expiration")


class CVBatchAnalysisRequest(BaseModel):
    """Request schema cho batch CV analysis"""
    file_ids: List[str] = Field(..., description="List of file IDs")
    analysis_type: str = Field(default="full", description="Analysis type")
    priority: str = Field(default="normal", description="Processing priority")


class CVBatchAnalysisResponse(BaseModel):
    """Response schema cho batch CV analysis"""
    success: bool = Field(..., description="Batch analysis success status")
    message: str = Field(..., description="Response message")
    batch_id: str = Field(..., description="Batch ID")
    total_files: int = Field(..., description="Total files in batch")
    queued_files: int = Field(..., description="Files queued for processing")
    processing_files: int = Field(..., description="Files currently processing")
    completed_files: int = Field(..., description="Files completed")
    failed_files: int = Field(..., description="Files failed")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    batch_timestamp: datetime = Field(..., description="Batch creation timestamp")


class CVHealthResponse(BaseModel):
    """Response schema cho CV service health"""
    service: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Service version")
    dependencies: Dict[str, str] = Field(..., description="Dependency status")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Service metrics")


class CVErrorResponse(BaseModel):
    """Response schema cho CV errors"""
    success: bool = Field(False, description="Request success status")
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    timestamp: datetime = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
