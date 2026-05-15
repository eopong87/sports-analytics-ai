import json
import boto3
import requests
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
kinesis = boto3.client('kinesis')

import os
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'

def save_to_dynamodb(table_name, item):
    table = dynamodb.Table(table_name)
    item['updatedAt'] = datetime.utcnow().isoformat()
    table.put_item(Item=item)

def send_to_kinesis(stream_name, data, partition_key):
    try:
        kinesis.put_record(StreamName=stream_name, Data=json.dumps(data), PartitionKey=partition_key)
    except Exception as e:
        logger.error(f"Kinesis error: {str(e)}")

def format_response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(body)
    }

def get_todays_games():
    table = dynamodb.Table('sports-analytics-live-games')
    return table.scan().get('Items', [])

def get_todays_odds():
    table = dynamodb.Table('sports-analytics-betting-odds')
    return table.scan().get('Items', [])

def build_prompt(games, odds):
    games_summary = []
    for game in games[:20]:
        games_summary.append(
            f"{game.get('sport','?')} - {game.get('awayTeam','')} vs {game.get('homeTeam','')} | "
            f"Score: {game.get('awayScore',0)}-{game.get('homeScore',0)} | Status: {game.get('status','')}"
        )
    odds_summary = []
    for odd in odds[:5]:
        odds_summary.append(f"{odd.get('sport','')} - {odd.get('awayTeam','')} vs {odd.get('homeTeam','')}")

    return f"""You are an expert sports analyst covering NBA, NFL, and MLB.

TODAY'S GAMES ({len(games_summary)} total):
{chr(10).join(games_summary) if games_summary else 'No games today'}

BETTING LINES:
{chr(10).join(odds_summary) if odds_summary else 'No odds available'}

Provide:
1. GAME INSIGHTS - key storylines and performances
2. BETTING PICKS - top 3 with confidence (Low/Medium/High)
3. KEY TAKEAWAYS - 3 most important things today

Be concise and actionable."""

def analyze_with_groq(prompt):
    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': 'llama-3.3-70b-versatile',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 1000,
        'temperature': 0.7
    }
    response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']

def lambda_handler(event, context):
    logger.info("AI Analysis started")
    try:
        games = get_todays_games()
        odds = get_todays_odds()
        logger.info(f"Found {len(games)} games, {len(odds)} odds")

        if not games:
            return format_response(200, {
                'message': 'No games to analyze',
                'timestamp': datetime.utcnow().isoformat()
            })

        prompt = build_prompt(games, odds)
        insights = analyze_with_groq(prompt)
        logger.info("Groq/Llama analysis complete")

        save_to_dynamodb('sports-analytics-ai-insights', {
            'sport': 'ALL',
            'timestamp': datetime.utcnow().isoformat(),
            'insights': insights,
            'gamesAnalyzed': len(games),
            'date': datetime.utcnow().strftime('%Y-%m-%d')
        })

        send_to_kinesis('sports-analytics-live-stream',
            {'type': 'AI_INSIGHTS', 'insights': insights, 'timestamp': datetime.utcnow().isoformat()},
            'ai-insights')

        return format_response(200, {
            'message': 'AI analysis complete',
            'gamesAnalyzed': len(games),
            'insights': insights,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"AI Analysis failed: {str(e)}")
        return format_response(500, {'error': str(e), 'timestamp': datetime.utcnow().isoformat()})
