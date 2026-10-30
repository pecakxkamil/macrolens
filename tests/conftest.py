"""Keep unit/API tests independent of credentials, providers and real databases."""
import socket
import sys

import httpx
import psycopg
import pytest


_guard = None
_attempts = []


@pytest.fixture(autouse=True)
def isolate_unrelated_bea_source(request,monkeypatch):
    if request.node.module.__name__.endswith('test_bea_direct'):
        return
    from app.ingestion import sync_bea_reports
    from app.analytics import bea_direct
    monkeypatch.setattr(sync_bea_reports,'sync_source',lambda *a,**k:{'status':'success'})
    monkeypatch.setattr(bea_direct,'load_state',lambda *a,**k:{'documents':[],'observations':{}})
    monkeypatch.setattr(bea_direct,'overview',lambda rows,*a,**k:rows)


@pytest.fixture(autouse=True)
def isolate_unrelated_ft900_source(request, monkeypatch):
    if request.node.module.__name__.endswith('test_ft900'):
        return
    from app.ingestion import sync_ft900
    monkeypatch.setattr(sync_ft900,'read_schedule',lambda *a,**k:{'events':[],'history':[],'tbd_periods':[]})
    monkeypatch.setattr(sync_ft900,'sync_source',lambda *a,**k:{'status':'success'})


@pytest.fixture(autouse=True)
def isolate_unrelated_empire_source(request, monkeypatch):
    """Existing source tests do not consume a developer's local NY Fed store.

    Empire integration tests opt into their explicit synthetic documents/DB.
    Network and database guards below remain in force for every test.
    """
    if request.node.module.__name__.endswith('test_empire_state'):
        return
    from app.analytics import empire_state
    from app.ingestion import sync_empire_state
    monkeypatch.setattr(empire_state,'read_schedule',lambda *a,**k:{'events':[],'history':[]})
    monkeypatch.setattr(sync_empire_state,'sync_source',lambda *a,**k:{'status':'success'})


def pytest_configure(config):
    # Install before collection too: importing a test module must not reach a
    # provider/database before per-test fixtures get a chance to run.
    global _guard
    _guard = pytest.MonkeyPatch()
    _attempts.clear()
    _install_guard(_guard)


def pytest_unconfigure(config):
    if _guard is not None:
        _guard.undo()


def pytest_sessionfinish(session, exitstatus):
    if _attempts and session.exitstatus == 0:
        session.exitstatus = 1


@pytest.fixture(autouse=True)
def no_external_services():
    before = len(_attempts)
    yield
    assert len(_attempts) == before, "A test attempted real network/database access, possibly in a background task."


def _install_guard(monkeypatch):
    # Never load the developer's .env, even when a forgotten mock reaches an
    # application helper. Tests may still override individual dummy settings.
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    monkeypatch.setenv("FRED_API_KEY", "")
    for key, value in dict(DB_HOST="invalid.test", DB_PORT="1",
                           DB_NAME="macrolens_test_unused", DB_USER="unused",
                           DB_PASSWORD="unused").items():
        monkeypatch.setenv(key, value)

    def blocked(*args, **kwargs):
        # No URL/arguments: they could contain credentials. Failed derives from
        # BaseException, so application error handling cannot hide the failure.
        _attempts.append(True)
        pytest.fail("Real network/database access is forbidden in tests; use a fixture or mock.")

    async def blocked_async(*args, **kwargs):
        blocked()

    real_connect = socket.socket.connect
    pair_code = getattr(socket.socketpair, "__code__", None)

    def guarded_connect(sock, address):
        # Python 3.9 on Windows implements asyncio's internal socketpair using
        # loopback TCP. Permit only that exact stdlib caller, never arbitrary
        # localhost HTTP/database connections. Linux uses native socketpair.
        if (sys.platform == "win32" and pair_code is not None
                and sys._getframe(1).f_code is pair_code
                and address[0] in ("127.0.0.1", "::1")):
            return real_connect(sock, address)
        blocked()

    # MockTransport and FastAPI's in-process TestClient stay usable. Block real
    # HTTP before DNS; sockets also cover other Python network clients.
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", blocked_async)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    # libpq opens native sockets, so the Python socket guard alone is insufficient.
    monkeypatch.setattr(psycopg, "connect", blocked)
    monkeypatch.setattr(psycopg.Connection, "connect", blocked)
    monkeypatch.setattr(psycopg.AsyncConnection, "connect", blocked_async)
