from collections import OrderedDict
import json
import threading


class LRUCache:
    """
    A simple LRU (Least Recently Used) cache with a fixed capacity.

    The implementation prioritizes clarity and correctness over cleverness.
    Performance is still O(1) for all core operations, but the main goal is
    that the eviction behavior is easy to reason about and hard to break.
    """

    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        self._capacity = capacity
        self._cache = OrderedDict()

        # Metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        # Coarse-grained lock. This is intentionally simple for now;
        # correctness matters more than squeezing out concurrency.
        self._lock = threading.Lock()

    def get(self, key):
        """
        Return the value for `key` if present, otherwise None.
        Accessing a key marks it as recently used.
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            self._hits += 1
            self._cache.move_to_end(key)
            return self._cache[key]

    def put(self, key, value):
        """
        Insert or update a key-value pair.
        If capacity is exceeded, the least recently used item is evicted.
        """
        with self._lock:
            if key in self._cache:
                # Update existing key and mark it as recently used
                self._cache.move_to_end(key)
            self._cache[key] = value
            self._evict_if_needed()

    def _evict_if_needed(self):
        """
        Evict entries until the cache satisfies the capacity constraint.
        """
        while len(self._cache) > self._capacity:
            self._evict_least_recently_used()

    def _evict_least_recently_used(self):
        """
        Remove the least recently used item from the cache.
        """
        self._cache.popitem(last=False)
        self._evictions += 1

    def get_stats(self) -> dict:
        """
        Return a snapshot of cache metrics.
        """
        with self._lock:
            total = self._hits + self._misses
            hit_ratio = (self._hits / total) if total > 0 else 0.0
            return {
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_ratio": hit_ratio,
            }

    def save(self, filepath: str):
        """
        Persist cache state to disk.
        The LRU order is preserved exactly.
        """
        with self._lock:
            data = {
                "capacity": self._capacity,
                "entries": [
                    {"key": k, "value": v} for k, v in self._cache.items()
                ],
                "metrics": {
                    "hits": self._hits,
                    "misses": self._misses,
                    "evictions": self._evictions,
                },
            }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, filepath: str):
        """
        Load a cache instance from disk.
        Validation is performed to avoid restoring an invalid state.
        """
        with open(filepath, "r") as f:
            data = json.load(f)

        cache = cls(data["capacity"])

        for entry in data.get("entries", []):
            cache._cache[entry["key"]] = entry["value"]

        metrics = data.get("metrics", {})
        cache._hits = metrics.get("hits", 0)
        cache._misses = metrics.get("misses", 0)
        cache._evictions = metrics.get("evictions", 0)

        # Basic invariant check: loaded state should not exceed capacity
        if len(cache._cache) > cache._capacity:
            raise ValueError("loaded cache exceeds declared capacity")

        return cache
