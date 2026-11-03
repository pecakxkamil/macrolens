"""Opt-in E2A migration, deliberately restricted to isolated E2A databases."""
from pathlib import Path


def initialize(connection):
    if not connection.info.dbname.startswith('macrolens_earnings_'):
        raise ValueError('E2A schema may only be applied to an owned macrolens_earnings_* database')
    with connection.transaction():
        connection.execute(Path(__file__).with_name('earnings_schema.sql').read_text(encoding='utf-8'))
