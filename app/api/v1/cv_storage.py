"""
API endpoints cho CV storage và management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from typing import Dict, Any, List, Optional
import logging

from app.core.security import get_current_user
from app.models.user import User
from app.services.cv_storage import cv_storage_service
from app.schemas.cv import (
    CVUploadResponse, CVAnalysisResponse,
    CVSearchRequest, CVSearchResponse, CVUpdateRequest, CVUpdateResponse,
    CVDeleteRequest, CVDeleteResponse, CVStatsResponse, CVExportRequest, CVExportResponse
)
from app.utils.rate_limit import rate_limit_dependency

router = APIRouter(tags=["CV Analysis"])
logger = logging.getLogger(__name__)


@router.get("/cv/{cv_id}", response_model=Dict[str, Any],
           summary="Get CV by ID",
           description="Lấy thông tin chi tiết của CV theo ID. Chỉ chủ sở hữu mới có thể truy cập.")
async def get_cv_by_id(
    cv_id: str,
    current_user: User = Depends(get_current_user)
):
    """Lấy CV theo ID"""
    try:
        cv_data = await cv_storage_service.get_cv_by_id(cv_id)
        
        if not cv_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="CV not found"
            )
        
        # Verify ownership
        if cv_data['user_id'] != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: CV does not belong to user"
            )
        
        return {
            'success': True,
            'cv_data': cv_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get CV: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get CV"
        )


@router.get("/cv/user/{user_id}", response_model=List[Dict[str, Any]])
async def get_user_cvs(
    user_id: str,
    limit: int = Query(50, ge=1, le=100),
    last_key: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """Lấy danh sách CV của user"""
    try:
        # Verify user can access this data
        if user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: Cannot access other user's CVs"
            )
        
        cvs, next_key = await cv_storage_service.get_user_cvs(user_id, limit, last_key)
        
        return {
            'success': True,
            'cvs': cvs,
            'next_key': next_key,
            'total_count': len(cvs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user CVs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user CVs"
        )


@router.post("/cv/{cv_id}/analyze", response_model=Dict[str, Any])
async def analyze_cv(
    cv_id: str,
    current_user: User = Depends(get_current_user)
):
    """Bắt đầu phân tích CV"""
    try:
        # Get CV record
        cv_data = await cv_storage_service.get_cv_by_id(cv_id)
        if not cv_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="CV not found"
            )
        
        # Verify ownership
        if cv_data['user_id'] != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: CV does not belong to user"
            )
        
        # Check if already analyzed
        if cv_data['status'] == 'analyzed':
            return {
                'success': True,
                'message': 'CV already analyzed',
                'cv_id': cv_id,
                'status': cv_data['status']
            }
        
        # Start analysis
        result = await cv_storage_service.analyze_cv_from_s3(
            cv_id, 
            cv_data['s3_key'], 
            current_user.user_id
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze CV: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze CV"
        )


@router.get("/cv/{cv_id}/analysis-result", response_model=Dict[str, Any])
async def get_analysis_result(
    cv_id: str,
    current_user: User = Depends(get_current_user)
):
    """Lấy kết quả phân tích CV"""
    try:
        # Get CV record
        cv_data = await cv_storage_service.get_cv_by_id(cv_id)
        if not cv_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="CV not found"
            )
        
        # Verify ownership
        if cv_data['user_id'] != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: CV does not belong to user"
            )
        
        # Check if analysis is complete
        if cv_data['status'] != 'analyzed':
            return {
                'success': True,
                'cv_id': cv_id,
                'status': cv_data['status'],
                'message': 'Analysis not complete yet'
            }
        
        # Get analysis result
        if cv_data.get('textract_job_id'):
            result = await cv_storage_service.get_textract_result(
                cv_id, 
                cv_data['textract_job_id']
            )
            return result
        else:
            return {
                'success': True,
                'cv_id': cv_id,
                'analysis_result': cv_data.get('analysis_result'),
                'raw_content': cv_data.get('raw_content'),
                'status': cv_data['status']
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis result: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analysis result"
        )


@router.post("/cv/search", response_model=Dict[str, Any],
            summary="Search CVs",
            description="Tìm kiếm CV theo từ khóa, kỹ năng, kinh nghiệm và các tiêu chí khác.")
async def search_cvs(
    search_request: CVSearchRequest,
    current_user: User = Depends(get_current_user),
    rate_limit_status: bool = Depends(rate_limit_dependency)
):
    """Tìm kiếm CV theo criteria"""
    try:
        result = await cv_storage_service.search_cvs(
            search_request.dict(),
            current_user.user_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to search CVs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search CVs"
        )


@router.put("/cv/{cv_id}", response_model=Dict[str, Any])
async def update_cv(
    cv_id: str,
    update_request: CVUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """Cập nhật CV metadata"""
    try:
        result = await cv_storage_service.update_cv_metadata(
            cv_id,
            current_user.user_id,
            update_request.dict()
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to update CV: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update CV"
        )


@router.delete("/cv/{cv_id}", response_model=Dict[str, Any])
async def delete_cv(
    cv_id: str,
    current_user: User = Depends(get_current_user)
):
    """Xóa CV"""
    try:
        result = await cv_storage_service.delete_cv(cv_id, current_user.user_id)
        
        if not result['success']:
            if 'not found' in result.get('error', '').lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result['error']
                )
            elif 'unauthorized' in result.get('error', '').lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=result['error']
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result['error']
                )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete CV: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete CV"
        )


@router.get("/cv/analytics/{user_id}", response_model=Dict[str, Any])
async def get_cv_analytics(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """Lấy analytics cho user"""
    try:
        # Verify user can access this data
        if user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: Cannot access other user's analytics"
            )
        
        result = await cv_storage_service.get_cv_analytics(user_id)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get CV analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get CV analytics"
        )


@router.get("/cv/searches/recent", response_model=Dict[str, Any])
async def get_recent_searches(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Lấy recent searches của user"""
    try:
        result = await cv_storage_service.get_recent_searches(
            current_user.user_id, 
            limit
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get recent searches: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recent searches"
        )


@router.post("/cv/{cv_id}/export", response_model=Dict[str, Any])
async def export_cv_data(
    cv_id: str,
    export_request: CVExportRequest,
    current_user: User = Depends(get_current_user)
):
    """Export CV data"""
    try:
        result = await cv_storage_service.export_cv_data(
            cv_id,
            current_user.user_id,
            export_request.format
        )
        
        if not result['success']:
            if 'not found' in result.get('error', '').lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result['error']
                )
            elif 'unauthorized' in result.get('error', '').lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=result['error']
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result['error']
                )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export CV data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export CV data"
        )


@router.get("/cv/health", response_model=Dict[str, str])
async def cv_storage_health_check():
    """Health check cho CV storage service"""
    try:
        # Test database connection
        # This would require implementing a health check method in repository
        return {
            'status': 'healthy',
            'service': 'cv_storage',
            'message': 'CV storage service is running'
        }
    except Exception as e:
        logger.error(f"CV storage health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'service': 'cv_storage',
            'error': str(e)
        }
