#!/usr/bin/env python3

import asyncio
import discord
from discord.ext import commands
import sys
import os

# Mock database for testing
class MockDB:
    def __getitem__(self, key):
        return MockCollection()

class MockCollection:
    def find_one(self, query):
        return None
    def insert_one(self, doc):
        pass
    def update_one(self, query, update):
        pass

# Set up environment
os.environ['DISCORD_TOKEN'] = 'fake_token_for_testing'

# Create bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix=None, intents=intents, help_command=None)
bot.db = MockDB()

async def test_all_winners_only():
    """Test loading just the all_winners cog to isolate the issue"""
    try:
        print("🔄 Testing all_winners cog in isolation...")
        
        # Load only the all_winners cog
        await bot.load_extension("cogs.all_winners")
        print("✅ Successfully loaded all_winners cog")
        
        # Check the cog
        all_winners_cog = bot.get_cog('AllWinners')
        if all_winners_cog:
            cog_commands = all_winners_cog.get_app_commands()
            cog_command_names = [cmd.name for cmd in cog_commands]
            print(f"📋 AllWinners cog has {len(cog_commands)} app commands:")
            for cmd_name in cog_command_names:
                print(f"  - {cmd_name}")
            
            # Check for target commands
            target_commands = ['view_general_campaign', 'admin_view_all_campaign_points']
            for target in target_commands:
                if target in cog_command_names:
                    print(f"✅ {target} found in AllWinners cog")
                else:
                    print(f"❌ {target} NOT found in AllWinners cog")
        else:
            print("❌ AllWinners cog not found after loading")
            return
        
        # Check command tree
        tree_commands = bot.tree.get_commands()
        tree_command_names = [cmd.name for cmd in tree_commands]
        print(f"\n🌳 Bot command tree has {len(tree_commands)} commands:")
        for cmd_name in tree_command_names:
            print(f"  - {cmd_name}")
        
        # Check for target commands in tree
        target_commands = ['view_general_campaign', 'admin_view_all_campaign_points']
        for target in target_commands:
            if target in tree_command_names:
                print(f"✅ {target} found in command tree")
            else:
                print(f"❌ {target} NOT found in command tree")
        
        print("\n🎉 Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_all_winners_only())