import os
import hashlib
import json
import pickle
from pathlib import Path
from typing import Optional, Any


class DiskCache:
    """
    Filesystem-backed key-value cache.
    
    Acts as a persistence layer in a multi-tier cache architecture.
    No eviction policy is implemented by design.
    """
    
    def __init__(self, cache_dir: str):
        """
        Initialize a disk cache.
        
        Args:
            cache_dir: Directory path where cache files will be stored.
                     Will be created if it doesn't exist.
        
        Raises:
            OSError: If the directory cannot be created or accessed.
        """
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        
        if not os.access(self._cache_dir, os.W_OK):
            raise OSError(f"Cannot write to cache directory: {cache_dir}")
    
    def _key_to_filename(self, key: Any) -> str:
        """
        Convert a cache key to a filesystem-safe filename.
        
        Uses SHA256 hash of the serialized key to ensure:
        - Filesystem-safe characters
        - Consistent mapping (same key -> same filename)
        - No collisions in practice
        
        Args:
            key: The cache key (must be serializable)
        
        Returns:
            Filename string (hex digest of hash)
        """
        key_bytes = pickle.dumps(key)
        # Hash for stable, filesystem-safe filename
        hash_obj = hashlib.sha256(key_bytes)
        return hash_obj.hexdigest()
    
    def _get_filepath(self, key: Any) -> Path:
        """
        Get the full filepath for a given key.
        
        Args:
            key: The cache key
        
        Returns:
            Path object for the cache file
        """
        filename = self._key_to_filename(key)
        return self._cache_dir / filename
    
    def get(self, key: Any) -> Optional[Any]:
        """
        Retrieve a value from disk cache.
        
        Args:
            key: The cache key
        
        Returns:
            The cached value if found, None otherwise
        """
        filepath = self._get_filepath(key)
        
        if not filepath.exists():
            return None
        
        try:
            with open(filepath, 'rb') as f:
                value = pickle.load(f)
            return value
        except (IOError, OSError, pickle.PickleError):
            return None
    
    def put(self, key: Any, value: Any):
        """
        Store a value in disk cache.
        
        Args:
            key: The cache key
            value: The value to cache (must be serializable)
        
        Raises:
            OSError: If the file cannot be written
            pickle.PickleError: If the value cannot be serialized
        """
        filepath = self._get_filepath(key)
        
        # Atomic write via temp file to avoid partial corruption
        temp_filepath = filepath.with_suffix('.tmp')
        
        try:
            with open(temp_filepath, 'wb') as f:
                pickle.dump(value, f)
            
            temp_filepath.replace(filepath)
        except Exception:
            if temp_filepath.exists():
                try:
                    temp_filepath.unlink()
                except OSError:
                    pass
            raise
    
    def remove(self, key: Any) -> bool:
        """
        Remove a key from disk cache.
        
        Args:
            key: The cache key to remove
        
        Returns:
            True if the key was removed, False if it didn't exist
        """
        filepath = self._get_filepath(key)
        
        if not filepath.exists():
            return False
        
        try:
            filepath.unlink()
            return True
        except OSError:
            return False
    
    def clear(self):
        """
        Remove all cached entries from disk.
        
        This deletes all files in the cache directory.
        """
        for filepath in self._cache_dir.iterdir():
            if filepath.is_file():
                try:
                    filepath.unlink()
                except OSError:
                    pass
    
    def exists(self, key: Any) -> bool:
        """
        Check if a key exists in the disk cache.
        
        Args:
            key: The cache key to check
        
        Returns:
            True if the key exists, False otherwise
        """
        filepath = self._get_filepath(key)
        return filepath.exists()
    
    def get_size_bytes(self) -> int:
        """
        Get the total size of all cache files in bytes.
        
        Returns:
            Total size in bytes
        """
        total_size = 0
        for filepath in self._cache_dir.iterdir():
            if filepath.is_file():
                try:
                    total_size += filepath.stat().st_size
                except OSError:
                    pass
        return total_size

