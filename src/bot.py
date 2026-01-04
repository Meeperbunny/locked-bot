import discord
from dotenv import load_dotenv
from discord.ext import commands, tasks
import pandas as pd
import os
from datetime import datetime, date
import pytz
import json
import re

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
if not token:
    raise ValueError("DISCORD_TOKEN environment variable not set")

script_dir = os.path.dirname(os.path.abspath(__file__))

quotes_csv_filepath = os.path.join(script_dir, "..", "data", "quotes.csv")
df = pd.read_csv(quotes_csv_filepath)
quotes_dict = dict(zip(df["Date"], df["Quote"]))

subscribed_users_file = os.path.join(script_dir, "..", "data", "subscribed_users.json")

countdowns_file = os.path.join(script_dir, "..", "data", "countdowns.csv")

def load_subscribed_users():
    if os.path.exists(subscribed_users_file):
        with open(subscribed_users_file, "r") as f:
            return set(json.load(f))
    return set()

def save_subscribed_users():
    os.makedirs(os.path.dirname(subscribed_users_file), exist_ok=True)
    with open(subscribed_users_file, "w") as f:
        json.dump(list(subscribed_users), f)

def load_countdowns():
    if os.path.exists(countdowns_file):
        dfc = pd.read_csv(countdowns_file)
        if not dfc.empty:
            dfc["user_id"] = dfc["user_id"].astype("int64")
            dfc["date"] = dfc["date"].astype(str)
            dfc["name"] = dfc["name"].astype(str)
        return dfc
    return pd.DataFrame(columns=["user_id", "date", "name"])

def save_countdowns(dfc):
    os.makedirs(os.path.dirname(countdowns_file), exist_ok=True)
    dfc.to_csv(countdowns_file, index=False)

def get_day_suffix(day):
    if day in [1, 21, 31]:
        return "st"
    if day in [2, 22]:
        return "nd"
    if day in [3, 23]:
        return "rd"
    return "th"

def format_quote(text):
    lines = text.split("\n")
    formatted_lines = []
    prev_empty = False
    in_quote = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            if not prev_empty:
                formatted_lines.append("")
            prev_empty = True
            in_quote = False
            continue

        prev_empty = False

        if stripped.isupper() and len(stripped) > 3:
            formatted_lines.append(f"## **{stripped}**")
            in_quote = False
        elif in_quote and not (stripped.startswith("—") or stripped.startswith("–")):
            formatted_lines.append(f"> {stripped}")
        elif stripped.startswith("—") or stripped.startswith("–"):
            formatted_lines.append(f"> *{stripped}*")
            in_quote = False
        else:
            formatted_lines.append(stripped)
            in_quote = True

    return "\n".join(formatted_lines)

def parse_countdown_add(message_content):
    m = re.match(r'^\s*countdown\s+add\s+([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})\s+"([^"]+)"\s*$', message_content, re.IGNORECASE)
    if not m:
        return None
    date_str = m.group(1)
    name = m.group(2).strip()
    month_s, day_s, year_s = date_str.split("/")
    y = int(year_s)
    mo = int(month_s)
    d = int(day_s)
    dt = date(y, mo, d)
    return dt, name

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

subscribed_users = load_subscribed_users()
countdowns_df = load_countdowns()

pst = pytz.timezone("America/Los_Angeles")

@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    print(f"Currently have {len(subscribed_users)} quote subscribers")
    print(f"Currently have {0 if countdowns_df is None else len(countdowns_df)} countdown rows")
    send_daily_quote.start()
    send_daily_countdowns.start()

