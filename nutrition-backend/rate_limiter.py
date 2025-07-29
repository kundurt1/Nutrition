# nutrition-backend/rate_limiter.py
import time
import asyncio
import hashlib
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""
    pass


class TokenBucketRateLimiter:
    """Advanced token bucket rate limiter with multiple tiers"""

    def __init__(self,
                 max_requests: int = 100,
                 window_seconds: int = 3600,
                 burst_limit: int = None):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.burst_limit = burst_limit or max_requests // 10  # 10% burst allowance

        # Storage for client request history
        self.clients: Dict[str, deque] = defaultdict(deque)
        self.blocked_clients: Dict[str, float] = {}  # client_id -> unblock_time
        self.burst_tracking: Dict[str, deque] = defaultdict(deque)

        # Thread safety
        self.lock = asyncio.Lock()

        # Statistics
        self.stats = {
            'total_requests': 0,
            'blocked_requests': 0,
            'unique_clients': 0
        }

    async def is_allowed(self, client_id: str, endpoint_type: str = "general") -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is allowed for client
        Returns: (is_allowed, rate_limit_info)
        """
        async with self.lock:
            now = time.time()

            # Check if client is temporarily blocked
            if client_id in self.blocked_clients:
                if now < self.blocked_clients[client_id]:
                    self.stats['blocked_requests'] += 1
                    return False, {
                        'allowed': False,
                        'reason': 'temporarily_blocked',
                        'retry_after': int(self.blocked_clients[client_id] - now),
                        'limit': self.max_requests,
                        'window': self.window_seconds
                    }
                else:
                    # Unblock client
                    del self.blocked_clients[client_id]

            # Get or create client request history
            client_requests = self.clients[client_id]
            burst_requests = self.burst_tracking[client_id]

            # Clean old requests outside the window
            cutoff_time = now - self.window_seconds
            while client_requests and client_requests[0] < cutoff_time:
                client_requests.popleft()

            # Clean old burst tracking (last 60 seconds)
            burst_cutoff = now - 60
            while burst_requests and burst_requests[0] < burst_cutoff:
                burst_requests.popleft()

            # Check burst limit (requests in last minute)
            if len(burst_requests) >= self.burst_limit:
                logger.warning(f"Burst limit exceeded for client {client_id[:8]}... ({len(burst_requests)} req/min)")
                # Temporarily block for 5 minutes
                self.blocked_clients[client_id] = now + 300
                self.stats['blocked_requests'] += 1
                return False, {
                    'allowed': False,
                    'reason': 'burst_limit_exceeded',
                    'retry_after': 300,
                    'limit': self.burst_limit,
                    'window': 60
                }

            # Check main rate limit
            current_requests = len(client_requests)
            if current_requests >= self.max_requests:
                logger.warning(
                    f"Rate limit exceeded for client {client_id[:8]}... ({current_requests}/{self.max_requests})")
                self.stats['blocked_requests'] += 1
                return False, {
                    'allowed': False,
                    'reason': 'rate_limit_exceeded',
                    'retry_after': int(self.window_seconds - (now - client_requests[0])),
                    'limit': self.max_requests,
                    'window': self.window_seconds,
                    'current': current_requests
                }

            # Allow request - add to tracking
            client_requests.append(now)
            burst_requests.append(now)

            # Update statistics
            self.stats['total_requests'] += 1
            if client_id not in self.clients or len(self.clients[client_id]) == 1:
                self.stats['unique_clients'] += 1

            return True, {
                'allowed': True,
                'limit': self.max_requests,
                'remaining': self.max_requests - len(client_requests),
                'reset_time': int(client_requests[0] + self.window_seconds) if client_requests else int(
                    now + self.window_seconds),
                'window': self.window_seconds
            }

    def get_stats(self) -> Dict[str, any]:
        """Get rate limiter statistics"""
        return {
            **self.stats,
            'active_clients': len(self.clients),
            'blocked_clients': len(self.blocked_clients)
        }

    async def cleanup_old_entries(self):
        """Clean up old entries to prevent memory bloat"""
        now = time.time()
        cutoff_time = now - self.window_seconds * 2  # Keep 2 windows worth

        async with self.lock:
            # Clean up client request histories
            clients_to_remove = []
            for client_id, requests in self.clients.items():
                while requests and requests[0] < cutoff_time:
                    requests.popleft()
                if not requests:
                    clients_to_remove.append(client_id)

            for client_id in clients_to_remove:
                del self.clients[client_id]

            # Clean up blocked clients
            blocked_to_remove = [
                client_id for client_id, unblock_time in self.blocked_clients.items()
                if now > unblock_time
            ]
            for client_id in blocked_to_remove:
                del self.blocked_clients[client_id]


# Rate limiter instances for different endpoint types
class RateLimitConfig:
    """Configuration for different rate limiting tiers"""

    # General API endpoints
    GENERAL = TokenBucketRateLimiter(
        max_requests=100,  # 100 requests per hour
        window_seconds=3600,  # 1 hour window
        burst_limit=20  # Max 20 requests per minute
    )

    # OpenAI/AI generation endpoints (more restrictive)
    AI_GENERATION = TokenBucketRateLimiter(
        max_requests=20,  # 20 AI requests per hour
        window_seconds=3600,  # 1 hour window
        burst_limit=5  # Max 5 AI requests per minute
    )

    # Authentication endpoints (very restrictive)
    AUTH = TokenBucketRateLimiter(
        max_requests=10,  # 10 auth attempts per hour
        window_seconds=3600,  # 1 hour window
        burst_limit=3  # Max 3 auth attempts per minute
    )

    # Image upload endpoints
    UPLOADS = TokenBucketRateLimiter(
        max_requests=50,  # 50 uploads per hour
        window_seconds=3600,  # 1 hour window
        burst_limit=10  # Max 10 uploads per minute
    )


def get_client_identifier(request: Request) -> str:
    """
    Get unique client identifier for rate limiting
    Uses multiple factors to identify clients
    """
    identifiers = []

    # 1. Try to get authenticated user ID
    user_id = None
    auth_header = request.headers.get("authorization")
    if auth_header:
        try:
            # Extract user ID from JWT token (simplified)
            user_id = request.headers.get("x-user-id")
        except:
            pass

    if user_id:
        identifiers.append(f"user:{user_id}")

    # 2. Get IP address
    client_ip = request.client.host
    forwarded_for = request.headers.get("x-forwarded-for")
    real_ip = request.headers.get("x-real-ip")

    if forwarded_for:
        # Take the first IP in the chain
        client_ip = forwarded_for.split(",")[0].strip()
    elif real_ip:
        client_ip = real_ip

    identifiers.append(f"ip:{client_ip}")

    # 3. Add user agent hash for additional uniqueness
    user_agent = request.headers.get("user-agent", "")
    if user_agent:
        ua_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]
        identifiers.append(f"ua:{ua_hash}")

    # Combine identifiers
    combined = "|".join(identifiers)

    # Hash the combined identifier for privacy and consistent length
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def get_endpoint_type(request: Request) -> str:
    """Determine the rate limit tier based on the endpoint"""
    path = str(request.url.path).lower()
    method = request.method.upper()

    # AI/OpenAI endpoints
    ai_patterns = [
        '/generate', '/recipe', '/coaching', '/nutrition-advice',
        '/openai', '/ai', '/chat', '/completion'
    ]
    if any(pattern in path for pattern in ai_patterns):
        return "ai_generation"

    # Authentication endpoints
    auth_patterns = [
        '/login', '/signup', '/auth', '/register', '/password',
        '/token', '/oauth', '/verify'
    ]
    if any(pattern in path for pattern in auth_patterns):
        return "auth"

    # Upload endpoints
    if method == "POST" and any(pattern in path for pattern in ['/upload', '/image', '/file']):
        return "uploads"

    # Default to general
    return "general"


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware for FastAPI
    """
    # Get client identifier and endpoint type
    client_id = get_client_identifier(request)
    endpoint_type = get_endpoint_type(request)

    # Select appropriate rate limiter
    limiters = {
        "general": RateLimitConfig.GENERAL,
        "ai_generation": RateLimitConfig.AI_GENERATION,
        "auth": RateLimitConfig.AUTH,
        "uploads": RateLimitConfig.UPLOADS
    }

    limiter = limiters.get(endpoint_type, RateLimitConfig.GENERAL)