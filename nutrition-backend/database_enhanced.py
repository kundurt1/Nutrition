# nutrition-backend/database_enhanced.py - FIXED FOR SUPABASE
import asyncio
import time
from typing import Optional, List, Dict, Any, Union
from contextlib import asynccontextmanager
import logging
from dataclasses import dataclass
import json

# Use Supabase client instead of direct PostgreSQL
from supabase import create_client, Client
from dotenv import load_dotenv
import os

from config import config
from exceptions import DatabaseError, DatabaseErrorContext, ErrorHandler

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration settings for Supabase"""
    request_timeout: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    max_connections: int = 20  # For connection pooling simulation
    health_check_interval: int = 60


class DatabasePool:
    """Enhanced Supabase client wrapper with monitoring and health checks"""

    def __init__(self, config_obj: DatabaseConfig = None):
        self.config = config_obj or DatabaseConfig()
        self.client: Optional[Client] = None
        self.is_initialized = False

        # Connection statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0.0,
            'last_health_check': 0
        }

        # Health monitoring
        self.last_health_check = 0
        self.health_check_interval = 60  # seconds
        self.is_healthy = False

    async def initialize(self) -> bool:
        """Initialize the Supabase client"""
        if self.is_initialized:
            logger.warning("Database client already initialized")
            return True

        try:
            logger.info("Initializing Supabase client...")

            # Get credentials from environment/config
            supabase_url = config.supabase_url
            supabase_key = config.supabase_key

            if not supabase_url or not supabase_key:
                raise DatabaseError("Supabase URL and key are required")

            # Create Supabase client
            self.client = create_client(supabase_url, supabase_key)

            # Test the connection
            await self._test_connection()

            self.is_initialized = True
            self.is_healthy = True
            logger.info("✅ Supabase client initialized successfully")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase client: {e}")
            self.is_healthy = False
            raise DatabaseError(
                f"Database initialization failed: {str(e)}",
                operation="client_initialization"
            )

    async def _test_connection(self):
        """Test the Supabase connection"""
        try:
            # Simple test query
            result = self.client.table("users").select("id").limit(1).execute()
            logger.debug("✅ Supabase connection test successful")
        except Exception as e:
            logger.warning(f"⚠️ Supabase connection test failed: {e} (this may be normal if tables don't exist yet)")
            # Don't raise error for connection test failure - tables might not exist yet

    async def execute_query(self, operation: str, table: str, **kwargs) -> Any:
        """Execute a Supabase operation with monitoring"""
        start_time = time.time()

        try:
            self.stats['total_requests'] += 1

            # Get table reference
            table_ref = self.client.table(table)

            # Execute operation based on type
            if operation == "select":
                result = table_ref.select(kwargs.get('columns', '*'))
                if 'where' in kwargs:
                    for condition in kwargs['where']:
                        result = result.eq(condition['column'], condition['value'])
                if 'limit' in kwargs:
                    result = result.limit(kwargs['limit'])
                if 'order' in kwargs:
                    result = result.order(kwargs['order'])
                return result.execute()

            elif operation == "insert":
                return table_ref.insert(kwargs.get('data', {})).execute()

            elif operation == "update":
                result = table_ref.update(kwargs.get('data', {}))
                if 'where' in kwargs:
                    for condition in kwargs['where']:
                        result = result.eq(condition['column'], condition['value'])
                return result.execute()

            elif operation == "delete":
                result = table_ref.delete()
                if 'where' in kwargs:
                    for condition in kwargs['where']:
                        result = result.eq(condition['column'], condition['value'])
                return result.execute()

            else:
                raise DatabaseError(f"Unsupported operation: {operation}")

        except Exception as e:
            self.stats['failed_requests'] += 1
            logger.error(f"Database operation failed: {e}")
            raise DatabaseError(f"Database operation failed: {str(e)}", operation=operation)

        finally:
            # Update statistics
            response_time = time.time() - start_time
            self._update_stats(response_time, success=True)

    def _update_stats(self, response_time: float, success: bool):
        """Update request statistics"""
        if success:
            self.stats['successful_requests'] += 1

            # Update average response time
            total_successful = self.stats['successful_requests']
            current_avg = self.stats['average_response_time']
            self.stats['average_response_time'] = (
                    (current_avg * (total_successful - 1) + response_time) / total_successful
            )

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        current_time = time.time()

        # Skip if checked recently
        if current_time - self.last_health_check < self.health_check_interval:
            return {'status': 'healthy' if self.is_healthy else 'unhealthy', 'cached': True}

        try:
            # Test basic connectivity
            start_time = time.time()
            result = self.client.table("users").select("id").limit(1).execute()
            response_time = time.time() - start_time

            self.is_healthy = True
            self.last_health_check = current_time

            return {
                'status': 'healthy',
                'response_time': response_time,
                'client_initialized': self.is_initialized,
                'statistics': self.stats,
                'last_check': current_time
            }

        except Exception as e:
            self.is_healthy = False
            self.last_health_check = current_time

            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': current_time,
                'statistics': self.stats
            }

    async def close(self):
        """Close the client connection"""
        if self.client:
            # Supabase client doesn't require explicit closing
            self.client = None
            self.is_initialized = False
            self.is_healthy = False
            logger.info("✅ Supabase client closed")

    def get_stats(self) -> Dict[str, Any]:
        """Get current database statistics"""
        success_rate = 0
        if self.stats['total_requests'] > 0:
            success_rate = (self.stats['successful_requests'] / self.stats['total_requests']) * 100

        return {
            **self.stats,
            'success_rate_percent': success_rate,
            'is_healthy': self.is_healthy,
            'is_initialized': self.is_initialized
        }

    @property
    def supabase_client(self) -> Client:
        """Get the underlying Supabase client"""
        if not self.client:
            raise DatabaseError("Database client not initialized")
        return self.client


# Repository Pattern for Database Operations
class BaseRepository:
    """Base repository class with common database operations using Supabase"""

    def __init__(self, db_pool: DatabasePool, table_name: str):
        self.db = db_pool
        self.table_name = table_name

    async def find_by_id(self, id_value: Any, id_column: str = "id") -> Optional[Dict[str, Any]]:
        """Find record by ID"""
        try:
            result = await self.db.execute_query(
                "select",
                self.table_name,
                where=[{'column': id_column, 'value': id_value}],
                limit=1
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error finding {self.table_name} by {id_column}: {e}")
            return None

    async def find_all(self, where_conditions: List[Dict] = None, limit: int = None,
                       order_by: str = None) -> List[Dict[str, Any]]:
        """Find all records with optional filtering"""
        try:
            kwargs = {}
            if where_conditions:
                kwargs['where'] = where_conditions
            if limit:
                kwargs['limit'] = limit
            if order_by:
                kwargs['order'] = order_by

            result = await self.db.execute_query("select", self.table_name, **kwargs)
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error finding all {self.table_name}: {e}")
            return []

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new record"""
        try:
            result = await self.db.execute_query("insert", self.table_name, data=data)
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating {self.table_name}: {e}")
            raise DatabaseError(f"Failed to create {self.table_name}: {str(e)}")

    async def update(self, id_value: Any, data: Dict[str, Any],
                     id_column: str = "id") -> Dict[str, Any]:
        """Update record by ID"""
        try:
            result = await self.db.execute_query(
                "update",
                self.table_name,
                data=data,
                where=[{'column': id_column, 'value': id_value}]
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error updating {self.table_name}: {e}")
            raise DatabaseError(f"Failed to update {self.table_name}: {str(e)}")

    async def delete(self, id_value: Any, id_column: str = "id") -> bool:
        """Delete record by ID"""
        try:
            result = await self.db.execute_query(
                "delete",
                self.table_name,
                where=[{'column': id_column, 'value': id_value}]
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting {self.table_name}: {e}")
            return False


# Specific Repository Classes
class UserRepository(BaseRepository):
    """Repository for user-related database operations"""

    def __init__(self, db_pool: DatabasePool):
        super().__init__(db_pool, "users")

    async def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find user by email"""
        try:
            result = await self.db.execute_query(
                "select",
                self.table_name,
                where=[{'column': 'email', 'value': email}],
                limit=1
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error finding user by email: {e}")
            return None


class RecipeRepository(BaseRepository):
    """Repository for recipe-related database operations"""

    def __init__(self, db_pool: DatabasePool):
        super().__init__(db_pool, "recipes")

    async def find_by_user_id(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Find recipes by user ID"""
        return await self.find_all(
            where_conditions=[{'column': 'user_id', 'value': user_id}],
            limit=limit,
            order_by="created_at.desc"
        )


class UserPreferencesRepository(BaseRepository):
    """Repository for user preferences"""

    def __init__(self, db_pool: DatabasePool):
        super().__init__(db_pool, "user_preferences")


# Database Manager
class DatabaseManager:
    """Centralized database management"""

    def __init__(self):
        self.pool: Optional[DatabasePool] = None
        self.repositories: Dict[str, BaseRepository] = {}
        self.is_initialized = False

    async def initialize(self) -> bool:
        """Initialize database pool and repositories"""
        if self.is_initialized:
            return True

        try:
            # Initialize pool
            self.pool = DatabasePool()
            await self.pool.initialize()

            # Initialize repositories
            self.repositories = {
                'users': UserRepository(self.pool),
                'recipes': RecipeRepository(self.pool),
                'user_preferences': UserPreferencesRepository(self.pool)
            }

            self.is_initialized = True
            logger.info("✅ Database manager initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Database manager initialization failed: {e}")
            raise

    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
        self.is_initialized = False
        logger.info("✅ Database manager closed")

    def get_repository(self, name: str) -> BaseRepository:
        """Get repository by name"""
        if not self.is_initialized:
            raise DatabaseError("Database manager not initialized")

        if name not in self.repositories:
            raise DatabaseError(f"Repository '{name}' not found")

        return self.repositories[name]

    async def health_check(self) -> Dict[str, Any]:
        """Get overall database health status"""
        if not self.pool:
            return {'status': 'not_initialized'}

        return await self.pool.health_check()

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        if not self.pool:
            return {'status': 'not_initialized'}

        return self.pool.get_stats()

    @property
    def supabase_client(self) -> Client:
        """Get the underlying Supabase client"""
        if not self.pool:
            raise DatabaseError("Database not initialized")
        return self.pool.supabase_client


# Global instance
db_manager = DatabaseManager()


# Convenience functions
async def get_db_pool() -> DatabasePool:
    """Get database pool instance"""
    if not db_manager.is_initialized:
        await db_manager.initialize()
    return db_manager.pool


async def get_repository(name: str) -> BaseRepository:
    """Get repository instance"""
    return db_manager.get_repository(name)


# Database initialization for FastAPI
async def init_database():
    """Initialize database for FastAPI startup"""
    try:
        await db_manager.initialize()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise


async def close_database():
    """Close database for FastAPI shutdown"""
    try:
        await db_manager.close()
        logger.info("✅ Database closed successfully")
    except Exception as e:
        logger.error(f"❌ Database closure error: {e}")


# Database health check endpoint helper
async def database_health_check() -> Dict[str, Any]:
    """Health check helper for API endpoints"""
    try:
        return await db_manager.health_check()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


# Export all
__all__ = [
    # Core classes
    'DatabasePool', 'DatabaseConfig', 'DatabaseManager',
    # Repository classes
    'BaseRepository', 'UserRepository', 'RecipeRepository', 'UserPreferencesRepository',
    # Global instances and functions
    'db_manager', 'get_db_pool', 'get_repository',
    'init_database', 'close_database', 'database_health_check'
]