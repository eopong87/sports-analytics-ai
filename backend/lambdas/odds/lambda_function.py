import json
import boto3
import requests
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

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

def get_odds(api_key):
    sports = ['basketball_nba', 'americanfootball_nfl', 'baseball_mlb']
    all_odds = []
    for sport in sports:
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
        params = {
            'apiKey': api_key,
            'regions': 'us',
            'markets': 'h2h,spreads,totals',
            'oddsFormat': 'american'
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            odds_data = response.json()
            all_odds.extend(odds_data)
            logger.info(f"Fetched {len(odds_data)} {sport} odds")
        else:
            logger.error(f"Failed to fetch {sport} odds: {response.status_code}")
    return all_odds

def save_odds_to_dynamodb(odds_data):
    saved = 0
    for game in odds_data:
        item = {
            'gameId': f"ODDS-{game.get('id', 'unknown')}",
            'market': 'h2h',
            'timestamp': datetime.utcnow().isoformat(),
            'sport': game.get('sport_key', ''),
            'homeTeam': game.get('home_team', ''),
            'awayTeam': game.get('away_team', ''),
            'commenceTime': game.get('commence_time', ''),
            'bookmakers': json.dumps(game.get('bookmakers', [])),
            'updatedAt': datetime.utcnow().isoformat()
        }
        save_to_dynamodb('sports-analytics-betting-odds', item)
        saved += 1
    return saved

def lambda_handler(event, context):
    start_time = datetime.utcnow()
    logger.info(f"Odds Fetcher started at {start_time.isoformat()}")
    try:
        keys = get_api_keys()
        odds_api_key = keys['odds_api_key']
        logger.info("Fetching betting odds...")
        all_odds = get_odds(odds_api_key)
        logger.info(f"Total odds fetched: {len(all_odds)}")
        saved = save_odds_to_dynamodb(all_odds)
        logger.info(f"Saved {saved} odds records")
        send_to_kinesis(
            'sports-analytics-live-stream',
            {
                'type': 'ODDS_UPDATE',
                'count': len(all_odds),
                'timestamp': datetime.utcnow().isoformat()
            },
            'odds-update'
        )
        return format_response(200, {
            'message': 'Odds fetched successfully',
            'oddsProcessed': saved,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Odds Fetcher failed: {str(e)}")
        return format_response(500, {
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })