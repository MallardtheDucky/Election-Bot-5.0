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

async def test_final_fix():
    """Test the final fix with all cogs loaded"""
    try:
        print("🔄 Testing final fix with all cogs...")
        
        # Load all cogs including the problematic ones
        cogs_to_load = [
            "cogs.basics",
            "cogs.setup", 
            "cogs.elections",
            "cogs.polling",
            "cogs.all_signups",
            "cogs.all_winners",  # Our target cog
            "cogs.party_management",
            "cogs.presidential_signups",
            "cogs.ideology",  # This has guild restrictions
            "cogs.general_campaign_actions",
            "cogs.presidential_winners",
            "cogs.endorsements",
            "cogs.delegates",
            "cogs.demographics",
            "cogs.admin_central",
            "cogs.pres_campaign_actions",
            "cogs.special_elections",
            "cogs.momentum"
        ]
        
        for cog_module in cogs_to_load:
            try:
                await bot.load_extension(cog_module)
                print(f"✅ Loaded {cog_module}")
            except Exception as e:
                print(f"❌ Failed to load {cog_module}: {e}")
        
        print("\n📊 Initial command tree check...")
        initial_commands = bot.tree.get_commands()
        initial_command_names = [cmd.name for cmd in initial_commands]
        print(f"Initial tree has {len(initial_commands)} commands")
        
        target_commands = ['view_general_campaign', 'admin_view_all_campaign_points']
        for target in target_commands:
            if target in initial_command_names:
                print(f"✅ {target} found initially")
            else:
                print(f"❌ {target} missing initially")
        
        # Apply the fix: Ensure all non-guild-restricted commands are in the global tree
        print("\n🔧 Applying fix...")
        print("Ensuring all global commands are properly registered...")
        
        for cog_name, cog in bot.cogs.items():
            if hasattr(cog, 'get_app_commands'):
                for cmd in cog.get_app_commands():
                    # Only add commands that don't have guild restrictions
                    if not hasattr(cmd, 'guild_ids') or not cmd.guild_ids:
                        try:
                            # Check if command is already in tree
                            existing_cmd = bot.tree.get_command(cmd.name)
                            if not existing_cmd:
                                bot.tree.add_command(cmd)
                                print(f"Added missing global command: {cmd.name}")
                        except Exception as e:
                            print(f"Failed to add {cmd.name}: {e}")
        
        # Final verification
        print("\n🎯 Final verification...")
        final_commands = bot.tree.get_commands()
        final_command_names = [cmd.name for cmd in final_commands]
        print(f"Final tree has {len(final_commands)} commands")
        
        for target in target_commands:
            if target in final_command_names:
                print(f"✅ {target} confirmed in global tree")
            else:
                print(f"❌ {target} missing from global tree")
        
        if len(final_commands) > 70:
            print("🎉 SUCCESS: Command tree has expected number of commands!")
        else:
            print("⚠️  WARNING: Command tree seems incomplete")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_final_fix())