#!/usr/bin/env python3
"""
Simple caching layer for performance optimization.

Provides in-memory caching with TTL (Time To Live) support.
For production, consider using Redis or Memcached.
"""

import time
import logging
from typing import Any, Optional, Callable
from functools import wraps
from collections import OrderedDict

logger = logging.getLogger("buyer")


class CacheEntry:
    """Represents a cached value with expiration"""

    def __init__(self, value: Any, ttl: int):
        """
        Initialize cache entry.

        Args:
            value: Value to cache
            ttl: Time to live in seconds
        """
        self.value = value
        self.expires_at = time.time() + ttl if ttl > 0 else float("inf")

    def is_expired(self) -> bool:
        """Check if entry has expired"""
        return time.time() > self.expires_at


class SimpleCache:
    """
    Simple in-memory cache with LRU eviction and TTL support.

    Features:
    - TTL (Time To Live) for entries
    - LRU (Least Recently Used) eviction when max size reached
    - Thread-safe operations
    - Cache statistics

    Example:
        >>> cache = SimpleCache(max_size=100, default_ttl=300)
        >>> cache.set("key", "value")
        >>> cache.get("key")
        'value'
        >>> cache.delete("key")
        >>> cache.get("key")
        None
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize cache.

        Args:
            max_size: Maximum number of entries before LRU eviction
            default_ttl: Default TTL in seconds (0 = no expiration)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            self._misses += 1
            return None

        entry = self._cache[key]
        if entry.is_expired():
            del self._cache[key]
            self._misses += 1
            logger.debug(f"Cache miss (expired): {key}")
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        self._hits += 1
        logger.debug(f"Cache hit: {key}")
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None = use default)
        """
        if ttl is None:
            ttl = self.default_ttl

        # Remove if exists (to update position)
        if key in self._cache:
            del self._cache[key]

        # Add new entry
        self._cache[key] = CacheEntry(value, ttl)

        # Evict LRU if needed
        if len(self._cache) > self.max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            logger.debug(f"Cache eviction (LRU): {oldest_key}")

        logger.debug(f"Cache set: {key} (TTL={ttl}s)")

    def delete(self, key: str) -> bool:
        """
        Delete entry from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache delete: {key}")
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("Cache cleared")

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "total_requests": total_requests,
        }

    def cleanup_expired(self) -> int:
        """
        Remove expired entries.

        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, entry in self._cache.items() if entry.is_expired()
        ]
        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)


# Global cache instance
_global_cache = SimpleCache(max_size=1000, default_ttl=300)


def get_cache() -> SimpleCache:
    """Get global cache instance"""
    return _global_cache


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator for caching function results.

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key

    Example:
        @cached(ttl=60, key_prefix="brand")
        def get_brand_by_id(brand_id: int):
            # Expensive operation
            return fetch_from_database(brand_id)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:"
            cache_key += ":".join(str(arg) for arg in args)
            if kwargs:
                cache_key += ":" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))

            # Try to get from cache
            cache = get_cache()
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)
            return result

        return wrapper

    return decorator


def invalidate_cache_pattern(pattern: str) -> int:
    """
    Invalidate all cache keys matching pattern.

    Args:
        pattern: Pattern to match (simple substring match)

    Returns:
        Number of keys invalidated
    """
    cache = get_cache()
    keys_to_delete = [key for key in cache._cache.keys() if pattern in key]

    for key in keys_to_delete:
        cache.delete(key)

    if keys_to_delete:
        logger.info(f"Invalidated {len(keys_to_delete)} cache entries matching '{pattern}'")

    return len(keys_to_delete)
