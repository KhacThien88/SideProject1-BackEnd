from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
import math

logger = logging.getLogger(__name__)


class JobFilterService:
    """Service for filtering and searching jobs with advanced criteria"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def filter_by_location(
        self, 
        jobs: List[Dict[str, Any]], 
        location: str, 
        radius_km: float = 50.0
    ) -> List[Dict[str, Any]]:
        """
        Filter jobs by location with radius support
        
        Args:
            jobs: List of job dictionaries
            location: Target location (city, address, or coordinates)
            radius_km: Search radius in kilometers
            
        Returns:
            Filtered list of jobs within the radius
        """
        try:
            self.logger.info(f"Filtering {len(jobs)} jobs by location: {location} (radius: {radius_km}km)")
            
            # TODO: Implement actual geographic filtering
            # This is a placeholder implementation
            
            # For now, return jobs that contain the location string
            filtered_jobs = []
            for job in jobs:
                job_location = job.get("location", "").lower()
                if location.lower() in job_location:
                    filtered_jobs.append(job)
            
            self.logger.info(f"Found {len(filtered_jobs)} jobs matching location criteria")
            return filtered_jobs
            
        except Exception as e:
            self.logger.error(f"Error filtering by location: {e}")
            return []
    
    def filter_by_salary_range(
        self, 
        jobs: List[Dict[str, Any]], 
        min_salary: Optional[float] = None,
        max_salary: Optional[float] = None,
        currency: str = "USD"
    ) -> List[Dict[str, Any]]:
        """
        Filter jobs by salary range with currency conversion
        
        Args:
            jobs: List of job dictionaries
            min_salary: Minimum salary threshold
            max_salary: Maximum salary threshold
            currency: Currency code (USD, EUR, VND, etc.)
            
        Returns:
            Filtered list of jobs within salary range
        """
        try:
            self.logger.info(f"Filtering jobs by salary range: {min_salary}-{max_salary} {currency}")
            
            filtered_jobs = []
            for job in jobs:
                job_salary = job.get("salary", {})
                job_min = job_salary.get("min")
                job_max = job_salary.get("max")
                job_currency = job_salary.get("currency", "USD")
                
                # Convert currencies if needed
                if job_currency != currency:
                    # TODO: Implement currency conversion
                    pass
                
                # Check if job salary overlaps with filter range
                if self._salary_overlaps(job_min, job_max, min_salary, max_salary):
                    filtered_jobs.append(job)
            
            self.logger.info(f"Found {len(filtered_jobs)} jobs matching salary criteria")
            return filtered_jobs
            
        except Exception as e:
            self.logger.error(f"Error filtering by salary: {e}")
            return []
    
    def filter_by_job_type(
        self, 
        jobs: List[Dict[str, Any]], 
        job_types: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Filter jobs by job type (full-time, part-time, contract, remote)
        
        Args:
            jobs: List of job dictionaries
            job_types: List of job types to filter by
            
        Returns:
            Filtered list of jobs matching job types
        """
        try:
            self.logger.info(f"Filtering jobs by types: {job_types}")
            
            filtered_jobs = []
            for job in jobs:
                job_type = job.get("job_type", "").lower()
                if any(jt.lower() in job_type for jt in job_types):
                    filtered_jobs.append(job)
            
            self.logger.info(f"Found {len(filtered_jobs)} jobs matching job type criteria")
            return filtered_jobs
            
        except Exception as e:
            self.logger.error(f"Error filtering by job type: {e}")
            return []
    
    def filter_by_experience_level(
        self, 
        jobs: List[Dict[str, Any]], 
        experience_level: str,
        cv_experience_years: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter jobs by experience level matching with CV analysis
        
        Args:
            jobs: List of job dictionaries
            experience_level: Target experience level
            cv_experience_years: Years of experience from CV
            
        Returns:
            Filtered list of jobs matching experience criteria
        """
        try:
            self.logger.info(f"Filtering jobs by experience level: {experience_level}")
            
            filtered_jobs = []
            for job in jobs:
                job_experience = job.get("required_experience", {})
                job_min_years = job_experience.get("min_years", 0)
                job_max_years = job_experience.get("max_years", 999)
                
                # Match experience level
                if self._experience_matches(experience_level, job_min_years, job_max_years, cv_experience_years):
                    filtered_jobs.append(job)
            
            self.logger.info(f"Found {len(filtered_jobs)} jobs matching experience criteria")
            return filtered_jobs
            
        except Exception as e:
            self.logger.error(f"Error filtering by experience: {e}")
            return []
    
    def filter_by_skills(
        self, 
        jobs: List[Dict[str, Any]], 
        required_skills: List[str],
        fuzzy_match: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Filter jobs by skills with fuzzy matching support
        
        Args:
            jobs: List of job dictionaries
            required_skills: List of required skills
            fuzzy_match: Enable fuzzy matching for similar skills
            
        Returns:
            Filtered list of jobs matching skills criteria
        """
        try:
            self.logger.info(f"Filtering jobs by skills: {required_skills} (fuzzy: {fuzzy_match})")
            
            filtered_jobs = []
            for job in jobs:
                job_skills = job.get("required_skills", [])
                
                if self._skills_match(required_skills, job_skills, fuzzy_match):
                    filtered_jobs.append(job)
            
            self.logger.info(f"Found {len(filtered_jobs)} jobs matching skills criteria")
            return filtered_jobs
            
        except Exception as e:
            self.logger.error(f"Error filtering by skills: {e}")
            return []
    
    def filter_by_date_range(
        self, 
        jobs: List[Dict[str, Any]], 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter jobs by posting date range
        
        Args:
            jobs: List of job dictionaries
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            Filtered list of jobs within date range
        """
        try:
            self.logger.info(f"Filtering jobs by date range: {start_date} to {end_date}")
            
            filtered_jobs = []
            for job in jobs:
                job_date = job.get("posted_date")
                if job_date:
                    job_datetime = datetime.fromisoformat(job_date.replace('Z', '+00:00'))
                    
                    if start_date and job_datetime < start_date:
                        continue
                    if end_date and job_datetime > end_date:
                        continue
                    
                    filtered_jobs.append(job)
            
            self.logger.info(f"Found {len(filtered_jobs)} jobs matching date criteria")
            return filtered_jobs
            
        except Exception as e:
            self.logger.error(f"Error filtering by date range: {e}")
            return []
    
    def apply_complex_filters(
        self, 
        jobs: List[Dict[str, Any]], 
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Apply complex filters with boolean logic support
        
        Args:
            jobs: List of job dictionaries
            filters: Dictionary containing filter criteria and logic
            
        Returns:
            Filtered list of jobs matching complex criteria
        """
        try:
            self.logger.info(f"Applying complex filters: {filters}")
            
            filtered_jobs = jobs.copy()
            
            # Apply location filter
            if "location" in filters:
                filtered_jobs = self.filter_by_location(
                    filtered_jobs, 
                    filters["location"], 
                    filters.get("radius_km", 50.0)
                )
            
            # Apply salary filter
            if "salary_range" in filters:
                salary_range = filters["salary_range"]
                filtered_jobs = self.filter_by_salary_range(
                    filtered_jobs,
                    salary_range.get("min"),
                    salary_range.get("max"),
                    salary_range.get("currency", "USD")
                )
            
            # Apply job type filter
            if "job_types" in filters:
                filtered_jobs = self.filter_by_job_type(filtered_jobs, filters["job_types"])
            
            # Apply experience filter
            if "experience_level" in filters:
                filtered_jobs = self.filter_by_experience_level(
                    filtered_jobs,
                    filters["experience_level"],
                    filters.get("cv_experience_years")
                )
            
            # Apply skills filter
            if "required_skills" in filters:
                filtered_jobs = self.filter_by_skills(
                    filtered_jobs,
                    filters["required_skills"],
                    filters.get("fuzzy_match", True)
                )
            
            # Apply date range filter
            if "date_range" in filters:
                date_range = filters["date_range"]
                start_date = datetime.fromisoformat(date_range["start"]) if date_range.get("start") else None
                end_date = datetime.fromisoformat(date_range["end"]) if date_range.get("end") else None
                filtered_jobs = self.filter_by_date_range(filtered_jobs, start_date, end_date)
            
            self.logger.info(f"Complex filtering completed: {len(filtered_jobs)} jobs remaining")
            return filtered_jobs
            
        except Exception as e:
            self.logger.error(f"Error applying complex filters: {e}")
            return []
    
    def _salary_overlaps(
        self, 
        job_min: Optional[float], 
        job_max: Optional[float],
        filter_min: Optional[float], 
        filter_max: Optional[float]
    ) -> bool:
        """Check if job salary range overlaps with filter range"""
        if not job_min and not job_max:
            return True  # No salary info, include by default
        
        if not filter_min and not filter_max:
            return True  # No filter, include all
        
        # Convert None to extreme values for comparison
        job_min = job_min or 0
        job_max = job_max or float('inf')
        filter_min = filter_min or 0
        filter_max = filter_max or float('inf')
        
        return not (job_max < filter_min or job_min > filter_max)
    
    def _experience_matches(
        self, 
        experience_level: str, 
        job_min_years: int, 
        job_max_years: int,
        cv_experience_years: Optional[int]
    ) -> bool:
        """Check if experience level matches job requirements"""
        if not cv_experience_years:
            return True  # No CV experience info, include by default
        
        # Map experience levels to years
        level_mapping = {
            "entry": (0, 2),
            "junior": (1, 3),
            "mid": (2, 5),
            "senior": (4, 8),
            "lead": (6, 12),
            "executive": (10, 20)
        }
        
        if experience_level.lower() in level_mapping:
            level_min, level_max = level_mapping[experience_level.lower()]
            return level_min <= cv_experience_years <= level_max
        
        # Fallback to job requirements
        return job_min_years <= cv_experience_years <= job_max_years
    
    def _skills_match(
        self, 
        required_skills: List[str], 
        job_skills: List[str], 
        fuzzy_match: bool
    ) -> bool:
        """Check if required skills match job skills"""
        if not required_skills:
            return True  # No skill requirements, include by default
        
        if not job_skills:
            return False  # Job has no skills listed
        
        required_lower = [skill.lower() for skill in required_skills]
        job_lower = [skill.lower() for skill in job_skills]
        
        if fuzzy_match:
            # Simple fuzzy matching - check if any required skill is contained in job skills
            return any(any(req_skill in job_skill for job_skill in job_lower) for req_skill in required_lower)
        else:
            # Exact matching
            return any(skill in job_lower for skill in required_lower)


# Global instance
job_filter_service = JobFilterService()
