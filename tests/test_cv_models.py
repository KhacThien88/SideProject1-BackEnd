"""
Tests for CV models, particularly score calculation logic
"""
import pytest
from datetime import date
from app.models.cv import (
    CVAnalysis,
    DocumentType,
    PersonalInfo,
    ContactInfo,
    WorkExperience,
    Education,
    EducationLevel,
    Skill,
    SkillCategory,
    QUALITY_SCORE_CONTACT_INFO,
    QUALITY_SCORE_PER_WORK_EXPERIENCE,
    QUALITY_SCORE_WORK_EXPERIENCE_MAX,
    QUALITY_SCORE_PER_SKILL,
    QUALITY_SCORE_SKILLS_MAX,
    QUALITY_SCORE_PER_EDUCATION,
    QUALITY_SCORE_EDUCATION_MAX,
    QUALITY_SCORE_MAX,
    MIN_RAW_TEXT_LENGTH,
)


class TestCVAnalysisScores:
    """Test CV analysis score calculations"""

    def test_quality_score_with_all_sections(self):
        """Test quality score calculation with all sections present"""
        # Create CV with all sections
        personal_info = PersonalInfo(
            full_name="John Doe",
            contact=ContactInfo(email="john@example.com", phone="1234567890")
        )
        
        work_exp = [
            WorkExperience(
                company="Company A",
                position="Developer",
                start_date=date(2020, 1, 1),
                end_date=date(2022, 1, 1)
            ),
            WorkExperience(
                company="Company B",
                position="Senior Developer",
                start_date=date(2022, 2, 1),
                is_current=True
            )
        ]
        
        skills = [
            Skill(name="Python", category=SkillCategory.TECHNICAL),
            Skill(name="FastAPI", category=SkillCategory.TECHNICAL),
            Skill(name="Leadership", category=SkillCategory.SOFT)
        ]
        
        education = [
            Education(
                institution="University A",
                degree="Bachelor",
                level=EducationLevel.BACHELOR,
                start_date=date(2016, 9, 1),
                end_date=date(2020, 6, 1)
            )
        ]
        
        cv = CVAnalysis(
            document_type=DocumentType.CV,
            personal_info=personal_info,
            work_experience=work_exp,
            skills=skills,
            education=education
        )
        
        # Calculate expected quality score
        expected_quality = (
            QUALITY_SCORE_CONTACT_INFO +  # 20 for contact info
            min(len(work_exp) * QUALITY_SCORE_PER_WORK_EXPERIENCE, QUALITY_SCORE_WORK_EXPERIENCE_MAX) +  # min(2*10, 40) = 20
            min(len(skills) * QUALITY_SCORE_PER_SKILL, QUALITY_SCORE_SKILLS_MAX) +  # min(3*2, 20) = 6
            min(len(education) * QUALITY_SCORE_PER_EDUCATION, QUALITY_SCORE_EDUCATION_MAX)  # min(1*10, 20) = 10
        )
        expected_quality = min(expected_quality, QUALITY_SCORE_MAX)  # 56
        
        assert cv.quality_score == expected_quality
        assert cv.completeness_score == 100.0  # All 4 fields present

    def test_quality_score_max_work_experience(self):
        """Test that work experience score caps at maximum"""
        personal_info = PersonalInfo(full_name="John Doe")
        
        # Create 5 work experiences (5 * 10 = 50, but max is 40)
        work_exp = [
            WorkExperience(
                company=f"Company {i}",
                position="Developer",
                start_date=date(2020, 1, 1),
                end_date=date(2021, 1, 1)
            )
            for i in range(5)
        ]
        
        cv = CVAnalysis(
            document_type=DocumentType.CV,
            personal_info=personal_info,
            work_experience=work_exp
        )
        
        # Quality should include only max work experience score
        expected_quality = min(
            len(work_exp) * QUALITY_SCORE_PER_WORK_EXPERIENCE,
            QUALITY_SCORE_WORK_EXPERIENCE_MAX
        )
        assert cv.quality_score == QUALITY_SCORE_WORK_EXPERIENCE_MAX

    def test_quality_score_max_skills(self):
        """Test that skills score caps at maximum"""
        # Create 15 skills (15 * 2 = 30, but max is 20)
        skills = [
            Skill(name=f"Skill {i}", category=SkillCategory.TECHNICAL)
            for i in range(15)
        ]
        
        cv = CVAnalysis(
            document_type=DocumentType.CV,
            skills=skills
        )
        
        # Quality should include only max skills score
        assert cv.quality_score == QUALITY_SCORE_SKILLS_MAX

    def test_quality_score_max_education(self):
        """Test that education score caps at maximum"""
        # Create 3 education entries (3 * 10 = 30, but max is 20)
        education = [
            Education(
                institution=f"University {i}",
                level=EducationLevel.BACHELOR
            )
            for i in range(3)
        ]
        
        cv = CVAnalysis(
            document_type=DocumentType.CV,
            education=education
        )
        
        # Quality should include only max education score
        assert cv.quality_score == QUALITY_SCORE_EDUCATION_MAX

    def test_quality_score_empty_cv(self):
        """Test quality score with minimal CV data"""
        cv = CVAnalysis(document_type=DocumentType.CV)
        
        assert cv.quality_score == 0
        assert cv.completeness_score == 0

    def test_completeness_score_partial(self):
        """Test completeness score with partial data"""
        personal_info = PersonalInfo(full_name="John Doe")
        skills = [Skill(name="Python", category=SkillCategory.TECHNICAL)]
        
        cv = CVAnalysis(
            document_type=DocumentType.CV,
            personal_info=personal_info,
            skills=skills
        )
        
        # 2 out of 4 required fields = 50%
        assert cv.completeness_score == 50.0


class TestCVContentValidation:
    """Test CV content validation"""

    def test_min_raw_text_length_valid(self):
        """Test that raw text with minimum length is accepted"""
        from app.models.cv import CVContent
        
        # Create text with exactly MIN_RAW_TEXT_LENGTH characters
        min_text = "x" * MIN_RAW_TEXT_LENGTH
        
        cv_content = CVContent(
            file_id="test-123",
            raw_text=min_text
        )
        
        assert len(cv_content.raw_text) == MIN_RAW_TEXT_LENGTH

    def test_min_raw_text_length_invalid(self):
        """Test that raw text shorter than minimum is rejected"""
        from app.models.cv import CVContent
        
        # Create text shorter than MIN_RAW_TEXT_LENGTH
        short_text = "x" * (MIN_RAW_TEXT_LENGTH - 1)
        
        with pytest.raises(ValueError, match=f"Raw text must be at least {MIN_RAW_TEXT_LENGTH} characters"):
            CVContent(
                file_id="test-123",
                raw_text=short_text
            )
