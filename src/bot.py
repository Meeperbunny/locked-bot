import discord
from dotenv import load_dotenv
from discord.ext import commands, tasks
import pandas as pd
import os
from datetime import datetime, time
import pytz
import json

# Load environment variables
load_dotenv()
token = os.getenv('DISCORD_TOKEN')

if not token:
    raise ValueError("DISCORD_TOKEN environment variable not set")

# Load quotes from CSV
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_filepath = os.path.join(script_dir, '..', 'data', 'quotes.csv')
df = pd.read_csv(csv_filepath)

# Create a dictionary of date -> quote
quotes_dict = dict(zip(df['Date'], df['Quote']))

# Load subscribed users from file
subscribed_users_file = os.path.join(script_dir, '..', 'data', 'subscribed_users.json')

def load_subscribed_users():
    if os.path.exists(subscribed_users_file):
        with open(subscribed_users_file, 'r') as f:
            return set(json.load(f))
    return set()

def save_subscribed_users():
    os.makedirs(os.path.dirname(subscribed_users_file), exist_ok=True)
    with open(subscribed_users_file, 'w') as f:
        json.dump(list(subscribed_users), f)

# Set up bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Store subscribed user IDs in a set
subscribed_users = load_subscribed_users()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Currently have {len(subscribed_users)} subscribed users')
    send_daily_quote.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if message.content.lower() == 'subscribe':
        subscribed_users.add(message.author.id)
        save_subscribed_users()
        print(f'{message.author} subscribed. Total subscribers: {len(subscribed_users)}')
        await message.reply('✅ You have subscribed to daily Stoic quotes!')
    elif message.content.lower() == 'unsubscribe':
        subscribed_users.discard(message.author.id)
        save_subscribed_users()
        print(f'{message.author} unsubscribed. Total subscribers: {len(subscribed_users)}')
        await message.reply('❌ You have unsubscribed from daily Stoic quotes.')
    
    await bot.process_commands(message)


@tasks.loop(minutes=1)
async def send_daily_quote():
    # Check if it's 7:30 AM PST
    pst = pytz.timezone('America/Los_Angeles')
    now = datetime.now(pst)
    
    if now.hour == 7 and now.minute == 30:
        # Get today's date in the format from CSV (e.g., "January 1st")
        month = now.strftime('%B')
        day = now.day
        suffix = get_day_suffix(day)
        today_date = f"{month} {day}{suffix}"
        
        # Get the quote for today
        quote = quotes_dict.get(today_date, "Quote not found for today.")
        
        # Format the quote with markdown
        formatted_quote = format_quote(quote)
        
        print(f'Sending daily quote for {today_date} to {len(subscribed_users)} users')
        
        # Send to all subscribed users
        for user_id in subscribed_users:
            try:
                user = await bot.fetch_user(user_id)
                await user.send(f"# 📖 Daily Stoic Quote - {today_date}\n\n{formatted_quote}")
                print(f'✓ Sent quote to {user}')
            except discord.errors.NotFound:
                print(f'✗ User {user_id} not found, removing from subscriptions')
                subscribed_users.discard(user_id)
                save_subscribed_users()

def format_quote(text):
    """Format quote text with markdown for titles and quotes"""
    lines = text.split('\n')
    formatted_lines = []
    prev_empty = False
    in_quote = False
    
    for line in lines:
        stripped = line.strip()
        
        # Handle empty lines - add spacing but avoid multiple blank lines
        if not stripped:
            if not prev_empty:
                formatted_lines.append('')
            prev_empty = True
            in_quote = False
            continue
        
        prev_empty = False
        
        # If line is all caps (likely a title), make it a bold header
        if stripped.isupper() and len(stripped) > 3:
            formatted_lines.append(f"## **{stripped}**")
            in_quote = False
        # If we're in a quote and line doesn't start with —, continue quoting
        elif in_quote and not (stripped.startswith('—') or stripped.startswith('–')):
            formatted_lines.append(f"> {stripped}")
        # If line starts with — or – (em dash or en dash), it's likely attribution
        elif stripped.startswith('—') or stripped.startswith('–'):
            formatted_lines.append(f"> *{stripped}*")
            in_quote = False
        else:
            formatted_lines.append(stripped)
    
    return '\n'.join(formatted_lines)

def get_day_suffix(day):
    """Get the day suffix (st, nd, rd, th)"""
    if day in [1, 21, 31]:
        return 'st'
    elif day in [2, 22]:
        return 'nd'
    elif day in [3, 23]:  
        return 'rd'
    else:
        return 'th'

# Run the bot
print('Starting Discord bot...')
bot.run(token)