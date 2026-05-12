import json
import boto3
import anthropic
import sys
import os
from datetime import datetime

# Import our shared utilities
sys.path.append('/var/task')
from shared.utils import (
    get_api_keys,
    get_from_dynamodb,
    save_to_dynamodb,
    send_to_kinesis,
    format_response,
    log_execution,
    logger
)

def get_todays_games():
    """
    Fetch all of today's games from DynamoDB
    These were saved by our NBA/NFL/MLB fetcher Lambdas
    """
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('sports-analytics-live-games')
    
    # Scan for all games updated today
    response = table.scan()
    games = response.get('Items', [])
    logger.info(f"Found {len(games)} games for analysis")
    return games

def get_player_stats_for_game(game_id):
    """
    Fetch all player stats for a specific game
    """
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('sports-analytics-player-stats')
    
    response = table.query(
        KeyConditionExpression='gameId = :gid',
        ExpressionAttributeValues={':gid': game_id}
    )
    return response.get('Items', [])

def build_nba_prompt(games, player_stats):
    """
    Build the prompt we send to Claude
    The quality of this prompt determines the quality of insights
    This is what AI Engineers get paid to do!
    """
    games_summary = []
    for game in games:
        if game.get('sport') == 'NBA':
            games_summary.append(
                f"{game['awayTeam']} {game['awayScore']} - "
                f"{game['homeTeam']} {game['homeScore']} "
                f"({game['status']}, Q{game.get('quarter', 'N/A')})"
            )
    
    stats_summary = []
    for player in player_stats[:10]:  # Top 10 players
        stats_summary.append(
            f"{player['name']} ({player['team']}): "
            f"{player['points']}pts, {player['rebounds']}reb, "
            f"{player['assists']}ast"
        )

    prompt = f"""You are an expert NBA analyst. Analyze the following live game data 
and provide insights in a clear, engaging way.

TODAY'S NBA GAMES:
{chr(10).join(games_summary) if games_summary else 'No games today'}

TOP PERFORMER STATS:
{chr(10).join(stats_summary) if stats_summary else 'No stats available'}

Please provide:
1. GAME INSIGHTS (2-3 sentences per active game)
   - Current momentum and key storylines
   - Standout performances

2. PLAYER TRENDS (top 3 performers)
   - Who is hot and why
   - Any surprising performances

3. BETTING INSIGHTS (3 recommendations)
   - Over/under recommendations based on current pace
   - Player prop recommendations
   - Confidence level for each (Low/Medium/High)

4. KEY TAKEAWAYS (2-3 bullet points)
   - Most important things happening in NBA today

Keep the tone conversational and engaging.
Format each section clearly with the headers above.
Base all insights strictly on the data provided."""

    return prompt

def analyze_with_claude(prompt, api_key):
    """
    Send data to Claude and get back AI insights
    This is the core AI integration
    """
    client = anthropic.Anthropic(api_key=api_key)
    
    logger.info("Sending data to Claude for analysis...")
    
    message = client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=1500,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    
    insights = message.content[0].text
    logger.info("Claude analysis complete")
    return insights

def save_insights_to_dynamodb(sport, insights):
    """
    Save Claude's analysis back to DynamoDB
    Frontend reads from here to display AI insights
    """
    item = {
        'sport': sport,
        'timestamp': datetime.utcnow().isoformat(),
        'insights': insights,
        'generatedBy': 'claude-opus-4',
        'date': datetime.utcnow().strftime('%Y-%m-%d')
    }
    
    save_to_dynamodb('sports-analytics-ai-insights', item)
    logger.info(f"Saved {sport} insights to DynamoDB")
    return item

def lambda_handler(event, context):
    """
    Main Lambda entry point
    Triggered every 5 minutes by EventBridge
    Reads all sports data and generates AI insights
    """
    start_time = datetime.utcnow()
    logger.info(f"AI Analysis Engine started at {start_time.isoformat()}")
    
    try:
        # Step 1 — Get API keys
        logger.info("Fetching API keys...")
        keys = get_api_keys()
        anthropic_key = keys['anthropic_api_key']
        
        # Step 2 — Get today's games from DynamoDB
        logger.info("Fetching today's games...")
        games = get_todays_games()
        
        if not games:
            logger.info("No games found today — skipping analysis")
            return format_response(200, {
                'message': 'No games to analyze today',
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Step 3 — Get player stats for each game
        logger.info("Fetching player stats...")
        all_player_stats = []
        for game in games:
            stats = get_player_stats_for_game(game['gameId'])
            all_player_stats.extend(stats)
        
        logger.info(f"Retrieved stats for {len(all_player_stats)} players")
        
        # Step 4 — Build prompt and analyze with Claude
        logger.info("Building AI prompt...")
        nba_prompt = build_nba_prompt(games, all_player_stats)
        
        logger.info("Analyzing with Claude AI...")
        nba_insights = analyze_with_claude(nba_prompt, anthropic_key)
        
        # Step 5 — Save insights to DynamoDB
        logger.info("Saving insights to DynamoDB...")
        saved_insights = save_insights_to_dynamodb('NBA', nba_insights)
        
        # Step 6 — Send to Kinesis for real-time frontend updates
        send_to_kinesis(
            'sports-analytics-live-stream',
            {
                'type': 'AI_INSIGHTS',
                'sport': 'NBA',
                'insights': nba_insights,
                'timestamp': datetime.utcnow().isoformat()
            },
            'NBA-insights'
        )
        
        # Step 7 — Log execution stats
        log_execution('ai-analysis', start_time, len(games))
        
        return format_response(200, {
            'message': 'AI analysis complete',
            'gamesAnalyzed': len(games),
            'playersAnalyzed': len(all_player_stats),
            'insights': nba_insights,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"AI Analysis failed: {str(e)}")
        return format_response(500, {
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })