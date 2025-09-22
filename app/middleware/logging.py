from fastapi import Request, Response
from fastapi.responses import JSONResponse
import time
import logging
import json
from typing import Dict, Any
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LoggingMiddleware:
    """Middleware for request/response logging"""
    
    def __init__(self):
        self.logger = logger

    async def __call__(self, request: Request, call_next):
        # Start time
        start_time = time.time()
        
        # Log request
        await self._log_request(request)
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            await self._log_response(request, response, process_time)
            
            return response
            
        except Exception as e:
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log error
            await self._log_error(request, e, process_time)
            
            # Return error response
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

    async def _log_request(self, request: Request):
        """Log incoming request"""
        try:
            # Get client info
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")
            
            # Get request body for POST/PUT requests (be careful with sensitive data)
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    # Only log body for non-sensitive endpoints
                    if not any(sensitive in str(request.url) for sensitive in ["/auth/login", "/auth/register"]):
                        body_bytes = await request.body()
                        if body_bytes:
                            body = body_bytes.decode("utf-8")[:1000]  # Limit body size
                except Exception:
                    body = "[Could not read body]"
            
            # Create log entry
            log_entry = {
                "type": "request",
                "timestamp": datetime.utcnow().isoformat(),
                "method": request.method,
                "url": str(request.url),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "headers": dict(request.headers),
                "body": body
            }
            
            self.logger.info(f"Request: {request.method} {request.url.path} from {client_ip}")
            self.logger.debug(f"Request details: {json.dumps(log_entry, indent=2)}")
            
        except Exception as e:
            self.logger.error(f"Error logging request: {e}")

    async def _log_response(self, request: Request, response: Response, process_time: float):
        """Log outgoing response"""
        try:
            # Get response info
            status_code = response.status_code
            content_type = response.headers.get("content-type", "unknown")
            
            # Create log entry
            log_entry = {
                "type": "response",
                "timestamp": datetime.utcnow().isoformat(),
                "method": request.method,
                "url": str(request.url),
                "status_code": status_code,
                "content_type": content_type,
                "process_time": round(process_time, 4),
                "headers": dict(response.headers)
            }
            
            # Log based on status code
            if status_code >= 500:
                self.logger.error(f"Response: {request.method} {request.url.path} -> {status_code} ({process_time:.4f}s)")
            elif status_code >= 400:
                self.logger.warning(f"Response: {request.method} {request.url.path} -> {status_code} ({process_time:.4f}s)")
            else:
                self.logger.info(f"Response: {request.method} {request.url.path} -> {status_code} ({process_time:.4f}s)")
            
            self.logger.debug(f"Response details: {json.dumps(log_entry, indent=2)}")
            
        except Exception as e:
            self.logger.error(f"Error logging response: {e}")

    async def _log_error(self, request: Request, error: Exception, process_time: float):
        """Log error"""
        try:
            # Create error log entry
            log_entry = {
                "type": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "method": request.method,
                "url": str(request.url),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "process_time": round(process_time, 4)
            }
            
            self.logger.error(f"Error: {request.method} {request.url.path} -> {type(error).__name__}: {str(error)} ({process_time:.4f}s)")
            self.logger.debug(f"Error details: {json.dumps(log_entry, indent=2)}")
            
        except Exception as e:
            self.logger.error(f"Error logging error: {e}")


# Security logging for authentication events
class SecurityLogger:
    """Logger for security-related events"""
    
    def __init__(self):
        self.logger = logging.getLogger("security")

    def log_login_attempt(self, email: str, success: bool, client_ip: str, user_agent: str):
        """Log login attempt"""
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"LOGIN_ATTEMPT: {status} - Email: {email}, IP: {client_ip}")
        
        if not success:
            self.logger.warning(f"FAILED_LOGIN: Email: {email}, IP: {client_ip}, User-Agent: {user_agent}")

    def log_registration_attempt(self, email: str, success: bool, client_ip: str):
        """Log registration attempt"""
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"REGISTRATION_ATTEMPT: {status} - Email: {email}, IP: {client_ip}")

    def log_token_refresh(self, user_id: str, success: bool, client_ip: str):
        """Log token refresh attempt"""
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"TOKEN_REFRESH: {status} - User: {user_id}, IP: {client_ip}")

    def log_logout(self, user_id: str, client_ip: str):
        """Log logout"""
        self.logger.info(f"LOGOUT: User: {user_id}, IP: {client_ip}")

    def log_suspicious_activity(self, activity: str, client_ip: str, details: str = ""):
        """Log suspicious activity"""
        self.logger.warning(f"SUSPICIOUS_ACTIVITY: {activity} - IP: {client_ip}, Details: {details}")


# Global security logger instance
security_logger = SecurityLogger()
