import json
import boto3
import requests
import sys
from datetime import datetime

sys.path.append('/var/task')
from shared.utils import (
    get_api_keys,
    save_to_dynamodb,
    send_to_kinesis,
    format_response,
    log_execution,
    logger
)

def get_odds(api_key):
    """
    Fetch betting odds from The Odds API
    Covers NBA, NFL and MLB in one call
    """
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

    return all_odds

def get_player_props(api_key, sport):
    """
    Fetch player props for a specific sport
    These are the individual player betting lines
    e.g. LeBron over/under 27.5 points
    """
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/events"
    params = {'apiKey': api_key}

    response = requests.get(url, params=params, timeout=10)
    if response.status_code != 200:
        return []

    events = response.json()
    all_props = []

    for event in events[:5]:  # Limit to 5 events to save API calls
        props_url = f"https://api.the-odds-api.com/v4/sports/{sport}/events/{event['id']}/odds"
        props_params = {
            'apiKey': api_key,
            'markets': 'player_points,player_rebounds,player_assists',
            'oddsFormat': 'american'
        }

        props_response = requests.get(props_url, params=props_params, timeout=10)
        if props_response.status_code == 200:
            all_props.extend(props_response.json().get('bookmakers', []))

    return all_props

def save_odds_to_dynamodb(odds_data):
    """
    Save betting odds to DynamoDB
    Frontend reads this for the EdgeAI betting dashboard
    """
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
    """
    Main Lambda entry point for odds data
    Triggered every 5 minutes by EventBridge
    """
    start_time = datetime.utcnow()
    logger.info(f"Odds Fetcher started at {start_time.isoformat()}")

    try:
        # Step 1 - Get API keys
        keys = get_api_keys()
        odds_api_key = keys['odds_api_key']

        # Step 2 - Fetch odds for all sports
        logger.info("Fetching betting odds...")
        all_odds = get_odds(odds_api_key)
        logger.info(f"Total odds fetched: {len(all_odds)}")

        # Step 3 - Save to DynamoDB
        saved = save_odds_to_dynamodb(all_odds)
        logger.info(f"Saved {saved} odds records")

        # Step 4 - Send to Kinesis
        send_to_kinesis(
            'sports-analytics-live-stream',
            {
                'type': 'ODDS_UPDATE',
                'count': len(all_odds),
                'timestamp': datetime.utcnow().isoformat()
            },
            'odds-update'
        )

        log_execution('odds-fetcher', start_time, saved)

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