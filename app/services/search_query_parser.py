import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class SearchQueryParser:
    """Parser for complex search queries with filters and operators"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Query operators
        self.operators = {
            'and': ['AND', 'and', '&', '+'],
            'or': ['OR', 'or', '|'],
            'not': ['NOT', 'not', '!', '-'],
            'equals': ['=', '==', 'equals', 'is'],
            'contains': ['contains', 'like', 'includes'],
            'greater_than': ['>', 'gt', 'greater than', 'more than'],
            'less_than': ['<', 'lt', 'less than', 'below'],
            'range': ['between', 'range', 'from', 'to']
        }
        
        # Field mappings
        self.field_mappings = {
            'title': ['title', 'job_title', 'position', 'role'],
            'company': ['company', 'employer', 'organization'],
            'location': ['location', 'city', 'state', 'country', 'place'],
            'salary': ['salary', 'pay', 'compensation', 'wage'],
            'skills': ['skills', 'technologies', 'tech', 'programming'],
            'experience': ['experience', 'exp', 'years', 'level'],
            'education': ['education', 'degree', 'qualification'],
            'job_type': ['type', 'employment', 'full_time', 'part_time'],
            'remote': ['remote', 'work_from_home', 'wfh', 'hybrid'],
            'date': ['date', 'posted', 'created', 'updated']
        }
        
        # Value parsers
        self.value_parsers = {
            'salary': self._parse_salary_value,
            'experience': self._parse_experience_value,
            'date': self._parse_date_value,
            'location': self._parse_location_value,
            'skills': self._parse_skills_value,
            'boolean': self._parse_boolean_value
        }
        
        # Common search patterns
        self.search_patterns = {
            'quoted_string': r'"([^"]+)"',
            'field_query': r'(\w+):\s*([^\s]+(?:\s+[^\s]+)*)',
            'range_query': r'(\w+):\s*(\d+)\s*-\s*(\d+)',
            'operator_query': r'(\w+)\s+(AND|OR|NOT)\s+(\w+)',
            'parentheses': r'\(([^)]+)\)'
        }
    
    def parse_search_query(self, query: str) -> Dict[str, Any]:
        """
        Parse complex search query into structured filters
        
        Args:
            query: Raw search query string
            
        Returns:
            Dictionary containing parsed query structure
        """
        try:
            self.logger.info(f"Parsing search query: {query}")
            
            # Clean query
            cleaned_query = self._clean_query(query)
            
            # Parse query structure
            parsed_query = {
                'raw_query': query,
                'cleaned_query': cleaned_query,
                'filters': [],
                'keywords': [],
                'operators': [],
                'field_queries': [],
                'range_queries': [],
                'boolean_logic': [],
                'metadata': {
                    'parsed_at': datetime.utcnow().isoformat(),
                    'query_length': len(query),
                    'complexity_score': 0
                }
            }
            
            # Extract different query components
            parsed_query['keywords'] = self._extract_keywords(cleaned_query)
            parsed_query['field_queries'] = self._extract_field_queries(cleaned_query)
            parsed_query['range_queries'] = self._extract_range_queries(cleaned_query)
            parsed_query['boolean_logic'] = self._extract_boolean_logic(cleaned_query)
            
            # Build filters
            parsed_query['filters'] = self._build_filters(parsed_query)
            
            # Calculate complexity score
            parsed_query['metadata']['complexity_score'] = self._calculate_complexity(parsed_query)
            
            self.logger.info(f"Query parsing completed. Found {len(parsed_query['filters'])} filters")
            return parsed_query
            
        except Exception as e:
            self.logger.error(f"Error parsing search query: {e}")
            return {
                'raw_query': query,
                'error': str(e),
                'parsed_at': datetime.utcnow().isoformat()
            }
    
    def _clean_query(self, query: str) -> str:
        """Clean and normalize query"""
        # Remove extra whitespace
        query = re.sub(r'\s+', ' ', query)
        
        # Normalize operators
        for operator, variants in self.operators.items():
            for variant in variants:
                if variant != operator:
                    query = query.replace(variant, operator)
        
        return query.strip()
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query"""
        keywords = []
        
        # Extract quoted strings
        quoted_matches = re.findall(self.search_patterns['quoted_string'], query)
        keywords.extend(quoted_matches)
        
        # Remove quoted strings from query for further processing
        query_without_quotes = re.sub(self.search_patterns['quoted_string'], '', query)
        
        # Extract field queries
        field_matches = re.findall(self.search_patterns['field_query'], query_without_quotes)
        query_without_fields = re.sub(self.search_patterns['field_query'], '', query_without_fields)
        
        # Extract remaining keywords
        remaining_words = query_without_fields.split()
        for word in remaining_words:
            if word.lower() not in ['and', 'or', 'not'] and len(word) > 2:
                keywords.append(word)
        
        return keywords
    
    def _extract_field_queries(self, query: str) -> List[Dict[str, Any]]:
        """Extract field:value queries"""
        field_queries = []
        
        matches = re.findall(self.search_patterns['field_query'], query)
        for field, value in matches:
            field_queries.append({
                'field': field.lower(),
                'value': value,
                'operator': 'equals',
                'parsed_value': self._parse_field_value(field.lower(), value)
            })
        
        return field_queries
    
    def _extract_range_queries(self, query: str) -> List[Dict[str, Any]]:
        """Extract range queries (field:min-max)"""
        range_queries = []
        
        matches = re.findall(self.search_patterns['range_query'], query)
        for field, min_val, max_val in matches:
            range_queries.append({
                'field': field.lower(),
                'min_value': min_val,
                'max_value': max_val,
                'operator': 'range',
                'parsed_min': self._parse_field_value(field.lower(), min_val),
                'parsed_max': self._parse_field_value(field.lower(), max_val)
            })
        
        return range_queries
    
    def _extract_boolean_logic(self, query: str) -> List[Dict[str, Any]]:
        """Extract boolean logic operators"""
        boolean_logic = []
        
        # Find AND/OR/NOT operators
        words = query.split()
        for i, word in enumerate(words):
            if word.lower() in ['and', 'or', 'not']:
                boolean_logic.append({
                    'operator': word.lower(),
                    'position': i,
                    'left_operand': words[i-1] if i > 0 else None,
                    'right_operand': words[i+1] if i < len(words)-1 else None
                })
        
        return boolean_logic
    
    def _build_filters(self, parsed_query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build structured filters from parsed query"""
        filters = []
        
        # Add field queries as filters
        for field_query in parsed_query['field_queries']:
            filters.append({
                'type': 'field',
                'field': field_query['field'],
                'operator': field_query['operator'],
                'value': field_query['parsed_value'],
                'raw_value': field_query['value']
            })
        
        # Add range queries as filters
        for range_query in parsed_query['range_queries']:
            filters.append({
                'type': 'range',
                'field': range_query['field'],
                'operator': 'range',
                'min_value': range_query['parsed_min'],
                'max_value': range_query['parsed_max'],
                'raw_min': range_query['min_value'],
                'raw_max': range_query['max_value']
            })
        
        # Add keyword filters
        if parsed_query['keywords']:
            filters.append({
                'type': 'keywords',
                'field': 'text',
                'operator': 'contains',
                'value': parsed_query['keywords'],
                'raw_value': ' '.join(parsed_query['keywords'])
            })
        
        return filters
    
    def _parse_field_value(self, field: str, value: str) -> Any:
        """Parse field value based on field type"""
        # Map field to parser
        field_type = self._get_field_type(field)
        
        if field_type in self.value_parsers:
            return self.value_parsers[field_type](value)
        
        return value
    
    def _get_field_type(self, field: str) -> str:
        """Get field type for parsing"""
        for field_type, field_names in self.field_mappings.items():
            if field in field_names:
                return field_type
        
        return 'string'
    
    def _parse_salary_value(self, value: str) -> Dict[str, Any]:
        """Parse salary value"""
        # Remove currency symbols and commas
        clean_value = re.sub(r'[$,]', '', value)
        
        # Check for range
        if '-' in clean_value:
            parts = clean_value.split('-')
            if len(parts) == 2:
                try:
                    return {
                        'min': float(parts[0].strip()),
                        'max': float(parts[1].strip()),
                        'currency': 'USD'
                    }
                except ValueError:
                    pass
        
        # Single value
        try:
            amount = float(clean_value)
            return {
                'amount': amount,
                'currency': 'USD'
            }
        except ValueError:
            return {'raw': value}
    
    def _parse_experience_value(self, value: str) -> Dict[str, Any]:
        """Parse experience value"""
        # Extract years
        years_match = re.search(r'(\d+)', value)
        if years_match:
            years = int(years_match.group(1))
            return {
                'years': years,
                'level': self._get_experience_level(years)
            }
        
        # Check for level keywords
        level_keywords = {
            'entry': ['entry', 'junior', 'jr', 'beginner'],
            'mid': ['mid', 'middle', 'intermediate'],
            'senior': ['senior', 'sr', 'lead', 'principal'],
            'executive': ['executive', 'director', 'vp', 'ceo']
        }
        
        for level, keywords in level_keywords.items():
            if any(keyword in value.lower() for keyword in keywords):
                return {'level': level}
        
        return {'raw': value}
    
    def _parse_date_value(self, value: str) -> Dict[str, Any]:
        """Parse date value"""
        # Relative dates
        if 'today' in value.lower():
            return {'date': datetime.utcnow().date()}
        elif 'yesterday' in value.lower():
            return {'date': (datetime.utcnow() - timedelta(days=1)).date()}
        elif 'week' in value.lower():
            return {'date': (datetime.utcnow() - timedelta(weeks=1)).date()}
        elif 'month' in value.lower():
            return {'date': (datetime.utcnow() - timedelta(days=30)).date()}
        
        # Specific dates
        date_patterns = [
            r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
            r'(\d{2})/(\d{2})/(\d{4})',   # MM/DD/YYYY
            r'(\d{1,2})/(\d{1,2})/(\d{4})'  # M/D/YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, value)
            if match:
                try:
                    if pattern.startswith(r'(\d{4})'):
                        year, month, day = match.groups()
                    else:
                        month, day, year = match.groups()
                    
                    return {'date': datetime(int(year), int(month), int(day)).date()}
                except ValueError:
                    continue
        
        return {'raw': value}
    
    def _parse_location_value(self, value: str) -> Dict[str, Any]:
        """Parse location value"""
        # Check for remote work
        if any(keyword in value.lower() for keyword in ['remote', 'wfh', 'work from home']):
            return {'type': 'remote'}
        
        # Check for hybrid work
        if 'hybrid' in value.lower():
            return {'type': 'hybrid'}
        
        # Parse city, state
        location_parts = value.split(',')
        if len(location_parts) == 2:
            return {
                'city': location_parts[0].strip(),
                'state': location_parts[1].strip()
            }
        
        return {'raw': value}
    
    def _parse_skills_value(self, value: str) -> List[str]:
        """Parse skills value"""
        # Split by common separators
        skills = re.split(r'[,;|]', value)
        return [skill.strip() for skill in skills if skill.strip()]
    
    def _parse_boolean_value(self, value: str) -> bool:
        """Parse boolean value"""
        true_values = ['true', 'yes', '1', 'on', 'enabled']
        false_values = ['false', 'no', '0', 'off', 'disabled']
        
        value_lower = value.lower()
        if value_lower in true_values:
            return True
        elif value_lower in false_values:
            return False
        
        return bool(value)
    
    def _get_experience_level(self, years: int) -> str:
        """Get experience level from years"""
        if years <= 2:
            return 'entry'
        elif years <= 5:
            return 'mid'
        elif years <= 10:
            return 'senior'
        else:
            return 'executive'
    
    def _calculate_complexity(self, parsed_query: Dict[str, Any]) -> int:
        """Calculate query complexity score"""
        complexity = 0
        
        # Base complexity
        complexity += len(parsed_query['keywords'])
        complexity += len(parsed_query['field_queries'])
        complexity += len(parsed_query['range_queries'])
        
        # Boolean logic complexity
        complexity += len(parsed_query['boolean_logic']) * 2
        
        # Nested complexity (parentheses, etc.)
        if '(' in parsed_query['raw_query'] or ')' in parsed_query['raw_query']:
            complexity += 3
        
        return complexity
    
    def validate_query(self, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parsed query"""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'suggestions': []
        }
        
        # Check for empty query
        if not parsed_query.get('keywords') and not parsed_query.get('field_queries'):
            validation_result['errors'].append('Query must contain keywords or field filters')
            validation_result['is_valid'] = False
        
        # Check for invalid field names
        for field_query in parsed_query.get('field_queries', []):
            field = field_query['field']
            if not any(field in fields for fields in self.field_mappings.values()):
                validation_result['warnings'].append(f'Unknown field: {field}')
        
        # Check for complex boolean logic
        if len(parsed_query.get('boolean_logic', [])) > 5:
            validation_result['warnings'].append('Complex boolean logic may impact performance')
        
        return validation_result


# Global instance
search_query_parser = SearchQueryParser()
