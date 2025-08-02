# nutrition-backend/main.py - UPDATED WITH ALL P0 & P1 FIXES
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Import our security and performance modules
from config import config, ConfigurationError
from security import sanitizer
from rate_limiter import rate_limit_middleware, cleanup_rate_limiters
from exceptions import (
    nutrition_app_exception_handler, validation_exception_handler,
    http_exception_handler, general_exception_handler,
    NutritionAppException, ValidationError, DatabaseError, ExternalServiceError
)
from database_enhanced import init_database, close_database, database_health_check, db_manager
from services.enhanced_openai_service import enhanced_openai_service as openai_service

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
    logging.getLogger("asyncpg").setLevel(logging.WARNING)


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
        raise

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

# Rate limiting middleware (must be added BEFORE routes)
if config.environment == "development":
    logger.info("⚠️ Rate limiting disabled in development mode")
else:
    app.middleware("http")(rate_limit_middleware)


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
            "rate_limiting": True,
            "cors_configured": True,
            "security_headers": True,
            "request_sanitization": True
        },
        "performance": {
            "async_operations": True,
            "connection_pooling": True,
            "caching_enabled": False,  # TODO: Implement caching
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
                    "original": data["text"][:100],  # Limit for security
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


# Include routers with enhanced error handling
try:
    from routers import recipes, grocery, ratings, nutrition, favorites, mealPlanning, pantry
    from routers import recipeScaling, nutritionCoach, socialMediaImport

    # Include all routers
    app.include_router(recipes.router, tags=["recipes"])
    app.include_router(ratings.router, tags=["ratings"])
    app.include_router(nutrition.router, tags=["nutrition"])
    app.include_router(grocery.router, tags=["grocery"])
    app.include_router(nutritionCoach.router, tags=["coaching"])
    app.include_router(socialMediaImport.router, tags=["social"])
    app.include_router(recipeScaling.router, tags=["scaling"])
    app.include_router(favorites.router, tags=["favorites"])


    logger.info("✅ All routers loaded successfully")

except ImportError as e:
    logger.warning(f"⚠️ Some routers could not be loaded: {e}")
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
        "system_info": "/info"
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