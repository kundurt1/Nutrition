# nutrition-backend/exceptions.py
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import logging
import traceback
import sys
from typing import Dict, Any, Optional, Union
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Error categorization for better handling"""
    VALIDATION = "validation"
    DATABASE = "database"
    EXTERNAL_SERVICE = "external_service"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    NETWORK = "network"
    TIMEOUT = "timeout"


class NutritionAppException(Exception):
    """Base exception for the nutrition app"""

    def __init__(self,
                 message: str,
                 category: ErrorCategory = ErrorCategory.SYSTEM,
                 status_code: int = 500,
                 details: Optional[Dict[str, Any]] = None,
                 user_message: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.category = category
        self.status_code = status_code
        self.details = details or {}
        self.user_message = user_message or self._get_default_user_message()

    def _get_default_user_message(self) -> str:
        """Get user-friendly message based on category"""
        user_messages = {
            ErrorCategory.VALIDATION: "The information provided is invalid. Please check your input and try again.",
            ErrorCategory.DATABASE: "We're experiencing database issues. Please try again in a few minutes.",
            ErrorCategory.EXTERNAL_SERVICE: "We're having trouble connecting to external services. Please try again later.",
            ErrorCategory.AUTHENTICATION: "Authentication failed. Please sign in again.",
            ErrorCategory.AUTHORIZATION: "You don't have permission to perform this action.",
            ErrorCategory.BUSINESS_LOGIC: "This operation cannot be completed due to business rules.",
            ErrorCategory.SYSTEM: "We're experiencing technical difficulties. Please try again later.",
            ErrorCategory.NETWORK: "Network connection issues. Please check your connection and try again.",
            ErrorCategory.TIMEOUT: "The request took too long to process. Please try again."
        }
        return user_messages.get(self.category, "An unexpected error occurred.")


# Specific Exception Classes

class ValidationError(NutritionAppException):
    """Input validation errors"""

    def __init__(self, message: str, field: str = None, value: Any = None):
        details = {}
        if field:
            details['field'] = field
        if value is not None:
            details['invalid_value'] = str(value)[:100]  # Limit for security

        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            status_code=400,
            details=details,
            user_message=f"Invalid input: {message}"
        )


class DatabaseError(NutritionAppException):
    """Database operation errors"""

    def __init__(self, message: str, operation: str = None, table: str = None):
        details = {}
        if operation:
            details['operation'] = operation
        if table:
            details['table'] = table

        super().__init__(
            message=message,
            category=ErrorCategory.DATABASE,
            status_code=503,
            details=details
        )


class ExternalServiceError(NutritionAppException):
    """External service errors (OpenAI, etc.)"""

    def __init__(self, message: str, service: str = None, error_code: str = None):
        details = {}
        if service:
            details['service'] = service
        if error_code:
            details['error_code'] = error_code

        super().__init__(
            message=message,
            category=ErrorCategory.EXTERNAL_SERVICE,
            status_code=503,
            details=details
        )


class AuthenticationError(NutritionAppException):
    """Authentication errors"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            category=ErrorCategory.AUTHENTICATION,
            status_code=401,
            user_message="Please sign in to continue."
        )


class AuthorizationError(NutritionAppException):
    """Authorization errors"""

    def __init__(self, message: str = "Access denied", required_permission: str = None):
        details = {}
        if required_permission:
            details['required_permission'] = required_permission

        super().__init__(
            message=message,
            category=ErrorCategory.AUTHORIZATION,
            status_code=403,
            details=details,
            user_message="You don't have permission to perform this action."
        )


class BusinessLogicError(NutritionAppException):
    """Business logic validation errors"""

    def __init__(self, message: str, rule: str = None):
        details = {}
        if rule:
            details['business_rule'] = rule

        super().__init__(
            message=message,
            category=ErrorCategory.BUSINESS_LOGIC,
            status_code=422,
            details=details
        )


class TimeoutError(NutritionAppException):
    """Timeout errors"""

    def __init__(self, message: str, timeout_duration: float = None, operation: str = None):
        details = {}
        if timeout_duration:
            details['timeout_duration'] = timeout_duration
        if operation:
            details['operation'] = operation

        super().__init__(
            message=message,
            category=ErrorCategory.TIMEOUT,
            status_code=504,
            details=details,
            user_message="The request is taking too long. Please try again."
        )


class NetworkError(NutritionAppException):
    """Network-related errors"""

    def __init__(self, message: str, endpoint: str = None):
        details = {}
        if endpoint:
            details['endpoint'] = endpoint

        super().__init__(
            message=message,
            category=ErrorCategory.NETWORK,
            status_code=503,
            details=details
        )


# Error Handler Classes

class ErrorHandler:
    """Centralized error handling and logging"""

    @staticmethod
    def log_error(error: Exception,
                  request: Request = None,
                  user_id: str = None,
                  additional_context: Dict[str, Any] = None):
        """Log error with comprehensive context"""

        error_context = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
        }

        # Add request context
        if request:
            error_context.update({
                'method': request.method,
                'url': str(request.url),
                'client_ip': getattr(request.client, 'host', 'unknown'),
                'user_agent': request.headers.get('user-agent', 'unknown'),
                'request_id': request.headers.get('x-request-id', 'unknown')
            })

        # Add user context
        if user_id:
            error_context['user_id'] = user_id

        # Add additional context
        if additional_context:
            error_context.update(additional_context)

        # Add exception-specific context
        if isinstance(error, NutritionAppException):
            error_context.update({
                'category': error.category.value,
                'status_code': error.status_code,
                'details': error.details
            })

        # Log with appropriate level
        if isinstance(error, (ValidationError, BusinessLogicError)):
            logger.warning(f"User error: {error}", extra=error_context)
        elif isinstance(error, (AuthenticationError, AuthorizationError)):
            logger.warning(f"Auth error: {error}", extra=error_context)
        elif isinstance(error, (DatabaseError, ExternalServiceError, TimeoutError, NetworkError)):
            logger.error(f"Service error: {error}", extra=error_context)
        else:
            logger.error(f"Unexpected error: {error}", extra=error_context, exc_info=True)

    @staticmethod
    def handle_database_error(error: Exception, operation: str = None, table: str = None) -> DatabaseError:
        """Handle database-specific errors"""
        error_str = str(error).lower()

        # Connection errors
        if any(term in error_str for term in ['connection', 'connect', 'unreachable', 'refused']):
            return DatabaseError(
                "Database connection failed",
                operation=operation,
                table=table
            )

        # Timeout errors
        elif any(term in error_str for term in ['timeout', 'timed out']):
            return DatabaseError(
                "Database operation timed out",
                operation=operation,
                table=table
            )

        # Constraint violations
        elif any(term in error_str for term in ['unique', 'constraint', 'duplicate']):
            return DatabaseError(
                "Data already exists",
                operation=operation,
                table=table
            )

        # Foreign key violations
        elif any(term in error_str for term in ['foreign key', 'fk_', 'reference']):
            return DatabaseError(
                "Related data not found",
                operation=operation,
                table=table
            )

        # Not found errors
        elif any(term in error_str for term in ['not found', 'does not exist', 'no rows']):
            return DatabaseError(
                "Requested data not found",
                operation=operation,
                table=table
            )

        # Permission errors
        elif any(term in error_str for term in ['permission', 'access denied', 'unauthorized']):
            return DatabaseError(
                "Database permission denied",
                operation=operation,
                table=table
            )

        # Generic database error
        else:
            return DatabaseError(
                "Database operation failed",
                operation=operation,
                table=table
            )

    @staticmethod
    def handle_external_service_error(error: Exception, service: str = None) -> ExternalServiceError:
        """Handle external service errors"""
        error_str = str(error).lower()

        # OpenAI specific errors
        if 'openai' in error_str or service == 'openai':
            if 'rate limit' in error_str:
                return ExternalServiceError(
                    "AI service rate limit exceeded",
                    service='openai',
                    error_code='rate_limit'
                )
            elif 'authentication' in error_str or 'api key' in error_str:
                return ExternalServiceError(
                    "AI service authentication failed",
                    service='openai',
                    error_code='auth_failed'
                )
            elif 'timeout' in error_str:
                return ExternalServiceError(
                    "AI service timeout",
                    service='openai',
                    error_code='timeout'
                )
            else:
                return ExternalServiceError(
                    "AI service error",
                    service='openai',
                    error_code='unknown'
                )

        # Supabase specific errors
        elif 'supabase' in error_str or service == 'supabase':
            return ExternalServiceError(
                "Database service error",
                service='supabase',
                error_code='service_error'
            )

        # Generic external service error
        else:
            return ExternalServiceError(
                "External service unavailable",
                service=service or 'unknown',
                error_code='service_unavailable'
            )

    @staticmethod
    def handle_validation_error(error: Exception, field: str = None) -> ValidationError:
        """Handle validation errors"""
        error_str = str(error)

        # Pydantic validation errors
        if 'pydantic' in str(type(error)).lower():
            return ValidationError(
                f"Invalid data format: {error_str}",
                field=field
            )

        # Type errors
        elif isinstance(error, TypeError):
            return ValidationError(
                f"Invalid data type: {error_str}",
                field=field
            )

        # Value errors
        elif isinstance(error, ValueError):
            return ValidationError(
                f"Invalid value: {error_str}",
                field=field
            )

        # Generic validation error
        else:
            return ValidationError(
                error_str,
                field=field
            )


# Exception Handler Functions for FastAPI

