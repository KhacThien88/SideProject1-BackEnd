from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Tuple
import time
import asyncio
from collections import defaultdict
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

rate_limit_store: Dict[str, Dict[str, float]] = defaultdict(lambda: {"count": 0, "reset_time": 0})


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = None, window_seconds: int = None):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute or settings.rate_limit_requests
        self.window_seconds = window_seconds or settings.rate_limit_window

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        
        current_time = time.time()
        
        if self._is_rate_limited(client_ip, current_time):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": self.window_seconds
                },
                headers={"Retry-After": str(self.window_seconds)}
            )
        
        response = await call_next(request)
        
        self._update_rate_limit(client_ip, current_time)
        
        return response

    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """Check if client is rate limited"""
        client_data = rate_limit_store[client_ip]
        
        if current_time >= client_data["reset_time"]:
            client_data["count"] = 0
            client_data["reset_time"] = current_time + self.window_seconds
        
        return client_data["count"] >= self.requests_per_minute

    def _update_rate_limit(self, client_ip: str, current_time: float):
        """Update rate limit counter"""
        client_data = rate_limit_store[client_ip]
        
        if current_time >= client_data["reset_time"]:
            client_data["count"] = 1
            client_data["reset_time"] = current_time + self.window_seconds
        else:
            client_data["count"] += 1


# Rate limiting decorator for specific endpoints
def rate_limit(requests_per_minute: int = None, window_seconds: int = None):
    """Decorator for rate limiting specific endpoints"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get request from kwargs
            request = kwargs.get('request')
            if not request:
                return await func(*args, **kwargs)
            
            client_ip = request.client.host
            current_time = time.time()
            
            # Check rate limit
            if RateLimitMiddleware(requests_per_minute, window_seconds)._is_rate_limited(client_ip, current_time):
                logger.warning(f"Rate limit exceeded for IP: {client_ip} on endpoint: {request.url.path}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later."
                )
            
            # Update rate limit
            RateLimitMiddleware(requests_per_minute, window_seconds)._update_rate_limit(client_ip, current_time)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
