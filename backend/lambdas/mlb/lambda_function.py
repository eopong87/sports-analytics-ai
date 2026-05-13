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

def get_mlb_schedule(api_key):
    """
    Fetch MLB schedule and scores from SportsRadar
    MLB uses year/month/day format like NBA
    """
    today = datetime.utcnow()
    year = today.strftime('%Y')
    month = today.strftime('%m')
    day = today.strftime('%d')

    url = f"https://api.sportradar.com/mlb/trial/v7/en/games/{year}/{month}/{day}/schedule.json"

    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()

def get_mlb_boxscore(api_key, game_id):
    """
    Fetch MLB boxscore including pitcher stats
    Baseball has unique stats — ERA, WHIP, strikeouts
    """
    url = f"https://api.sportradar.com/mlb/trial/v7/en/games/{game_id}/boxscore.json"

    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()

def save_mlb_game(game_data):
    """
    Save MLB game to DynamoDB
    Baseball has innings instead of quarters
    """
    item = {
        'gameId': f"MLB-{game_data.get('id', 'unknown')}",
        'timestamp': datetime.utcnow().isoformat(),
        'sport': 'MLB',
        'homeTeam': game_data.get('home', {}).get('name', ''),
        'awayTeam': game_data.get('away', {}).get('name', ''),
        'homeScore': game_data.get('home', {}).get('runs', 0),
        'awayScore': game_data.get('away', {}).get('runs', 0),
        'status': game_data.get('status', ''),
        'inning': game_data.get('inning', 0),
        'inningHalf': game_data.get('inning_half', ''),
        'venue': game_data.get('venue', {}).get('name', ''),
        'updatedAt': datetime.utcnow().isoformat()
    }

    save_to_dynamodb('sports-analytics-live-games', item)
    return item

def save_mlb_pitcher_stats(game_id, boxscore):
    """
    Save pitcher stats — the most important stat in baseball
    Pitchers determine game outcomes more than any other player
    """
    players_saved = 0

    for team_type in ['home', 'away']:
        team = boxscore.get(team_type, {})
        team_name = team.get('name', '')

        # Pitcher stats
        for player in team.get('pitching', []):
            item = {
                'playerId': f"MLB-{player.get('id', 'unknown')}",
                'gameId': f"MLB-{game_id}",
                'name': f"{player.get('first_name', '')} {player.get('last_name', '')}",
                'team': team_name,
                'sport': 'MLB',
                'position': 'P',
                'inningsPitched': player.get('ip_2', 0),
                'strikeouts': player.get('ktotal', 0),
                'earnedRuns': player.get('er', 0),
                'hits': player.get('h', 0),
                'walks': player.get('bb', 0),
                'pitchCount': player.get('p', 0),
                'era': player.get('era', 0),
                'updatedAt': datetime.utcnow().isoformat()
            }
            save_to_dynamodb('sports-analytics-player-stats', item)
            players_saved += 1

        # Batting stats
        for player in team.get('hitting', []):
            item = {
                'playerId': f"MLB-BAT-{player.get('id', 'unknown')}",
                'gameId': f"MLB-{game_id}",
                'name': f"{player.get('first_name', '')} {player.get('last_name', '')}",
                'team': team_name,
                'sport': 'MLB',
                'position': player.get('position', ''),
                'atBats': player.get('ab', 0),
                'hits': player.get('h', 0),
                'homeRuns': player.get('hr', 0),
                'rbi': player.get('rbi', 0),
                'avg': player.get('avg', 0),
                'updatedAt': datetime.utcnow().isoformat()
            }
            save_to_dynamodb('sports-analytics-player-stats', item)
            players_saved += 1

    return players_saved

def lambda_handler(event, context):
    """
    Main Lambda entry point for MLB data
    Triggered every 60 seconds by EventBridge
    """
    start_time = datetime.utcnow()
    logger.info(f"MLB Fetcher started at {start_time.isoformat()}")

    try:
        # Step 1 - Get API keys
        keys = get_api_keys()
        api_key = keys['sportradar_master_key']

        # Step 2 - Get today's MLB schedule
        logger.info("Fetching MLB schedule...")
        schedule_data = get_mlb_schedule(api_key)
        games = schedule_data.get('games', [])
        logger.info(f"Found {len(games)} MLB games today")

        # Step 3 - Process each game
        saved_games = []
        total_players = 0

        for game in games:
            saved_game = save_mlb_game(game)
            saved_games.append(saved_game)
            logger.info(f"Saved: {saved_game['awayTeam']} vs {saved_game['homeTeam']} — {saved_game['awayScore']}-{saved_game['homeScore']}")

            # Get pitcher stats for active games
            if game.get('status') in ['inprogress', 'delayed']:
                boxscore = get_mlb_boxscore(api_key, game.get('id'))
                players_saved = save_mlb_pitcher_stats(game.get('id'), boxscore)
                total_players += players_saved
                logger.info(f"Saved stats for {players_saved} players")

            # Send to Kinesis
            send_to_kinesis(
                'sports-analytics-live-stream',
                {
                    'type': 'MLB_GAME_UPDATE',
                    'game': saved_game,
                    'timestamp': datetime.utcnow().isoformat()
                },
                f"MLB-{game.get('id', 'unknown')}"
            )

        log_execution('mlb-fetcher', start_time, len(saved_games))

        return format_response(200, {
            'message': 'MLB data fetched successfully',
            'gamesProcessed': len(saved_games),
            'playersProcessed': total_players,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"MLB Fetcher failed: {str(e)}")
        return format_response(500, {
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })