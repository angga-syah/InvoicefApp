"""
Invoice Management System - Cache Service
Performance optimization through intelligent caching strategies.
"""

import time
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union
from threading import Lock
from functools import wraps
import logging
import hashlib

from config import redis_config, performance_config

logger = logging.getLogger(__name__)

class MemoryCache:
    """In-memory cache with TTL support"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict] = {}
        self._lock = Lock()
        self._access_order: List[str] = []
    
    def _is_expired(self, entry: Dict) -> bool:
        """Check if cache entry is expired"""
        if 'expires_at' not in entry:
            return False
        return datetime.now() > entry['expires_at']
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries"""
        current_time = datetime.now()
        expired_keys = []
        
        for key, entry in self._cache.items():
            if 'expires_at' in entry and current_time > entry['expires_at']:
                expired_keys.append(key)
        
        for key in expired_keys:
            self._cache.pop(key, None)
            if key in self._access_order:
                self._access_order.remove(key)
    
    def _evict_lru(self) -> None:
        """Evict least recently used entries if cache is full"""
        while len(self._cache) >= self.max_size and self._access_order:
            lru_key = self._access_order.pop(0)
            self._cache.pop(lru_key, None)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check expiration
            if self._is_expired(entry):
                self._cache.pop(key, None)
                if key in self._access_order:
                    self._access_order.remove(key)
                return None
            
            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        with self._lock:
            if ttl is None:
                ttl = self.default_ttl
            
            expires_at = datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None
            
            # Clean expired entries periodically
            if len(self._cache) % 100 == 0:
                self._cleanup_expired()
            
            # Evict if necessary
            if len(self._cache) >= self.max_size:
                self._evict_lru()
            
            # Store entry
            self._cache[key] = {
                'value': value,
                'created_at': datetime.now(),
                'expires_at': expires_at
            }
            
            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self._lock:
            if key in self._cache:
                self._cache.pop(key, None)
                if key in self._access_order:
                    self._access_order.remove(key)
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    def keys(self, pattern: str = None) -> List[str]:
        """Get all keys, optionally filtered by pattern"""
        with self._lock:
            self._cleanup_expired()
            
            if pattern is None:
                return list(self._cache.keys())
            
            import fnmatch
            return [key for key in self._cache.keys() if fnmatch.fnmatch(key, pattern)]
    
    def size(self) -> int:
        """Get current cache size"""
        with self._lock:
            self._cleanup_expired()
            return len(self._cache)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            self._cleanup_expired()
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'keys': len(self._access_order)
            }

class RedisCache:
    """Redis-based cache implementation"""
    
    def __init__(self):
        self.enabled = redis_config.enabled
        self.redis_client = None
        
        if self.enabled:
            try:
                import redis
                self.redis_client = redis.from_url(redis_config.url)
                # Test connection
                self.redis_client.ping()
                logger.info("Redis cache initialized successfully")
            except ImportError:
                logger.warning("Redis not available, falling back to memory cache")
                self.enabled = False
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}, falling back to memory cache")
                self.enabled = False
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        if not self.enabled:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value is not None:
                return json.loads(value.decode('utf-8'))
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in Redis"""
        if not self.enabled:
            return
        
        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                self.redis_client.setex(key, ttl, serialized)
            else:
                self.redis_client.set(key, serialized)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
    
    def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self.enabled:
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    def clear(self) -> None:
        """Clear all Redis keys"""
        if not self.enabled:
            return
        
        try:
            self.redis_client.flushdb()
        except Exception as e:
            logger.error(f"Redis clear error: {e}")

class CacheService:
    """Main cache service with fallback strategy"""
    
    def __init__(self):
        self.redis_cache = RedisCache()
        self.memory_cache = MemoryCache(
            max_size=performance_config.cache_size,
            default_ttl=3600
        )
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._sets = 0
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            if isinstance(arg, (dict, list)):
                key_parts.append(hashlib.md5(json.dumps(arg, sort_keys=True, default=str).encode()).hexdigest())
            else:
                key_parts.append(str(arg))
        
        # Add keyword arguments
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            kwargs_str = json.dumps(sorted_kwargs, default=str)
            key_parts.append(hashlib.md5(kwargs_str.encode()).hexdigest())
        
        return ':'.join(key_parts)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache with fallback"""
        # Try Redis first
        value = self.redis_cache.get(key)
        if value is not None:
            self._hits += 1
            return value
        
        # Fallback to memory cache
        value = self.memory_cache.get(key)
        if value is not None:
            self._hits += 1
            return value
        
        self._misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        self._sets += 1
        
        # Set in both caches
        self.redis_cache.set(key, value, ttl)
        self.memory_cache.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        redis_deleted = self.redis_cache.delete(key)
        memory_deleted = self.memory_cache.delete(key)
        return redis_deleted or memory_deleted
    
    def clear(self, pattern: str = None) -> None:
        """Clear cache entries"""
        if pattern:
            # Clear matching keys
            keys = self.memory_cache.keys(pattern)
            for key in keys:
                self.delete(key)
        else:
            # Clear all
            self.redis_cache.clear()
            self.memory_cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hits': self._hits,
            'misses': self._misses,
            'sets': self._sets,
            'hit_rate': f"{hit_rate:.2f}%",
            'memory_cache': self.memory_cache.stats(),
            'redis_enabled': self.redis_cache.enabled
        }

# Global cache service instance
cache_service = CacheService()

def cached(prefix: str, ttl: int = 3600, use_args: bool = True, use_kwargs: bool = True):
    """Decorator for caching function results"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if use_args or use_kwargs:
                key_args = args if use_args else ()
                key_kwargs = kwargs if use_kwargs else {}
                cache_key = cache_service._generate_key(prefix, *key_args, **key_kwargs)
            else:
                cache_key = prefix
            
            # Try to get from cache
            cached_result = cache_service.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                return cached_result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {func.__name__}: {cache_key}")
            result = func(*args, **kwargs)
            
            cache_service.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

def invalidate_cache(pattern: str) -> None:
    """Invalidate cache entries matching pattern"""
    cache_service.clear(pattern)

class QueryCache:
    """Specialized cache for database queries"""
    
    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
    
    @cached("companies:active", ttl=1800)
    def get_active_companies(self) -> List[Dict]:
        """Cache active companies"""
        # This will be called by the actual data service
        pass
    
    @cached("tka:active", ttl=1800)
    def get_active_tka_workers(self) -> List[Dict]:
        """Cache active TKA workers"""
        pass
    
    @cached("jobs", ttl=3600)
    def get_company_jobs(self, company_id: int) -> List[Dict]:
        """Cache company job descriptions"""
        pass
    
    @cached("settings", ttl=7200)
    def get_application_settings(self) -> Dict[str, Any]:
        """Cache application settings"""
        pass
    
    def invalidate_company_cache(self, company_id: int = None) -> None:
        """Invalidate company-related cache"""
        if company_id:
            invalidate_cache(f"jobs:*:{company_id}:*")
        else:
            invalidate_cache("companies:*")
            invalidate_cache("jobs:*")
    
    def invalidate_tka_cache(self) -> None:
        """Invalidate TKA-related cache"""
        invalidate_cache("tka:*")
    
    def invalidate_settings_cache(self) -> None:
        """Invalidate settings cache"""
        invalidate_cache("settings:*")

class SearchCache:
    """Specialized cache for search results"""
    
    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
        self.search_ttl = 300  # 5 minutes for search results
    
    def get_search_results(self, entity_type: str, query: str, limit: int = 50) -> Optional[List[Dict]]:
        """Get cached search results"""
        cache_key = self.cache._generate_key(f"search:{entity_type}", query, limit)
        return self.cache.get(cache_key)
    
    def set_search_results(self, entity_type: str, query: str, results: List[Dict], limit: int = 50) -> None:
        """Cache search results"""
        cache_key = self.cache._generate_key(f"search:{entity_type}", query, limit)
        self.cache.set(cache_key, results, self.search_ttl)
    
    def invalidate_search_cache(self, entity_type: str = None) -> None:
        """Invalidate search cache"""
        if entity_type:
            invalidate_cache(f"search:{entity_type}:*")
        else:
            invalidate_cache("search:*")

class SessionCache:
    """User session-specific cache"""
    
    def __init__(self, cache_service: CacheService, user_id: int):
        self.cache = cache_service
        self.user_id = user_id
        self.session_ttl = 3600  # 1 hour
    
    def _user_key(self, key: str) -> str:
        """Generate user-specific cache key"""
        return f"user:{self.user_id}:{key}"
    
    def get_user_preference(self, key: str) -> Optional[Any]:
        """Get user preference from cache"""
        cache_key = self._user_key(f"pref:{key}")
        return self.cache.get(cache_key)
    
    def set_user_preference(self, key: str, value: Any) -> None:
        """Set user preference in cache"""
        cache_key = self._user_key(f"pref:{key}")
        self.cache.set(cache_key, value, self.session_ttl * 24)  # Preferences last longer
    
    def get_recent_items(self, item_type: str) -> Optional[List[Dict]]:
        """Get recently accessed items"""
        cache_key = self._user_key(f"recent:{item_type}")
        return self.cache.get(cache_key)
    
    def add_recent_item(self, item_type: str, item: Dict, max_items: int = 10) -> None:
        """Add item to recent items list"""
        cache_key = self._user_key(f"recent:{item_type}")
        recent_items = self.get_recent_items(item_type) or []
        
        # Remove item if already exists
        recent_items = [i for i in recent_items if i.get('id') != item.get('id')]
        
        # Add to front
        recent_items.insert(0, item)
        
        # Limit list size
        recent_items = recent_items[:max_items]
        
        self.cache.set(cache_key, recent_items, self.session_ttl)
    
    def clear_user_cache(self) -> None:
        """Clear all user-specific cache"""
        invalidate_cache(f"user:{self.user_id}:*")

# Cache instances
query_cache = QueryCache(cache_service)
search_cache = SearchCache(cache_service)

def get_session_cache(user_id: int) -> SessionCache:
    """Get session cache for user"""
    return SessionCache(cache_service, user_id)

def warm_up_cache():
    """Warm up cache with frequently accessed data"""
    logger.info("Warming up cache...")
    
    try:
        # This would be called during application startup
        # to preload frequently accessed data
        
        # Example: Preload active companies
        # companies = data_service.get_active_companies()
        # cache_service.set("companies:active", companies, 3600)
        
        logger.info("Cache warm-up completed")
    except Exception as e:
        logger.error(f"Cache warm-up failed: {e}")

def cleanup_cache():
    """Cleanup expired cache entries"""
    logger.info("Cleaning up cache...")
    
    try:
        # Memory cache cleanup is automatic
        # Redis cleanup can be done here if needed
        
        stats = cache_service.stats()
        logger.info(f"Cache cleanup completed. Stats: {stats}")
    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")

if __name__ == "__main__":
    # Test cache service
    print("Testing cache service...")
    
    # Test basic operations
    cache_service.set("test_key", {"data": "test_value"}, 60)
    value = cache_service.get("test_key")
    print(f"Cache test: {value}")
    
    # Test decorator
    @cached("test_func", ttl=60)
    def expensive_function(x: int) -> int:
        time.sleep(0.1)  # Simulate expensive operation
        return x * x
    
    # First call - should be slow
    start_time = time.time()
    result1 = expensive_function(5)
    time1 = time.time() - start_time
    
    # Second call - should be fast (cached)
    start_time = time.time()
    result2 = expensive_function(5)
    time2 = time.time() - start_time
    
    print(f"First call: {result1} in {time1:.3f}s")
    print(f"Second call: {result2} in {time2:.3f}s")
    print(f"Cache speedup: {time1/time2:.1f}x")
    
    # Print statistics
    stats = cache_service.stats()
    print(f"Cache stats: {stats}")
    
    print("✅ Cache service test completed")