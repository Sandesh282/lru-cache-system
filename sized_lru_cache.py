import sys
from lru_cache import LRUCache


class SizedLRUCache(LRUCache):
    """
    LRU cache with size-based eviction instead of count-based eviction.
    
    Designed to model mobile-style memory constraints (Android LruCache,
    iOS NSCache). Entry sizing is approximate and intentionally heuristic.
    """
    
    def __init__(self, max_size_bytes: int):
        """
        Initialize a size-based LRU cache.
        
        Args:
            max_size_bytes: Maximum total memory size in bytes for all cached items.
                          Must be positive.
        
        Raises:
            ValueError: If max_size_bytes is not positive.
        """
        if max_size_bytes <= 0:
            raise ValueError("max_size_bytes must be positive")
        
        # Base class capacity is irrelevant; eviction is enforced by size
        super().__init__(capacity=10**9)
        
        self._max_size_bytes = max_size_bytes
        self._current_size_bytes = 0
    
    def size_of(self, key, value) -> int:
        """
        Calculate the approximate memory size of a key-value pair.
        
        This is a protected method that subclasses can override to provide
        custom sizing logic. The default implementation uses sys.getsizeof()
        as a heuristic.
        
        Note: sys.getsizeof() only measures the object itself, not nested
        objects. For complex objects, this is an approximation.
        
        Args:
            key: The cache key
            value: The cache value
        
        Returns:
            Approximate size in bytes
        """
        key_size = sys.getsizeof(key)
        value_size = sys.getsizeof(value)
        
        # Heuristic overhead for container bookkeeping
        overhead = 100
        
        return key_size + value_size + overhead
    
    def put(self, key, value):
        """
        Insert or update a key-value pair, evicting entries as needed
        to stay within memory limits.
        
        If the item itself is larger than max_size_bytes, it will be rejected
        and not cached.
        
        Args:
            key: The cache key
            value: The cache value
        """
        with self._lock:
            item_size = self.size_of(key, value)
            
            if item_size > self._max_size_bytes:
                return
            
            if key in self._cache:
                old_value = self._cache[key]
                old_size = self.size_of(key, old_value)
                
                self._cache[key] = value
                self._mark_recently_used(key)
                
                self._current_size_bytes -= old_size
                self._current_size_bytes += item_size
                
                # Re-validate size invariant
                self._evict_if_needed()
            else:
                # Evict until enough space exists for new entry
                self._evict_until_space_available(item_size)
                
                self._cache[key] = value
                self._mark_recently_used(key)
                self._current_size_bytes += item_size
    
    def _evict_if_needed(self):
        """
        Evict LRU entries until size invariant is satisfied.
        """
        while self._current_size_bytes > self._max_size_bytes and len(self._cache) > 0:
            self._evict_least_recently_used()
    
    def _evict_until_space_available(self, required_size: int):
        """
        Evict entries until there's enough space for an item of the given size.
        
        Args:
            required_size: Size in bytes needed for the new item
        """
        available_space = self._max_size_bytes - self._current_size_bytes
        
        while available_space < required_size and len(self._cache) > 0:
            self._evict_least_recently_used()
            available_space = self._max_size_bytes - self._current_size_bytes
    
    def _evict_least_recently_used(self):
        """
        Evict the least recently used entry and update size tracking.
        """
        if len(self._cache) == 0:
            return
        
        lru_key = next(iter(self._cache))
        lru_value = self._cache[lru_key]
        evicted_size = self.size_of(lru_key, lru_value)
        
        self._cache.popitem(last=False)
        self._current_size_bytes -= evicted_size
        
        # Defensive guard against accounting drift
        if self._current_size_bytes < 0:
            self._current_size_bytes = 0
        
        self._record_eviction()
    
    def get_stats(self) -> dict:
        """
        Get cache statistics including memory usage.
        
        Returns:
            Dictionary with hits, misses, evictions, hit_ratio, and
            memory usage information.
        """
        stats = super().get_stats()
        
        with self._lock:
            stats.update({
                "current_size_bytes": self._current_size_bytes,
                "max_size_bytes": self._max_size_bytes,
                "size_utilization": self._current_size_bytes / self._max_size_bytes if self._max_size_bytes > 0 else 0.0
            })
        
        return stats

