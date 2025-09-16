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

async def test_cog_loading_sequence():
    """Test loading cogs in sequence to find which one breaks all_winners commands"""
    target_commands = ['view_general_campaign', 'admin_view_all_campaign_points']
    
    try:
        print("🔄 Testing cog loading sequence to find conflicts...")
        
        # First load all_winners to establish baseline
        print("📦 Loading all_winners first (baseline)...")
        await bot.load_extension("cogs.all_winners")
        print("✅ Successfully loaded all_winners")
        
        # Check baseline
        tree_commands = bot.tree.get_commands()
        tree_command_names = [cmd.name for cmd in tree_commands]
        print(f"🌳 Baseline: Command tree has {len(tree_commands)} commands")
        
        for target in target_commands:
            if target in tree_command_names:
                print(f"✅ {target} present in baseline")
            else:
                print(f"❌ {target} missing in baseline")
        
        # Now load other cogs one by one to find the culprit
        cogs_to_test = [
            ("cogs.basics", "basics"),
            ("cogs.setup", "setup"), 
            ("cogs.elections", "elections"),
            ("cogs.polling", "polling"),
            ("cogs.all_signups", "all_signups"),
            ("cogs.party_management", "party_management"),
            ("cogs.presidential_signups", "presidential_signups"),
            ("cogs.ideology", "ideology"),  # Suspect this one
            ("cogs.general_campaign_actions", "general_campaign_actions"),
            ("cogs.presidential_winners", "presidential_winners"),
            ("cogs.endorsements", "endorsements"),
            ("cogs.delegates", "delegates"),
            ("cogs.demographics", "demographics"),
            ("cogs.admin_central", "admin_central"),
            ("cogs.pres_campaign_actions", "pres_campaign_actions"),
            ("cogs.special_elections", "special_elections"),
            ("cogs.momentum", "momentum")
        ]
        
        for cog_module, cog_name in cogs_to_test:
            try:
                print(f"\n📦 Loading {cog_name}...")
                await bot.load_extension(cog_module)
                print(f"✅ Successfully loaded {cog_name}")
                
                # Check command tree after each load
                tree_commands = bot.tree.get_commands()
                tree_command_names = [cmd.name for cmd in tree_commands]
                
                print(f"🌳 Command tree now has {len(tree_commands)} commands")
                
                # Check if our target commands are still there
                missing_commands = []
                for target in target_commands:
                    if target in tree_command_names:
                        print(f"✅ {target} still present")
                    else:
                        print(f"❌ {target} MISSING after loading {cog_name}")
                        missing_commands.append(target)
                
                if missing_commands:
                    print(f"🚨 CONFLICT DETECTED: {cog_name} caused {missing_commands} to disappear!")
                    
                    # Show what commands are in the tree now
                    print(f"Current commands in tree: {tree_command_names}")
                    
                    # Try to identify what happened
                    if len(tree_command_names) < 10:
                        print(f"⚠️  Command tree was drastically reduced to {len(tree_command_names)} commands")
                    
                    break
                    
            except Exception as e:
                print(f"❌ Failed to load {cog_name}: {e}")
                continue
        
        print("\n🎉 Conflict test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_cog_loading_sequence())