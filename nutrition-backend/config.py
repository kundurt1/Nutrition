# nutrition-backend/config.py
import os
from typing import Optional
import logging
import re

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid"""
    pass


class Config:
    """Secure configuration management with validation"""

    def __init__(self):
        # Load and validate required environment variables
        self.openai_api_key = self._get_validated_openai_key()
        self.supabase_url = self._get_required_env("SUPABASE_URL")
        self.supabase_key = self._get_required_env("SUPABASE_KEY")
        self.environment = os.getenv("ENVIRONMENT", "development")

        # Security settings
        self.secret_key = self._get_or_generate_secret_key()
        self.allowed_origins = self._get_allowed_origins()
        self.rate_limit_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
        self.rate_limit_window = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))

        # API settings
        self.openai_timeout = int(os.getenv("OPENAI_TIMEOUT", "30"))
        self.openai_max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "3"))

        logger.info(f"Configuration loaded successfully (Environment: {self.environment})")

    def _get_required_env(self, key: str) -> str:
        """Get required environment variable with validation"""
        value = os.getenv(key)
        if not value:
            raise ConfigurationError(f"Required environment variable {key} is not set")
        return value.strip()

    def _get_validated_openai_key(self) -> str:
        """Get and validate OpenAI API key"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ConfigurationError("OPENAI_API_KEY environment variable is required")

        api_key = api_key.strip()

        # Validate API key format
        if len(api_key) < 20:
            raise ConfigurationError("Invalid OpenAI API key: too short")

        if not api_key.startswith("sk-"):
            raise ConfigurationError("Invalid OpenAI API key: must start with 'sk-'")

        # Check for placeholder values
        if api_key in ["sk-your-key-here", "sk-placeholder", "your-openai-api-key"]:
            raise ConfigurationError("Please replace placeholder OpenAI API key with real key")

        return api_key

    def _get_or_generate_secret_key(self) -> str:
        """Get or generate secret key for JWT tokens"""
        secret = os.getenv("SECRET_KEY")
        if not secret:
            import secrets
            secret = secrets.token_urlsafe(32)
            logger.warning("No SECRET_KEY found, generated temporary key. Set SECRET_KEY env var for production!")
        return secret

    def _get_allowed_origins(self) -> list:
        """Get CORS allowed origins based on environment"""
        if self.is_production:
            # Production: Only allow specific domains
            origins_env = os.getenv("ALLOWED_ORIGINS", "")
            if origins_env:
                return [origin.strip() for origin in origins_env.split(",")]
            else:
                raise ConfigurationError("ALLOWED_ORIGINS must be set in production")
        else:
            # Development: Allow localhost variations
            return [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:3000",
                "http://127.0.0.1:3000"
            ]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"

    def validate_all(self) -> bool:
        """Validate all configuration is correct"""
        try:
            # Test Supabase URL format
            if not self.supabase_url.startswith("https://") or "supabase.co" not in self.supabase_url:
                raise ConfigurationError("Invalid Supabase URL format")

            # Test Supabase key format
            if len(self.supabase_key) < 100:  # Supabase keys are typically long
                raise ConfigurationError("Invalid Supabase key: too short")

            logger.info("All configuration validation passed")
            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise ConfigurationError(f"Configuration validation failed: {e}")


# Initialize and validate global config
try:
    config = Config()
    config.validate_all()
except ConfigurationError as e:
    logger.error(f"❌ Configuration error: {e}")
    print(f"\n❌ CONFIGURATION ERROR: {e}")
    print("\n📝 Required Environment Variables:")
    print("  • OPENAI_API_KEY (starts with 'sk-')")
    print("  • SUPABASE_URL (your Supabase project URL)")
    print("  • SUPABASE_KEY (your Supabase anon key)")
    print("\n💡 Optional Environment Variables:")
    print("  • ENVIRONMENT (development/production)")
    print("  • SECRET_KEY (for JWT tokens)")
    print("  • ALLOWED_ORIGINS (comma-separated URLs for production)")
    print("  • RATE_LIMIT_REQUESTS (default: 100)")
    print("  • RATE_LIMIT_WINDOW (default: 3600)")
    raise SystemExit(1)

# Export config
__all__ = ['config', 'ConfigurationError']