import json
import boto3
import requests
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
secretsmanager = boto3.client('secretsmanager')
kinesis = boto3.client('kinesis')

def get_api_keys():
    secret = secretsmanager.get_secret_value(
        SecretId='sports-analytics/dev/api-keys'
    )
    return json.loads(secret['SecretString'])

def save_to_dynamodb(table_name, item):
    table = dynamodb.Table(table_name)
    item['updatedAt'] = datetime.utcnow().isoformat()
    table.put_item(Item=item)

def send_to_kinesis(stream_name, data, partition_key):
    try:
        kinesis.put_record(
            StreamName=stream_name,
            Data=json.dumps(data),
            PartitionKey=partition_key
        )
    except Exception as e:
        logger.error(f"Kinesis error: {str(e)}")

def format_response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body)
    }

def get_nfl_schedule(api_key):
    today = datetime.utcnow()
    year = today.strftime('%Y')
    month = today.strftime('%m')
    day = today.strftime('%d')
    url = f"https://api.sportradar.com/nfl/official/trial/v7/en/games/{year}/{month}/{day}/schedule.json"
    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()

def save_nfl_game(game_data):
    item = {
        'gameId': f"NFL-{game_data.get('id', 'unknown')}",
        'timestamp': datetime.utcnow().isoformat(),
        'sport': 'NFL',
        'homeTeam': game_data.get('home', {}).get('name', ''),
        'awayTeam': game_data.get('away', {}).get('name', ''),
        'homeScore': game_data.get('home', {}).get('points', 0),
        'awayScore': game_data.get('away', {}).get('points', 0),
        'status': game_data.get('status', ''),
        'quarter': game_data.get('quarter', 0),
        'clock': game_data.get('clock', ''),
        'week': game_data.get('week', ''),
        'venue': game_data.get('venue', {}).get('name', ''),
        'updatedAt': datetime.utcnow().isoformat()
    }
    save_to_dynamodb('sports-analytics-live-games', item)
    return item

def lambda_handler(event, context):
    start_time = datetime.utcnow()
    logger.info(f"NFL Fetcher started at {start_time.isoformat()}")
    try:
        keys = get_api_keys()
        api_key = keys['sportradar_master_key']
        logger.info("Fetching NFL schedule...")
        schedule_data = get_nfl_schedule(api_key)
        games = schedule_data.get('games', [])
        logger.info(f"Found {len(games)} NFL games today")
        saved_games = []
        for game in games:
            saved_game = save_nfl_game(game)
            saved_games.append(saved_game)
            logger.info(f"Saved: {saved_game['awayTeam']} vs {saved_game['homeTeam']}")
            send_to_kinesis(
                'sports-analytics-live-stream',
                {
                    'type': 'NFL_GAME_UPDATE',
                    'game': saved_game,
                    'timestamp': datetime.utcnow().isoformat()
                },
                f"NFL-{game.get('id', 'unknown')}"
            )
        return format_response(200, {
            'message': 'NFL data fetched successfully',
            'gamesProcessed': len(saved_games),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"NFL Fetcher failed: {str(e)}")
        return format_response(500, {
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })