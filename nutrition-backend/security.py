# nutrition-backend/security.py
import bleach
import re
import html
from typing import Any, Dict, Union, List, Optional
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when security validation fails"""
    pass


class InputSanitizer:
    """Advanced input sanitization and validation"""

    # Extremely restrictive HTML settings
    ALLOWED_TAGS = []  # No HTML tags allowed
    ALLOWED_ATTRIBUTES = {}

    # SQL injection patterns (comprehensive list)
    SQL_INJECTION_PATTERNS = [
        # Basic SQL keywords
        r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|TRUNCATE|REPLACE)\b',
        # SQL comments
        r'(--|\/\*|\*\/|#)',
        # SQL operators and functions
        r'\b(OR|AND|NOT|XOR|LIKE|REGEXP|RLIKE|SOUNDS)\s+',
        # Boolean-based injection
        r'(\d+\s*=\s*\d+|[\'"`]\s*=\s*[\'"`])',
        r'\b(TRUE|FALSE|NULL)\b',
        # UNION-based injection
        r'\bUNION\s+(ALL\s+)?SELECT\b',
        # Time-based injection
        r'\b(SLEEP|DELAY|WAITFOR|BENCHMARK)\s*\(',
        # Database-specific functions
        r'\b(LOAD_FILE|INTO\s+OUTFILE|INTO\s+DUMPFILE)\b',
        r'\b(CHAR|ASCII|ORD|HEX|UNHEX|MD5|SHA1)\s*\(',
        # Error-based injection
        r'\b(EXTRACTVALUE|UPDATEXML|GEOMETRYCOLLECTION)\s*\(',
        # Stacked queries
        r';\s*(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE)',
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r'<\s*script[^>]*>.*?<\s*/\s*script\s*>',
        r'<\s*iframe[^>]*>.*?<\s*/\s*iframe\s*>',
        r'<\s*object[^>]*>.*?<\s*/\s*object\s*>',
        r'<\s*embed[^>]*>',
        r'<\s*link[^>]*>',
        r'<\s*meta[^>]*>',
        r'javascript\s*:',
        r'data\s*:',
        r'vbscript\s*:',
        r'on\w+\s*=',
        r'expression\s*\(',
        r'@import',
        r'binding\s*:',
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r'\.\./|\.\.\|',
        r'%2e%2e%2f|%2e%2e%5c',
        r'\.\.%2f|\.\.%5c',
        r'%252e%252e%252f',
    ]

    @classmethod
    def sanitize_string(cls, input_str: str, max_length: int = 500, field_name: str = "input") -> str:
        """Comprehensive string sanitization"""
        if not isinstance(input_str, str):
            raise HTTPException(
                status_code=400,
                detail=f"{field_name} must be a string, got {type(input_str).__name__}"
            )

        # Length validation
        if len(input_str) > max_length:
            raise HTTPException(
                status_code=400,
                detail=f"{field_name} too long (max {max_length} characters, got {len(input_str)})"
            )

        # Remove null bytes and control characters
        cleaned = input_str.replace('\x00', '').replace('\r', '').replace('\n', ' ')

        # HTML entity decode to catch encoded attacks
        cleaned = html.unescape(cleaned)

        # Remove all HTML tags and attributes
        cleaned = bleach.clean(
            cleaned,
            tags=cls.ALLOWED_TAGS,
            attributes=cls.ALLOWED_ATTRIBUTES,
            strip=True
        )

        # Check for SQL injection patterns
        cls._check_sql_injection(cleaned, field_name)

        # Check for XSS patterns
        cls._check_xss_patterns(cleaned, field_name)

        # Check for path traversal
        cls._check_path_traversal(cleaned, field_name)

        # Final cleanup
        cleaned = cleaned.strip()

        # Log suspicious attempts
        if cleaned != input_str.strip():
            logger.warning(f"Input sanitized for {field_name}: '{input_str[:50]}...' -> '{cleaned[:50]}...'")

        return cleaned

    @classmethod
    def _check_sql_injection(cls, text: str, field_name: str):
        """Check for SQL injection patterns"""
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                logger.error(f"SQL injection attempt detected in {field_name}: {text[:100]}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid characters detected in {field_name}. SQL-like patterns are not allowed."
                )

    @classmethod
    def _check_xss_patterns(cls, text: str, field_name: str):
        """Check for XSS patterns"""
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL):
                logger.error(f"XSS attempt detected in {field_name}: {text[:100]}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid characters detected in {field_name}. Script-like patterns are not allowed."
                )

    @classmethod
    def _check_path_traversal(cls, text: str, field_name: str):
        """Check for path traversal patterns"""
        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.error(f"Path traversal attempt detected in {field_name}: {text[:100]}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid path characters detected in {field_name}."
                )

    @classmethod
    def validate_user_id(cls, user_id: str) -> str:
        """Validate UUID format for user IDs"""
        if not user_id or not isinstance(user_id, str):
            raise HTTPException(status_code=400, detail="User ID is required")

        user_id = user_id.strip()

        # UUID format validation (both with and without hyphens)
        uuid_pattern = r'^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$'
        if not re.match(uuid_pattern, user_id, re.IGNORECASE):
            raise HTTPException(
                status_code=400,
                detail="User ID must be a valid UUID format"
            )

        return user_id.lower()

    @classmethod
    def validate_numeric_range(cls,
                               value: Union[int, float, str],
                               min_val: float,
                               max_val: float,
                               field_name: str) -> float:
        """Validate numeric input within range"""
        try:
            if isinstance(value, str):
                # Remove common non-numeric characters
                cleaned_value = re.sub(r'[^0-9.-]', '', value)
                num_value = float(cleaned_value)
            else:
                num_value = float(value)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail=f"{field_name} must be a valid number"
            )

        # Check for special float values
        if not (-float('inf') < num_value < float('inf')):
            raise HTTPException(
                status_code=400,
                detail=f"{field_name} must be a finite number"
            )

        if not min_val <= num_value <= max_val:
            raise HTTPException(
                status_code=400,
                detail=f"{field_name} must be between {min_val} and {max_val}, got {num_value}"
            )

        return num_value

    @classmethod
    def validate_email(cls, email: str) -> str:
        """Validate email format"""
        if not email or not isinstance(email, str):
            raise HTTPException(status_code=400, detail="Email is required")

        email = email.strip().lower()

        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise HTTPException(status_code=400, detail="Invalid email format")

        # Check for suspicious patterns
        if any(char in email for char in ['<', '>', '"', "'", '&']):
            raise HTTPException(status_code=400, detail="Email contains invalid characters")

        return email

    @classmethod
    def sanitize_recipe_data(cls, recipe_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize recipe-specific data"""
        sanitized = {}

        # Title validation
        if 'title' in recipe_data:
            sanitized['title'] = cls.sanitize_string(
                recipe_data['title'],
                max_length=200,
                field_name="recipe title"
            )

        # Ingredients validation
        if 'ingredients' in recipe_data:
            if isinstance(recipe_data['ingredients'], list):
                sanitized['ingredients'] = [
                    cls.sanitize_string(ingredient, max_length=200, field_name="ingredient")
                    for ingredient in recipe_data['ingredients']
                    if ingredient and isinstance(ingredient, str)
                ]
            else:
                sanitized['ingredients'] = cls.sanitize_string(
                    str(recipe_data['ingredients']),
                    max_length=2000,
                    field_name="ingredients"
                )

        # Directions validation
        if 'directions' in recipe_data:
            if isinstance(recipe_data['directions'], list):
                sanitized['directions'] = [
                    cls.sanitize_string(direction, max_length=500, field_name="direction")
                    for direction in recipe_data['directions']
                    if direction and isinstance(direction, str)
                ]
            else:
                sanitized['directions'] = cls.sanitize_string(
                    str(recipe_data['directions']),
                    max_length=5000,
                    field_name="directions"
                )

        # Numeric validations
        if 'servings' in recipe_data:
            sanitized['servings'] = cls.validate_numeric_range(
                recipe_data['servings'], 1, 50, "servings"
            )

        if 'prep_time' in recipe_data:
            sanitized['prep_time'] = cls.validate_numeric_range(
                recipe_data['prep_time'], 0, 720, "prep time (minutes)"
            )

        if 'cook_time' in recipe_data:
            sanitized['cook_time'] = cls.validate_numeric_range(
                recipe_data['cook_time'], 0, 720, "cook time (minutes)"
            )

        if 'budget' in recipe_data:
            sanitized['budget'] = cls.validate_numeric_range(
                recipe_data['budget'], 0.01, 1000, "budget"
            )

        # User ID validation
        if 'user_id' in recipe_data:
            sanitized['user_id'] = cls.validate_user_id(recipe_data['user_id'])

        return sanitized


# Global sanitizer instance
sanitizer = InputSanitizer()


# Convenience functions
def sanitize_string(text: str, max_length: int = 500, field_name: str = "input") -> str:
    """Convenience function for string sanitization"""
    return sanitizer.sanitize_string(text, max_length, field_name)


def validate_user_id(user_id: str) -> str:
    """Convenience function for user ID validation"""
    return sanitizer.validate_user_id(user_id)


def validate_numeric_range(value, min_val: float, max_val: float, field_name: str) -> float:
    """Convenience function for numeric validation"""
    return sanitizer.validate_numeric_range(value, min_val, max_val, field_name)


def sanitize_recipe_data(recipe_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for recipe data sanitization"""
    return sanitizer.sanitize_recipe_data(recipe_data)


# Export all
__all__ = [
    'InputSanitizer', 'SecurityError', 'sanitizer',
    'sanitize_string', 'validate_user_id', 'validate_numeric_range', 'sanitize_recipe_data'
]