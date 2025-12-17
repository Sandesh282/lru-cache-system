import json
import threading
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        self._capacity = capacity
        self._cache = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            if key not in self._cache:
                self._record_miss()
                return None
            
            self._record_hit()
            self._mark_recently_used(key)
            return self._cache[key]

    def put(self, key, value):
        with self._lock:
            if key in self._cache:
                self._cache[key] = value
                self._mark_recently_used(key)
            else:
                self._evict_if_needed()
                self._cache[key] = value
                self._mark_recently_used(key)

    def _mark_recently_used(self, key):
        self._cache.move_to_end(key)

    def _evict_if_needed(self):
        if len(self._cache) >= self._capacity:
            self._evict_least_recently_used()

    def _evict_least_recently_used(self):
        self._cache.popitem(last=False)
        self._record_eviction()

    def _record_hit(self):
        self._hits += 1

    def _record_miss(self):
        self._misses += 1

    def _record_eviction(self):
        self._evictions += 1

    def get_stats(self) -> dict:
        with self._lock:
            total_requests = self._hits + self._misses
            hit_ratio = self._hits / total_requests if total_requests > 0 else 0.0
            
            return {
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_ratio": hit_ratio
            }

    def save(self, filepath: str):
        with self._lock:
            entries = [{"key": key, "value": value} for key, value in self._cache.items()]
            
            data = {
                "capacity": self._capacity,
                "entries": entries,
                "metrics": {
                    "hits": self._hits,
                    "misses": self._misses,
                    "evictions": self._evictions
                }
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> 'LRUCache':
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        capacity = data["capacity"]
        entries = data["entries"]
        metrics = data.get("metrics", {"hits": 0, "misses": 0, "evictions": 0})
        
        cache = cls(capacity)
        cache._cache = OrderedDict((entry["key"], entry["value"]) for entry in entries)
        cache._hits = metrics["hits"]
        cache._misses = metrics["misses"]
        cache._evictions = metrics["evictions"]
        
        cache._validate_after_load()
        
        return cache

    def _validate_after_load(self):
        if len(self._cache) > self._capacity:
            raise ValueError(f"Loaded cache has {len(self._cache)} entries but capacity is {self._capacity}")
        
        if self._hits < 0 or self._misses < 0 or self._evictions < 0:
            raise ValueError("Metrics cannot be negative")

