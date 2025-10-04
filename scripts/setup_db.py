from typing import Optional
import sys
import click
import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


USERS_TABLE_NAME = "users"
USER_SESSIONS_TABLE_NAME = "user_sessions"


def _dynamodb_resource():
    return boto3.resource(
        "dynamodb",
        region_name=settings.dynamodb_region,
        endpoint_url=settings.dynamodb_endpoint_url,
    )


def _table_exists(table_name: str) -> bool:
    dynamodb = _dynamodb_resource()
    table = dynamodb.Table(table_name)
    try:
        table.load()
        return True
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
            return False
        raise


def _delete_table_if_exists(table_name: str) -> None:
    dynamodb = _dynamodb_resource()
    table = dynamodb.Table(table_name)
    try:
        table.load()
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
            return
        raise
    table.delete()
    table.wait_until_not_exists()


def _create_users_table() -> None:
    dynamodb = _dynamodb_resource()
    if _table_exists(USERS_TABLE_NAME):
        return

    table = dynamodb.create_table(
        TableName=USERS_TABLE_NAME,
        KeySchema=[
            {"AttributeName": "user_id", "KeyType": "HASH"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "email", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "email-index",
                "KeySchema": [
                    {"AttributeName": "email", "KeyType": "HASH"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    table.wait_until_exists()


def _create_user_sessions_table() -> None:
    dynamodb = _dynamodb_resource()
    if _table_exists(USER_SESSIONS_TABLE_NAME):
        return

    table = dynamodb.create_table(
        TableName=USER_SESSIONS_TABLE_NAME,
        KeySchema=[
            {"AttributeName": "session_id", "KeyType": "HASH"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "session_id", "AttributeType": "S"},
            {"AttributeName": "user_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "user-id-index",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    table.wait_until_exists()


def ensure_tables(create: bool = True, delete: bool = False) -> None:
    """Create or delete DynamoDB tables using boto3 (On-demand)."""
    if delete:
        _delete_table_if_exists(USER_SESSIONS_TABLE_NAME)
        _delete_table_if_exists(USERS_TABLE_NAME)
        return

    if create:
        _create_users_table()
        _create_user_sessions_table()


@click.command()
@click.option("--create", is_flag=True, default=True, help="Create tables if not exist")
@click.option("--delete", is_flag=True, default=False, help="Delete tables")
def main(create: bool, delete: bool) -> None:
    click.echo(f"Region={settings.dynamodb_region} Host={settings.dynamodb_endpoint_url}")
    ensure_tables(create=create, delete=delete)
    click.echo(
        f"Users table: {USERS_TABLE_NAME} | User sessions table: {USER_SESSIONS_TABLE_NAME}"
    )


if __name__ == "__main__":
    main()

