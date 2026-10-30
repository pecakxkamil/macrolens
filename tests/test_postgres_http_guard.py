"""The SQL-only guard blocks transports without preventing real local SQL."""
import asyncio
import socket
import urllib.request

import httpx
import pytest

from tests.postgres_http_guard import no_publisher_http


def test_mock_transport_is_allowed_and_socket_functions_are_unchanged():
    connect = socket.socket.connect
    with no_publisher_http():
        assert socket.socket.connect is connect
        with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200))) as client:
            assert client.get("https://publisher.invalid").status_code == 200


@pytest.mark.parametrize("client", ["httpx", "urllib", "async"])
def test_unexpected_http_fails_even_if_the_importer_catches_the_exception(client):
    async def request():
        async with httpx.AsyncClient(trust_env=False) as session:
            await session.get("https://publisher.invalid")

    with pytest.raises(AssertionError, match="Unexpected publisher HTTP"):
        with no_publisher_http():
            try:
                if client == "httpx":
                    with httpx.Client(trust_env=False) as session:
                        session.get("https://publisher.invalid")
                elif client == "urllib":
                    urllib.request.urlopen("https://publisher.invalid")
                else:
                    asyncio.run(request())
            except AssertionError:
                pass