@bot.event
async def on_message(message):
    global countdowns_df

    if message.author == bot.user:
        return

    content = message.content.strip()

    if content.lower() == "subscribe":
        subscribed_users.add(message.author.id)
        save_subscribed_users()
        await message.reply("✅ You have subscribed to daily Stoic quotes!")
        await bot.process_commands(message)
        return

    if content.lower() == "unsubscribe":
        subscribed_users.discard(message.author.id)
        save_subscribed_users()
        await message.reply("❌ You have unsubscribed from daily Stoic quotes.")
        await bot.process_commands(message)
        return

    if content.lower() == "countdown":
        await message.reply('⏳ Countdown mode ready. Add one with:\n`countdown add 7/4/2026 "CALIFORNIA"`')
        await bot.process_commands(message)
        return

    if content.lower().startswith("countdown add"):
        parsed = parse_countdown_add(content)
        if not parsed:
            await message.reply('❌ Format:\n`countdown add 7/4/2026 "CALIFORNIA"`')
            await bot.process_commands(message)
            return

        dt, name = parsed
        iso = dt.isoformat()

        new_row = pd.DataFrame([{
            "user_id": int(message.author.id),
            "date": iso,
            "name": name
        }])

        countdowns_df = pd.concat([countdowns_df, new_row], ignore_index=True)
        save_countdowns(countdowns_df)

        await message.reply(f'✅ Added countdown **{name}** for **{dt.strftime("%B %d, %Y")}**.')
        await bot.process_commands(message)
        return

    await bot.process_commands(message)

@tasks.loop(minutes=1)
async def send_daily_quote():
    now = datetime.now(pst)

    if now.hour == 7 and now.minute == 30:
        month = now.strftime("%B")
        day_num = now.day
        suffix = get_day_suffix(day_num)
        today_date = f"{month} {day_num}{suffix}"

        quote = quotes_dict.get(today_date, "Quote not found for today.")
        formatted_quote = format_quote(quote)

        print(f"Sending daily quote for {today_date} to {len(subscribed_users)} users")

        to_remove = []
        for user_id in list(subscribed_users):
            try:
                user = await bot.fetch_user(user_id)
                await user.send(f"# 📖 Daily Stoic Quote - {today_date}\n\n{formatted_quote}")
                print(f"✓ Sent quote to {user}")
            except discord.errors.NotFound:
                to_remove.append(user_id)
            except Exception as e:
                print(f"✗ Failed to send quote to {user_id}: {e}")

        if to_remove:
            for uid in to_remove:
                subscribed_users.discard(uid)
            save_subscribed_users()

@tasks.loop(minutes=1)
async def send_daily_countdowns():
    global countdowns_df

    now = datetime.now(pst)
    if now.hour != 6 or now.minute != 0:
        return

    if countdowns_df is None or countdowns_df.empty:
        return

    today = now.date()

    print(f"Sending daily countdowns to {countdowns_df['user_id'].nunique()} users ({len(countdowns_df)} countdown rows)")

    grouped = countdowns_df.groupby("user_id", sort=False)

    users_to_drop = set()

    for user_id, group in grouped:
        lines = []
        for _, row in group.iterrows():
            try:
                target = date.fromisoformat(str(row["date"]))
            except Exception:
                continue

            name = str(row.get("name", "COUNTDOWN")).strip() or "COUNTDOWN"
            delta_days = (target - today).days

            if delta_days > 1:
                lines.append(f"**{name}**: {delta_days} days left")
            elif delta_days == 1:
                lines.append(f"**{name}**: 1 day left")
            elif delta_days == 0:
                lines.append(f"🎉 **{name}**: TODAY IS THE DAY!")
            else:
                lines.append(f"✅ **{name}**: passed ({abs(delta_days)} days ago)")

        if not lines:
            continue

        msg = "# ⏳ Countdown Update\n\n" + "\n".join(lines)

        try:
            user = await bot.fetch_user(int(user_id))
            await user.send(msg)
            print(f"✓ Sent countdowns to {user}")
        except discord.errors.NotFound:
            users_to_drop.add(int(user_id))
            print(f"✗ User {user_id} not found, removing their countdowns")
        except Exception as e:
            print(f"✗ Failed to send countdowns to {user_id}: {e}")

    if users_to_drop:
        countdowns_df = countdowns_df[~countdowns_df["user_id"].isin(users_to_drop)].reset_index(drop=True)
        save_countdowns(countdowns_df)

print("Starting Discord bot...")
bot.run(token)
