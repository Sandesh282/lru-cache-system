import os
import threading
from lru_cache import LRUCache


def test_basic_operations():
    print("Test 1: Basic operations")
    cache = LRUCache(2)
    
    cache.put(1, 1)
    cache.put(2, 2)
    print(f"get(1) = {cache.get(1)}")
    
    cache.put(3, 3)
    print(f"get(2) = {cache.get(2)}")
    print(f"get(3) = {cache.get(3)}")
    
    cache.put(4, 4)
    print(f"get(1) = {cache.get(1)}")
    print(f"get(3) = {cache.get(3)}")
    print(f"get(4) = {cache.get(4)}")
    
    stats = cache.get_stats()
    print(f"Stats: {stats}")
    print()


def test_update_existing():
    print("Test 2: Update existing key")
    cache = LRUCache(2)
    
    cache.put(1, 1)
    cache.put(2, 2)
    cache.put(1, 10)
    print(f"get(1) = {cache.get(1)}")
    print(f"get(2) = {cache.get(2)}")
    print()


def test_capacity_one():
    print("Test 3: Capacity of 1")
    cache = LRUCache(1)
    
    cache.put(1, 1)
    print(f"get(1) = {cache.get(1)}")
    
    cache.put(2, 2)
    print(f"get(1) = {cache.get(1)}")
    print(f"get(2) = {cache.get(2)}")
    print()


def test_missing_key():
    print("Test 4: Missing key")
    cache = LRUCache(2)
    
    print(f"get(99) = {cache.get(99)}")
    cache.put(1, 1)
    print(f"get(99) = {cache.get(99)}")
    print()


def test_metrics_observability():
    print("Test 5: Metrics and Observability")
    cache = LRUCache(3)
    
    print("Initial stats (no operations yet):")
    print(f"  {cache.get_stats()}")
    print()
    
    print("Adding keys 1, 2, 3...")
    cache.put(1, "one")
    cache.put(2, "two")
    cache.put(3, "three")
    print(f"  {cache.get_stats()}")
    print()
    
    print("Accessing existing keys (should be hits):")
    cache.get(1)
    cache.get(2)
    cache.get(3)
    print(f"  {cache.get_stats()}")
    print()
    
    print("Accessing missing keys (should be misses):")
    cache.get(99)
    cache.get(100)
    print(f"  {cache.get_stats()}")
    print()
    
    print("Adding new keys to trigger evictions:")
    cache.put(4, "four")
    cache.put(5, "five")
    print(f"  {cache.get_stats()}")
    print()
    
    print("Final stats:")
    stats = cache.get_stats()
    print(f"  Hits: {stats['hits']}")
    print(f"  Misses: {stats['misses']}")
    print(f"  Evictions: {stats['evictions']}")
    print(f"  Hit Ratio: {stats['hit_ratio']:.2%}")
    print()


def test_persistence():
    print("Test 6: Persistence (Save/Load)")
    cache = LRUCache(3)
    
    print("Populating cache with operations...")
    cache.put(1, "one")
    cache.put(2, "two")
    cache.get(1)
    cache.put(3, "three")
    cache.get(2)
    cache.put(4, "four")
    
    print("Cache state before save:")
    print(f"  Entries: {list(cache._cache.items())}")
    stats_before = cache.get_stats()
    print(f"  Stats: {stats_before}")
    print()
    
    filepath = "test_cache.json"
    print(f"Saving to {filepath}...")
    cache.save(filepath)
    print("  Saved successfully")
    print()
    
    print("Creating new cache instance and loading...")
    loaded_cache = LRUCache.load(filepath)
    print("  Loaded successfully")
    print()
    
    print("Cache state after load:")
    print(f"  Entries: {list(loaded_cache._cache.items())}")
    stats_after = loaded_cache.get_stats()
    print(f"  Stats: {stats_after}")
    print()
    
    print("Verifying correctness:")
    entries_match = list(cache._cache.items()) == list(loaded_cache._cache.items())
    stats_match = stats_before == stats_after
    capacity_match = cache._capacity == loaded_cache._capacity
    
    print(f"  Entries match: {entries_match}")
    print(f"  Stats match: {stats_match}")
    print(f"  Capacity matches: {capacity_match}")
    
    if entries_match and stats_match and capacity_match:
        print("  ✓ All invariants preserved!")
    else:
        print("  ✗ Validation failed!")
    print()
    
    print("Testing cache behavior after load:")
    print(f"  get(1) = {loaded_cache.get(1)}")
    print(f"  get(2) = {loaded_cache.get(2)}")
    print(f"  get(3) = {loaded_cache.get(3)}")
    print(f"  get(4) = {loaded_cache.get(4)}")
    print()
    
    print("Cleaning up test file...")
    if os.path.exists(filepath):
        os.remove(filepath)
        print(f"  Removed {filepath}")
    print()


