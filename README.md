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

## Usage

```python
from lru_cache import LRUCache

cache = LRUCache(capacity=2)
cache.put(1, "one")
cache.put(2, "two")
cache.get(1)
cache.put(3, "three")  # evicts key 2
```

---

## Notes

This project is intentionally incremental. Each axis adds complexity only after the previous one is stable and understandable. The emphasis is on clarity, correctness, and evolution rather than maximal feature coverage from the start.
