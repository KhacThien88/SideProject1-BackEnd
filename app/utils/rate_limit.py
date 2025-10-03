"""
Rate limiting utilities
"""
from fastapi import Request, HTTPException, status
from typing import Optional
import time
from datetime import datetime, timedelta

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def rate_limit_dependency(request: Request) -> bool:
    """
    Rate limiting dependency
    Returns True if request is allowed, raises HTTPException if rate limited
    """
    try:
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # For now, we'll implement a simple rate limiting
        # In production, you might want to use Redis or another caching solution
        
        # Check if we have rate limiting enabled
        if not hasattr(settings, 'rate_limit_requests') or settings.rate_limit_requests <= 0:
            return True
        
        # Simple in-memory rate limiting (not suitable for production)
        # This is a basic implementation - in production, use Redis or similar
        current_time = time.time()
        window_start = current_time - settings.rate_limit_window
        
        # For now, just return True (no rate limiting)
        # TODO: Implement proper rate limiting with Redis
        return True
        
    except Exception as e:
        logger.error(f"Rate limiting error: {str(e)}")
        # If rate limiting fails, allow the request
        return True


class RateLimitMiddleware:
    """Rate limiting middleware"""
    
    def __init__(self):
        self.requests = {}  # In-memory storage (not suitable for production)
    
    async def __call__(self, request: Request, call_next):
        """Process request with rate limiting"""
        try:
            # Get client IP
            client_ip = request.client.host if request.client else "unknown"
            
            # Check rate limit
            if not await self._check_rate_limit(client_ip):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later."
                )
            
            # Process request
            response = await call_next(request)
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limiting middleware error: {str(e)}")
            # If rate limiting fails, allow the request
            response = await call_next(request)
            return response
    
    async def _check_rate_limit(self, client_ip: str) -> bool:
        """Check if client is within rate limit"""
        try:
            current_time = time.time()
            window_start = current_time - settings.rate_limit_window
            
            # Clean old entries
            if client_ip in self.requests:
                self.requests[client_ip] = [
                    req_time for req_time in self.requests[client_ip]
                    if req_time > window_start
                ]
            else:
                self.requests[client_ip] = []
            
            # Check if within limit
            if len(self.requests[client_ip]) >= settings.rate_limit_requests:
                return False
            
            # Add current request
            self.requests[client_ip].append(current_time)
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check error: {str(e)}")
            # If rate limiting fails, allow the request
            return True
