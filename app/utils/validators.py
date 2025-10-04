"""
Validation utilities cho file uploads và data validation
"""

import os
import magic
from typing import Dict, Any, List, Optional
from fastapi import UploadFile
import re


def validate_file_type(file: UploadFile, allowed_extensions: set = None) -> Dict[str, Any]:
    """
    Validate file type based on extension và MIME type
    
    Args:
        file: UploadFile object
        allowed_extensions: Set of allowed extensions (default: {'.pdf', '.doc', '.docx'})
        
    Returns:
        Dict với validation result
    """
    if allowed_extensions is None:
        allowed_extensions = {'.pdf', '.doc', '.docx'}
    
    try:
        if not file.filename:
            return {
                "valid": False,
                "error": "No filename provided"
            }
        
        # Check extension
        file_ext = os.path.splitext(file.filename.lower())[1]
        if file_ext not in allowed_extensions:
            return {
                "valid": False,
                "error": f"File type not allowed. Supported types: {', '.join(allowed_extensions)}"
            }
        
        return {
            "valid": True,
            "extension": file_ext
        }
        
    except Exception as e:
        return {
            "valid": False,
            "error": f"File type validation failed: {str(e)}"
        }


def validate_file_size(file: UploadFile, max_size_mb: int = 10) -> Dict[str, Any]:
    """
    Validate file size
    
    Args:
        file: UploadFile object
        max_size_mb: Maximum size in MB (default: 10)
        
    Returns:
        Dict với validation result
    """
    try:
        max_size_bytes = max_size_mb * 1024 * 1024
        
        # Get file size
        file_size = file.size
        if file_size is None:
            return {
                "valid": False,
                "error": "Could not determine file size"
            }
        
        if file_size > max_size_bytes:
            return {
                "valid": False,
                "error": f"File too large. Maximum size: {max_size_mb}MB"
            }
        
        if file_size == 0:
            return {
                "valid": False,
                "error": "Empty file not allowed"
            }
        
        return {
            "valid": True,
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2)
        }
        
    except Exception as e:
        return {
            "valid": False,
            "error": f"File size validation failed: {str(e)}"
        }


def validate_email(email: str) -> Dict[str, Any]:
    """
    Validate email format
    
    Args:
        email: Email string to validate
        
    Returns:
        Dict với validation result
    """
    try:
        if not email:
            return {
                "valid": False,
                "error": "Email is required"
            }
        
        # Email regex pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            return {
                "valid": False,
                "error": "Invalid email format"
            }
        
        # Check length
        if len(email) > 254:  # RFC 5321 limit
            return {
                "valid": False,
                "error": "Email too long"
            }
        
        return {
            "valid": True,
            "email": email.lower().strip()
        }
        
    except Exception as e:
        return {
            "valid": False,
            "error": f"Email validation failed: {str(e)}"
        }


def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    Validate password strength
    
    Args:
        password: Password string to validate
        
    Returns:
        Dict với validation result và strength info
    """
    try:
        if not password:
            return {
                "valid": False,
                "error": "Password is required"
            }
        
        errors = []
        strength_score = 0
        
        # Length check
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        else:
            strength_score += 1
        
        # Uppercase check
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        else:
            strength_score += 1
        
        # Lowercase check
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        else:
            strength_score += 1
        
        # Number check
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        else:
            strength_score += 1
        
        # Special character check
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        else:
            strength_score += 1
        
        # Common password check
        common_passwords = [
            'password', '123456', '123456789', 'qwerty', 'abc123',
            'password123', 'admin', 'letmein', 'welcome', 'monkey'
        ]
        
        if password.lower() in common_passwords:
            errors.append("Password is too common")
            strength_score = 0
        
        # Determine strength level
        if strength_score <= 2:
            strength_level = "weak"
        elif strength_score <= 3:
            strength_level = "medium"
        elif strength_score <= 4:
            strength_level = "strong"
        else:
            strength_level = "very_strong"
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "strength_score": strength_score,
            "strength_level": strength_level
        }
        
    except Exception as e:
        return {
            "valid": False,
            "error": f"Password validation failed: {str(e)}"
        }


def validate_phone_number(phone: str) -> Dict[str, Any]:
    """
    Validate phone number format
    
    Args:
        phone: Phone number string to validate
        
    Returns:
        Dict với validation result
    """
    try:
        if not phone:
            return {
                "valid": False,
                "error": "Phone number is required"
            }
        
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)
        
        # Check if it's a valid length (7-15 digits)
        if len(digits_only) < 7 or len(digits_only) > 15:
            return {
                "valid": False,
                "error": "Phone number must be between 7 and 15 digits"
            }
        
        return {
            "valid": True,
            "phone": digits_only,
            "formatted": phone.strip()
        }
        
    except Exception as e:
        return {
            "valid": False,
            "error": f"Phone validation failed: {str(e)}"
        }


def validate_user_input(text: str, field_name: str, max_length: int = 255) -> Dict[str, Any]:
    """
    Validate general user input
    
    Args:
        text: Text to validate
        field_name: Name of the field for error messages
        max_length: Maximum allowed length
        
    Returns:
        Dict với validation result
    """
    try:
        if not text:
            return {
                "valid": False,
                "error": f"{field_name} is required"
            }
        
        # Check length
        if len(text) > max_length:
            return {
                "valid": False,
                "error": f"{field_name} is too long (max {max_length} characters)"
            }
        
        # Check for potentially dangerous content
        dangerous_patterns = [
            r'<script.*?>.*?</script>',  # Script tags
            r'javascript:',  # JavaScript URLs
            r'on\w+\s*=',  # Event handlers
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return {
                    "valid": False,
                    "error": f"{field_name} contains potentially dangerous content"
                }
        
        return {
            "valid": True,
            "text": text.strip()
        }
        
    except Exception as e:
        return {
            "valid": False,
            "error": f"{field_name} validation failed: {str(e)}"
        }


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename để tránh path traversal và special characters
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    try:
        if not filename:
            return "unnamed_file"
        
        # Remove path components
        filename = os.path.basename(filename)
        
        # Remove special characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Remove multiple underscores
        filename = re.sub(r'_+', '_', filename)
        
        # Remove leading/trailing underscores and dots
        filename = filename.strip('_.')
        
        # Ensure filename is not empty
        if not filename:
            filename = "unnamed_file"
        
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext
        
        return filename
        
    except Exception as e:
        return f"sanitized_file_{hash(filename) % 10000}"

