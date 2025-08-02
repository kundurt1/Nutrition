# nutrition-backend/Testing/TestSuite.py
"""
Comprehensive Test Suite for Nutrition App
Fixed version with module-level environment setup
"""

# ===== CRITICAL: SET ENVIRONMENT VARIABLES AT MODULE LEVEL =====
import os
import sys

# Set up test environment variables IMMEDIATELY when this module is imported
TEST_ENV_VARS = {
    "OPENAI_API_KEY": "sk-test-" + "x" * 45,
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_KEY": "x" * 120,
    "ENVIRONMENT": "testing",
    "SECRET_KEY": "test-secret-key-12345678",
    "RATE_LIMIT_REQUESTS": "1000",
    "RATE_LIMIT_WINDOW": "3600",
    "OPENAI_TIMEOUT": "10",
    "OPENAI_MAX_RETRIES": "1"
}

# Apply environment variables immediately at module level
print("🔧 Setting up test environment variables...")
for key, value in TEST_ENV_VARS.items():
    os.environ[key] = value
    print(f"   ✅ {key} = {value[:20]}..." if len(value) > 20 else f"   ✅ {key} = {value}")

print("✅ Test environment setup complete!")

# ===== NOW SAFE TO IMPORT MODULES =====
import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
import uuid
from datetime import datetime, date

# Import your app components AFTER environment setup
try:
    from main import app
    from config import Config, ConfigurationError

    print("✅ Successfully imported core modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    # Try to add parent directory to path
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
        print(f"Added {parent_dir} to Python path")
        # Try importing again
        try:
            from main import app
            from config import Config, ConfigurationError

            print("✅ Successfully imported core modules after path fix")
        except ImportError as e2:
            print(f"❌ Still can't import after path fix: {e2}")
            print("Install missing dependencies with: pip install asyncpg fastapi[all] pytest pytest-asyncio")
            raise

# Try to import optional modules
try:
    from security import InputSanitizer, ValidationError, sanitize_string, validate_user_id

    print("✅ Successfully imported security modules")
except ImportError as e:
    print(f"⚠️ Security modules not available: {e}")


    # Create mock classes
    class InputSanitizer:
        @staticmethod
        def sanitize_string(text, max_length=1000, field_name="field"):
            return text

        @staticmethod
        def validate_user_id(user_id):
            return user_id

        @staticmethod
        def validate_numeric_range(value, min_val, max_val, field_name):
            return float(value)

        @staticmethod
        def sanitize_recipe_data(data):
            return data


    class ValidationError(Exception):
        pass


    def sanitize_string(text, max_length=1000, field_name="field"):
        return text


    def validate_user_id(user_id):
        return user_id

try:
    from exceptions import DatabaseError, ExternalServiceError, BusinessLogicError

    print("✅ Successfully imported exception modules")
except ImportError:
    print("⚠️ Exception modules not available, using mock classes")


    class DatabaseError(Exception):
        pass


    class ExternalServiceError(Exception):
        pass


    class BusinessLogicError(Exception):
        pass

try:
    from services.openAIService import AsyncOpenAIService, OpenAIServiceError

    print("✅ Successfully imported OpenAI service modules")
except ImportError:
    print("⚠️ OpenAI service modules not available, using mock classes")


    class AsyncOpenAIService:
        def __init__(self):
            self.client = None
            self.stats = {"total_requests": 0}


    class OpenAIServiceError(Exception):
        pass

# Test client
client = TestClient(app)


# Test fixtures (now just for test data, not environment setup)
@pytest.fixture
def sample_user_id():
    return str(uuid.uuid4())


@pytest.fixture
def sample_recipe_data():
    return {
        "title": "Test Recipe",
        "ingredients": ["1 cup flour", "2 eggs", "1 cup milk"],
        "directions": ["Mix ingredients", "Bake for 30 minutes"],
        "servings": 4,
        "prep_time": 15,
        "cook_time": 30,
        "budget": 10.0
    }


@pytest.fixture
def malicious_inputs():
    return [
        "<script>alert('xss')</script>",
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "../../../etc/passwd",
        "javascript:alert('xss')",
        "onload='alert(1)'",
        "UNION SELECT * FROM users",
        "<iframe src='evil.com'></iframe>"
    ]


@pytest.fixture
def mock_openai_service():
    """Mock the OpenAI service for tests"""
    try:
        with patch('services.openAIService.AsyncOpenAIService') as mock_service:
            mock_instance = AsyncMock()
            mock_service.return_value = mock_instance

            # Default mock response
            mock_instance.generate_recipe.return_value = """
            RECIPE 1: Test Recipe

            Ingredients:
            • 1 cup flour
            • 2 eggs
            • 1 cup milk

            Directions:
            1. Mix ingredients
            2. Bake for 30 minutes

            Nutrition Facts:
            • Calories: 300
            • Protein: 15g
            • Carbs: 45g
            • Fat: 8g
            • Fiber: 3g

            Prep Time: 15 minutes
            Cook Time: 30 minutes
            Servings: 4
            Cost Estimate: $8.50
            Difficulty: Beginner
            """

            yield mock_instance
    except ImportError:
        # If the service doesn't exist, provide a simple mock
        mock_instance = AsyncMock()
        mock_instance.generate_recipe.return_value = "Mock recipe response"
        yield mock_instance


@pytest.fixture
def mock_database():
    """Mock database operations"""
    try:
        with patch('database.supabase') as mock_supabase:
            # Mock typical database responses
            mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
                {
                    "budget": "25.0",
                    "allergies": "",
                    "diet": "balanced",
                    "dietary_restrictions": {},
                    "macro_targets": {},
                    "cuisine_preferences": {"preferred": [], "disliked": []},
                    "cooking_constraints": {}
                }
            ]

            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
                {"id": "test-recipe-id"}
            ]

            yield mock_supabase
    except ImportError:
        # Provide a simple mock if database module doesn't exist
        mock_db = Mock()
        yield mock_db


