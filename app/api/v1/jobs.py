from fastapi import APIRouter, HTTPException, status, Depends, Request, Query
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from app.core.security import get_current_user
from app.models.user import User
from app.services.job_description_parser import job_description_parser
from app.services.search_query_parser import search_query_parser
from app.services.data_validation_parser import data_validation_parser
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
        
        # Parse search criteria using Search Query Parser
        parsed_query = search_query_parser.parse_search_query(str(search_criteria))
        
        # Validate parsed query
        validation_result = search_query_parser.validate_query(parsed_query)
        
        if not validation_result['is_valid']:
            logger.warning(f"Invalid search query: {validation_result['errors']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid search query: {', '.join(validation_result['errors'])}"
            )
        
        # TODO: Get actual job data from database/external API
        # For now, use empty list as placeholder
        all_jobs = []
        
        # Apply filters using JobFilterService with parsed query
        filtered_jobs = job_filter_service.apply_complex_filters(all_jobs, parsed_query['filters'])
        
        # Enhanced results with parsing metadata
        results = {
            "search_criteria": search_criteria,
            "parsed_query": parsed_query,
            "validation_result": validation_result,
            "total_results": len(filtered_jobs),
            "jobs": filtered_jobs,
            "filters_applied": parsed_query['filters'],
            "search_metadata": {
                "search_time": datetime.utcnow().isoformat(),
                "user_id": current_user.user_id,
                "query_complexity": parsed_query['metadata']['complexity_score'],
                "parsing_errors": validation_result.get('errors', []),
                "parsing_warnings": validation_result.get('warnings', [])
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


@router.post("/parse-job-description", response_model=Dict[str, Any],
            summary="Parse Job Description",
            description="Parse job description text into structured data")
async def parse_job_description(
    request: Request,
    job_description: Dict[str, str],
    current_user: User = Depends(get_current_user)
):
    """
    Parse job description into structured data
    
    - **job_description**: Dictionary containing job description text
    """
    try:
        logger.info(f"Job description parsing request by user {current_user.user_id}")
        
        # Validate input data
        validation_schema = {
            'text': {
                'required': True,
                'type': 'string',
                'max_length': 50000,
                'sanitize': ['whitespace', 'html', 'sql_injection', 'xss']
            }
        }
        
        validation_result = data_validation_parser.validate_data(job_description, validation_schema)
        
        if not validation_result['is_valid']:
            logger.warning(f"Invalid job description data: {validation_result['errors']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid job description: {', '.join(validation_result['errors'])}"
            )
        
        # Parse job description
        parsed_data = job_description_parser.parse_job_description(
            validation_result['sanitized_data']['text']
        )
        
        # Enhanced response with validation metadata
        response_data = {
            "parsed_data": parsed_data,
            "validation_result": validation_result,
            "parsing_metadata": {
                "parsed_at": datetime.utcnow().isoformat(),
                "user_id": current_user.user_id,
                "input_length": len(job_description.get('text', '')),
                "output_sections": len(parsed_data.get('sections', {})),
                "data_quality_score": parsed_data.get('metadata', {}).get('total_words', 0) / 100
            }
        }
        
        logger.info(f"Job description parsing completed. Found {len(parsed_data.get('sections', {}))} sections")
        return response_data
    
    except Exception as e:
        logger.error(f"Error parsing job description: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during job description parsing"
        )


@router.post("/parse-search-query", response_model=Dict[str, Any],
            summary="Parse Search Query",
            description="Parse complex search query into structured filters")
async def parse_search_query(
    request: Request,
    query_data: Dict[str, str],
    current_user: User = Depends(get_current_user)
):
    """
    Parse search query into structured filters
    
    - **query**: Search query string to parse
    """
    try:
        logger.info(f"Search query parsing request by user {current_user.user_id}")
        
        # Validate input data
        validation_schema = {
            'query': {
                'required': True,
                'type': 'string',
                'max_length': 1000,
                'sanitize': ['whitespace', 'html', 'sql_injection', 'xss']
            }
        }
        
        validation_result = data_validation_parser.validate_data(query_data, validation_schema)
        
        if not validation_result['is_valid']:
            logger.warning(f"Invalid search query data: {validation_result['errors']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid search query: {', '.join(validation_result['errors'])}"
            )
        
        # Parse search query
        parsed_query = search_query_parser.parse_search_query(
            validation_result['sanitized_data']['query']
        )
        
        # Validate parsed query
        query_validation = search_query_parser.validate_query(parsed_query)
        
        # Enhanced response with parsing metadata
        response_data = {
            "parsed_query": parsed_query,
            "validation_result": validation_result,
            "query_validation": query_validation,
            "parsing_metadata": {
                "parsed_at": datetime.utcnow().isoformat(),
                "user_id": current_user.user_id,
                "query_length": len(query_data.get('query', '')),
                "complexity_score": parsed_query.get('metadata', {}).get('complexity_score', 0),
                "filters_count": len(parsed_query.get('filters', [])),
                "keywords_count": len(parsed_query.get('keywords', []))
            }
        }
        
        logger.info(f"Search query parsing completed. Complexity: {parsed_query.get('metadata', {}).get('complexity_score', 0)}")
        return response_data
    
    except Exception as e:
        logger.error(f"Error parsing search query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during search query parsing"
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
