"""Manual PostgreSQL connectivity check for local development."""

import sys

from app.database.connection import get_connection


def main() -> int:
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()

        if result and result[0] == 1:
            print("PostgreSQL connection successful.")
            return 0

        print(f"PostgreSQL connection check failed: unexpected result {result!r}")
        return 1
    except Exception as error:
        print(f"PostgreSQL connection check failed: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
