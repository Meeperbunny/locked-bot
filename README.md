# locked-bot

A Discord bot that sends daily Stoic quotes from "The Daily Stoic" book to subscribed users.

## Overview

This project fetches quotes from "The Daily Stoic: 366 Meditations on Wisdom, Perseverance, and the Art of Living" and delivers them via Discord bot. Users can subscribe to receive a daily meditation at 7:30 AM PST.

## Features

- Fetches quotes from archive.org and parses them by date
- Discord bot that sends daily quotes at 7:30 AM PST
- User subscription management (subscribe/unsubscribe via DM)
- Stores quotes in CSV format for easy access
- Handles all 366 daily meditations
- Formatted embeds with gold color theme

## Installation

1. Clone the repository
2. Install required dependencies:
```bash
pip install discord.py pandas pytz requests beautifulsoup4
```

3. Create a Discord bot:
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Go to "Bot" section and create a bot
   - Copy the token
   - Enable "Message Content Intent" in Privileged Gateway Intents

4. Update `src/bot.py` with your bot token:
```python
bot.run('YOUR_DISCORD_TOKEN')
```

## Usage

### Generate Quote Data

First, fetch and parse the quotes from archive.org:
```bash
python src/parse_quotes.py
```

This creates `data/quotes.csv` with all 366 daily quotes.

### Run the Discord Bot

```bash
python src/bot.py
```

### Subscribe to Daily Quotes

Send a DM to the bot with:
```
subscribe
```

You'll receive a confirmation message and start getting daily quotes at 7:30 AM PST.

### Unsubscribe

Send a DM to the bot with:
```
unsubscribe
```

## Project Structure

```
locked-bot/
├── src/
│   ├── parse_quotes.py       # Fetches and parses quotes from archive.org
│   └── bot.py                # Discord bot that sends daily quotes
├── data/
│   └── quotes.csv            # Generated CSV with all quotes (generated)
└── README.md
```

## How It Works

1. `parse_quotes.py` fetches the full text from archive.org
2. Extracts quotes by date (January 1st - December 31st)
3. Stores them in `data/quotes.csv`
4. `bot.py` loads the CSV and checks every minute if it's 7:30 AM PST
5. Sends the day's quote to all subscribed users via DM

## Loading Quotes with Pandas

```python
import pandas as pd

df = pd.read_csv('data/quotes.csv')
print(df.head())
```

## License

Check source materials for licensing information.