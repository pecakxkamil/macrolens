"""A per-job request budget; ordinary explicit ingestion keeps its existing behavior."""
from contextlib import contextmanager
from contextvars import ContextVar
import time

_budget = ContextVar('provider_request_budget', default=None)


@contextmanager
def request_budget(seconds=600, fred_spacing=0.6):
    token = _budget.set({'deadline': time.monotonic()+seconds, 'last_fred': 0, 'spacing': fred_spacing})
    try:
        yield
    finally:
        _budget.reset(token)


def before_request(provider):
    budget = _budget.get()
    if not budget:
        return
    if provider == 'FRED':
        delay = max(0, budget['last_fred'] + budget['spacing'] - time.monotonic())
        if delay:
            time.sleep(delay)
        budget['last_fred'] = time.monotonic()
    if time.monotonic() >= budget['deadline']:
        raise TimeoutError('Overview refresh request budget exceeded.')
