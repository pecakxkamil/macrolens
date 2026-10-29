"""Provenance of explicit availability checks, never inferred from stored readings.

The existing refresh processes write one run before contacting their provider and
finish it after validation/storage. Reads and feature computation never write here.
"""
import json
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from app.database.connection import get_independent_connection as get_connection

logger = logging.getLogger(__name__)


def utc_now():
    return datetime.now(timezone.utc)


def write_run(run, connection=None):
    owned = connection is None
    connection = connection or get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""INSERT INTO source_check_runs
                (id, resource, attempted_at, finished_at, status, scope, error_code)
                VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s)
                ON CONFLICT (id) DO UPDATE SET finished_at=EXCLUDED.finished_at,
                    status=EXCLUDED.status, scope=EXCLUDED.scope, error_code=EXCLUDED.error_code""",
                (run['id'], run['resource'], run['attempted_at'], run['finished_at'],
                 run['status'], json.dumps(run['scope']), run['error_code']))
        if owned: connection.commit()
    except Exception:
        if owned: connection.rollback()
        raise
    finally:
        if owned: connection.close()


def _record(run):
    try:
        write_run(run)
    except Exception:
        # Do not leak HTTP URLs (FRED keys), SQL parameters or connection strings.
        # A failed provenance write cannot manufacture a successful check.
        logger.warning("Availability-check metadata was not recorded; apply the source-check schema migration and check database access.")


@contextmanager
def availability_check(resource, scope=None, connection=None):
    run = dict(id=str(uuid4()), resource=resource, attempted_at=utc_now(),
               finished_at=None, status='running', scope=dict(scope or {}), error_code=None)
    _record(run)
    try:
        yield run
    except Exception:
        run.update(status='error', finished_at=utc_now(), error_code='refresh_failed')
        _record(run)
        raise
    else:
        if run['status'] == 'running':
            run['status'] = 'success'
        run['finished_at'] = utc_now()
        if connection is None:
            _record(run)
        else:
            # A direct-publisher importer can commit its final success receipt
            # together with observations and the published Overview generation.
            write_run(run, connection)
