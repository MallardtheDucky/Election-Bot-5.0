#!/usr/bin/env python3
"""
Test script to verify command sync functionality without requiring a Discord token
"""

import discord
from discord.ext import commands
import asyncio
import sys
import os

# Mock the database connection
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

async def test_command_sync():
    """Test that commands can be properly registered to the command tree"""
    try:
        # Set up intents
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        
        # Create bot without token
        bot = commands.Bot(command_prefix=None, intents=intents, help_command=None)
        
        # Mock the database
        bot.db = MockDB()
        
        print("Loading AllWinners cog...")
        
        # Load the cog
        await bot.load_extension("cogs.all_winners")
        
        print("✅ AllWinners cog loaded successfully")
        
        # Get all commands from the tree
        tree_commands = bot.tree.get_commands()
        command_names = [cmd.name for cmd in tree_commands]
        
        print(f"Found {len(tree_commands)} commands in command tree:")
        for name in sorted(command_names):
            print(f"  - {name}")
        
        # Check for our target commands
        target_commands = ['admin_view_all_campaign_points', 'view_general_campaign']
        
        print(f"\nChecking for target commands in tree:")
        all_found = True
        for target in target_commands:
            if target in command_names:
                print(f"  ✅ {target} - FOUND in command tree")
            else:
                print(f"  ❌ {target} - MISSING from command tree")
                all_found = False
        
        # Test getting specific commands
        print(f"\nTesting command retrieval:")
        for target in target_commands:
            cmd = bot.tree.get_command(target)
            if cmd:
                print(f"  ✅ {target} - Retrieved successfully")
                print(f"    Type: {type(cmd)}")
                print(f"    Description: {cmd.description}")
            else:
                print(f"  ❌ {target} - Failed to retrieve")
                all_found = False
        
        return all_found
        
    except Exception as e:
        print(f"Error during sync test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("Testing command sync functionality...")
    success = await test_command_sync()
    
    if success:
        print(f"\n✅ SUCCESS: All commands properly registered to command tree!")
        return 0
    else:
        print(f"\n❌ FAILURE: Commands not properly registered!")
        return 1

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)