import re
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, date
import json
import email_validator
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class DataValidationParser:
    """Parser for validating and sanitizing input data"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Validation patterns
        self.validation_patterns = {
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'phone': r'^[\+]?[1-9][\d]{0,15}$',
            'url': r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$',
            'uuid': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            'date_iso': r'^\d{4}-\d{2}-\d{2}$',
            'datetime_iso': r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?$',
            'alphanumeric': r'^[a-zA-Z0-9]+$',
            'alphabetic': r'^[a-zA-Z\s]+$',
            'numeric': r'^\d+$',
            'decimal': r'^\d+\.?\d*$',
            'currency': r'^\$?\d{1,3}(,\d{3})*(\.\d{2})?$',
            'zip_code': r'^\d{5}(-\d{4})?$',
            'ssn': r'^\d{3}-\d{2}-\d{4}$',
            'credit_card': r'^\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}$'
        }
        
        # Sanitization rules
        self.sanitization_rules = {
            'html': {
                'allowed_tags': ['b', 'i', 'em', 'strong', 'p', 'br'],
                'strip_tags': True
            },
            'sql_injection': {
                'patterns': [r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b)', r'(\b(UNION|OR|AND)\b.*\b(SELECT|INSERT|UPDATE|DELETE)\b)'],
                'action': 'remove'
            },
            'xss': {
                'patterns': [r'<script[^>]*>.*?</script>', r'javascript:', r'on\w+\s*='],
                'action': 'remove'
            },
            'whitespace': {
                'normalize': True,
                'trim': True
            }
        }
        
        # Field validation rules
        self.field_rules = {
            'email': {
                'required': True,
                'pattern': 'email',
                'max_length': 254,
                'sanitize': ['whitespace', 'html']
            },
            'password': {
                'required': True,
                'min_length': 8,
                'max_length': 128,
                'pattern': r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]',
                'sanitize': []
            },
            'name': {
                'required': True,
                'min_length': 2,
                'max_length': 100,
                'pattern': 'alphabetic',
                'sanitize': ['whitespace', 'html']
            },
            'phone': {
                'required': False,
                'pattern': 'phone',
                'sanitize': ['whitespace']
            },
            'url': {
                'required': False,
                'pattern': 'url',
                'max_length': 2048,
                'sanitize': ['whitespace', 'html']
            },
            'text': {
                'required': False,
                'max_length': 10000,
                'sanitize': ['whitespace', 'html', 'sql_injection', 'xss']
            },
            'number': {
                'required': False,
                'pattern': 'decimal',
                'sanitize': ['whitespace']
            },
            'date': {
                'required': False,
                'pattern': 'date_iso',
                'sanitize': ['whitespace']
            }
        }
    
    def validate_data(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data against schema
        
        Args:
            data: Data to validate
            schema: Validation schema
            
        Returns:
            Validation result with errors and sanitized data
        """
        try:
            self.logger.info("Starting data validation")
            
            validation_result = {
                'is_valid': True,
                'errors': [],
                'warnings': [],
                'sanitized_data': {},
                'metadata': {
                    'validated_at': datetime.utcnow().isoformat(),
                    'fields_validated': 0,
                    'fields_sanitized': 0
                }
            }
            
            # Validate each field
            for field_name, field_value in data.items():
                field_schema = schema.get(field_name, {})
                
                # Get field rules
                field_rules = self._get_field_rules(field_name, field_schema)
                
                # Validate field
                field_result = self._validate_field(field_name, field_value, field_rules)
                
                # Add to result
                if field_result['is_valid']:
                    validation_result['sanitized_data'][field_name] = field_result['sanitized_value']
                    validation_result['metadata']['fields_validated'] += 1
                    if field_result['was_sanitized']:
                        validation_result['metadata']['fields_sanitized'] += 1
                else:
                    validation_result['is_valid'] = False
                    validation_result['errors'].extend(field_result['errors'])
                
                validation_result['warnings'].extend(field_result['warnings'])
            
            # Check for missing required fields
            missing_fields = self._check_required_fields(data, schema)
            if missing_fields:
                validation_result['is_valid'] = False
                validation_result['errors'].extend(missing_fields)
            
            self.logger.info(f"Data validation completed. Valid: {validation_result['is_valid']}")
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Error validating data: {e}")
            return {
                'is_valid': False,
                'errors': [f'Validation error: {str(e)}'],
                'sanitized_data': {},
                'validated_at': datetime.utcnow().isoformat()
            }
    
    def _get_field_rules(self, field_name: str, field_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Get validation rules for field"""
        # Start with default rules
        rules = self.field_rules.get(field_name, {}).copy()
        
        # Override with schema rules
        rules.update(field_schema)
        
        return rules
    
    def _validate_field(self, field_name: str, field_value: Any, rules: Dict[str, Any]) -> Dict[str, Any]:
        """Validate individual field"""
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'sanitized_value': field_value,
            'was_sanitized': False
        }
        
        # Check if field is required
        if rules.get('required', False) and (field_value is None or field_value == ''):
            result['is_valid'] = False
            result['errors'].append(f'{field_name} is required')
            return result
        
        # Skip validation if field is empty and not required
        if field_value is None or field_value == '':
            return result
        
        # Sanitize value
        sanitized_value = self._sanitize_value(field_value, rules.get('sanitize', []))
        if sanitized_value != field_value:
            result['sanitized_value'] = sanitized_value
            result['was_sanitized'] = True
        
        # Validate length
        if isinstance(sanitized_value, str):
            length_result = self._validate_length(sanitized_value, rules)
            if not length_result['is_valid']:
                result['is_valid'] = False
                result['errors'].extend(length_result['errors'])
            result['warnings'].extend(length_result['warnings'])
        
        # Validate pattern
        if 'pattern' in rules:
            pattern_result = self._validate_pattern(sanitized_value, rules['pattern'])
            if not pattern_result['is_valid']:
                result['is_valid'] = False
                result['errors'].extend(pattern_result['errors'])
        
        # Validate type
        if 'type' in rules:
            type_result = self._validate_type(sanitized_value, rules['type'])
            if not type_result['is_valid']:
                result['is_valid'] = False
                result['errors'].extend(type_result['errors'])
        
        # Validate range
        if 'min' in rules or 'max' in rules:
            range_result = self._validate_range(sanitized_value, rules)
            if not range_result['is_valid']:
                result['is_valid'] = False
                result['errors'].extend(range_result['errors'])
        
        return result
    
    def _sanitize_value(self, value: Any, sanitize_rules: List[str]) -> Any:
        """Sanitize value based on rules"""
        if not isinstance(value, str):
            return value
        
        sanitized = value
        
        for rule in sanitize_rules:
            if rule == 'whitespace':
                sanitized = self._sanitize_whitespace(sanitized)
            elif rule == 'html':
                sanitized = self._sanitize_html(sanitized)
            elif rule == 'sql_injection':
                sanitized = self._sanitize_sql_injection(sanitized)
            elif rule == 'xss':
                sanitized = self._sanitize_xss(sanitized)
        
        return sanitized
    
    def _sanitize_whitespace(self, value: str) -> str:
        """Sanitize whitespace"""
        # Normalize whitespace
        value = re.sub(r'\s+', ' ', value)
        
        # Trim
        value = value.strip()
        
        return value
    
    def _sanitize_html(self, value: str) -> str:
        """Sanitize HTML"""
        # Remove all HTML tags except allowed ones
        allowed_tags = self.sanitization_rules['html']['allowed_tags']
        
        # Remove script tags
        value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove other dangerous tags
        value = re.sub(r'<[^>]*>', '', value)
        
        return value
    
    def _sanitize_sql_injection(self, value: str) -> str:
        """Sanitize SQL injection attempts"""
        patterns = self.sanitization_rules['sql_injection']['patterns']
        
        for pattern in patterns:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        
        return value
    
    def _sanitize_xss(self, value: str) -> str:
        """Sanitize XSS attempts"""
        patterns = self.sanitization_rules['xss']['patterns']
        
        for pattern in patterns:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        
        return value
    
    def _validate_length(self, value: str, rules: Dict[str, Any]) -> Dict[str, Any]:
        """Validate string length"""
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        length = len(value)
        
        if 'min_length' in rules and length < rules['min_length']:
            result['is_valid'] = False
            result['errors'].append(f'Minimum length is {rules["min_length"]}, got {length}')
        
        if 'max_length' in rules and length > rules['max_length']:
            result['is_valid'] = False
            result['errors'].append(f'Maximum length is {rules["max_length"]}, got {length}')
        
        return result
    
    def _validate_pattern(self, value: Any, pattern: str) -> Dict[str, Any]:
        """Validate value against pattern"""
        result = {
            'is_valid': True,
            'errors': []
        }
        
        if isinstance(value, str):
            # Get pattern from validation_patterns
            regex_pattern = self.validation_patterns.get(pattern, pattern)
            
            if not re.match(regex_pattern, value):
                result['is_valid'] = False
                result['errors'].append(f'Value does not match required pattern: {pattern}')
        
        return result
    
    def _validate_type(self, value: Any, expected_type: str) -> Dict[str, Any]:
        """Validate value type"""
        result = {
            'is_valid': True,
            'errors': []
        }
        
        type_mapping = {
            'string': str,
            'integer': int,
            'float': float,
            'boolean': bool,
            'date': date,
            'datetime': datetime,
            'list': list,
            'dict': dict
        }
        
        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type and not isinstance(value, expected_python_type):
            result['is_valid'] = False
            result['errors'].append(f'Expected {expected_type}, got {type(value).__name__}')
        
        return result
    
    def _validate_range(self, value: Any, rules: Dict[str, Any]) -> Dict[str, Any]:
        """Validate numeric range"""
        result = {
            'is_valid': True,
            'errors': []
        }
        
        if isinstance(value, (int, float)):
            if 'min' in rules and value < rules['min']:
                result['is_valid'] = False
                result['errors'].append(f'Value must be >= {rules["min"]}, got {value}')
            
            if 'max' in rules and value > rules['max']:
                result['is_valid'] = False
                result['errors'].append(f'Value must be <= {rules["max"]}, got {value}')
        
        return result
    
    def _check_required_fields(self, data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """Check for missing required fields"""
        missing_fields = []
        
        for field_name, field_schema in schema.items():
            if field_schema.get('required', False) and field_name not in data:
                missing_fields.append(f'Required field missing: {field_name}')
        
        return missing_fields
    
    def validate_email(self, email: str) -> Dict[str, Any]:
        """Validate email address"""
        result = {
            'is_valid': True,
            'errors': [],
            'sanitized_email': email
        }
        
        try:
            # Use email-validator library
            validated_email = email_validator.validate_email(email)
            result['sanitized_email'] = validated_email.email
        except email_validator.EmailNotValidError as e:
            result['is_valid'] = False
            result['errors'].append(f'Invalid email: {str(e)}')
        
        return result
    
    def validate_url(self, url: str) -> Dict[str, Any]:
        """Validate URL"""
        result = {
            'is_valid': True,
            'errors': [],
            'sanitized_url': url
        }
        
        try:
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                result['is_valid'] = False
                result['errors'].append('Invalid URL format')
        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f'URL validation error: {str(e)}')
        
        return result
    
    def validate_phone(self, phone: str) -> Dict[str, Any]:
        """Validate phone number"""
        result = {
            'is_valid': True,
            'errors': [],
            'sanitized_phone': phone
        }
        
        # Remove all non-digit characters except +
        clean_phone = re.sub(r'[^\d+]', '', phone)
        
        # Check if it matches phone pattern
        if not re.match(self.validation_patterns['phone'], clean_phone):
            result['is_valid'] = False
            result['errors'].append('Invalid phone number format')
        
        result['sanitized_phone'] = clean_phone
        return result
    
    def validate_date(self, date_str: str) -> Dict[str, Any]:
        """Validate date string"""
        result = {
            'is_valid': True,
            'errors': [],
            'parsed_date': None
        }
        
        try:
            # Try to parse ISO date
            parsed_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
            result['parsed_date'] = parsed_date
        except ValueError:
            result['is_valid'] = False
            result['errors'].append('Invalid date format. Use YYYY-MM-DD')
        
        return result
    
    def validate_json(self, json_str: str) -> Dict[str, Any]:
        """Validate JSON string"""
        result = {
            'is_valid': True,
            'errors': [],
            'parsed_json': None
        }
        
        try:
            parsed_json = json.loads(json_str)
            result['parsed_json'] = parsed_json
        except json.JSONDecodeError as e:
            result['is_valid'] = False
            result['errors'].append(f'Invalid JSON: {str(e)}')
        
        return result


# Global instance
data_validation_parser = DataValidationParser()
