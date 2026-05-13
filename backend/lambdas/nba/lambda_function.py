import json
import boto3
import requests
import os
from datetime import datetime

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
secretsmanager = boto3.client('secretsmanager')

def get_api_keys():
    """
    Fetch API keys from AWS Secrets Manager
    Lambda never hardcodes keys — always fetches at runtime
    """
    secret = secretsmanager.get_secret_value(
        SecretId='sports-analytics/dev/api-keys'
    )
    return json.loads(secret['SecretString'])

def get_live_scores(api_key):
    today = datetime.utcnow()
    year = today.strftime('%Y')
    month = today.strftime('%m')
    day = today.strftime('%d')
    
    url = f"https://api.sportradar.com/nba/trial/v8/en/games/{year}/{month}/{day}/schedule.json"
    
    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }
    
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()

def get_player_stats(api_key, game_id):
    """
    Fetch player stats for a specific game
    Called for each active game
    """
    url = f"https://api.sportradar.com/nba/trial/v8/en/games/{game_id}/boxscore.json?api_key={api_key}"
    
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

def save_game_to_dynamodb(game_data):
    """
    Save live game data to DynamoDB
    Table: sports-analytics-live-games
    """
    table = dynamodb.Table('sports-analytics-live-games')
    
    # Build the item we're storing
    item = {
        'gameId': f"NBA-{game_data.get('id', 'unknown')}",
        'timestamp': datetime.utcnow().isoformat(),
        'sport': 'NBA',
        'homeTeam': game_data.get('home', {}).get('name', ''),
        'awayTeam': game_data.get('away', {}).get('name', ''),
        'homeScore': game_data.get('home_points', 0),
        'awayScore': game_data.get('away_points', 0),
        'status': game_data.get('status', ''),
        'quarter': game_data.get('quarter', 0),
        'clock': game_data.get('clock', ''),
        'updatedAt': datetime.utcnow().isoformat()
    }
    
    table.put_item(Item=item)
    return item

def save_player_stats_to_dynamodb(game_id, players):
    """
    Save player stats to DynamoDB
    Table: sports-analytics-player-stats
    """
    table = dynamodb.Table('sports-analytics-player-stats')
    
    for player in players:
        item = {
            'playerId': f"NBA-{player.get('id', 'unknown')}",
            'gameId': f"NBA-{game_id}",
            'name': f"{player.get('first_name', '')} {player.get('last_name', '')}",
            'team': player.get('team', ''),
            'points': player.get('points', 0),
            'rebounds': player.get('rebounds', 0),
            'assists': player.get('assists', 0),
            'steals': player.get('steals', 0),
            'blocks': player.get('blocks', 0),
            'turnovers': player.get('turnovers', 0),
            'minutesPlayed': player.get('minutes', '0:00'),
            'fieldGoalsMade': player.get('field_goals_made', 0),
            'fieldGoalsAttempted': player.get('field_goals_att', 0),
            'threesMade': player.get('three_points_made', 0),
            'threesAttempted': player.get('three_points_att', 0),
            'updatedAt': datetime.utcnow().isoformat()
        }
        
        table.put_item(Item=item)

def lambda_handler(event, context):
    """
    Main Lambda entry point
    AWS calls this function every 60 seconds via EventBridge
    """
    print(f"NBA Fetcher started at {datetime.utcnow().isoformat()}")
    
    try:
        # Step 1 — Get API keys from Secrets Manager
        print("Fetching API keys from Secrets Manager...")
        keys = get_api_keys()
        api_key = keys['sportradar_master_key']
        
        # Step 2 — Get today's NBA scores
        print("Fetching live NBA scores...")
        scores_data = get_live_scores(api_key)
        games = scores_data.get('games', [])
        print(f"Found {len(games)} NBA games today")
        
        # Step 3 — Process each game
        saved_games = []
        for game in games:
            # Save the game score
            saved_game = save_game_to_dynamodb(game)
            saved_games.append(saved_game)
            print(f"Saved: {saved_game['awayTeam']} vs {saved_game['homeTeam']} — {saved_game['awayScore']}-{saved_game['homeScore']}")
            
            # Get and save player stats for active games
            if game.get('status') in ['inprogress', 'halftime']:
                print(f"Fetching player stats for game {game.get('id')}...")
                boxscore = get_player_stats(api_key, game.get('id'))
                
                # Get all players from both teams
                home_players = boxscore.get('home', {}).get('players', [])
                away_players = boxscore.get('away', {}).get('players', [])
                all_players = home_players + away_players
                
                save_player_stats_to_dynamodb(game.get('id'), all_players)
                print(f"Saved stats for {len(all_players)} players")
        
        # Step 4 — Return success
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'NBA data fetched successfully',
                'gamesProcessed': len(saved_games),
                'timestamp': datetime.utcnow().isoformat()
            })
        }
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }