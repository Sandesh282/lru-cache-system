# LRU Cache: In-Memory Key-Value Store

## Problem Statement

This cache solves the problem of maintaining a bounded in-memory key-value store that automatically manages memory by evicting entries when capacity is exceeded. The challenge is maintaining both fast lookups and efficient tracking of access patterns.

## Why LRU Eviction?

Least Recently Used (LRU) eviction is appropriate because:

1. **Temporal Locality**: Recently accessed items are likely to be accessed again soon
2. **Predictable Behavior**: The eviction policy is deterministic and easy to reason about
3. **Widely Applicable**: LRU works well for many real-world access patterns (web caches, database buffers, OS page replacement)

When capacity is exceeded, we evict the item that hasn't been touched in the longest time, preserving items that are actively being used.

## O(1) Guarantee

All operations run in constant time because:

### Data Structure Choice: `collections.OrderedDict`

`OrderedDict` is a hash table that maintains insertion order. It provides:

- **O(1) lookup**: Hash table provides constant-time key access
- **O(1) reordering**: `move_to_end()` moves an item to the end in constant time
- **O(1) eviction**: `popitem(last=False)` removes the oldest item in constant time

### Operation Analysis

- **`get(key)`**: 
  - Hash lookup: O(1)
  - Move to end: O(1)
  - Total: O(1)

- **`put(key, value)`**:
  - Hash lookup: O(1)
  - Insert/update: O(1)
  - Move to end: O(1)
  - Evict (if needed): O(1)
  - Total: O(1)

## Design Decisions

### 1. Encapsulation of Internal State

All internal data structures are private (prefixed with `_`):
- `_cache`: The OrderedDict storing key-value pairs
- `_capacity`: Maximum number of entries

This prevents external code from bypassing the cache's eviction logic or violating invariants.

### 2. Separation of Eviction Logic

Eviction is handled by dedicated private methods:
- `_evict_if_needed()`: Checks capacity and triggers eviction
- `_evict_least_recently_used()`: Performs the actual eviction

This separation makes it clear where eviction happens and makes it easy to swap eviction strategies in the future.

### 3. Extensibility for Alternative Eviction Policies

The design makes it obvious how to add other eviction policies:

1. **Override `_evict_least_recently_used()`**: For LFU, random, or FIFO policies
2. **Override `_mark_recently_used()`**: For policies that track usage differently
3. **Add tracking data structures**: Without changing `get()` or `put()` signatures

The public API (`get` and `put`) remains unchanged regardless of eviction policy.

### 4. OrderedDict vs. Custom Implementation

We use `OrderedDict` instead of manually implementing a hash map + doubly linked list because:

- **Clarity**: The code is immediately readable
- **Correctness**: We rely on a well-tested standard library component
- **Maintainability**: Less code to maintain and debug

The tradeoff is slightly less control over internal representation, but for Axis 1 (clean design), this is the right choice.

### 5. Return Value for Missing Keys

`get()` returns `None` for missing keys. This is Pythonic and allows callers to use:
```python
value = cache.get(key)
if value is not None:
    # use value
```

## Tradeoffs

### What We Gain

- **Simplicity**: Clear, readable code
- **Correctness**: Standard library reduces bugs
- **Extensibility**: Easy to add new eviction policies
- **Performance**: All operations are O(1)

### What We Accept

- **Memory Overhead**: OrderedDict has slightly more overhead than a custom implementation
- **Limited Control**: We can't fine-tune the hash table or linked list internals
- **Single Policy**: Only LRU is implemented (by design for Axis 1)

## Observability and Metrics (Axis 2)

### Why Observability Matters for Caches

A cache is only useful if it's actually working. Without metrics, you're flying blind:

- **Is the cache helping?** High hit rates mean the cache is effective; low hit rates suggest the cache isn't worth the memory.
- **Are we wasting memory?** Frequent evictions might indicate the capacity is too small, or the access pattern doesn't benefit from caching.
- **Is the eviction policy appropriate?** Metrics reveal whether LRU is the right choice for your workload.

Guessing cache effectiveness is unreliable. Metrics provide objective data to make informed decisions about capacity, eviction policies, and whether caching is appropriate for your use case.

### Available Metrics

The cache tracks three core counters:

1. **`hits`**: Number of successful `get()` operations where the key was found
2. **`misses`**: Number of `get()` operations where the key was not found
3. **`evictions`**: Number of entries removed due to capacity constraints

### Hit Ratio

The `hit_ratio` is calculated as:

```
hit_ratio = hits / (hits + misses)
```

**Interpreting Hit Ratio:**

- **High hit ratio (0.8-1.0)**: The cache is highly effective. Most requests are served from cache, reducing expensive lookups.
- **Medium hit ratio (0.5-0.8)**: The cache is providing value, but there's room for improvement. Consider increasing capacity or analyzing access patterns.
- **Low hit ratio (<0.5)**: The cache may not be effective for this workload. Consider:
  - Whether caching is appropriate for this access pattern
  - Whether the capacity is too small
  - Whether a different eviction policy (e.g., LFU) might work better

