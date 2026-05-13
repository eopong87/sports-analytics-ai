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

def get_nfl_schedule(api_key):
    """
    Fetch NFL schedule and scores from SportsRadar
    NFL uses a different URL structure than NBA
    """
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

def get_nfl_boxscore(api_key, game_id):
    """
    Fetch detailed stats for a specific NFL game
    Includes passing, rushing, receiving stats
    """
    url = f"https://api.sportradar.com/nfl/official/trial/v7/en/games/{game_id}/boxscore.json"

    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()

def save_nfl_game(game_data):
    """
    Save NFL game data to DynamoDB
    NFL has different stats than NBA — touchdowns, yards etc
    """
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
        'season': game_data.get('season', ''),
        'venue': game_data.get('venue', {}).get('name', ''),
        'updatedAt': datetime.utcnow().isoformat()
    }

    save_to_dynamodb('sports-analytics-live-games', item)
    return item

def save_nfl_player_stats(game_id, boxscore):
    """
    Save NFL player stats — passing, rushing, receiving
    Very different from NBA stats
    """
    players_saved = 0

    for team_type in ['home', 'away']:
        team = boxscore.get(team_type, {})
        team_name = team.get('name', '')

        # Passing stats
        for player in team.get('passing', []):
            item = {
                'playerId': f"NFL-{player.get('id', 'unknown')}",
                'gameId': f"NFL-{game_id}",
                'name': f"{player.get('first_name', '')} {player.get('last_name', '')}",
                'team': team_name,
                'sport': 'NFL',
                'position': 'QB',
                'passingYards': player.get('yards', 0),
                'passingTDs': player.get('touchdowns', 0),
                'interceptions': player.get('interceptions', 0),
                'completions': player.get('completions', 0),
                'attempts': player.get('attempts', 0),
                'updatedAt': datetime.utcnow().isoformat()
            }
            save_to_dynamodb('sports-analytics-player-stats', item)
            players_saved += 1

        # Rushing stats
        for player in team.get('rushing', []):
            item = {
                'playerId': f"NFL-RUSH-{player.get('id', 'unknown')}",
                'gameId': f"NFL-{game_id}",
                'name': f"{player.get('first_name', '')} {player.get('last_name', '')}",
                'team': team_name,
                'sport': 'NFL',
                'position': 'RB',
                'rushingYards': player.get('yards', 0),
                'rushingTDs': player.get('touchdowns', 0),
                'carries': player.get('attempts', 0),
                'updatedAt': datetime.utcnow().isoformat()
            }
            save_to_dynamodb('sports-analytics-player-stats', item)
            players_saved += 1

        # Receiving stats
        for player in team.get('receiving', []):
            item = {
                'playerId': f"NFL-REC-{player.get('id', 'unknown')}",
                'gameId': f"NFL-{game_id}",
                'name': f"{player.get('first_name', '')} {player.get('last_name', '')}",
                'team': team_name,
                'sport': 'NFL',
                'position': 'WR',
                'receivingYards': player.get('yards', 0),
                'receivingTDs': player.get('touchdowns', 0),
                'receptions': player.get('receptions', 0),