from supabase import create_client, Client
import os
import asyncio
import time
import random
from functools import wraps
from dotenv import load_dotenv
from pathlib import Path

# CRITICAL: Load .env file from the correct location
# Try multiple paths to find the .env file
env_paths = [
    Path('.env'),  # Current directory
    Path('nutrition-backend/.env'),  # If running from parent directory
    Path('../.env'),  # If running from subdirectory
    Path(__file__).parent / '.env'  # Same directory as this file
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded .env from: {env_path}")
        break
else:
    print("⚠️ No .env file found, using system environment variables")
    load_dotenv()  # Try system env vars

# Try both variable names for compatibility
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

# Debug prints to help diagnose issues
print(f"Supabase URL loaded: {'Yes' if SUPABASE_URL else 'No'}")
if SUPABASE_URL:
    print(f"  URL starts with: {SUPABASE_URL[:30]}...")
print(f"Supabase Key loaded: {'Yes' if SUPABASE_KEY else 'No'}")
if SUPABASE_KEY:
    print(f"  Key length: {len(SUPABASE_KEY)} characters")


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
                        'connection', 'timeout', 'network',
                        'temporary failure', 'server error', 'errno 35'
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
                        'connection', 'timeout', 'network',
                        'temporary failure', 'server error', 'errno 35'
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

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class SupabaseWrapper:
    """Wrapper class for Supabase client with retry logic"""

    def __init__(self, client: Client):
        self._client = client

    @retry_on_connection_error(max_retries=3)
    def table(self, table_name: str):
        """Get table reference with retry logic"""
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
        print("Please check your SUPABASE_URL and SUPABASE_KEY in .env file")
        supabase = None
else:
    print("⚠️ Supabase credentials missing - database features disabled")
    print("\n📝 Please create a .env file in nutrition-backend/ with:")
    print("SUPABASE_URL=your-supabase-url")
    print("SUPABASE_SERVICE_KEY=your-service-key")
    print("SUPABASE_KEY=your-anon-key")
    print("OPENAI_API_KEY=your-openai-key")
    supabase = None

# Export the client
__all__ = ['supabase', 'retry_on_connection_error']