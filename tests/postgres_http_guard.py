"""Real SQL validations must never fall through to publisher HTTP transports."""
from contextlib import contextmanager
from unittest.mock import patch
import urllib.request

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
    with patch.object(httpx.HTTPTransport, "handle_request", blocked), \
         patch.object(httpx.AsyncHTTPTransport, "handle_async_request", blocked_async), \
         patch.object(urllib.request, "urlopen", blocked):
        try:
            yield
        finally:
            # Importers deliberately catch source errors. Even a swallowed
            # transport exception must fail the encompassing validation.
            if attempts:
                raise AssertionError("Unexpected publisher HTTP in PostgreSQL validation")
