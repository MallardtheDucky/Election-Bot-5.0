import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def sync_commands():
    bot = commands.Bot(command_prefix=None, intents=discord.Intents.default())
    guild = discord.Object(id=1139705914803359764)
    
    async with bot:
        await bot.login(os.getenv("DISCORD_TOKEN"))
        
        # Load cog
        await bot.load_extension("cogs.all_winners")
        print("Loaded all_winners cog")
        
        # Clear and sync
        bot.tree.clear_commands(guild=guild)
        await bot.tree.sync(guild=guild)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        
        print(f"Synced {len(synced)} commands:")
        for cmd in synced:
            print(f"  - {cmd.name}")

asyncio.run(sync_commands())