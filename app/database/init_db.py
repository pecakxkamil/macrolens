"""Initialize the MacroLens database schema."""

import sys
from pathlib import Path

from app.database.connection import get_connection


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def main() -> int:
    connection = None

    try:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute(schema_sql)

        connection.commit()
        print("Database schema initialized successfully.")
        return 0
    except Exception as error:
        if connection is not None:
            connection.rollback()
        print(f"Database schema initialization failed: {error}")
        return 1
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    sys.exit(main())
