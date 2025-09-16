#!/usr/bin/env python3
"""
Force sync script to manually sync Discord commands
Run this if commands are not showing up in Discord
"""

import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
TESTING = True  # Set to False for production
dev_guild_id = 1139705914803359764  # Replace with your dev guild ID

# Set up intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Create bot
bot = discord.ext.commands.Bot(command_prefix=None, intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Starting force sync process...")
    
    try:
        if TESTING:
            # Clear guild commands first
            guild = discord.Object(id=dev_guild_id)
            bot.tree.clear_commands(guild=guild)
            await bot.tree.sync(guild=guild)
            print("Cleared guild commands")
            
            # Load the cog manually to get commands
            from cogs.all_winners import AllWinners
            
            # Create the cog and get its commands
            cog = AllWinners(bot)
            
            # Add the specific commands we need
            target_commands = ['view_general_campaign', 'admin_view_all_campaign_points']
            
            for cmd in cog.get_app_commands():
                if cmd.name in target_commands:
                    bot.tree.add_command(cmd)
                    print(f"Added command: {cmd.name}")
            
            # Sync to guild
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} commands to guild {dev_guild_id}")
            
            # List synced commands
            for cmd in synced:
                print(f"  - {cmd.name}: {cmd.description}")
                
        else:
            # Global sync
            from cogs.all_winners import AllWinners
            
            cog = AllWinners(bot)
            
            target_commands = ['view_general_campaign', 'admin_view_all_campaign_points']
            
            for cmd in cog.get_app_commands():
                if cmd.name in target_commands:
                    bot.tree.add_command(cmd)
                    print(f"Added command: {cmd.name}")
            
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} commands globally")
            
            for cmd in synced:
                print(f"  - {cmd.name}: {cmd.description}")
        
        print("Force sync completed successfully!")
        
    except Exception as e:
        print(f"Error during force sync: {e}")
        import traceback
        traceback.print_exc()
    
    await bot.close()

async def main():
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("Please set the DISCORD_TOKEN environment variable.")
        return
    
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())