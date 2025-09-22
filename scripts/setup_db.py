from typing import Optional
import sys
import click

from app.models.user import UserTable, UserSessionTable
from app.core.config import settings


def _table_status(table) -> str:
    try:
        return table.describe_table()["Table"]["TableStatus"]
    except Exception:
        return "UNKNOWN"


def ensure_tables(create: bool = True, delete: bool = False) -> None:
    """Create or delete DynamoDB tables."""
    if delete:
        if UserSessionTable.exists():
            UserSessionTable.delete_table()
        if UserTable.exists():
            UserTable.delete_table()
        return

    if create:
        if not UserTable.exists():
            UserTable.create_table(read_capacity_units=5, write_capacity_units=5, wait=True)
        if not UserSessionTable.exists():
            UserSessionTable.create_table(read_capacity_units=5, write_capacity_units=5, wait=True)


@click.command()
@click.option("--create", is_flag=True, default=True, help="Create tables if not exist")
@click.option("--delete", is_flag=True, default=False, help="Delete tables")
def main(create: bool, delete: bool) -> None:
    click.echo(f"Region={settings.dynamodb_region} Host={settings.dynamodb_endpoint_url}")
    ensure_tables(create=create, delete=delete)
    click.echo(
        f"UserTable: {UserTable.Meta.table_name} status={_table_status(UserTable)} | "
        f"UserSessionTable: {UserSessionTable.Meta.table_name} status={_table_status(UserSessionTable)}"
    )


if __name__ == "__main__":
    main()


