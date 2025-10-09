"""
Validation utilities cho file uploads và data validation
"""

import os
from typing import Dict, Any, List, Optional
from fastapi import UploadFile
import re

# Constants for validation
MAX_EMAIL_LENGTH = 254
MIN_PASSWORD_LENGTH = 8
MAX_PHONE_DIGITS = 15
MIN_PHONE_DIGITS = 7
MAX_FILENAME_LENGTH = 255
MAX_INPUT_LENGTH = 255

# Common password blacklist
COMMON_PASSWORDS = {
    'password', '123456', '123456789', 'qwerty', 'abc123',
    'password123', 'admin', 'letmein', 'welcome', 'monkey'
}

# Dangerous patterns for input validation
DANGEROUS_PATTERNS = [
    r'<script.*?>.*?</script>',  # Script tags
    r'javascript:',  # JavaScript URLs
    r'on\w+\s*=',  # Event handlers
]


def validate_file_type(file: UploadFile, allowed_extensions: set = None) -> Dict[str, Any]:
    """
    Validate file type based on extension và MIME type
    
    Args:
        file: UploadFile object
        allowed_extensions: Set of allowed extensions (default: {'.pdf', '.jpg', '.jpeg', '.png'})
        
    Returns:
        Dict với validation result
    """
    if allowed_extensions is None:
        allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png'}
    
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
    """Validate email format"""
    if not email:
        return {"valid": False, "error": "Email is required"}
    
    # Email regex pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        return {"valid": False, "error": "Invalid email format"}
    
    # Check length
    if len(email) > MAX_EMAIL_LENGTH:
        return {"valid": False, "error": "Email too long"}
    
    return {"valid": True, "email": email.lower().strip()}


def validate_password_strength(password: str) -> Dict[str, Any]:
    """Validate password strength"""
    if not password:
        return {"valid": False, "error": "Password is required"}
    
    errors = []
    strength_score = 0
    
    # Length check
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")
    else:
        strength_score += 1
    
    # Character checks
    checks = [
        (r'[A-Z]', "uppercase letter"),
        (r'[a-z]', "lowercase letter"), 
        (r'\d', "number"),
        (r'[!@#$%^&*(),.?":{}|<>]', "special character")
    ]
    
    for pattern, description in checks:
        if not re.search(pattern, password):
            errors.append(f"Password must contain at least one {description}")
        else:
            strength_score += 1
    
    # Common password check
    if password.lower() in COMMON_PASSWORDS:
        errors.append("Password is too common")
        strength_score = 0
    
    # Determine strength level with reachable "very_strong"
    # Max strength_score is 5 (length + 4 character classes)
    strength_levels = ["weak", "medium", "strong", "very_strong"]
    if strength_score <= 1:
        strength_index = 0  # weak
    elif strength_score <= 2:
        strength_index = 1  # medium
    elif strength_score <= 4:
        strength_index = 2  # strong
    else:
        strength_index = 3  # very_strong
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "strength_score": strength_score,
        "strength_level": strength_levels[strength_index]
    }


def validate_phone_number(phone: str) -> Dict[str, Any]:
    """Validate phone number format"""
    if not phone:
        return {"valid": False, "error": "Phone number is required"}
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Check if it's a valid length
    if len(digits_only) < MIN_PHONE_DIGITS or len(digits_only) > MAX_PHONE_DIGITS:
        return {"valid": False, "error": f"Phone number must be between {MIN_PHONE_DIGITS} and {MAX_PHONE_DIGITS} digits"}
    
    return {"valid": True, "phone": digits_only, "formatted": phone.strip()}


def validate_user_input(text: str, field_name: str, max_length: int = MAX_INPUT_LENGTH) -> Dict[str, Any]:
    """Validate general user input"""
    if not text:
        return {"valid": False, "error": f"{field_name} is required"}
    
    # Check length
    if len(text) > max_length:
        return {"valid": False, "error": f"{field_name} is too long (max {max_length} characters)"}
    
    # Check for potentially dangerous content
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return {"valid": False, "error": f"{field_name} contains potentially dangerous content"}
    
    return {"valid": True, "text": text.strip()}


def sanitize_filename(filename: str) -> str:
    """Sanitize filename để tránh path traversal và special characters"""
    if not filename:
        return "unnamed_file"
    
    # Remove path components and special characters in one step
    filename = re.sub(r'[<>:"/\\|?*]', '_', os.path.basename(filename))
    filename = re.sub(r'_+', '_', filename).strip('_.')
    
    # Ensure filename is not empty
    if not filename:
        filename = "unnamed_file"
    
    # Limit length
    if len(filename) > MAX_FILENAME_LENGTH:
        name, ext = os.path.splitext(filename)
        filename = name[:MAX_FILENAME_LENGTH-len(ext)] + ext
    
    return filename

