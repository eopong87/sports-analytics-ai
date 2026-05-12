import json
import boto3
import logging
from datetime import datetime

# Set up logging
# This is what you see in CloudWatch when Lambda runs
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients once
# Reusing these across functions saves time and money
dynamodb = boto3.resource('dynamodb')
secretsmanager = boto3.client('secretsmanager')
kinesis = boto3.client('kinesis')

def get_api_keys(secret_name='sports-analytics/dev/api-keys'):
    """
    Fetch all API keys from Secrets Manager
    Used by every Lambda function
    """
    try:
        logger.info(f"Fetching secrets from {secret_name}")
        secret = secretsmanager.get_secret_value(SecretId=secret_name)
        keys = json.loads(secret['SecretString'])
        logger.info("API keys fetched successfully")
        return keys
    except Exception as e:
        logger.error(f"Failed to fetch API keys: {str(e)}")
        raise

def save_to_dynamodb(table_name, item):
    """
    Save any item to any DynamoDB table
    Used by all Lambda functions to store data
    """
    try:
        table = dynamodb.Table(table_name)
        
        # Always add timestamps automatically
        item['createdAt'] = datetime.utcnow().isoformat()
        item['updatedAt'] = datetime.utcnow().isoformat()
        
        table.put_item(Item=item)
        logger.info(f"Saved item to {table_name}: {item.get('gameId') or item.get('playerId') or 'unknown'}")
        return True
    except Exception as e:
        logger.error(f"Failed to save to DynamoDB {table_name}: {str(e)}")
        raise

def send_to_kinesis(stream_name, data, partition_key):
    """
    Send data to Kinesis stream for real-time processing
    Think of this as putting data onto the highway
    """
    try:
        kinesis.put_record(
            StreamName=stream_name,
            Data=json.dumps(data),
            PartitionKey=partition_key
        )
        logger.info(f"Sent data to Kinesis stream: {stream_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to send to Kinesis: {str(e)}")
        raise

def get_from_dynamodb(table_name, key):
    """
    Fetch a single item from DynamoDB by its key
    Used by AI analysis to read stats
    """
    try:
        table = dynamodb.Table(table_name)
        response = table.get_item(Key=key)
        return response.get('Item')
    except Exception as e:
        logger.error(f"Failed to get from DynamoDB {table_name}: {str(e)}")
        raise

def query_dynamodb(table_name, key_condition, expression_values):
    """
    Query multiple items from DynamoDB
    Used to get all games or all player stats
    """
    try:
        table = dynamodb.Table(table_name)
        response = table.query(
            KeyConditionExpression=key_condition,
            ExpressionAttributeValues=expression_values
        )
        return response.get('Items', [])
    except Exception as e:
        logger.error(f"Failed to query DynamoDB {table_name}: {str(e)}")
        raise

def format_response(status_code, body):
    """
    Standard response format for all Lambda functions
    API Gateway expects this exact format
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',  # Allows React frontend to call API
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
        },
        'body': json.dumps(body)
    }

def log_execution(function_name, start_time, records_processed):
    """
    Log execution stats to CloudWatch
    Helps us monitor performance and debug issues
    """
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"""
    ================================
    Function: {function_name}
    Duration: {duration:.2f} seconds
    Records processed: {records_processed}
    Timestamp: {datetime.utcnow().isoformat()}
    ================================
    """)