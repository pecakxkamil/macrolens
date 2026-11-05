"""Synthetic CI source + real backup/restore; never opens a normal database.

The complete restored-clone validation is shared with the local activation
trial. CI uses its real service identity, without impersonating production.
"""
import json
import os
import re
import runpy
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from app import forecast_f1 as model
from tests.postgres_earnings_monitor_validation import initialize
from tests.postgres_earnings_financial_activation_validation import make_backup
from tests.postgres_http_guard import no_publisher_http


def main():
    container = os.environ['F1_TEST_CONTAINER']
    params = dict(host=os.environ['DB_HOST'], port=int(os.environ['DB_PORT']),
                  user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'])
    if (os.environ.get('GITHUB_ACTIONS') != 'true'
        or os.environ.get('DB_NAME') != 'macrolens_f1_activation_control'
        or params['host'] != '127.0.0.1' or params['user'] != 'macrolens_ci'
        or not re.fullmatch(r'[0-9a-f]{64}', container)):
        raise ValueError('Exact loopback CI service and control required')
    name = "macrolens_earnings_e2b_e2c_e2d_e2e_ci_source_" + uuid4().hex[:12]
    with psycopg.connect(**params, dbname='postgres', autocommit=True) as admin, TemporaryDirectory(prefix='f1_activation_ci_') as directory:
        raw = Path(directory)
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        try:
            factory = lambda: psycopg.connect(**params, dbname=name)
            initialize(factory)
            with factory() as c:
                c.execute((model.ROOT/'app/database/earnings_monitor_schema.sql').read_text(encoding='utf-8'))
                c.execute("INSERT INTO series(series_id,name,category,frequency,unit) VALUES('CPIAUCSL','Synthetic CPI','inflation','monthly','Index')")
                c.execute("INSERT INTO economic_releases(release_id,name) VALUES(10,'Consumer Price Index')")
                c.execute("INSERT INTO series_release_map VALUES('CPIAUCSL',10)")
                c.execute("INSERT INTO release_dates(release_id,release_date) VALUES(10,'2026-11-12')")
            backup = make_backup(factory, admin, name, container, raw)
            (raw/'normal-backup.json').write_text(json.dumps(backup))
            os.environ['F1_ACTIVATION_DIR'] = str(raw)
            os.environ['F1_SYNTHETIC_SOURCE'] = name
            # The restored clone has its own true identity and is always removed.
            try:
                runpy.run_path(str(Path(__file__).with_name('postgres_forecast_f1_activation_validation.py')), run_name='__main__')
            finally:
                keep = raw/'keep-clone'
                if keep.exists():
                    clone = keep.read_text()
                    if not clone.startswith(model.PREFIX+'activation_'):
                        raise ValueError('Unexpected clone name')
                    admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(clone)))
        finally:
            admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
    print('F1 CI PASSED: synthetic source, actual backup/restore, complete activation trial')


if __name__ == '__main__':
    with no_publisher_http():
        main()
