import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class CVContentParser:
    """Parser for extracting structured information from CV text"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Common section headers patterns
        self.section_patterns = {
            'experience': [
                r'(?i)(work\s+experience|professional\s+experience|employment\s+history|career\s+history|experience)',
                r'(?i)(employment|work\s+history|job\s+history)',
                r'(?i)(professional\s+background|career\s+summary)'
            ],
            'education': [
                r'(?i)(education|academic\s+background|qualifications|degrees)',
                r'(?i)(academic\s+qualifications|educational\s+background)',
                r'(?i)(university|college|school)'
            ],
            'skills': [
                r'(?i)(skills|technical\s+skills|core\s+competencies|competencies)',
                r'(?i)(technical\s+expertise|proficiencies|abilities)',
                r'(?i)(programming\s+skills|software\s+skills)'
            ],
            'projects': [
                r'(?i)(projects|portfolio|key\s+projects|notable\s+projects)',
                r'(?i)(project\s+experience|project\s+portfolio)'
            ],
            'certifications': [
                r'(?i)(certifications|certificates|professional\s+certifications)',
                r'(?i)(licenses|credentials|accreditations)'
            ],
            'languages': [
                r'(?i)(languages|language\s+skills|linguistic\s+abilities)',
                r'(?i)(spoken\s+languages|foreign\s+languages)'
            ],
            'achievements': [
                r'(?i)(achievements|awards|honors|recognition)',
                r'(?i)(accomplishments|notable\s+achievements)'
            ],
            'summary': [
                r'(?i)(summary|profile|objective|career\s+objective)',
                r'(?i)(professional\s+summary|executive\s+summary)',
                r'(?i)(about\s+me|personal\s+statement)'
            ]
        }
        
        # Common skill keywords
        self.skill_keywords = {
            'programming': ['python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust', 'swift', 'kotlin'],
            'web': ['html', 'css', 'react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask', 'spring', 'laravel'],
            'database': ['mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'sqlite', 'oracle', 'sql server'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'jenkins', 'ci/cd'],
            'mobile': ['android', 'ios', 'react native', 'flutter', 'xamarin', 'ionic'],
            'data': ['python', 'r', 'sql', 'pandas', 'numpy', 'tensorflow', 'pytorch', 'scikit-learn', 'spark'],
            'design': ['photoshop', 'illustrator', 'figma', 'sketch', 'adobe xd', 'ui/ux', 'wireframing'],
            'tools': ['git', 'github', 'gitlab', 'jira', 'confluence', 'slack', 'trello', 'notion']
        }
        
        # Experience patterns
        self.experience_patterns = {
            'company': r'(?i)(at\s+)?([A-Z][a-zA-Z\s&.,-]+(?:Inc|Corp|LLC|Ltd|Company|Co\.)?)',
            'position': r'(?i)(senior|junior|lead|principal|staff|associate|manager|director|vp|ceo|cto|cfo)\s+([a-zA-Z\s]+)',
            'duration': r'(?i)(\d{4})\s*[-–]\s*(\d{4}|present|current|now)',
            'location': r'(?i)(in|at|from)\s+([A-Z][a-zA-Z\s,]+)'
        }
    
    def parse_cv_content(self, raw_text: str) -> Dict[str, Any]:
        """
        Parse raw CV text into structured sections
        
        Args:
            raw_text: Raw text content from CV
            
        Returns:
            Dictionary containing structured CV data
        """
        try:
            self.logger.info("Starting CV content parsing")
            
            # Clean and normalize text
            cleaned_text = self._clean_text(raw_text)
            
            # Extract sections
            sections = self._extract_sections(cleaned_text)
            
            # Parse each section
            parsed_data = {
                'raw_text': raw_text,
                'cleaned_text': cleaned_text,
                'sections': {},
                'metadata': {
                    'parsed_at': datetime.utcnow().isoformat(),
                    'total_words': len(cleaned_text.split()),
                    'total_characters': len(cleaned_text)
                }
            }
            
            # Parse each section
            for section_name, section_content in sections.items():
                parsed_data['sections'][section_name] = self._parse_section(section_name, section_content)
            
            # Extract key information
            parsed_data['key_information'] = self._extract_key_information(parsed_data)
            
            self.logger.info(f"CV parsing completed. Found {len(sections)} sections")
            return parsed_data
            
        except Exception as e:
            self.logger.error(f"Error parsing CV content: {e}")
            return {
                'raw_text': raw_text,
                'error': str(e),
                'parsed_at': datetime.utcnow().isoformat()
            }
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,;:!?()-]', '', text)
        
        # Normalize line breaks
        text = re.sub(r'\n+', '\n', text)
        
        return text.strip()
    
    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract sections from CV text"""
        sections = {}
        lines = text.split('\n')
        
        current_section = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line is a section header
            section_found = self._identify_section(line)
            
            if section_found:
                # Save previous section
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content)
                
                # Start new section
                current_section = section_found
                current_content = []
            else:
                # Add to current section
                if current_section:
                    current_content.append(line)
                else:
                    # If no section identified yet, add to summary
                    if 'summary' not in sections:
                        sections['summary'] = []
                    sections['summary'].append(line)
        
        # Save last section
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content)
        
        # Convert summary list to string
        if 'summary' in sections and isinstance(sections['summary'], list):
            sections['summary'] = '\n'.join(sections['summary'])
        
        return sections
    
    def _identify_section(self, line: str) -> Optional[str]:
        """Identify if a line is a section header"""
        line_lower = line.lower()
        
        for section_name, patterns in self.section_patterns.items():
            for pattern in patterns:
                if re.search(pattern, line_lower):
                    return section_name
        
        return None
    
    def _parse_section(self, section_name: str, content: str) -> Dict[str, Any]:
        """Parse specific section content"""
        if section_name == 'experience':
            return self._parse_experience(content)
        elif section_name == 'education':
            return self._parse_education(content)
        elif section_name == 'skills':
            return self._parse_skills(content)
        elif section_name == 'projects':
            return self._parse_projects(content)
        elif section_name == 'certifications':
            return self._parse_certifications(content)
        elif section_name == 'languages':
            return self._parse_languages(content)
        elif section_name == 'achievements':
            return self._parse_achievements(content)
        else:
            return self._parse_generic(content)
    
    def _parse_experience(self, content: str) -> Dict[str, Any]:
        """Parse experience section"""
        experiences = []
        lines = content.split('\n')
        
        current_experience = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for company name
            company_match = re.search(self.experience_patterns['company'], line)
            if company_match:
                if current_experience:
                    experiences.append(current_experience)
                current_experience = {
                    'company': company_match.group(2).strip(),
                    'position': '',
                    'duration': '',
                    'location': '',
                    'description': []
                }
                continue
            
            # Check for position
            position_match = re.search(self.experience_patterns['position'], line)
            if position_match and current_experience:
                current_experience['position'] = line.strip()
                continue
            
            # Check for duration
            duration_match = re.search(self.experience_patterns['duration'], line)
            if duration_match and current_experience:
                current_experience['duration'] = line.strip()
                continue
            
            # Check for location
            location_match = re.search(self.experience_patterns['location'], line)
            if location_match and current_experience:
                current_experience['location'] = location_match.group(2).strip()
                continue
            
            # Add as description
            if current_experience:
                current_experience['description'].append(line)
        
        # Add last experience
        if current_experience:
            experiences.append(current_experience)
        
        return {
            'type': 'experience',
            'count': len(experiences),
            'items': experiences,
            'raw_content': content
        }
    
    def _parse_skills(self, content: str) -> Dict[str, Any]:
        """Parse skills section"""
        skills = []
        categorized_skills = {}
        
        # Extract skills from content
        words = re.findall(r'\b\w+\b', content.lower())
        
        for word in words:
            for category, skill_list in self.skill_keywords.items():
                if word in skill_list:
                    if category not in categorized_skills:
                        categorized_skills[category] = []
                    if word not in categorized_skills[category]:
                        categorized_skills[category].append(word)
                    if word not in skills:
                        skills.append(word)
        
        # Also extract skills from comma-separated lists
        comma_skills = re.findall(r'([^,\n]+)', content)
        for skill in comma_skills:
            skill = skill.strip().lower()
            if len(skill) > 2 and skill not in skills:
                skills.append(skill)
        
        return {
            'type': 'skills',
            'total_count': len(skills),
            'skills': skills,
            'categorized': categorized_skills,
            'raw_content': content
        }
    
    def _parse_education(self, content: str) -> Dict[str, Any]:
        """Parse education section"""
        education_items = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for degree patterns
            degree_patterns = [
                r'(?i)(bachelor|master|phd|doctorate|associate|diploma|certificate)',
                r'(?i)(b\.?s\.?|m\.?s\.?|m\.?b\.?a\.?|ph\.?d\.?)',
                r'(?i)(university|college|institute|school)'
            ]
            
            for pattern in degree_patterns:
                if re.search(pattern, line):
                    education_items.append({
                        'institution': line,
                        'degree': '',
                        'field': '',
                        'year': ''
                    })
                    break
        
        return {
            'type': 'education',
            'count': len(education_items),
            'items': education_items,
            'raw_content': content
        }
    
    def _parse_projects(self, content: str) -> Dict[str, Any]:
        """Parse projects section"""
        projects = []
        lines = content.split('\n')
        
        current_project = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Simple project detection (lines that look like project names)
            if len(line) < 100 and not line.endswith('.'):
                if current_project:
                    projects.append(current_project)
                current_project = {
                    'name': line,
                    'description': []
                }
            else:
                if current_project:
                    current_project['description'].append(line)
        
        if current_project:
            projects.append(current_project)
        
        return {
            'type': 'projects',
            'count': len(projects),
            'items': projects,
            'raw_content': content
        }
    
    def _parse_certifications(self, content: str) -> Dict[str, Any]:
        """Parse certifications section"""
        certifications = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line:
                certifications.append({
                    'name': line,
                    'issuer': '',
                    'date': ''
                })
        
        return {
            'type': 'certifications',
            'count': len(certifications),
            'items': certifications,
            'raw_content': content
        }
    
    def _parse_languages(self, content: str) -> Dict[str, Any]:
        """Parse languages section"""
        languages = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line:
                # Extract language and proficiency
                parts = re.split(r'[,\-–]', line)
                if parts:
                    languages.append({
                        'language': parts[0].strip(),
                        'proficiency': parts[1].strip() if len(parts) > 1 else '',
                        'raw': line
                    })
        
        return {
            'type': 'languages',
            'count': len(languages),
            'items': languages,
            'raw_content': content
        }
    
    def _parse_achievements(self, content: str) -> Dict[str, Any]:
        """Parse achievements section"""
        achievements = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line:
                achievements.append({
                    'achievement': line,
                    'date': '',
                    'organization': ''
                })
        
        return {
            'type': 'achievements',
            'count': len(achievements),
            'items': achievements,
            'raw_content': content
        }
    
    def _parse_generic(self, content: str) -> Dict[str, Any]:
        """Parse generic section"""
        return {
            'type': 'generic',
            'content': content,
            'word_count': len(content.split()),
            'raw_content': content
        }
    
    def _extract_key_information(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key information from parsed data"""
        key_info = {
            'total_experience_years': 0,
            'skill_count': 0,
            'education_level': '',
            'languages': [],
            'certifications': [],
            'key_skills': []
        }
        
        # Extract from sections
        sections = parsed_data.get('sections', {})
        
        # Calculate experience years
        if 'experience' in sections:
            experience_data = sections['experience']
            key_info['total_experience_years'] = experience_data.get('count', 0)
        
        # Extract skills
        if 'skills' in sections:
            skills_data = sections['skills']
            key_info['skill_count'] = skills_data.get('total_count', 0)
            key_info['key_skills'] = skills_data.get('skills', [])[:10]  # Top 10 skills
        
        # Extract languages
        if 'languages' in sections:
            languages_data = sections['languages']
            key_info['languages'] = [item.get('language', '') for item in languages_data.get('items', [])]
        
        # Extract certifications
        if 'certifications' in sections:
            cert_data = sections['certifications']
            key_info['certifications'] = [item.get('name', '') for item in cert_data.get('items', [])]
        
        return key_info


# Global instance
cv_content_parser = CVContentParser()
