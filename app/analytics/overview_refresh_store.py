"""Durable job state and disposable coherent Overview publications."""
import json
from uuid import uuid4
from fastapi.encoders import jsonable_encoder
from app.database.connection import get_independent_connection

LOCK_ID = 726530019


def encoded(value):
    return json.dumps(jsonable_encoder(value), allow_nan=False)


class RefreshStore:
    def acquire(self):
        connection = get_independent_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_try_advisory_lock(%s)', (LOCK_ID,))
                acquired = cursor.fetchone()[0]
            connection.commit()
            if acquired:
                return connection
        except Exception:
            connection.close()
            raise
        connection.close()
        return None

    def release(self, lease):
        try:
            with lease.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_unlock(%s)', (LOCK_ID,))
            lease.commit()
        finally:
            lease.close()

    def read(self):
        connection = get_independent_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT job_id,status,attempted_at,completed_at,next_check_at,publication_id,source_versions,results FROM overview_refresh_state WHERE id=1')
                row = cursor.fetchone()
            if row is None:
                raise RuntimeError('Overview refresh schema has not been initialized.')
            result = dict(zip(('job_id','status','attempted_at','completed_at','next_check_at','publication_id','source_versions','results'), row))
            for key in ('job_id','publication_id'):
                if result[key] is not None: result[key] = str(result[key])
            return result
        finally:
            connection.close()

    def start(self, job_id, now, next_check):
        self.update(dict(job_id=job_id, status='running', attempted_at=now, completed_at=None,
                         next_check_at=next_check, results=[]))

    def update(self, fields, connection=None):
        owned = connection is None
        connection = connection or get_independent_connection()
        try:
            columns, values = [], []
            for key, value in fields.items():
                if key not in {'job_id','status','attempted_at','completed_at','next_check_at','publication_id','source_versions','results'}:
                    raise ValueError('Unsupported refresh state field.')
                columns.append(key+'=%s'+('::jsonb' if key in ('source_versions','results') else ''))
                values.append(encoded(value) if key in ('source_versions','results') else value)
            with connection.cursor() as cursor:
                cursor.execute('UPDATE overview_refresh_state SET '+','.join(columns)+' WHERE id=1', values)
            if owned: connection.commit()
        except Exception:
            if owned: connection.rollback()
            raise
        finally:
            if owned: connection.close()

    def publication(self, publication_id=None, key=None):
        connection = get_independent_connection()
        try:
            with connection.cursor() as cursor:
                if publication_id is None:
                    cursor.execute('SELECT p.id,p.brief FROM overview_refresh_state s JOIN overview_publications p ON p.id=s.publication_id WHERE s.id=1')
                elif key is None:
                    cursor.execute('SELECT id,brief FROM overview_publications WHERE id=%s', (publication_id,))
                else:
                    cursor.execute('SELECT id,histories->%s FROM overview_publications WHERE id=%s', (key, publication_id))
                row = cursor.fetchone()
                return (str(row[0]), row[1]) if row else None
        finally:
            connection.close()

    def publish(self, connection, brief, histories, now):
        publication_id = str(uuid4())
        brief = {**brief, 'data_revision': publication_id, 'automatic_refresh_supported': True}
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO overview_publications(id,created_at,brief,histories) VALUES (%s,%s,%s::jsonb,%s::jsonb)',
                           (publication_id,now,encoded(brief),encoded(histories)))
            cursor.execute('UPDATE overview_refresh_state SET publication_id=%s WHERE id=1', (publication_id,))
            # Retain recent cache generations for in-flight chart requests. This
            # only evicts disposable caches, never observation/feature history.
            cursor.execute('DELETE FROM overview_publications WHERE id NOT IN (SELECT id FROM overview_publications ORDER BY created_at DESC LIMIT 8) AND id != %s', (publication_id,))
        return publication_id