async def nutrition_app_exception_handler(request: Request, exc: NutritionAppException) -> JSONResponse:
    """Handle custom nutrition app exceptions"""

    # Log the error
    ErrorHandler.log_error(
        exc,
        request=request,
        user_id=request.headers.get('x-user-id')
    )

    # Create response
    response_data = {
        "error": True,
        "message": exc.user_message,
        "category": exc.category.value,
        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
    }

    # Add details in development mode
    if __import__('os').getenv('ENVIRONMENT', 'development') == 'development':
        response_data.update({
            "technical_message": exc.message,
            "details": exc.details
        })

    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )


async def validation_exception_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle validation exceptions"""

    validation_error = ErrorHandler.handle_validation_error(exc)
    return await nutrition_app_exception_handler(request, validation_error)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions"""

    ErrorHandler.log_error(
        exc,
        request=request,
        user_id=request.headers.get('x-user-id')
    )

    # Map HTTP status codes to user-friendly messages
    user_messages = {
        400: "The request is invalid. Please check your input.",
        401: "Authentication required. Please sign in.",
        403: "You don't have permission to access this resource.",
        404: "The requested resource was not found.",
        422: "The data provided is invalid.",
        429: "Too many requests. Please slow down.",
        500: "Internal server error. Please try again later.",
        502: "Bad gateway. Please try again later.",
        503: "Service temporarily unavailable. Please try again later.",
        504: "Request timeout. Please try again."
    }

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": user_messages.get(exc.status_code, "An error occurred"),
            "detail": exc.detail if __import__('os').getenv('ENVIRONMENT') == 'development' else None,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions"""

    # Try to categorize the error
    error_str = str(exc).lower()

    if any(term in error_str for term in ['database', 'supabase', 'postgresql', 'sql']):
        handled_error = ErrorHandler.handle_database_error(exc)
    elif any(term in error_str for term in ['openai', 'api', 'external']):
        handled_error = ErrorHandler.handle_external_service_error(exc)
    elif any(term in error_str for term in ['timeout', 'timed out']):
        handled_error = TimeoutError("Operation timed out")
    elif any(term in error_str for term in ['connection', 'network', 'unreachable']):
        handled_error = NetworkError("Network connection failed")
    else:
        # Generic system error
        handled_error = NutritionAppException(
            "An unexpected error occurred",
            category=ErrorCategory.SYSTEM,
            status_code=500
        )

    return await nutrition_app_exception_handler(request, handled_error)


# Context Managers for Error Handling

class DatabaseErrorContext:
    """Context manager for database operations"""

    def __init__(self, operation: str, table: str = None, user_id: str = None):
        self.operation = operation
        self.table = table
        self.user_id = user_id

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            # Convert database exceptions
            db_error = ErrorHandler.handle_database_error(
                exc_val,
                operation=self.operation,
                table=self.table
            )

            # Log with context
            ErrorHandler.log_error(
                db_error,
                user_id=self.user_id,
                additional_context={
                    'operation': self.operation,
                    'table': self.table
                }
            )

            # Re-raise as our custom exception
            raise db_error from exc_val


class ExternalServiceErrorContext:
    """Context manager for external service operations"""

    def __init__(self, service: str, operation: str = None, user_id: str = None):
        self.service = service
        self.operation = operation
        self.user_id = user_id

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            # Convert external service exceptions
            service_error = ErrorHandler.handle_external_service_error(
                exc_val,
                service=self.service
            )

            # Log with context
            ErrorHandler.log_error(
                service_error,
                user_id=self.user_id,
                additional_context={
                    'service': self.service,
                    'operation': self.operation
                }
            )

            # Re-raise as our custom exception
            raise service_error from exc_val


# Utility Functions

def safe_operation(operation_name: str):
    """Decorator for safe operation execution"""

    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except NutritionAppException:
                    # Re-raise our custom exceptions
                    raise
                except Exception as e:
                    # Convert unknown exceptions
                    logger.error(f"Error in {operation_name}: {e}", exc_info=True)
                    raise NutritionAppException(
                        f"Error in {operation_name}",
                        category=ErrorCategory.SYSTEM
                    ) from e

            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except NutritionAppException:
                    # Re-raise our custom exceptions
                    raise
                except Exception as e:
                    # Convert unknown exceptions
                    logger.error(f"Error in {operation_name}: {e}", exc_info=True)
                    raise NutritionAppException(
                        f"Error in {operation_name}",
                        category=ErrorCategory.SYSTEM
                    ) from e

            return sync_wrapper

    return decorator


# Export all
__all__ = [
    # Exception classes
    'NutritionAppException', 'ValidationError', 'DatabaseError', 'ExternalServiceError',
    'AuthenticationError', 'AuthorizationError', 'BusinessLogicError', 'TimeoutError', 'NetworkError',

    # Error handling
    'ErrorHandler', 'ErrorCategory',

    # FastAPI exception handlers
    'nutrition_app_exception_handler', 'validation_exception_handler',
    'http_exception_handler', 'general_exception_handler',

    # Context managers
    'DatabaseErrorContext', 'ExternalServiceErrorContext',

    # Utilities
    'safe_operation'
]