import discord
import asyncio
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

TESTING = True
dev_guild = discord.Object(id=1139705914803359764)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix=None, intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    
    try:
        # Load the cog first
        await bot.load_extension("cogs.db")
        await bot.load_extension("cogs.all_winners")
        print("✅ Loaded all_winners cog")
        
        # Clear ALL commands first
        bot.tree.clear_commands(guild=None)  # Clear global
        bot.tree.clear_commands(guild=dev_guild)  # Clear guild
        
        # Sync empty to clear Discord's cache
        await bot.tree.sync(guild=dev_guild)
        print("✅ Cleared all commands")
        
        # Wait a moment
        await asyncio.sleep(2)
        
        # Now copy and sync new commands
        bot.tree.copy_global_to(guild=dev_guild)
        synced = await bot.tree.sync(guild=dev_guild)
        
        print(f"✅ Synced {len(synced)} commands:")
        for cmd in synced:
            print(f"  - {cmd.name}")
            
        # Verify target commands
        target_commands = ['view_general_campaign', 'admin_view_all_campaign_points']
        synced_names = [cmd.name for cmd in synced]
        
        for target in target_commands:
            if target in synced_names:
                print(f"✅ {target} synced successfully")
            else:
                print(f"❌ {target} missing")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    await bot.close()

async def main():
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("❌ No DISCORD_TOKEN found")
        return
    
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())