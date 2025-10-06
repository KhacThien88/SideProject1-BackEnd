"""
Unit tests for validators utility functions
"""
import pytest
from app.utils.validators import validate_password_strength


class TestPasswordStrength:
    """Test password strength validation"""
    
    def test_empty_password(self):
        """Test with empty password"""
        result = validate_password_strength("")
        assert result["valid"] is False
        assert result["error"] == "Password is required"
    
    def test_weak_password_short(self):
        """Test weak password - too short"""
        result = validate_password_strength("Ab1!")
        assert result["valid"] is False
        assert result["strength_level"] == "weak"
        assert "at least 8 characters" in result["errors"][0]
    
    def test_weak_password_only_lowercase(self):
        """Test weak password - only lowercase and length"""
        result = validate_password_strength("abcdefgh")
        assert result["valid"] is False
        # Score: 2 (length + lowercase)
        assert result["strength_score"] == 2
        # With 2 criteria, should be medium
        assert result["strength_level"] == "medium"
    
    def test_medium_password_two_criteria(self):
        """Test medium password - length + one character type"""
        result = validate_password_strength("Abcdefgh")
        assert result["valid"] is False
        # Score: 3 (length + uppercase + lowercase)
        assert result["strength_score"] == 3
        # With 3 criteria, should be strong
        assert result["strength_level"] == "strong"
    
    def test_strong_password_three_criteria(self):
        """Test strong password - length + two character types"""
        result = validate_password_strength("Abcdefg1")
        assert result["valid"] is False
        # Score: 4 (length + uppercase + lowercase + number)
        assert result["strength_score"] == 4
        # With 4 criteria, should be strong
        assert result["strength_level"] == "strong"
    
    def test_very_strong_password_four_criteria(self):
        """Test very strong password - length + all character types"""
        result = validate_password_strength("Abcdef1!")
        assert result["valid"] is True
        # Score: 5 (length + uppercase + lowercase + number + special)
        assert result["strength_score"] == 5
        # With all 5 criteria, should be very_strong
        assert result["strength_level"] == "very_strong"
    
    def test_very_strong_password_all_criteria(self):
        """Test very strong password - all criteria met with good length"""
        result = validate_password_strength("MyP@ssw0rd123!")
        assert result["valid"] is True
        assert result["strength_level"] == "very_strong"
        # Score: 5 (all criteria)
        assert result["strength_score"] == 5
    
    def test_common_password_resets_score(self):
        """Test that common passwords reset score to 0"""
        result = validate_password_strength("Password123!")
        assert result["valid"] is False
        assert result["strength_score"] == 0
        assert result["strength_level"] == "weak"
        assert "too common" in " ".join(result["errors"]).lower()
    
    def test_password_with_all_checks(self):
        """Test password that passes all criteria"""
        result = validate_password_strength("SecureP@ss123")
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["strength_score"] == 5
        assert result["strength_level"] == "very_strong"
    
    def test_score_to_level_mapping(self):
        """Test that scores map correctly to strength levels"""
        test_cases = [
            ("_", 0, "weak"),           # No criteria (underscore matches nothing)
            ("abcdefg", 1, "weak"),     # Only lowercase (too short for length criteria)
            ("abcdefgh", 2, "medium"),  # Length + lowercase
            ("Abcdefgh", 3, "strong"),  # Length + upper + lower
            ("Abcdefg1", 4, "strong"),  # Length + upper + lower + number
            ("Abcdef1!", 5, "very_strong"),  # All 5 criteria
        ]
        
        for password, expected_score, expected_level in test_cases:
            result = validate_password_strength(password)
            assert result["strength_score"] == expected_score, \
                f"Password '{password}' should have score {expected_score}, got {result['strength_score']}"
            assert result["strength_level"] == expected_level, \
                f"Password '{password}' with score {expected_score} should be '{expected_level}', got '{result['strength_level']}'"
