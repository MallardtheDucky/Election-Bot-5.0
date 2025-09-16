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

class MockDB:
    def __getitem__(self, key):
        return MockCollection()

class MockCollection:
    def find_one(self, query):
        return None

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    
    try:
        # Mock DB to avoid connection issues
        bot.db = MockDB()
        
        # Load only the all_winners cog
        await bot.load_extension("cogs.all_winners")
        print("✅ Loaded all_winners cog")
        
        # Check commands before sync
        before_commands = bot.tree.get_commands()
        print(f"Commands before sync: {[cmd.name for cmd in before_commands]}")
        
        # Clear and sync
        bot.tree.clear_commands(guild=dev_guild)
        await bot.tree.sync(guild=dev_guild)
        print("✅ Cleared commands")
        
        await asyncio.sleep(1)
        
        bot.tree.copy_global_to(guild=dev_guild)
        synced = await bot.tree.sync(guild=dev_guild)
        print(f"Sync returned: {type(synced)}, length: {len(synced) if synced else 'None'}")
        
        if synced:
            print(f"✅ Synced {len(synced)} commands:")
            for cmd in synced:
                print(f"  - {cmd.name}")
        else:
            print("❌ No commands synced")
            
        # Also check what's in the tree now
        after_commands = bot.tree.get_commands()
        print(f"Commands in tree after sync: {[cmd.name for cmd in after_commands]}")
            
        target_commands = ['view_general_campaign', 'admin_view_all_campaign_points']
        synced_names = [cmd.name for cmd in synced] if synced else []
        tree_names = [cmd.name for cmd in bot.tree.get_commands()]
        
        for target in target_commands:
            in_synced = target in synced_names
            in_tree = target in tree_names
            print(f"{target}: synced={in_synced}, in_tree={in_tree}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Script completed")
    
    await bot.close()

async def main():
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("❌ No DISCORD_TOKEN found")
        return
    
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())