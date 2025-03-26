from django.core.cache import cache
from django.conf import settings
from functools import wraps
import hashlib
import json

# Default cache timeout (1 hour)
DEFAULT_TIMEOUT = 3600

def cache_result(timeout=DEFAULT_TIMEOUT, prefix=None):
    """
    Cache decorator for functions/methods with automatic key generation
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate a cache key based on function name, args and kwargs
            key_parts = [prefix or func.__name__]
            
            # Add stringified args and kwargs
            for arg in args:
                if hasattr(arg, 'pk') and arg.pk:
                    # If it's a model instance, use its primary key
                    key_parts.append(f"{arg.__class__.__name__}_{arg.pk}")
                else:
                    key_parts.append(str(arg))
            
            # Sort kwargs to ensure consistent key generation
            for k in sorted(kwargs.keys()):
                key_parts.append(f"{k}_{kwargs[k]}")
            
            # Create a hash from all parts to keep the key length in check
            key = hashlib.md5('_'.join(key_parts).encode()).hexdigest()
            
            # Check if result is in cache
            cached_result = cache.get(key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(key, result, timeout)
            return result
        return wrapper
    return decorator

def invalidate_model_cache(instance, prefix=None):
    """
    Invalidate cache for specific model instance
    """
    if prefix:
        key = f"{prefix}_{instance.__class__.__name__}_{instance.pk}"
        cache.delete(key)

def cache_page_fragment(fragment_name, timeout=DEFAULT_TIMEOUT):
    """
    Template helper to cache fragments
    Usage:
    {% load cache_utils %}
    {% cache_page_fragment "user_profile_{user.id}" 3600 %}
        ... expensive template content ...
    {% end_cache_page_fragment %}
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            cache_key = fragment_name
            cached_content = cache.get(cache_key)
            if cached_content is not None:
                return cached_content
            
            response = func(request, *args, **kwargs)
            cache.set(cache_key, response, timeout)
            return response
        return wrapper
    return decorator
