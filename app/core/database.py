import boto3
from typing import Optional, Dict, Any, List
from botocore.exceptions import ClientError
from app.core.config import settings
import json
from datetime import datetime


class DynamoDBClient:
    def __init__(self):
        # Prepare boto3 configuration
        boto3_config = {
            'region_name': settings.dynamodb_region,
        }
        
        # Add endpoint_url if specified (for local DynamoDB)
        if settings.dynamodb_endpoint_url:
            boto3_config['endpoint_url'] = settings.dynamodb_endpoint_url
        
        # Add AWS credentials if specified
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            boto3_config['aws_access_key_id'] = settings.aws_access_key_id
            boto3_config['aws_secret_access_key'] = settings.aws_secret_access_key
        
        self.dynamodb = boto3.resource('dynamodb', **boto3_config)
        self.client = boto3.client('dynamodb', **boto3_config)

    def get_table(self, table_name: str):
        """Get DynamoDB table"""
        return self.dynamodb.Table(table_name)

    def put_item(self, table_name: str, item: Dict[str, Any]) -> bool:
        """Put item into DynamoDB table"""
        try:
            table = self.get_table(table_name)
            table.put_item(Item=item)
            return True
        except ClientError as e:
            print(f"Error putting item: {e}")
            return False

    def get_item(self, table_name: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get item from DynamoDB table"""
        try:
            table = self.get_table(table_name)
            response = table.get_item(Key=key)
            return response.get('Item')
        except ClientError as e:
            print(f"Error getting item: {e}")
            return None

    def update_item(self, table_name: str, key: Dict[str, Any], update_expression: str, 
                   expression_attribute_values: Dict[str, Any]) -> bool:
        """Update item in DynamoDB table"""
        try:
            table = self.get_table(table_name)
            table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
            return True
        except ClientError as e:
            print(f"Error updating item: {e}")
            return False

    def delete_item(self, table_name: str, key: Dict[str, Any]) -> bool:
        """Delete item from DynamoDB table"""
        try:
            table = self.get_table(table_name)
            table.delete_item(Key=key)
            return True
        except ClientError as e:
            print(f"Error deleting item: {e}")
            return False

    def query(self, table_name: str, key_condition_expression: str, 
              expression_attribute_values: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query items from DynamoDB table"""
        try:
            table = self.get_table(table_name)
            response = table.query(
                KeyConditionExpression=key_condition_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
            return response.get('Items', [])
        except ClientError as e:
            print(f"Error querying items: {e}")
            return []

    def scan(self, table_name: str, filter_expression: Optional[str] = None,
             expression_attribute_values: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Scan items from DynamoDB table"""
        try:
            table = self.get_table(table_name)
            scan_kwargs = {}
            if filter_expression:
                scan_kwargs['FilterExpression'] = filter_expression
            if expression_attribute_values:
                scan_kwargs['ExpressionAttributeValues'] = expression_attribute_values
            
            response = table.scan(**scan_kwargs)
            return response.get('Items', [])
        except ClientError as e:
            print(f"Error scanning items: {e}")
            return []


# Global database client instance
db_client = DynamoDBClient()


def get_dynamodb_resource():
    """Get DynamoDB resource instance"""
    return db_client.dynamodb


def get_dynamodb_client():
    """Get DynamoDB client instance"""
    return db_client.client
