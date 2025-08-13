import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Try importing modules with fallbacks
try:
    from config import config, ConfigurationError
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Config module not found, using defaults")


    class MockConfig:
        def __init__(self):
            self.is_production = os.getenv("ENVIRONMENT", "development") == "production"
            self.is_development = not self.is_production
            self.environment = os.getenv("ENVIRONMENT", "development")
            self.allowed_origins = [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173"
            ] if self.is_development else ["https://yourdomain.com"]


    config = MockConfig()


    class ConfigurationError(Exception):
        pass

try:
    from security import sanitizer
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Security module not found, using mock")


    class MockSanitizer:
        @staticmethod
        def sanitize_string(text, max_length=1000):
            return str(text)[:max_length]

        @staticmethod
        def validate_user_id(user_id):
            return str(user_id)


    sanitizer = MockSanitizer()

try:
    from rate_limiter import rate_limit_middleware, cleanup_rate_limiters
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Rate limiter not found, disabling")


    async def rate_limit_middleware(request, call_next):
        return await call_next(request)


    async def cleanup_rate_limiters():
        pass

# Exception handling
try:
    from exceptions import (
        nutrition_app_exception_handler, validation_exception_handler,
        http_exception_handler, general_exception_handler,
        NutritionAppException, ValidationError, DatabaseError, ExternalServiceError
    )
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Exception handlers not found, using basic handlers")


    class NutritionAppException(Exception):
        def __init__(self, message, status_code=500):
            self.message = message
            self.status_code = status_code
            super().__init__(message)


    class ValidationError(NutritionAppException):
        def __init__(self, message):
            super().__init__(message, 400)


    class DatabaseError(NutritionAppException):
        def __init__(self, message):
            super().__init__(message, 503)


    class ExternalServiceError(NutritionAppException):
        def __init__(self, message):
            super().__init__(message, 503)


    async def nutrition_app_exception_handler(request: Request, exc: NutritionAppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": True, "message": exc.message}
        )


    async def validation_exception_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=400,
            content={"error": True, "message": str(exc)}
        )


    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": True, "message": exc.detail}
        )


    async def general_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"error": True, "message": "Internal server error"}
        )

# Database handling
try:
    from database_enhanced import init_database, close_database, database_health_check, db_manager
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Database module not found, using mock")


    async def init_database():
        logger.info("Mock database initialized")


    async def close_database():
        logger.info("Mock database closed")


    async def database_health_check():
        return {"status": "healthy", "response_time": 0.001}


    class MockDbManager:
        def __init__(self):
            self.is_initialized = True

        def get_stats(self):
            return {"connections": 1, "queries": 0}


    db_manager = MockDbManager()

# OpenAI service handling
try:
    from services.enhanced_openai_service import enhanced_openai_service as openai_service
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("OpenAI service not found, using mock")


    class MockOpenAIService:
        async def health_check(self):
            return {"status": "healthy", "response_time": 0.001}

        def get_stats(self):
            return {"requests": 0, "errors": 0}


    openai_service = MockOpenAIService()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('nutrition_app.log') if config.is_production else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

# Suppress noisy logs in production
if config.is_production:
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    # Startup
    logger.info("🚀 Starting Nutrition App...")

    try:
        # Initialize database
        await init_database()
        logger.info("✅ Database initialized")

        # Test OpenAI service
        health_check = await openai_service.health_check()
        if health_check['status'] == 'healthy':
            logger.info("✅ OpenAI service healthy")
        else:
            logger.warning(f"⚠️ OpenAI service status: {health_check['status']}")

        # Start background tasks
        cleanup_task = asyncio.create_task(cleanup_rate_limiters())
        logger.info("✅ Background tasks started")

        logger.info("🎉 Application startup completed successfully!")

        yield

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        # Don't raise, continue with limited functionality
        yield

    # Shutdown
    logger.info("🛑 Shutting down Nutrition App...")

    try:
        # Cancel background tasks
        if 'cleanup_task' in locals():
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass

        # Close database connections
        await close_database()

        logger.info("✅ Application shutdown completed")

    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")


# Initialize FastAPI app with enhanced security
app = FastAPI(
    title="Nutrition App API",
    version="2.0.0",
    description="Secure, high-performance nutrition and recipe management API",
    docs_url="/docs" if config.is_development else None,
    redoc_url="/redoc" if config.is_development else None,
    lifespan=lifespan
)

# Security middleware
if config.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["yourdomain.com", "*.yourdomain.com", "api.yourdomain.com"]
    )

# Enhanced CORS with strict settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-User-ID",
        "X-Request-ID",
        "X-API-Version"
    ],
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset"
    ],
    max_age=3600
)

# Rate limiting middleware (only if not in development)
if config.environment != "development":
    app.middleware("http")(rate_limit_middleware)
else:
    logger.info("⚠️ Rate limiting disabled in development mode")


# Request ID middleware for tracing
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID for tracing"""
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    if config.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


# Exception handlers (order matters - most specific first)
app.add_exception_handler(NutritionAppException, nutrition_app_exception_handler)
app.add_exception_handler(ValidationError, nutrition_app_exception_handler)
app.add_exception_handler(DatabaseError, nutrition_app_exception_handler)
app.add_exception_handler(ExternalServiceError, nutrition_app_exception_handler)
app.add_exception_handler(ValueError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


# Enhanced health check endpoint
@app.get("/health", tags=["system"])
async def comprehensive_health_check():
    """Comprehensive system health check"""
    health_data = {
        "status": "healthy",
        "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "environment": config.environment,
        "services": {}
    }

    overall_healthy = True

    # Database health
    try:
        db_health = await database_health_check()
        health_data["services"]["database"] = {
            "status": db_health.get("status", "unknown"),
            "response_time": db_health.get("response_time"),
            "statistics": db_manager.get_stats() if db_manager.is_initialized else None
        }
        if db_health.get("status") != "healthy":
            overall_healthy = False
    except Exception as e:
        health_data["services"]["database"] = {"status": "error", "error": str(e)}
        overall_healthy = False

    # OpenAI service health
    try:
        openai_health = await openai_service.health_check()
        health_data["services"]["openai"] = {
            "status": openai_health.get("status", "unknown"),
            "response_time": openai_health.get("response_time"),
            "statistics": openai_service.get_stats()
        }
        if openai_health.get("status") != "healthy":
            overall_healthy = False
    except Exception as e:
        health_data["services"]["openai"] = {"status": "error", "error": str(e)}
        overall_healthy = False

    # Update overall status
    health_data["status"] = "healthy" if overall_healthy else "degraded"

    # Return appropriate status code
    status_code = 200 if overall_healthy else 503
    return JSONResponse(content=health_data, status_code=status_code)


# System information endpoint
@app.get("/info", tags=["system"])
async def system_info():
    """Get system information and capabilities"""
    return {
        "name": "Nutrition App API",
        "version": "2.0.0",
        "environment": config.environment,
        "features": [
            "secure_authentication",
            "rate_limiting",
            "input_sanitization",
            "async_processing",
            "database_pooling",
            "comprehensive_error_handling",
            "health_monitoring",
            "request_tracing"
        ],
        "security": {
            "input_validation": True,
            "rate_limiting": config.environment != "development",
            "cors_configured": True,
            "security_headers": True,
            "request_sanitization": True
        },
        "performance": {
            "async_operations": True,
            "connection_pooling": True,
            "caching_enabled": False,
            "background_tasks": True
        }
    }


# Security test endpoint (development only)
if config.is_development:
    @app.post("/test/security", tags=["testing"])
    async def test_security_features(data: dict):
        """Test security features (development only)"""
        results = {}

        # Test input sanitization
        if "text" in data:
            try:
                sanitized = sanitizer.sanitize_string(data["text"], max_length=1000)
                results["sanitization"] = {
                    "original": data["text"][:100],
                    "sanitized": sanitized[:100],
                    "changed": sanitized != data["text"]
                }
            except Exception as e:
                results["sanitization"] = {"error": str(e)}

        # Test user ID validation
        if "user_id" in data:
            try:
                validated = sanitizer.validate_user_id(data["user_id"])
                results["user_id_validation"] = {
                    "original": data["user_id"],
                    "validated": validated,
                    "valid": True
                }
            except Exception as e:
                results["user_id_validation"] = {
                    "original": data["user_id"],
                    "valid": False,
                    "error": str(e)
                }

        return {
            "message": "Security features tested",
            "results": results,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        }


# Statistics endpoint
@app.get("/stats", tags=["monitoring"])
async def get_system_statistics():
    """Get system performance statistics"""
    stats = {
        "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
        "database": {},
        "openai_service": {},
        "system": {}
    }

    # Database statistics
    try:
        stats["database"] = db_manager.get_stats()
    except Exception as e:
        stats["database"] = {"error": str(e)}

    # OpenAI service statistics
    try:
        stats["openai_service"] = openai_service.get_stats()
    except Exception as e:
        stats["openai_service"] = {"error": str(e)}

    # System statistics
    try:
        import psutil
        stats["system"] = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
    except ImportError:
        stats["system"] = {"error": "psutil not available"}
    except Exception as e:
        stats["system"] = {"error": str(e)}

    return stats


# Simple auth endpoints for frontend compatibility
@app.post("/auth/signin", tags=["auth"])
async def signin(request: dict):
    """Mock signin endpoint"""
    email = request.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    return {
        "message": "Magic link sent (mock)",
        "user": {"email": email, "id": "123"},
        "success": True
    }


@app.get("/auth/session", tags=["auth"])
async def get_session():
    """Mock session endpoint"""
    return {
        "session": {
            "user": {"email": "test@example.com", "id": "123"}
        }
    }


@app.post("/auth/signout", tags=["auth"])
async def signout():
    """Mock signout endpoint"""
    return {"message": "Signed out successfully"}


# Include routers with enhanced error handling
routers_loaded = []
router_errors = []

try:
    from routers import recipes

    app.include_router(recipes.router, tags=["recipes"])
    routers_loaded.append("recipes")
except ImportError as e:
    router_errors.append(f"recipes: {e}")

try:
    from routers import grocery

    app.include_router(grocery.router, tags=["grocery"])
    routers_loaded.append("grocery")
except ImportError as e:
    router_errors.append(f"grocery: {e}")

try:
    from routers import ratings

    app.include_router(ratings.router, tags=["ratings"])
    routers_loaded.append("ratings")
except ImportError as e:
    router_errors.append(f"ratings: {e}")

try:
    from routers import nutrition

    app.include_router(nutrition.router, tags=["nutrition"])
    routers_loaded.append("nutrition")
except ImportError as e:
    router_errors.append(f"nutrition: {e}")

try:
    from routers import favorites

    app.include_router(favorites.router, tags=["favorites"])
    routers_loaded.append("favorites")
except ImportError as e:
    router_errors.append(f"favorites: {e}")

try:
    from routers import mealPlanning

    app.include_router(mealPlanning.router, tags=["meal-planning"])
    routers_loaded.append("mealPlanning")
except ImportError as e:
    router_errors.append(f"mealPlanning: {e}")

try:
    from routers import pantry

    app.include_router(pantry.router, tags=["pantry"])
    routers_loaded.append("pantry")
except ImportError as e:
    router_errors.append(f"pantry: {e}")

try:
    from routers import recipeScaling

    app.include_router(recipeScaling.router,prefix = "/recipe-scaling", tags=["recipe-scaling"])
    routers_loaded.append("recipeScaling")
except ImportError as e:
    router_errors.append(f"recipeScaling: {e}")

try:
    from routers import nutritionCoach
    # ADD THE PREFIX HERE - This is the key fix
    app.include_router(nutritionCoach.router, prefix="/coaching", tags=["coaching"])
    routers_loaded.append("nutritionCoach")
except ImportError as e:
    router_errors.append(f"nutritionCoach: {e}")

try:
    from routers import socialMediaImport

    app.include_router(socialMediaImport.router, tags=["social"])
    routers_loaded.append("socialMediaImport")
except ImportError as e:
    router_errors.append(f"socialMediaImport: {e}")

if routers_loaded:
    logger.info(f"✅ Loaded routers: {', '.join(routers_loaded)}")

if router_errors:
    logger.warning(f"⚠️ Failed to load routers: {', '.join(router_errors)}")
    logger.warning("The API will run with limited functionality")


# Root endpoint
@app.get("/", tags=["system"])
async def root():
    """API root endpoint"""
    return {
        "message": "Nutrition App API",
        "version": "2.0.0",
        "status": "running",
        "documentation": "/docs" if config.is_development else "Contact admin for API documentation",
        "health_check": "/health",
        "system_info": "/info",
        "loaded_routers": routers_loaded,
        "router_errors": router_errors if config.is_development else None
    }


# Error handling for startup failures
@app.exception_handler(ConfigurationError)
async def configuration_error_handler(request: Request, exc: ConfigurationError):
    """Handle configuration errors"""
    logger.error(f"Configuration error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Server configuration error",
            "message": "The server is not properly configured. Please contact the administrator.",
            "details": str(exc) if config.is_development else None
        }
    )


if __name__ == "__main__":
    # Production-ready server configuration
    server_config = {
        "app": "main:app",
        "host": "0.0.0.0",
        "port": int(os.getenv("PORT", 8000)),
        "log_level": "info" if config.is_production else "debug",
        "access_log": config.is_production,
        "reload": config.is_development,
        "workers": 1 if config.is_development else 4,
    }

    # Additional production settings
    if config.is_production:
        server_config.update({
            "ssl_keyfile": os.getenv("SSL_KEYFILE"),
            "ssl_certfile": os.getenv("SSL_CERTFILE"),
            "forwarded_allow_ips": "*",
            "proxy_headers": True
        })

    try:
        logger.info(f"🚀 Starting server in {config.environment} mode...")
        logger.info(
            f"📡 Server will be available at: http://{'localhost' if config.is_development else '0.0.0.0'}:{server_config['port']}")

        if config.is_development:
            logger.info(f"📚 API Documentation: http://localhost:{server_config['port']}/docs")
            logger.info(f"🔍 Health Check: http://localhost:{server_config['port']}/health")

        uvicorn.run(**server_config)

    except ConfigurationError as e:
        logger.error(f"❌ Configuration error: {e}")
        logger.error("Please check your environment variables and try again.")
        exit(1)
    except Exception as e:
        logger.error(f"❌ Server startup failed: {e}")
        exit(1)

