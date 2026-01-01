# LRU Cache: In-Memory Key-Value Store

This project implements a bounded in-memory key-value cache with **Least Recently Used (LRU)** eviction. The goal is not just to make an LRU cache work, but to design it in a way that is easy to reason about, extend, and debug as the system grows.

The project is intentionally built in **axes**, where each axis adds a new concern without rewriting the previous ones.

---

## Problem Statement

We want a cache with a fixed capacity that:

* Supports fast key lookups
* Automatically evicts old entries when full
* Preserves deterministic and explainable behavior

The core challenge is balancing **time complexity**, **correct eviction order**, and **maintainability**.

---

## Why LRU Eviction

LRU eviction works well for many real-world workloads due to temporal locality: recently accessed items are more likely to be accessed again.

Other reasons for choosing LRU here:

* Predictable and easy-to-explain behavior
* Widely used in practice (OS page replacement, DB buffers, HTTP caches)
* Straightforward to validate and debug

The goal is not to claim LRU is universally optimal, but that it is a strong default policy to build around.

---

## Axis 1: Core LRU Cache

### Data Structure Choice

The cache is implemented using `collections.OrderedDict`.

This gives us:

* Constant-time key lookup
* Constant-time reordering on access
* Constant-time eviction of the least recently used item

A custom hash map + doubly linked list was considered initially, but that approach added complexity without providing much benefit at this stage.

### Complexity

Both `get` and `put` operations run in constant time.

Eviction is deterministic: when capacity is exceeded, the entry that has not been accessed for the longest time is removed.

---

## Design Decisions

### Encapsulation

All internal state is private:

* `_cache` stores key-value pairs
* `_capacity` defines the upper bound

This prevents callers from bypassing eviction logic or mutating internal structures directly.

### Separation of Responsibilities

Eviction logic is isolated in dedicated methods rather than being embedded directly into `put()`.

This keeps the control flow readable and makes future eviction strategies easier to experiment with.

### OrderedDict vs Custom Implementation

Using `OrderedDict` trades some low-level control for clarity and correctness. Given the goals of this axis, this tradeoff felt reasonable.

---

## Mistakes and Iterations

The first version of this cache used a custom hash map combined with a manually maintained doubly linked list.

While this gave full control over the data structures, it quickly became tedious to reason about pointer updates and edge cases around eviction order, especially once metrics were added.

After a few iterations, it became clear that the extra control was not worth the complexity for this stage of the project. Switching to `OrderedDict` significantly reduced surface area for bugs and made the core logic easier to reason about.

---

## Axis 2: Observability and Metrics

A cache that cannot be measured is hard to trust.

This axis adds lightweight metrics to understand whether the cache is actually helping:

* Cache hits
* Cache misses
* Evictions

From these values, a hit ratio is derived.

The metrics are updated at the exact points where events occur, rather than being inferred later. This keeps them accurate and easy to validate.

### Interpreting Metrics

* High hit ratio suggests the cache is effective
* Frequent evictions may indicate insufficient capacity
* A consistently low hit ratio may suggest caching is not appropriate for the workload

The cache does not attempt to self-tune based on metrics. Interpretation and action are left to the caller.

---

## Axis 3: Persistence

An in-memory cache is lost on process restart. Persistence allows:

* Warm restarts
* Preservation of eviction order
* Continuity of metrics

The cache can be serialized to and restored from disk using JSON.

### Serialization Format

The serialized state preserves:

* Capacity
* Cache entries in exact LRU order
* Metrics counters

The order of entries is critical: the first element is the least recently used, and the last is the most recently used.

Validation is performed during load to ensure invariants are not violated.

---

## Axis 4: Concurrency and Thread Safety

The cache supports concurrent access using a single coarse-grained lock.

All public methods acquire the same lock, ensuring:

* Atomic operations
* Consistent eviction behavior
* Correct metric tracking

This approach prioritizes correctness and simplicity over maximum throughput. In practice, worrying about fine-grained locking here is premature unless profiling shows the cache itself is a bottleneck.

---

## What Is Intentionally Not Implemented

This project deliberately avoids:

* Fine-grained or lock-free concurrency
* Alternative eviction policies (LFU, FIFO, etc.)
* Automatic persistence
* External monitoring integrations

These are possible future axes, but are out of scope for now.

---

## Size-Based Eviction (Axis 3 Extension)
---

## Axis Extensions vs New Axes

Not every new idea deserves a new axis.

Axes in this project represent **new system-level concerns** that affect the core model in a fundamental way.  
Extensions, on the other hand, refine or specialize an existing concern without introducing a new dimension of complexity.

Size-based eviction and multi-layer caching both build directly on **Axis 3 (Persistence and lifecycle)**:

- Size-based eviction changes *how capacity is interpreted*, not how eviction works
- A disk-backed cache refines *what happens to evicted entries*, not concurrency or correctness
- Neither introduces a new synchronization model or API contract

