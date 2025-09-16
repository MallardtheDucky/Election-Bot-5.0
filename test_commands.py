#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cogs.all_winners import AllWinners
import discord
from discord.ext import commands

# Create a mock bot
class MockBot:
    def __init__(self):
        self.db = {}

# Test if commands are detected
bot = MockBot()
cog = AllWinners(bot)

# Get all app commands from the cog
app_commands = []
for attr_name in dir(cog):
    attr = getattr(cog, attr_name)
    if hasattr(attr, '__discord_app_commands_is_command__'):
        app_commands.append(attr_name)

print(f"Found {len(app_commands)} app commands:")
for cmd in app_commands:
    print(f"  - {cmd}")

# Check if specific commands exist
target_commands = ['view_general_campaign', 'admin_view_all_campaign_points']
for cmd in target_commands:
    if hasattr(cog, cmd):
        method = getattr(cog, cmd)
        print(f"✓ {cmd} exists as method")
        if hasattr(method, '__discord_app_commands_is_command__'):
            print(f"✓ {cmd} is properly decorated as app_command")
        else:
            print(f"❌ {cmd} is NOT decorated as app_command")
    else:
        print(f"❌ {cmd} does not exist")