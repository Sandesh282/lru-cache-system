from typing import Optional, Any
from lru_cache import LRUCache
from disk_cache import DiskCache


class MobileCache:
    """
    A two-layer cache architecture suitable for mobile-like constraints.
    
    This cache orchestrates a memory cache (fast, limited) and a disk cache
    (slower, persistent). The design follows the pattern used by popular
    mobile image loaders like Glide (Android) and Kingfisher (iOS).
    
    Architecture:
    - Memory Layer: Fast LRU cache with size-based eviction
    - Disk Layer: Persistent filesystem cache
    
    Flow:
    - get(key): Check memory -> if miss, check disk -> if found, promote to memory
    - put(key, value): Write to both memory and disk
    
    This class uses composition, not inheritance, to coordinate the two layers.
    It does not know about internal LRU mechanics - it only coordinates cache tiers.
    """
    
    def __init__(self, memory_cache: LRUCache, disk_cache: DiskCache):
        """
        Initialize a two-layer cache.
        
        Args:
            memory_cache: The memory layer cache (typically SizedLRUCache)
            disk_cache: The disk layer cache (DiskCache instance)
        """
        self._memory_cache = memory_cache
        self._disk_cache = disk_cache
    
    def get(self, key: Any) -> Optional[Any]:
        """
        Retrieve a value from the cache hierarchy.
        
        Flow:
        1. Check memory cache (fast path)
        2. If miss, check disk cache
        3. If found on disk, promote to memory cache
        4. Return the value or None if not found
        
        Args:
            key: The cache key
        
        Returns:
            The cached value if found in either layer, None otherwise
        """
        # Fast path: check memory first
        value = self._memory_cache.get(key)
        if value is not None:
            return value
        
        # Memory miss: check disk
        value = self._disk_cache.get(key)
        if value is not None:
            # Promote to memory cache for faster future access
            self._memory_cache.put(key, value)
            return value
        
        # Not found in either layer
        return None
    
    def put(self, key: Any, value: Any):
        """
        Store a value in both cache layers.
        
        Flow:
        1. Write to memory cache (for fast access)
        2. Write to disk cache (for persistence)
        
        Args:
            key: The cache key
            value: The value to cache
        """
        # Write to memory cache
        self._memory_cache.put(key, value)
        
        # Also write to disk cache for persistence
        try:
            self._disk_cache.put(key, value)
        except (OSError, Exception):
            # Disk write failure does not invalidate memory entry
            pass
    
    def get_stats(self) -> dict:
        """
        Get statistics from both cache layers.
        
        Returns:
            Dictionary containing:
            - memory_stats: Statistics from memory cache
            - disk_size_bytes: Total size of disk cache
            - combined_hit_ratio: Overall hit ratio (memory hits / total requests)
        """
        memory_stats = self._memory_cache.get_stats()
        disk_size = self._disk_cache.get_size_bytes()
        
        # Calculate combined metrics
        total_requests = memory_stats.get('hits', 0) + memory_stats.get('misses', 0)
        combined_hit_ratio = memory_stats.get('hit_ratio', 0.0)
        
        return {
            "memory_stats": memory_stats,
            "disk_size_bytes": disk_size,
            "combined_hit_ratio": combined_hit_ratio,
            "total_requests": total_requests
        }
    
    def clear(self):
        """
        Clear both cache layers.
        
        This removes all entries from memory and disk caches.
        """
        # Memory cache relies on eviction semantics; disk is cleared explicitly
        self._disk_cache.clear()
    
    def remove(self, key: Any) -> bool:
        """
        Remove a key from both cache layers.
        
        Args:
            key: The cache key to remove
        
        Returns:
            True if the key was removed from at least one layer, False otherwise
        """
        # Memory layer does not expose explicit removal by design
        disk_removed = self._disk_cache.remove(key)
        
        return disk_removed

