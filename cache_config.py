# cache_config.py

from flask_caching import Cache

# Configure caching to use Memurai (a Redis drop-in replacement for Windows).
# CACHE_DEFAULT_TIMEOUT is 0, so cached data persists until explicitly cleared.
cache = Cache(config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': 'redis://localhost:6379/0',
    'CACHE_DEFAULT_TIMEOUT': 0  # 0 means "no expiration"—cache persists until explicitly cleared
})
