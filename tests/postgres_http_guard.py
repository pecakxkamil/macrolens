"""Real SQL validations must never fall through to publisher HTTP transports."""
from contextlib import contextmanager
from unittest.mock import patch
import urllib.request
from tempfile import TemporaryDirectory
from pathlib import Path

import httpx


@contextmanager
def no_publisher_http():
    attempts = []

    def blocked(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Unexpected publisher HTTP in PostgreSQL validation")

    async def blocked_async(*args, **kwargs):
        blocked()

    # MockTransport stays usable. Do not block sockets/libpq: SQL is real.
    from app import earnings_market_cap_cache
    with TemporaryDirectory(prefix='macrolens-pg-cap-cache-') as cache_dir, \
         patch.object(earnings_market_cap_cache, 'CACHE', Path(cache_dir) / 'uninitialized.json'), \
         patch.object(httpx.HTTPTransport, "handle_request", blocked), \
         patch.object(httpx.AsyncHTTPTransport, "handle_async_request", blocked_async), \
         patch.object(urllib.request, "urlopen", blocked):
        try:
            yield
        finally:
            # Importers deliberately catch source errors. Even a swallowed
            # transport exception must fail the encompassing validation.
            if attempts:
                raise AssertionError("Unexpected publisher HTTP in PostgreSQL validation")
