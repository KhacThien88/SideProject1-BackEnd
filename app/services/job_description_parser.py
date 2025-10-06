import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class JobDescriptionParser:
    """Parser for extracting structured information from job descriptions"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Job requirement patterns
        self.requirement_patterns = {
            'experience_years': [
                r'(?i)(\d+)\+?\s*years?\s*(?:of\s*)?(?:experience|exp)',
                r'(?i)(\d+)\+?\s*years?\s*(?:in|of)\s*(?:relevant\s*)?(?:experience|exp)',
                r'(?i)minimum\s*(\d+)\s*years?\s*(?:of\s*)?(?:experience|exp)',
                r'(?i)at\s*least\s*(\d+)\s*years?\s*(?:of\s*)?(?:experience|exp)'
            ],
            'education_level': [
                r'(?i)(bachelor|master|phd|doctorate|associate|diploma|certificate)',
                r'(?i)(b\.?s\.?|m\.?s\.?|m\.?b\.?a\.?|ph\.?d\.?)',
                r'(?i)(degree|graduation|graduate|undergraduate)'
            ],
            'skills': [
                r'(?i)(required|must\s*have|essential|mandatory)\s*skills?',
                r'(?i)(technical\s*skills?|programming\s*skills?|software\s*skills?)',
                r'(?i)(proficiency\s*in|experience\s*with|knowledge\s*of)'
            ],
            'responsibilities': [
                r'(?i)(responsibilities|duties|key\s*responsibilities)',
                r'(?i)(what\s*you\'ll\s*do|what\s*you\s*will\s*do)',
                r'(?i)(role\s*and\s*responsibilities)'
            ],
            'benefits': [
                r'(?i)(benefits|perks|compensation|package)',
                r'(?i)(what\s*we\s*offer|we\s*provide|we\s*offer)',
                r'(?i)(salary|pay|compensation)'
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
        
        # Salary patterns
        self.salary_patterns = [
            r'(?i)\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:-\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?))?\s*(?:k|thousand|per\s*year|annually|yearly)',
            r'(?i)(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:-\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?))?\s*(?:USD|dollars?)',
            r'(?i)salary\s*:\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:-\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?))?',
            r'(?i)compensation\s*:\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:-\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?))?'
        ]
        
        # Location patterns
        self.location_patterns = [
            r'(?i)(remote|work\s*from\s*home|wfh|hybrid)',
            r'(?i)(on\s*site|office|in\s*office)',
            r'(?i)([A-Z][a-zA-Z\s,]+(?:,\s*[A-Z]{2})?)',
            r'(?i)(san\s*francisco|new\s*york|los\s*angeles|chicago|boston|seattle|austin|denver)'
        ]
        
        # Job type patterns
        self.job_type_patterns = [
            r'(?i)(full\s*time|fulltime|ft)',
            r'(?i)(part\s*time|parttime|pt)',
            r'(?i)(contract|contractor|freelance)',
            r'(?i)(internship|intern)',
            r'(?i)(temporary|temp)'
        ]
    
    def parse_job_description(self, job_text: str) -> Dict[str, Any]:
        """
        Parse job description text into structured data
        
        Args:
            job_text: Raw job description text
            
        Returns:
            Dictionary containing structured job data
        """
        try:
            self.logger.info("Starting job description parsing")
            
            # Clean and normalize text
            cleaned_text = self._clean_text(job_text)
            
            # Extract sections
            sections = self._extract_sections(cleaned_text)
            
            # Parse structured data
            parsed_data = {
                'raw_text': job_text,
                'cleaned_text': cleaned_text,
                'sections': sections,
                'requirements': self._extract_requirements(cleaned_text),
                'benefits': self._extract_benefits(cleaned_text),
                'salary_info': self._extract_salary_info(cleaned_text),
                'location_info': self._extract_location_info(cleaned_text),
                'job_type': self._extract_job_type(cleaned_text),
                'skills': self._extract_skills(cleaned_text),
                'metadata': {
                    'parsed_at': datetime.utcnow().isoformat(),
                    'total_words': len(cleaned_text.split()),
                    'total_characters': len(cleaned_text)
                }
            }
            
            self.logger.info(f"Job description parsing completed. Found {len(sections)} sections")
            return parsed_data
            
        except Exception as e:
            self.logger.error(f"Error parsing job description: {e}")
            return {
                'raw_text': job_text,
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
        """Extract sections from job description"""
        sections = {}
        
        # Split by common section headers
        section_headers = [
            'job description', 'about the role', 'role overview',
            'responsibilities', 'key responsibilities', 'what you\'ll do',
            'requirements', 'qualifications', 'must have', 'required skills',
            'benefits', 'perks', 'compensation', 'what we offer',
            'about us', 'company', 'team', 'culture'
        ]
        
        current_section = 'overview'
        current_content = []
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line is a section header
            is_header = False
            for header in section_headers:
                if header.lower() in line.lower():
                    # Save previous section
                    if current_content:
                        sections[current_section] = '\n'.join(current_content)
                    
                    # Start new section
                    current_section = header.lower().replace(' ', '_')
                    current_content = []
                    is_header = True
                    break
            
            if not is_header:
                current_content.append(line)
        
        # Save last section
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _extract_requirements(self, text: str) -> Dict[str, Any]:
        """Extract job requirements"""
        requirements = {
            'experience_years': None,
            'education_level': '',
            'required_skills': [],
            'preferred_skills': [],
            'certifications': [],
            'languages': []
        }
        
        # Extract experience years
        for pattern in self.requirement_patterns['experience_years']:
            match = re.search(pattern, text)
            if match:
                requirements['experience_years'] = int(match.group(1))
                break
        
        # Extract education level
        for pattern in self.requirement_patterns['education_level']:
            match = re.search(pattern, text)
            if match:
                requirements['education_level'] = match.group(1).lower()
                break
        
        # Extract skills
        skills_section = self._find_skills_section(text)
        if skills_section:
            requirements['required_skills'] = self._extract_skills_from_section(skills_section)
        
        return requirements
    
    def _extract_benefits(self, text: str) -> Dict[str, Any]:
        """Extract job benefits"""
        benefits = {
            'salary_range': None,
            'benefits_list': [],
            'perks': [],
            'insurance': [],
            'time_off': None,
            'retirement': False,
            'professional_development': False
        }
        
        # Extract salary
        salary_info = self._extract_salary_info(text)
        if salary_info:
            benefits['salary_range'] = salary_info
        
        # Extract benefits from text
        benefits_keywords = [
            'health insurance', 'dental insurance', 'vision insurance',
            'paid time off', 'vacation', 'sick leave', 'paternity leave',
            '401k', 'retirement plan', 'pension', 'stock options',
            'flexible hours', 'work from home', 'remote work',
            'professional development', 'training', 'conference',
            'gym membership', 'fitness', 'wellness'
        ]
        
        for keyword in benefits_keywords:
            if keyword.lower() in text.lower():
                benefits['benefits_list'].append(keyword)
        
        return benefits
    
    def _extract_salary_info(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract salary information"""
        for pattern in self.salary_patterns:
            match = re.search(pattern, text)
            if match:
                min_salary = match.group(1).replace(',', '')
                max_salary = match.group(2).replace(',', '') if match.group(2) else None
                
                # Convert to numbers
                try:
                    min_amount = float(min_salary)
                    max_amount = float(max_salary) if max_salary else None
                    
                    # Handle 'k' suffix
                    if 'k' in pattern.lower():
                        min_amount *= 1000
                        if max_amount:
                            max_amount *= 1000
                    
                    return {
                        'min_amount': min_amount,
                        'max_amount': max_amount,
                        'currency': 'USD',
                        'period': 'annual'
                    }
                except ValueError:
                    continue
        
        return None
    
    def _extract_location_info(self, text: str) -> Dict[str, Any]:
        """Extract location information"""
        location_info = {
            'is_remote': False,
            'is_hybrid': False,
            'is_onsite': False,
            'city': '',
            'state': '',
            'country': 'US'
        }
        
        # Check for remote work
        if re.search(r'(?i)(remote|work\s*from\s*home|wfh)', text):
            location_info['is_remote'] = True
        
        # Check for hybrid work
        if re.search(r'(?i)(hybrid|flexible\s*work)', text):
            location_info['is_hybrid'] = True
        
        # Check for onsite work
        if re.search(r'(?i)(on\s*site|office|in\s*office)', text):
            location_info['is_onsite'] = True
        
        # Extract city/state
        location_match = re.search(r'(?i)([A-Z][a-zA-Z\s]+(?:,\s*[A-Z]{2})?)', text)
        if location_match:
            location = location_match.group(1).strip()
            if ',' in location:
                city, state = location.split(',', 1)
                location_info['city'] = city.strip()
                location_info['state'] = state.strip()
            else:
                location_info['city'] = location
        
        return location_info
    
    def _extract_job_type(self, text: str) -> str:
        """Extract job type"""
        for pattern in self.job_type_patterns:
            match = re.search(pattern, text)
            if match:
                job_type = match.group(1).lower()
                if 'full' in job_type:
                    return 'full_time'
                elif 'part' in job_type:
                    return 'part_time'
                elif 'contract' in job_type:
                    return 'contract'
                elif 'intern' in job_type:
                    return 'internship'
                elif 'temp' in job_type:
                    return 'temporary'
        
        return 'full_time'  # Default
    
    def _extract_skills(self, text: str) -> Dict[str, List[str]]:
        """Extract skills from job description"""
        skills = {
            'required': [],
            'preferred': [],
            'categorized': {}
        }
        
        # Find skills section
        skills_section = self._find_skills_section(text)
        if skills_section:
            skills['required'] = self._extract_skills_from_section(skills_section)
        
        # Categorize skills
        all_skills = skills['required'] + skills['preferred']
        for skill in all_skills:
            for category, skill_list in self.skill_keywords.items():
                if skill.lower() in skill_list:
                    if category not in skills['categorized']:
                        skills['categorized'][category] = []
                    if skill not in skills['categorized'][category]:
                        skills['categorized'][category].append(skill)
        
        return skills
    
    def _find_skills_section(self, text: str) -> Optional[str]:
        """Find skills section in text"""
        skills_keywords = [
            'required skills', 'technical skills', 'must have',
            'qualifications', 'requirements', 'proficiency in',
            'experience with', 'knowledge of'
        ]
        
        lines = text.split('\n')
        skills_section = []
        in_skills_section = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if we're entering skills section
            for keyword in skills_keywords:
                if keyword.lower() in line.lower():
                    in_skills_section = True
                    break
            
            if in_skills_section:
                # Check if we're leaving skills section
                if any(word in line.lower() for word in ['benefits', 'compensation', 'about', 'company']):
                    break
                skills_section.append(line)
        
        return '\n'.join(skills_section) if skills_section else None
    
    def _extract_skills_from_section(self, section: str) -> List[str]:
        """Extract skills from a specific section"""
        skills = []
        
        # Extract skills from comma-separated lists
        comma_skills = re.findall(r'([^,\n]+)', section)
        for skill in comma_skills:
            skill = skill.strip()
            if len(skill) > 2 and skill not in skills:
                skills.append(skill)
        
        # Extract skills from bullet points
        bullet_skills = re.findall(r'(?:•|\*|\-)\s*([^\n]+)', section)
        for skill in bullet_skills:
            skill = skill.strip()
            if len(skill) > 2 and skill not in skills:
                skills.append(skill)
        
        return skills


# Global instance
job_description_parser = JobDescriptionParser()
