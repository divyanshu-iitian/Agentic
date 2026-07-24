"""
Utility helper functions
"""

import time
from functools import wraps

from utils.logger import log


def retry(max_attempts: int = 3, delay: float = 1.0):
    """
    Retry decorator for functions.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay between retries (seconds)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        log.error(f"{func.__name__} failed after {max_attempts} attempts")
                        raise
                    log.warning(f"{func.__name__} attempt {attempt} failed: {e}, retrying...")
                    time.sleep(delay)

        return wrapper

    return decorator


def async_retry(max_attempts: int = 3, delay: float = 1.0):
    """
    Retry decorator for async functions.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import asyncio

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        log.error(f"{func.__name__} failed after {max_attempts} attempts")
                        raise
                    log.warning(f"{func.__name__} attempt {attempt} failed: {e}, retrying...")
                    await asyncio.sleep(delay)

        return wrapper

    return decorator