For this reason, these features are treated as **Axis 3 extensions** rather than new axes.

### Count-Based vs. Size-Based Eviction

The base `LRUCache` uses **count-based eviction**: it limits the number of entries regardless of their memory footprint. This works well when:
- All entries have roughly similar sizes
- You care about limiting the number of objects, not memory usage
- Memory is not the primary constraint

However, in **mobile and memory-constrained environments**, the real bottleneck is memory, not object count. A cache that holds 100 small strings uses very different memory than a cache that holds 100 large images.

**Size-based eviction** addresses this by:
- Tracking approximate memory usage of each entry
- Evicting entries until total memory usage is within limits
- Rejecting items that are too large to fit even in an empty cache

### Mobile Reality: Why Size Matters

Mobile operating systems (Android, iOS) kill applications under memory pressure. The OS doesn't care how many objects you have—it cares how much memory you're using. This is why:

- **Android's `LruCache`** uses `sizeOf(key, value)` to measure each entry
- **iOS's `NSCache`** uses `totalCostLimit` (a size-based limit)
- **Popular image loaders** (Glide, Kingfisher) use size-based caches

A count-based cache with capacity=100 might hold 100 tiny thumbnails (1MB total) or 100 full-resolution images (500MB total). The latter will get your app killed. Size-based eviction ensures you stay within memory budgets regardless of object sizes.

### Implementation: `SizedLRUCache`

`SizedLRUCache` extends `LRUCache` to use size-based eviction:

```python
from sized_lru_cache import SizedLRUCache

# Create a cache with 10MB memory limit
cache = SizedLRUCache(max_size_bytes=10 * 1024 * 1024)

cache.put("image1", large_image_data)
cache.put("image2", small_thumbnail)

stats = cache.get_stats()
print(f"Using {stats['current_size_bytes']} / {stats['max_size_bytes']} bytes")
print(f"Utilization: {stats['size_utilization']:.2%}")
```

**Key Design Decisions:**

1. **Inheritance over composition**: Subclasses `LRUCache` to change the constraint (count → size), not add a new layer.

2. **Approximate sizing**: Uses `sys.getsizeof()` as a heuristic. Doesn't account for all nested objects, but provides reasonable estimates.

3. **Loop-based eviction**: Evicts in a loop until enough space is available, handling cases where a single entry is larger than multiple evicted entries.

4. **Rejection of oversized items**: Items larger than `max_size_bytes` are rejected to prevent a single large item from consuming the entire cache.

### Size Estimation: Approximate, Not Exact

**Important Disclaimer**: `SizedLRUCache` uses `sys.getsizeof()` as a heuristic, which has limitations:

- **Shallow measurement**: `sys.getsizeof()` only measures the object itself, not nested objects (e.g., a list of strings only counts the list overhead, not the strings).

- **Platform-dependent**: Memory usage can vary between Python implementations (CPython, PyPy, etc.).

- **Overhead estimation**: Fixed overhead per entry (100 bytes) accounts for `OrderedDict` structure; actual overhead may vary.

Override `size_of()` for accurate measurements of specific object types.

## Two-Layer Cache Architecture (Axis 3 Extension)

### Why Two Layers?

A single memory cache has a fundamental limitation: when entries are evicted, they're lost forever. In mobile applications, this means:
- User scrolls through a feed → images load into memory cache
- User switches apps → OS kills your app under memory pressure
- User returns → all cached images are gone, must reload from network

A **two-layer cache** solves this by adding a persistent disk layer:

- **Memory Layer**: Fast, limited, volatile (lost on app kill)
- **Disk Layer**: Slower, larger, persistent (survives app restarts)

This is the architecture used by:
- **Glide** (Android): Memory cache + Disk cache
- **Kingfisher** (iOS): Memory cache + Disk cache
- **SDWebImage** (iOS): Memory cache + Disk cache

### Architecture Overview

```
┌─────────────────────────────────────────┐
│         MobileCache (Orchestrator)      │
│                                         │
│  ┌──────────────┐      ┌─────────────┐  │
│  │   Memory     │      │    Disk     │  │
│  │   Cache      │      │   Cache     │  │
│  │ (SizedLRU)   │      │ (Filesystem)│  │
│  │              │      │             │  │
│  │ Fast, Limited│      │ Slow, Large │  │
│  │ Volatile     │      │ Persistent  │  │
│  └──────────────┘      └─────────────┘  │
└─────────────────────────────────────────┘
```

### Flow: `get(key)`

1. **Check memory cache** (fast path, O(1))
   - If found: return immediately
   - If miss: continue to step 2

2. **Check disk cache** (slower, I/O)
   - If found: deserialize, promote to memory cache, return
   - If miss: return None

**Promotion Strategy**: When a value is found on disk, it's immediately promoted to memory. This leverages temporal locality—if you just accessed it, you're likely to access it again soon.

### Flow: `put(key, value)`

1. **Write to memory cache** (for fast future access)
2. **Write to disk cache** (for persistence across restarts)

Both writes happen synchronously.

### Implementation: `MobileCache`

`MobileCache` uses **composition** to orchestrate the two layers:

```python
from sized_lru_cache import SizedLRUCache
from disk_cache import DiskCache
from mobile_cache import MobileCache

# Create the two layers
memory_cache = SizedLRUCache(max_size_bytes=10 * 1024 * 1024)  # 10MB
disk_cache = DiskCache(cache_dir="./cache")

# Orchestrate them
cache = MobileCache(memory_cache, disk_cache)

# Use the two-layer cache
cache.put("image1", image_data)
value = cache.get("image1")  # Fast: from memory
value = cache.get("image2")  # Slower: from disk, then promoted to memory
```

**Key Design Decisions:**

1. **Composition over inheritance**: Composes two independent caches, keeping responsibilities clear:
   - Memory cache handles LRU eviction
   - Disk cache handles persistence
   - Mobile cache coordinates the two

2. **No knowledge of internals**: Only knows the public API (`get`, `put`), maintaining clean boundaries.

3. **Simple disk cache**: Intentionally minimal—stores and retrieves only. No LRU logic or complex policies.

4. **Synchronous disk I/O**: Disk writes are synchronous for simplicity.

### Android / iOS Conceptual Mapping

This implementation maps conceptually to mobile cache patterns:

| Concept | Android | iOS | This Project |
|---------|---------|-----|--------------|
| Memory Cache | `LruCache` | `NSCache` | `SizedLRUCache` |
| Disk Cache | `DiskLruCache` | File-based cache | `DiskCache` |
| Orchestrator | Glide's `Engine` | Kingfisher's `ImageCache` | `MobileCache` |
| Size Measurement | `LruCache.sizeOf()` | `NSCache.totalCostLimit` | `SizedLRUCache.size_of()` |

The key insight: **mobile caches are size-based, not count-based**, because memory is the real constraint, not object count.

## Usage

### Basic LRU Cache (Count-Based)

```python
from lru_cache import LRUCache

cache = LRUCache(capacity=2)
cache.put(1, "one")
cache.put(2, "two")
cache.get(1)
cache.put(3, "three")  # evicts key 2
```


### Size-Based LRU Cache

```python
from sized_lru_cache import SizedLRUCache

# Create a cache with 1MB memory limit
cache = SizedLRUCache(max_size_bytes=1024 * 1024)

cache.put("small", "a" * 100)  # ~100 bytes
cache.put("large", "b" * 1000000)  # ~1MB, may evict previous entry

stats = cache.get_stats()
print(f"Memory usage: {stats['current_size_bytes']} / {stats['max_size_bytes']} bytes")
print(f"Hit ratio: {stats['hit_ratio']:.2%}")
```

### Disk Cache

```python
from disk_cache import DiskCache
import os

# Create a disk cache in a directory
cache = DiskCache(cache_dir="./my_cache")

cache.put("key1", {"data": [1, 2, 3]})
value = cache.get("key1")  # Returns {"data": [1, 2, 3]}

# Check if key exists
if cache.exists("key1"):
    print("Key exists in disk cache")

# Get total cache size
size = cache.get_size_bytes()
print(f"Disk cache size: {size} bytes")

# Remove a key
cache.remove("key1")

# Clear all entries
cache.clear()
```

### Two-Layer Mobile Cache

```python
from sized_lru_cache import SizedLRUCache
from disk_cache import DiskCache
from mobile_cache import MobileCache
import os

# Create the two layers
memory_cache = SizedLRUCache(max_size_bytes=5 * 1024 * 1024)  # 5MB memory
disk_cache = DiskCache(cache_dir="./app_cache")

# Orchestrate them
cache = MobileCache(memory_cache, disk_cache)

# Store data (written to both layers)
cache.put("user_avatar", avatar_image_data)
cache.put("feed_image_1", feed_image_data)

# Retrieve data (fast path: from memory)
avatar = cache.get("user_avatar")  # Fast: from memory

# Retrieve data (slow path: from disk, then promoted)
image = cache.get("feed_image_1")  # If evicted from memory, loads from disk

# Get combined statistics
stats = cache.get_stats()
print(f"Memory stats: {stats['memory_stats']}")
print(f"Disk size: {stats['disk_size_bytes']} bytes")
print(f"Combined hit ratio: {stats['combined_hit_ratio']:.2%}")
```

## Notes

This project is intentionally incremental. Each axis adds complexity only after the previous one is stable and understandable. The emphasis is on clarity, correctness, and evolution rather than maximal feature coverage from the start.