def test_concurrent_access():
    print("Test 7: Concurrent Access (Thread Safety)")
    cache = LRUCache(10)
    errors = []
    results = []
    
    def worker_get(thread_id, iterations):
        for i in range(iterations):
            key = (thread_id * 1000) + i
            try:
                value = cache.get(key)
                results.append(("get", thread_id, key, value))
            except Exception as e:
                errors.append(f"Thread {thread_id} get error: {e}")
    
    def worker_put(thread_id, iterations):
        for i in range(iterations):
            key = (thread_id * 1000) + i
            value = f"value_{thread_id}_{i}"
            try:
                cache.put(key, value)
                results.append(("put", thread_id, key, value))
            except Exception as e:
                errors.append(f"Thread {thread_id} put error: {e}")
    
    def worker_stats(thread_id, iterations):
        for i in range(iterations):
            try:
                stats = cache.get_stats()
                results.append(("stats", thread_id, i, stats))
            except Exception as e:
                errors.append(f"Thread {thread_id} stats error: {e}")
    
    print("Starting concurrent operations...")
    threads = []
    
    for i in range(3):
        t = threading.Thread(target=worker_put, args=(i, 20))
        threads.append(t)
        t.start()
    
    for i in range(3, 6):
        t = threading.Thread(target=worker_get, args=(i - 3, 20))
        threads.append(t)
        t.start()
    
    for i in range(6, 8):
        t = threading.Thread(target=worker_stats, args=(i, 10))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    print(f"  Completed {len(results)} operations")
    print(f"  Errors: {len(errors)}")
    
    if errors:
        print("  ✗ Errors occurred:")
        for error in errors[:5]:
            print(f"    {error}")
    else:
        print("  ✓ No errors during concurrent access")
    
    print()
    
    print("Verifying cache state consistency...")
    final_stats = cache.get_stats()
    cache_size = len(cache._cache)
    
    print(f"  Cache size: {cache_size}")
    print(f"  Capacity: {cache._capacity}")
    print(f"  Final stats: {final_stats}")
    
    if cache_size <= cache._capacity:
        print("  ✓ Capacity constraint maintained")
    else:
        print("  ✗ Capacity exceeded!")
        errors.append("Capacity constraint violated")
    
    if final_stats['hits'] >= 0 and final_stats['misses'] >= 0 and final_stats['evictions'] >= 0:
        print("  ✓ Metrics are non-negative")
    else:
        print("  ✗ Negative metrics detected!")
        errors.append("Negative metrics")
    
    print()
    
    if not errors:
        print("  ✓ All invariants preserved under concurrent access")
    else:
        print(f"  ✗ {len(errors)} invariant violations detected")
    print()


def test_concurrent_persistence():
    print("Test 8: Concurrent Persistence")
    cache = LRUCache(5)
    
    for i in range(5):
        cache.put(i, f"value_{i}")
    
    filepath = "concurrent_test_cache.json"
    errors = []
    
    def worker_save(thread_id):
        try:
            cache.save(f"{filepath}.{thread_id}")
        except Exception as e:
            errors.append(f"Thread {thread_id} save error: {e}")
    
    def worker_get(thread_id):
        for i in range(10):
            try:
                cache.get(i % 5)
            except Exception as e:
                errors.append(f"Thread {thread_id} get error: {e}")
    
    print("Starting concurrent save and get operations...")
    threads = []
    
    for i in range(3):
        t = threading.Thread(target=worker_save, args=(i,))
        threads.append(t)
        t.start()
    
    for i in range(3, 6):
        t = threading.Thread(target=worker_get, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    print(f"  Errors: {len(errors)}")
    
    if errors:
        print("  ✗ Errors occurred:")
        for error in errors[:5]:
            print(f"    {error}")
    else:
        print("  ✓ No errors during concurrent persistence operations")
    
    print()
    
    print("Verifying saved files...")
    for i in range(3):
        test_file = f"{filepath}.{i}"
        if os.path.exists(test_file):
            try:
                loaded = LRUCache.load(test_file)
                print(f"  File {i}: Loaded successfully, size={len(loaded._cache)}")
                os.remove(test_file)
            except Exception as e:
                print(f"  File {i}: Load error - {e}")
                errors.append(f"Load error for file {i}")
        else:
            print(f"  File {i}: Not found")
    
    print()
    
    if not errors:
        print("  ✓ Persistence works correctly under concurrent access")
    else:
        print(f"  ✗ {len(errors)} persistence errors detected")
    print()


if __name__ == "__main__":
    test_basic_operations()
    test_update_existing()
    test_capacity_one()
    test_missing_key()
    test_metrics_observability()
    test_persistence()
    test_concurrent_access()
    test_concurrent_persistence()

