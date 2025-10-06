from fastapi import APIRouter, HTTPException, status, Depends, Request, Query
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from app.core.security import get_current_user
from app.models.user import User
from app.services.job_filter import job_filter_service
from app.repositories.job_match import job_match_repository
from app.schemas.job import (
    JobMatchRequest, JobMatchResponse, JobMatchHistoryResponse, 
    JobMatchAnalyticsResponse, JobApplicationRequest, JobApplicationResponse
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Job Matching"])


@router.get("/match/{cv_id}", response_model=JobMatchResponse,
           summary="Get Job Matches for CV",
           description="Find and rank jobs that match the specified CV")
async def get_job_matches_for_cv(
    cv_id: str,
    request: Request,
    limit: int = Query(default=20, le=100, description="Number of matches to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user)
):
    """
    Get job matches for a specific CV
    
    - **cv_id**: ID of the CV to match against jobs
    - **limit**: Maximum number of matches to return (default: 20, max: 100)
    - **offset**: Pagination offset (default: 0)
    """
    try:
        logger.info(f"Job matching request for CV {cv_id} by user {current_user.user_id}")
        
        # Get existing matches from repository
        matches = job_match_repository.get_job_matches_by_cv(cv_id, limit, offset)
        
        # TODO: Implement actual job matching logic with AI services
        # For now, return existing matches
        
        response_data = {
            "cv_id": cv_id,
            "total_matches": len(matches),
            "matches": matches,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": len(matches) == limit
            },
            "filters_applied": [],
            "matching_criteria": {
                "skills_weight": 0.4,
                "experience_weight": 0.3,
                "location_weight": 0.2,
                "salary_weight": 0.1
            }
        }
        
        logger.info(f"Found {response_data['total_matches']} matches for CV {cv_id}")
        return response_data
    
    except Exception as e:
        logger.error(f"Error in job matching for CV {cv_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during job matching"
        )


@router.post("/match", response_model=Dict[str, Any],
            summary="Custom Job Search",
            description="Search jobs with custom criteria and matching parameters")
async def custom_job_search(
    request: Request,
    search_criteria: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """
    Custom job search with specific criteria
    
    - **search_criteria**: Dictionary containing search parameters
    """
    try:
        logger.info(f"Custom job search request by user {current_user.user_id}")
        
        # Extract search criteria
        keywords = search_criteria.get("keywords", [])
        location = search_criteria.get("location", "")
        salary_min = search_criteria.get("salary_min")
        salary_max = search_criteria.get("salary_max")
        job_type = search_criteria.get("job_type", [])
        experience_level = search_criteria.get("experience_level", "")
        skills = search_criteria.get("skills", [])
        
        # TODO: Get actual job data from database/external API
        # For now, use empty list as placeholder
        all_jobs = []
        
        # Apply filters using JobFilterService
        filtered_jobs = job_filter_service.apply_complex_filters(all_jobs, search_criteria)
        
        # Mock response for now
        results = {
            "search_criteria": search_criteria,
            "total_results": len(filtered_jobs),
            "jobs": filtered_jobs,
            "filters_applied": {
                "keywords": keywords,
                "location": location,
                "salary_range": f"{salary_min}-{salary_max}" if salary_min and salary_max else None,
                "job_type": job_type,
                "experience_level": experience_level,
                "skills": skills
            },
            "search_metadata": {
                "search_time": datetime.utcnow().isoformat(),
                "user_id": current_user.user_id
            }
        }
        
        logger.info(f"Custom search completed with {results['total_results']} results")
        return results
    
    except Exception as e:
        logger.error(f"Error in custom job search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during job search"
        )


@router.get("/match/{cv_id}/history", response_model=JobMatchHistoryResponse,
           summary="Get Match History",
           description="Get job matching history for a specific CV")
async def get_match_history(
    cv_id: str,
    request: Request,
    limit: int = Query(default=50, le=100, description="Number of history records to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user)
):
    """
    Get job matching history for a CV
    
    - **cv_id**: ID of the CV
    - **limit**: Maximum number of history records (default: 50, max: 100)
    - **offset**: Pagination offset (default: 0)
    """
    try:
        logger.info(f"Match history request for CV {cv_id} by user {current_user.user_id}")
        
        # Get match history from repository
        history_data = job_match_repository.get_match_history(cv_id, limit, offset)
        
        logger.info(f"Retrieved {history_data['total_records']} history records for CV {cv_id}")
        return history_data
    
    except Exception as e:
        logger.error(f"Error retrieving match history for CV {cv_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during history retrieval"
        )


@router.post("/apply", response_model=JobApplicationResponse,
            summary="Apply to Job",
            description="Submit job application with CV")
async def apply_to_job(
    request: Request,
    application_data: JobApplicationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Apply to a job with CV
    
    - **job_id**: Job ID to apply to
    - **cv_id**: CV ID to use for application
    - **cover_letter**: Optional cover letter text
    """
    try:
        logger.info(f"Job application request by user {current_user.user_id} for job {application_data.job_id}")
        
        # TODO: Implement actual job application logic
        # This is a placeholder implementation
        
        # Mock response for now
        application_response = {
            "application_id": "mock-application-id",
            "job_id": application_data.job_id,
            "cv_id": application_data.cv_id,
            "user_id": current_user.user_id,
            "cover_letter": application_data.cover_letter,
            "application_status": "submitted",
            "applied_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "recruiter_notes": None,
            "interview_scheduled": None
        }
        
        logger.info(f"Job application submitted successfully: {application_response['application_id']}")
        return application_response
    
    except Exception as e:
        logger.error(f"Error submitting job application: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during job application"
        )


@router.get("/match/{cv_id}/analytics", response_model=JobMatchAnalyticsResponse,
           summary="Get Match Analytics",
           description="Get analytics and insights for job matching performance")
async def get_match_analytics(
    cv_id: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get analytics and insights for job matching
    
    - **cv_id**: ID of the CV to analyze
    """
    try:
        logger.info(f"Match analytics request for CV {cv_id} by user {current_user.user_id}")
        
        # TODO: Implement actual analytics logic
        # This is a placeholder implementation
        
        # Mock response for now
        analytics = {
            "cv_id": cv_id,
            "analytics_period": "30_days",
            "metrics": {
                "total_searches": 0,
                "total_matches_found": 0,
                "avg_match_score": 0.0,
                "top_matching_skills": [],
                "top_matching_companies": [],
                "salary_trends": {},
                "location_distribution": {}
            },
            "insights": {
                "strengths": [],
                "improvement_areas": [],
                "market_demand": {},
                "recommendations": []
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Analytics generated for CV {cv_id}")
        return analytics
    
    except Exception as e:
        logger.error(f"Error generating analytics for CV {cv_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during analytics generation"
        )