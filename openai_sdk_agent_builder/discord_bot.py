import discord
from discord.ext import commands
import asyncio
from main import run_agent
from dotenv import load_dotenv
from pathlib import Path
import os

# Load .env with override
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if not DISCORD_BOT_TOKEN:
    raise RuntimeError("❌ DISCORD_BOT_TOKEN is missing or not loading from .env")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# User-specific locks to prevent overlapping builds
user_locks = {}

@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user} (ID: {bot.user.id})")

@bot.command(name="alpha", aliases=["ai"])
async def alpha(ctx, *, prompt: str):
    user_id = str(ctx.author.id)

    if user_id in user_locks:
        await ctx.reply("⚠️ You're already running a task. Please wait for it to finish.")
        return

    user_locks[user_id] = True
    await ctx.reply(f"🧠 Received your build request:\n```{prompt}```\nSpinning up your private dev thread...")

    async def send_to_discord(message: str):
        # Truncate if message is too long for Discord
        if len(message) > 1900:
            message = message[:1900] + "…"
        await ctx.send(message)

    try:
        await run_agent(prompt, log_callback=send_to_discord)
    except Exception as e:
        await ctx.send(f"❌ Internal Error: {str(e)}")
    finally:
        user_locks.pop(user_id, None)
        await ctx.send("✅ Task finished.")

bot.run(DISCORD_BOT_TOKEN)
