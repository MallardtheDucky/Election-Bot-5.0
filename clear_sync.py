import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

bot = commands.Bot(command_prefix=None, intents=discord.Intents.default())
dev_guild = discord.Object(id=1139705914803359764)

@bot.event
async def on_ready():
    print("Clearing all commands...")
    bot.tree.clear_commands(guild=dev_guild)
    await bot.tree.sync(guild=dev_guild)
    print("All commands cleared!")
    await bot.close()

asyncio.run(bot.start(os.getenv("DISCORD_TOKEN")))