A hit ratio of 0.0 means no requests have been served from cache yet (all misses). This is safe to handle and returns 0.0 rather than causing a division-by-zero error.

### Using Metrics

```python
from lru_cache import LRUCache

cache = LRUCache(capacity=100)

# ... use cache ...

stats = cache.get_stats()
print(f"Hit ratio: {stats['hit_ratio']:.2%}")
print(f"Total requests: {stats['hits'] + stats['misses']}")
print(f"Evictions: {stats['evictions']}")
```

### Design Decisions for Metrics

Metrics are tracked internally without cluttering the core cache logic:

- **Separate recording methods**: `_record_hit()`, `_record_miss()`, `_record_eviction()` keep metrics updates isolated
- **No performance impact**: Simple integer increments are O(1) and don't affect cache operations
- **Accurate placement**: Metrics are updated exactly where the events occur:
  - Hits/misses in `get()`
  - Evictions in `_evict_least_recently_used()`

This design maintains the cache's readability while providing essential observability.

## Persistence (Axis 3)

### Why Persistence Matters

A cache that only exists in memory is lost when the process terminates. Persistence allows the cache to survive restarts, enabling:

- **State preservation**: Cache contents persist across application restarts
- **Warm starts**: Applications can resume with a pre-populated cache
- **Metrics continuity**: Historical metrics are preserved for analysis
- **Crash recovery**: Cache state can be restored after unexpected shutdowns

Without persistence, every restart means starting with an empty cache, losing all accumulated state and requiring time to rebuild effectiveness.

### Serialization Format

The cache is serialized to JSON, a human-readable format that's easy to inspect and debug. The format preserves all state needed for correctness:

```json
{
  "capacity": 3,
  "entries": [
    {"key": 1, "value": "one"},
    {"key": 2, "value": "two"},
    {"key": 3, "value": "three"}
  ],
  "metrics": {
    "hits": 5,
    "misses": 2,
    "evictions": 1
  }
}
```

**Key Design Decisions:**

1. **Ordered entries list**: The `entries` array preserves LRU ordering exactly. The first entry is the least recently used, the last entry is the most recently used. This order is critical for correct cache behavior after load.

2. **Separate metrics object**: Metrics are stored separately from cache entries, making the format clear and extensible.

3. **Human-readable**: JSON format allows manual inspection and debugging, which is valuable for a systems component.

### What Gets Preserved

The serialization preserves all state that defines cache correctness:

- **Capacity**: Maximum number of entries
- **Cache entries**: All key-value pairs in exact LRU order
- **Metrics**: Hits, misses, and evictions counters

After loading, the cache behaves identically to before saving:
- Same entries in the same order
- Same metrics values
- Same capacity constraints
- Same eviction behavior

### Using Persistence

```python
from lru_cache import LRUCache

# Create and use cache
cache = LRUCache(capacity=100)
cache.put(1, "one")
cache.put(2, "two")
cache.get(1)

# Save to disk
cache.save("cache_state.json")

# Later, load from disk
loaded_cache = LRUCache.load("cache_state.json")

# Cache behaves identically
assert loaded_cache.get(1) == "one"
assert loaded_cache.get_stats() == cache.get_stats()
```

### Invariant Validation

After loading, the cache validates that invariants are preserved:

1. **Capacity constraint**: The number of loaded entries must not exceed capacity
2. **Non-negative metrics**: All metric counters must be non-negative
3. **Order preservation**: LRU order is maintained exactly as saved

If validation fails, a `ValueError` is raised, preventing the cache from entering an invalid state.

### Design Decisions for Persistence

1. **JSON over binary**: JSON is human-readable and debuggable, which is more valuable than the slight performance gain of binary formats for this use case.

2. **Class method for load**: `load()` is a class method, making it clear that it creates a new cache instance rather than modifying an existing one.

3. **Validation after load**: Explicit validation ensures the loaded state is correct before the cache is used.

4. **No automatic persistence**: The cache doesn't auto-save on every operation. This keeps the API simple and gives callers control over when persistence happens.

5. **Complete state preservation**: All metrics are preserved, not just cache entries. This allows analysis of cache effectiveness across restarts.

## Concurrency & Thread Safety (Axis 4)

### Why Shared Mutable State Is Dangerous

When multiple threads access the same cache instance without synchronization, race conditions can corrupt internal state:

1. **Lost Updates**: Two threads updating metrics simultaneously can cause one update to be lost
2. **Inconsistent Ordering**: A thread reading the cache while another modifies it can see partially updated LRU order
3. **Corrupted Metrics**: Concurrent increments to hit/miss counters can result in incorrect totals
4. **Capacity Violations**: Two threads adding entries simultaneously can exceed capacity before eviction occurs
5. **Persistence Corruption**: Saving while another thread modifies the cache can write inconsistent state

Without proper synchronization, these race conditions can cause the cache to violate its invariants, return incorrect values, or crash.

### Race Conditions Without Locks

Consider what could happen without synchronization:

**Example 1: Metric Corruption**
```python
# Thread 1: cache.get(key) -> increments _hits
# Thread 2: cache.get(key) -> increments _hits
# Without locks: Both threads read _hits=5, both write _hits=6
# Result: _hits should be 7, but is 6 (lost update)
```

**Example 2: LRU Order Corruption**
```python
# Thread 1: cache.get(1) -> moves key 1 to end
# Thread 2: cache.get(2) -> moves key 2 to end
# Without locks: Both operations can interleave, corrupting the order
# Result: LRU order is incorrect, eviction removes wrong entry
```

**Example 3: Capacity Violation**
```python
# Thread 1: cache.put(1, v1) -> checks capacity, adds entry
# Thread 2: cache.put(2, v2) -> checks capacity, adds entry
# Without locks: Both see capacity not exceeded, both add entries
# Result: Cache exceeds capacity before eviction runs
```

### Chosen Locking Strategy

The cache uses **coarse-grained locking** with a single `threading.Lock`:

- **One lock protects all shared state**: `_cache`, `_hits`, `_misses`, `_evictions`
- **Public methods are critical sections**: Each public method (`get`, `put`, `get_stats`, `save`) acquires the lock at entry and releases it at exit
- **Context managers ensure safety**: The `with self._lock:` statement guarantees the lock is released even if an exception occurs

### Why Coarse-Grained Locking

Coarse-grained locking was chosen for several reasons:

1. **Correctness First**: A single lock eliminates all race conditions. Every operation is atomic, ensuring invariants are never violated.

2. **Simplicity**: The locking strategy is easy to understand, audit, and maintain. There's no risk of deadlock from multiple locks or complex lock ordering.

3. **Clear Synchronization Boundaries**: Public methods define the synchronization boundary. All internal state is protected by the same lock, making it obvious what's protected.

4. **Maintainability**: Adding new methods or modifying existing ones doesn't require understanding complex lock hierarchies or fine-grained locking protocols.

5. **Sufficient for Many Use Cases**: For most applications, the cache is not the bottleneck. The simplicity and correctness of coarse-grained locking outweighs the performance cost.

### Tradeoffs: Simplicity vs. Throughput

**What We Gain:**
- **Correctness**: No race conditions, no corrupted state
- **Simplicity**: Easy to reason about and maintain
- **Safety**: Context managers prevent deadlocks from forgotten lock releases

**What We Accept:**
- **Lower Throughput**: Only one thread can access the cache at a time
- **Potential Contention**: High-concurrency workloads may see threads waiting for the lock

**When This Matters:**
- If the cache is the bottleneck and profiling shows lock contention, fine-grained locking or lock-free structures could be considered
- For most applications, the cache operations are fast enough that coarse-grained locking provides sufficient performance

The design prioritizes correctness and maintainability over micro-optimizations. If performance becomes an issue, it can be addressed in a future axis with profiling data to guide optimization.

### Implementation Details

All public methods that access shared state are protected:

```python
def get(self, key):
    with self._lock:  # Acquire lock
        # ... all cache operations ...
        return value  # Lock released automatically

def put(self, key, value):
    with self._lock:  # Acquire lock
        # ... all cache operations ...
        # Lock released automatically

def get_stats(self) -> dict:
    with self._lock:  # Acquire lock
        # ... read metrics ...
        return stats  # Lock released automatically

def save(self, filepath: str):
    with self._lock:  # Acquire lock
        # ... serialize state ...
        # Lock released automatically
```

The `load()` class method doesn't need locking because it creates a new cache instance and doesn't access shared state from an existing instance.

### Thread Safety Guarantees

With the lock in place, the cache guarantees:

1. **Atomic Operations**: Each `get`, `put`, `get_stats`, and `save` operation is atomic
2. **Consistent State**: No thread can see partially updated cache state
3. **Correct Metrics**: All metric updates are serialized, preventing lost updates
4. **LRU Order Integrity**: LRU ordering operations are atomic, preventing corruption
5. **Capacity Invariants**: Capacity checks and evictions are atomic, preventing violations

## What Is Intentionally NOT Implemented

This is Axis 4: Concurrency & Thread Safety. The following remain deferred:

- **Fine-Grained Locking**: No read-write locks or per-bucket locking
- **Lock-Free Algorithms**: No lock-free data structures or atomic operations
- **Alternative Eviction Policies**: Only LRU is implemented
- **CLI/Web Interface**: No user-facing interface
- **Performance Benchmarking**: No performance profiling tools
- **Logging Framework**: No structured logging
- **External Monitoring**: No integration with monitoring systems
- **Async I/O**: No asyncio support
- **Multiprocessing**: No support for multiprocessing (only threading)

These will be addressed in future axes as the project grows.

## Usage

```python
from lru_cache import LRUCache

cache = LRUCache(capacity=2)

cache.put(1, "one")
cache.put(2, "two")
value = cache.get(1)  # Returns "one", marks 1 as recently used

cache.put(3, "three")  # Evicts key 2 (least recently used)
cache.get(2)  # Returns None (was evicted)
```

## Running Tests

```bash
python demo.py
```

