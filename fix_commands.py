#!/usr/bin/env python3
"""
Simple fix to ensure all_winners commands are properly registered.
This script demonstrates the fix that should be applied to main.py
"""

# The issue is that guild-restricted commands can interfere with global commands.
# Here's the fix to add to main.py after all cogs are loaded:

fix_code = '''
# Add this after all cogs are loaded in main.py:

# Ensure all non-guild-restricted commands are in the global tree
print("SYNC_LOG: Ensuring all global commands are properly registered...")
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
                        print(f"SYNC_LOG: Added missing global command: {cmd.name}")
                except Exception as e:
                    print(f"SYNC_LOG: Failed to add {cmd.name}: {e}")

# Final verification
final_commands = bot.tree.get_commands()
final_command_names = [cmd.name for cmd in final_commands]
print(f"SYNC_LOG: Final global command tree has {len(final_commands)} commands")

target_commands = ['view_general_campaign', 'admin_view_all_campaign_points']
for target in target_commands:
    if target in final_command_names:
        print(f"SYNC_LOG: ✅ {target} confirmed in global tree")
    else:
        print(f"SYNC_LOG: ❌ {target} missing from global tree")
'''

print("Fix code to add to main.py:")
print(fix_code)