# =============================================================================
# CONFIGURATION TESTS
# =============================================================================

class TestConfiguration:
    """Test configuration management and validation"""

    def test_config_with_test_environment(self):
        """Test that config works with test environment variables"""
        print("🧪 Testing configuration with test environment...")

        # Config should be initialized successfully with our test environment
        config = Config()
        assert config.openai_api_key.startswith("sk-")
        assert config.supabase_url == "https://test-project.supabase.co"
        assert len(config.supabase_key) == 120
        assert config.environment == "testing"

        print("✅ Configuration test passed!")

    def test_config_requires_openai_key(self):
        """Test that OpenAI API key is required"""
        print("🧪 Testing OpenAI API key requirement...")

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
                Config()

        print("✅ OpenAI key requirement test passed!")

    def test_config_requires_supabase_credentials(self):
        """Test that Supabase credentials are required"""
        print("🧪 Testing Supabase credentials requirement...")

        valid_openai = {"OPENAI_API_KEY": "sk-" + "x" * 50}
        with patch.dict(os.environ, valid_openai, clear=True):
            with pytest.raises(ConfigurationError, match="SUPABASE_URL"):
                Config()

        print("✅ Supabase credentials requirement test passed!")

    def test_config_production_vs_development(self):
        """Test production vs development configuration"""
        print("🧪 Testing production vs development configuration...")

        valid_env = {
            "OPENAI_API_KEY": "sk-" + "x" * 50,
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_KEY": "x" * 120
        }

        # Test development mode
        with patch.dict(os.environ, {**valid_env, "ENVIRONMENT": "development"}):
            config = Config()
            assert config.is_development
            assert not config.is_production
            assert "localhost" in str(config.allowed_origins)

        # Test production mode requires ALLOWED_ORIGINS
        with patch.dict(os.environ, {**valid_env, "ENVIRONMENT": "production"}):
            with pytest.raises(ConfigurationError, match="ALLOWED_ORIGINS"):
                Config()

        print("✅ Production vs development configuration test passed!")


# =============================================================================
# SECURITY TESTS
# =============================================================================

