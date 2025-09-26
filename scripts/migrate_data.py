"""
Simple migration utilities for BE-005.

Supported operations:
  - backfill indexes (no-op for GSI as managed by AWS)
  - normalize user phone/role/status fields if needed

Usage:
  python scripts/migrate_data.py --normalize-users
"""

import click
from datetime import datetime
from app.models.user import UserTable


@click.command()
@click.option("--normalize-users", is_flag=True, default=True, help="Normalize user fields")
def main(normalize_users: bool) -> None:
    if normalize_users:
        count = 0
        for item in UserTable.scan():
            changed = False
            if item.phone is None:
                item.update(actions=[UserTable.phone.set("")])
                changed = True
            if not item.status:
                item.update(actions=[UserTable.status.set("active")])
                changed = True
            if changed:
                count += 1
        click.echo(f"Normalized {count} users")


if __name__ == "__main__":
    main()


