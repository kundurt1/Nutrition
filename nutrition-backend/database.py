# database.py - Fixed compatible version
from supabase import create_client, Client
import os
import asyncio
import time
import random
from functools import wraps
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Debug prints to help diagnose issues
print(f"Supabase URL loaded: {'Yes' if SUPABASE_URL else 'No'}")
print(f"Supabase Key loaded: {'Yes' if SUPABASE_KEY else 'No'}")


# Connection retry decorator
def retry_on_connection_error(max_retries=3, base_delay=0.1):
    """Decorator to retry database operations on connection errors"""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    connection_errors = [
                        'resource temporarily unavailable',
                        'connection',
                        'timeout',
                        'network',
                        'temporary failure',
                        'server error',
                        'errno 35'
                    ]

                    if any(err in error_msg for err in connection_errors):
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 0.1)
                            print(
                                f"⚠️ Database connection error, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(delay)
                            continue
                    raise e
            return None

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    connection_errors = [
                        'resource temporarily unavailable',
                        'connection',
                        'timeout',
                        'network',
                        'temporary failure',
                        'server error',
                        'errno 35'
                    ]

                    if any(err in error_msg for err in connection_errors):
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 0.1)
                            print(
                                f"⚠️ Database connection error, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})")
                            time.sleep(delay)
                            continue
                    raise e
            return None

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class SupabaseWrapper:
    """Simple wrapper for Supabase client with retry functionality"""

    def __init__(self, client: Client):
        self._client = client

    @retry_on_connection_error(max_retries=3, base_delay=0.2)
    def table(self, table_name: str):
        """Get table with retry logic"""
        return self._client.table(table_name)

    @retry_on_connection_error(max_retries=3)
    def auth(self):
        """Get auth client with retry logic"""
        return self._client.auth

    @retry_on_connection_error(max_retries=3)
    def storage(self):
        """Get storage client with retry logic"""
        return self._client.storage

    def health_check(self):
        """Simple health check for the database connection"""
        try:
            # Try a simple query to test connection
            result = self._client.table("user_preferences").select("user_id").limit(1).execute()
            return True
        except Exception as e:
            print(f"❌ Database health check failed: {e}")
            return False


# Initialize the client
if SUPABASE_URL and SUPABASE_KEY:
    try:
        # Create basic Supabase client
        base_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase client initialized successfully")

        # Wrap it with retry functionality
        supabase = SupabaseWrapper(base_client)

        # Test the connection
        if supabase.health_check():
            print("✅ Database connection verified")
        else:
            print("⚠️ Database connection test failed, but client initialized")

    except Exception as e:
        print(f"❌ Error initializing Supabase: {e}")
        supabase = None
else:
    print("⚠️ Supabase credentials missing - database features disabled")
    supabase = None


# Utility functions for database operations
@retry_on_connection_error(max_retries=3)
def safe_db_operation(operation_func, *args, **kwargs):
    """Wrapper for safe database operations with automatic retry"""
    try:
        return operation_func(*args, **kwargs)
    except Exception as e:
        print(f"❌ Database operation failed: {e}")
        raise e


# Export the client
__all__ = ['supabase', 'retry_on_connection_error', 'safe_db_operation']