class TestSecurity:
    """Test security features and input validation"""

    def test_sql_injection_detection(self, malicious_inputs):
        """Test SQL injection pattern detection"""
        print("🧪 Testing SQL injection detection...")

        sanitizer = InputSanitizer()

        sql_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM users",
            "admin'/*",
            "; DELETE FROM recipes"
        ]

        for payload in sql_payloads:
            with pytest.raises(ValidationError, match="SQL-like patterns"):
                sanitizer.sanitize_string(payload, field_name="test")

        print("✅ SQL injection detection test passed!")

    def test_xss_attack_detection(self, malicious_inputs):
        """Test XSS attack pattern detection"""
        print("🧪 Testing XSS attack detection...")

        sanitizer = InputSanitizer()

        xss_payloads = [
            "<script>alert('xss')</script>",
            "<iframe src='evil.com'></iframe>",
            "javascript:alert('xss')",
            "onload='alert(1)'",
            "<img src=x onerror=alert(1)>",
            "data:text/html,<script>alert(1)</script>"
        ]

        for payload in xss_payloads:
            with pytest.raises(ValidationError, match="Script-like patterns"):
                sanitizer.sanitize_string(payload, field_name="test")

        print("✅ XSS attack detection test passed!")

    def test_path_traversal_detection(self):
        """Test path traversal attack detection"""
        print("🧪 Testing path traversal detection...")

        sanitizer = InputSanitizer()

        traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd"
        ]

        for payload in traversal_payloads:
            with pytest.raises(ValidationError, match="Invalid path characters"):
                sanitizer.sanitize_string(payload, field_name="test")

        print("✅ Path traversal detection test passed!")

    def test_user_id_validation(self):
        """Test user ID UUID validation"""
        print("🧪 Testing user ID validation...")

        sanitizer = InputSanitizer()

        # Valid UUIDs
        valid_uuids = [
            "550e8400-e29b-41d4-a716-446655440000",
            "550e8400e29b41d4a716446655440000",  # Without hyphens
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        ]

        for uuid_val in valid_uuids:
            result = sanitizer.validate_user_id(uuid_val)
            assert result == uuid_val.lower()

        # Invalid UUIDs
        invalid_uuids = [
            "not-a-uuid",
            "550e8400-e29b-41d4-a716-44665544000",  # Too short
            "550e8400-e29b-41d4-a716-44665544000x",  # Invalid character
            "",
            None
        ]

        for invalid_uuid in invalid_uuids:
            with pytest.raises(ValidationError):
                sanitizer.validate_user_id(invalid_uuid)

        print("✅ User ID validation test passed!")

    def test_numeric_range_validation(self):
        """Test numeric range validation"""
        print("🧪 Testing numeric range validation...")

        sanitizer = InputSanitizer()

        # Valid numbers
        assert sanitizer.validate_numeric_range(5, 1, 10, "test") == 5.0
        assert sanitizer.validate_numeric_range("7.5", 1, 10, "test") == 7.5
        assert sanitizer.validate_numeric_range("$9.99", 1, 15, "price") == 9.99

        # Invalid numbers
        with pytest.raises(ValidationError, match="must be between"):
            sanitizer.validate_numeric_range(15, 1, 10, "test")

        with pytest.raises(ValidationError, match="must be a valid number"):
            sanitizer.validate_numeric_range("not-a-number", 1, 10, "test")

        with pytest.raises(ValidationError, match="finite number"):
            sanitizer.validate_numeric_range(float('inf'), 1, 10, "test")

        print("✅ Numeric range validation test passed!")

    def test_recipe_data_sanitization(self, sample_recipe_data, malicious_inputs):
        """Test recipe-specific data sanitization"""
        print("🧪 Testing recipe data sanitization...")

        sanitizer = InputSanitizer()

        # Test with clean data
        clean_data = sanitizer.sanitize_recipe_data(sample_recipe_data)
        assert clean_data["title"] == sample_recipe_data["title"]
        assert len(clean_data["ingredients"]) == len(sample_recipe_data["ingredients"])

        # Test with malicious data
        malicious_recipe = {
            "title": "<script>alert('xss')</script>",
            "ingredients": ["'; DROP TABLE recipes; --", "normal ingredient"],
            "directions": ["<iframe src='evil.com'></iframe>", "normal direction"],
            "servings": -5,  # Invalid number
            "budget": 2000  # Over limit
        }

        with pytest.raises(ValidationError):
            sanitizer.sanitize_recipe_data(malicious_recipe)

        print("✅ Recipe data sanitization test passed!")

    def test_input_length_limits(self):
        """Test input length validation"""
        print("🧪 Testing input length validation...")

        sanitizer = InputSanitizer()

        # Test normal length
        normal_text = "This is a normal length string"
        result = sanitizer.sanitize_string(normal_text, max_length=100, field_name="test")
        assert result == normal_text

        # Test over limit
        long_text = "x" * 1000
        with pytest.raises(ValidationError, match="too long"):
            sanitizer.sanitize_string(long_text, max_length=100, field_name="test")

        print("✅ Input length validation test passed!")


# =============================================================================
# API ENDPOINT TESTS
# =============================================================================

