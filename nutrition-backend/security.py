# nutrition-backend/security.py
import json
import bleach
import re
import html
import urllib.parse
from typing import Any, Dict, Union, List, Optional
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when security validation fails"""
    pass


class ValidationError(Exception):
    """Custom validation error that matches the exceptions module"""

    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(message)
        self.message = message
        self.field = field
        self.value = value


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

    # Path traversal patterns - FIXED VERSION
    PATH_TRAVERSAL_PATTERNS = [
        # Basic path traversal (Unix and Windows)
        r'\.\.',  # Any occurrence of two dots
        # URL encoded variations
        r'%2e%2e',  # URL encoded ..
        r'%252e%252e',  # Double URL encoded ..
        # Multiple dots pattern (like ....//....//..../)
        r'\.{3,}',  # Three or more consecutive dots
        # Additional path patterns
        r'\.\./',  # ../
        r'\.\.\\',  # ..\
        r'%2e%2e%2f',  # URL encoded ../
        r'%2e%2e%5c',  # URL encoded ..\
    ]

    @classmethod
    def sanitize_string(cls, input_str: str, max_length: int = 500, field_name: str = "input") -> str:
        """Comprehensive string sanitization"""
        if not isinstance(input_str, str):
            raise ValidationError(
                f"{field_name} must be a string, got {type(input_str).__name__}",
                field=field_name,
                value=type(input_str).__name__
            )

        # Length validation
        if len(input_str) > max_length:
            raise ValidationError(
                f"{field_name} too long (max {max_length} characters, got {len(input_str)})",
                field=field_name,
                value=len(input_str)
            )

        # Remove null bytes and control characters
        cleaned = input_str.replace('\x00', '').replace('\r', '').replace('\n', ' ')

        # HTML entity decode to catch encoded attacks
        decoded_input = html.unescape(cleaned)

        # *** SECURITY CHECKS BEFORE CLEANING ***
        # Check for XSS patterns on ORIGINAL input (before bleach strips tags)
        cls._check_xss_patterns(decoded_input, field_name)

        # Check for SQL injection patterns
        cls._check_sql_injection(decoded_input, field_name)

        # Check for path traversal
        cls._check_path_traversal(decoded_input, field_name)

        # *** NOW CLEAN THE INPUT ***
        # Remove all HTML tags and attributes
        cleaned = bleach.clean(
            decoded_input,
            tags=cls.ALLOWED_TAGS,
            attributes=cls.ALLOWED_ATTRIBUTES,
            strip=True
        )

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
                raise ValidationError(
                    f"Invalid characters detected in {field_name}. SQL-like patterns are not allowed.",
                    field=field_name,
                    value=text[:100]
                )

    @classmethod
    def _check_xss_patterns(cls, text: str, field_name: str):
        """Check for XSS patterns"""
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL):
                logger.error(f"XSS attempt detected in {field_name}: {text[:100]}")
                raise ValidationError(
                    f"Invalid characters detected in {field_name}. Script-like patterns are not allowed.",
                    field=field_name,
                    value=text[:100]
                )

    @classmethod
    def _check_path_traversal(cls, text: str, field_name: str):
        """Check for path traversal patterns - FIXED VERSION"""
        # Check original text first
        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.error(f"Path traversal attempt detected in {field_name}: {text[:100]}")
                raise ValidationError(
                    f"Invalid path characters detected in {field_name}.",
                    field=field_name,
                    value=text[:100]
                )

        # Also check URL decoded version to catch encoded attacks
        try:
            decoded_text = urllib.parse.unquote(text)
            if decoded_text != text:  # Only check if decoding changed something
                for pattern in cls.PATH_TRAVERSAL_PATTERNS:
                    if re.search(pattern, decoded_text, re.IGNORECASE):
                        logger.error(
                            f"Path traversal attempt (URL decoded) detected in {field_name}: {decoded_text[:100]}")
                        raise ValidationError(
                            f"Invalid path characters detected in {field_name}.",
                            field=field_name,
                            value=decoded_text[:100]
                        )
        except Exception:
            # If URL decoding fails, continue with original checks
            pass

    @classmethod
    def validate_user_id(cls, user_id: str) -> str:
        """Validate UUID format for user IDs"""
        if not user_id or not isinstance(user_id, str):
            raise ValidationError("User ID is required", field="user_id")

        user_id = user_id.strip()

        # UUID format validation (both with and without hyphens)
        uuid_pattern = r'^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$'
        if not re.match(uuid_pattern, user_id, re.IGNORECASE):
            raise ValidationError(
                "User ID must be a valid UUID format",
                field="user_id",
                value=user_id
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
            raise ValidationError(
                f"{field_name} must be a valid number",
                field=field_name,
                value=value
            )

        # Check for special float values
        if not (-float('inf') < num_value < float('inf')):
            raise ValidationError(
                f"{field_name} must be a finite number",
                field=field_name,
                value=num_value
            )

        if not min_val <= num_value <= max_val:
            raise ValidationError(
                f"{field_name} must be between {min_val} and {max_val}, got {num_value}",
                field=field_name,
                value=num_value
            )

        return num_value

    @classmethod
    def validate_email(cls, email: str) -> str:
        """Validate email format"""
        if not email or not isinstance(email, str):
            raise ValidationError("Email is required", field="email")

        email = email.strip().lower()

        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError("Invalid email format", field="email", value=email)

        # Check for suspicious patterns
        if any(char in email for char in ['<', '>', '"', "'", '&']):
            raise ValidationError("Email contains invalid characters", field="email", value=email)

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

        # Numeric field validation
        if 'servings' in recipe_data:
            sanitized['servings'] = cls.validate_numeric_range(
                recipe_data['servings'], 1, 50, "servings"
            )

        if 'prep_time' in recipe_data:
            sanitized['prep_time'] = cls.validate_numeric_range(
                recipe_data['prep_time'], 0, 300, "prep_time"
            )

        if 'cook_time' in recipe_data:
            sanitized['cook_time'] = cls.validate_numeric_range(
                recipe_data['cook_time'], 0, 600, "cook_time"
            )

        if 'budget' in recipe_data:
            sanitized['budget'] = cls.validate_numeric_range(
                recipe_data['budget'], 1.0, 1000.0, "budget"
            )

        return sanitized

    @classmethod
    def validate_json_field(cls, json_str: str, field_name: str, max_size: int = 10000) -> Dict[str, Any]:
        """Validate and parse JSON field"""
        if not json_str:
            return {}

        if len(json_str) > max_size:
            raise ValidationError(
                f"{field_name} JSON too large (max {max_size} characters)",
                field=field_name
            )

        try:
            parsed = json.loads(json_str)
            if not isinstance(parsed, dict):
                raise ValidationError(
                    f"{field_name} must be a JSON object",
                    field=field_name
                )
            return parsed
        except json.JSONDecodeError as e:
            raise ValidationError(
                f"Invalid JSON in {field_name}: {str(e)}",
                field=field_name
            )

    @classmethod
    def validate_list_field(cls, list_data: Any, field_name: str, max_items: int = 100, item_max_length: int = 200) -> \
    List[str]:
        """Validate list field"""
        if not list_data:
            return []

        if not isinstance(list_data, list):
            raise ValidationError(
                f"{field_name} must be a list",
                field=field_name
            )

        if len(list_data) > max_items:
            raise ValidationError(
                f"{field_name} too many items (max {max_items})",
                field=field_name
            )

        validated_items = []
        for i, item in enumerate(list_data):
            if not isinstance(item, str):
                raise ValidationError(
                    f"{field_name}[{i}] must be a string",
                    field=f"{field_name}[{i}]"
                )

            validated_item = cls.sanitize_string(
                item,
                max_length=item_max_length,
                field_name=f"{field_name}[{i}]"
            )
            validated_items.append(validated_item)

        return validated_items

    @classmethod
    def validate_ingredient_list(cls, ingredients: Any) -> List[Dict[str, Any]]:
        """Validate ingredient list with structured data"""
        if not ingredients:
            return []

        if not isinstance(ingredients, list):
            raise ValidationError("Ingredients must be a list", field="ingredients")

        if len(ingredients) > 50:
            raise ValidationError(
                "Too many ingredients (max 50)",
                field="ingredients"
            )

        validated_ingredients = []
        for i, ingredient in enumerate(ingredients):
            if isinstance(ingredient, str):
                # Simple string ingredient
                validated_ingredient = {
                    'name': cls.sanitize_string(
                        ingredient,
                        max_length=200,
                        field_name=f"ingredient[{i}]"
                    ),
                    'amount': None,
                    'unit': None
                }
            elif isinstance(ingredient, dict):
                # Structured ingredient
                validated_ingredient = {}

                # Required name field
                if 'name' not in ingredient:
                    raise ValidationError(
                        f"Ingredient[{i}] missing required 'name' field",
                        field=f"ingredient[{i}].name"
                    )

                validated_ingredient['name'] = cls.sanitize_string(
                    ingredient['name'],
                    max_length=200,
                    field_name=f"ingredient[{i}].name"
                )

                # Optional amount field
                if 'amount' in ingredient and ingredient['amount'] is not None:
                    validated_ingredient['amount'] = cls.validate_numeric_range(
                        ingredient['amount'],
                        0.01, 1000.0,
                        f"ingredient[{i}].amount"
                    )
                else:
                    validated_ingredient['amount'] = None

                # Optional unit field
                if 'unit' in ingredient and ingredient['unit']:
                    validated_ingredient['unit'] = cls.sanitize_string(
                        ingredient['unit'],
                        max_length=50,
                        field_name=f"ingredient[{i}].unit"
                    )
                else:
                    validated_ingredient['unit'] = None
            else:
                raise ValidationError(
                    f"Ingredient[{i}] must be string or object",
                    field=f"ingredient[{i}]"
                )

            validated_ingredients.append(validated_ingredient)

        return validated_ingredients


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


def validate_json_field(json_str: str, field_name: str, max_size: int = 10000) -> Dict[str, Any]:
    """Convenience function for JSON validation"""
    return sanitizer.validate_json_field(json_str, field_name, max_size)


def validate_list_field(list_data: Any, field_name: str, max_items: int = 100, item_max_length: int = 200) -> List[str]:
    """Convenience function for list validation"""
    return sanitizer.validate_list_field(list_data, field_name, max_items, item_max_length)


def validate_ingredient_list(ingredients: Any) -> List[Dict[str, Any]]:
    """Convenience function for ingredient list validation"""
    return sanitizer.validate_ingredient_list(ingredients)


# Export all
__all__ = [
    'InputSanitizer', 'SecurityError', 'ValidationError', 'sanitizer',
    'sanitize_string', 'validate_user_id', 'validate_numeric_range', 'sanitize_recipe_data',
    'validate_json_field', 'validate_list_field', 'validate_ingredient_list'
]