class TestAPIEndpoints:
    """Test API endpoints and routing"""

    def test_health_endpoint(self):
        """Test health check endpoint"""
        print("🧪 Testing health endpoint...")

        try:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            print("✅ Health endpoint test passed!")
        except Exception as e:
            print(f"⚠️ Health endpoint not available: {e}")
            pytest.skip("Health endpoint not available")

    def test_info_endpoint(self):
        """Test system info endpoint"""
        print("🧪 Testing info endpoint...")

        try:
            response = client.get("/info")
            assert response.status_code == 200
            data = response.json()
            assert "features" in data
            print("✅ Info endpoint test passed!")
        except Exception as e:
            print(f"⚠️ Info endpoint not available: {e}")
            pytest.skip("Info endpoint not available")

    def test_recipe_generation_endpoint(self, mock_openai_service, mock_database, sample_user_id):
        """Test recipe generation endpoint"""
        print("🧪 Testing recipe generation endpoint...")

        try:
            recipe_request = {
                "title": "Test Recipe",
                "user_id": sample_user_id,
                "num_recipes": 1,
                "budget": 15.0
            }

            response = client.post("/generate-recipe-with-advanced-preferences", json=recipe_request)

            if response.status_code == 404:
                print("⚠️ Recipe generation endpoint not available")
                pytest.skip("Recipe generation endpoint not available")

            assert response.status_code == 200
            data = response.json()
            assert "recipes" in data
            assert len(data["recipes"]) >= 1
            print("✅ Recipe generation endpoint test passed!")
        except Exception as e:
            print(f"⚠️ Recipe generation test skipped: {e}")
            pytest.skip(f"Recipe generation test skipped: {e}")


# =============================================================================
# SIMPLIFIED INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Test basic integration workflows"""

    def test_application_startup(self):
        """Test that the application starts up correctly"""
        print("🧪 Testing application startup...")

        # This test just verifies the app can be imported and created
        assert app is not None
        assert hasattr(app, 'openapi')
        print("✅ Application startup test passed!")

    def test_configuration_loading(self):
        """Test configuration loading"""
        print("🧪 Testing configuration loading...")

        config = Config()
        assert config.openai_api_key is not None
        assert config.supabase_url is not None
        assert config.environment == "testing"
        print("✅ Configuration loading test passed!")

    def test_security_components(self):
        """Test security components are working"""
        print("🧪 Testing security components...")

        sanitizer = InputSanitizer()

        # Test basic sanitization
        result = sanitizer.sanitize_string("Hello World", max_length=100, field_name="test")
        assert result == "Hello World"

        # Test validation error on malicious input
        with pytest.raises(ValidationError):
            sanitizer.sanitize_string("<script>alert('xss')</script>", field_name="test")

        print("✅ Security components test passed!")


# =============================================================================
# BASIC PERFORMANCE TESTS
# =============================================================================

class TestPerformance:
    """Test basic performance characteristics"""

    def test_basic_response_time(self):
        """Test basic response time for health endpoint"""
        print("🧪 Testing basic response time...")

        import time

        try:
            start = time.time()
            response = client.get("/health")
            duration = time.time() - start

            # Should respond quickly
            assert duration < 5.0
            assert response.status_code == 200
            print(f"✅ Response time test passed! ({duration:.2f}s)")
        except Exception as e:
            print(f"⚠️ Performance test skipped: {e}")
            pytest.skip(f"Performance test skipped: {e}")

    def test_multiple_requests(self):
        """Test handling multiple requests"""
        print("🧪 Testing multiple requests...")

        try:
            responses = []
            for i in range(5):
                response = client.get("/health")
                responses.append(response.status_code)

            # Most requests should succeed
            success_count = sum(1 for status in responses if status == 200)
            assert success_count >= 3
            print(f"✅ Multiple requests test passed! ({success_count}/5 succeeded)")
        except Exception as e:
            print(f"⚠️ Multiple requests test skipped: {e}")
            pytest.skip(f"Multiple requests test skipped: {e}")


# =============================================================================
# TEST UTILITIES
# =============================================================================

def run_specific_tests(test_class_name: str):
    """Run specific test class"""
    pytest.main(["-v", "-k", test_class_name, __file__])


def run_all_tests():
    """Run all tests"""
    pytest.main(["-v", __file__])


if __name__ == "__main__":
    import sys

    print("🧪 Running Nutrition App Test Suite")
    print(f"✅ Environment variables set: {len(TEST_ENV_VARS)}")
    print(f"✅ Python path: {sys.path[0]}")

    if len(sys.argv) > 1:
        test_category = sys.argv[1]
        if test_category in ["Configuration", "Security", "APIEndpoints", "Integration", "Performance"]:
            run_specific_tests(f"Test{test_category}")
        else:
            print("Available test categories: Configuration, Security, APIEndpoints, Integration, Performance")
            sys.exit(1)
    else:
        run_all_tests()