import discord
import asyncio
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

### Configuration
TESTING = True  # Set to False for production - shitty code, I know
dev_guild= discord.Object(id=1139705914803359764)  # Replace with your dev guild ID
# Set up intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Create bot
bot = commands.Bot(command_prefix=None, intents=intents, help_command=None)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Log all interactions to track command usage"""
    if interaction.type == discord.InteractionType.application_command:
        command_name = getattr(interaction.command, 'name', 'unknown')
        if command_name in ['view_general_campaign', 'admin_view_all_campaign_points']:
            print(f"SYNC_LOG: Target command /{command_name} invoked by {interaction.user.display_name} ({interaction.user.id})")

@bot.event
async def on_ready():
    print("on_ready event triggered!")

    try:
        if TESTING:
            print("Testing mode: syncing to dev guild...")
            try:
                # Log all commands before syncing
                print("SYNC_LOG: Checking commands before sync...")
                all_commands = bot.tree.get_commands()
                command_names = [cmd.name for cmd in all_commands]
                print(f"SYNC_LOG: Found {len(all_commands)} commands to sync: {command_names}")
                
                # Check specifically for our target commands
                target_commands = ['view_general_campaign', 'admin_view_all_campaign_points']
                for target in target_commands:
                    if target in command_names:
                        print(f"SYNC_LOG: ✅ {target} found in command tree")
                    else:
                        print(f"SYNC_LOG: ❌ {target} NOT found in command tree")
                
                # Sync to dev guild
                bot.tree.copy_global_to(guild=dev_guild)
                synced = await bot.tree.sync(guild=dev_guild)
                print(f"Commands synced to dev guild: {len(synced)} commands")
                
                # Log commands after syncing
                synced_commands = bot.tree.get_commands()
                synced_names = [cmd.name for cmd in synced_commands]
                print(f"SYNC_LOG: After sync - {len(synced_commands)} commands available: {synced_names}")
            except discord.Forbidden:
                print("Warning: Missing permissions to sync commands to dev guild. Bot will work without slash commands.")
        else:
            print("Production mode: syncing globally...")
            try:
                # Log all commands before syncing
                print("SYNC_LOG: Checking global commands before sync...")
                all_commands = bot.tree.get_commands()
                command_names = [cmd.name for cmd in all_commands]
                print(f"SYNC_LOG: Found {len(all_commands)} global commands to sync: {command_names}")
                
                # Check specifically for our target commands
                target_commands = ['view_general_campaign', 'admin_view_all_campaign_points']
                for target in target_commands:
                    if target in command_names:
                        print(f"SYNC_LOG: ✅ {target} found in global command tree")
                    else:
                        print(f"SYNC_LOG: ❌ {target} NOT found in global command tree")
                
                # sync globally (can take up to 1 hour, slash commands suck)
                synced = await bot.tree.sync()
                print(f"Commands synced globally successfully: {len(synced)} commands")
            except discord.Forbidden:
                print("Warning: Missing permissions to sync commands globally. Bot will work without slash commands.")

        print(f"Logged in as {bot.user} (ID: {bot.user.id})")
        print("------")
        print("Bot is ready and all commands are synced!")
        print("SYNC_LOG: Bot startup complete - target endpoints should now be available")
        print("SYNC_LOG: Monitoring for command invocations...")
        
        # Check bot permissions in guild
        if TESTING:
            guild = bot.get_guild(dev_guild.id)
            if guild:
                bot_member = guild.get_member(bot.user.id)
                if bot_member:
                    perms = bot_member.guild_permissions
                    print(f"SYNC_LOG: Bot permissions in '{guild.name}':")
                    print(f"  - Use Slash Commands: {perms.use_slash_commands}")
                    print(f"  - Administrator: {perms.administrator}")
                    print(f"  - Manage Guild: {perms.manage_guild}")
                    
                    if not perms.use_slash_commands and not perms.administrator:
                        print("SYNC_LOG: ❌ Bot missing 'Use Slash Commands' permission!")
                        print("SYNC_LOG: Grant the bot 'Use Slash Commands' permission or Administrator role")
                else:
                    print(f"SYNC_LOG: Bot member not found in guild {guild.name}")
            else:
                print(f"SYNC_LOG: Guild {dev_guild.id} not found")
        
        # Test if commands are accessible (skip if missing permissions)
        try:
            if TESTING:
                guild_commands = await bot.tree.fetch_commands(guild=dev_guild)
            else:
                guild_commands = await bot.tree.fetch_commands()
            
            fetched_names = [cmd.name for cmd in guild_commands]
            print(f"SYNC_LOG: Fetched {len(guild_commands)} commands from Discord: {fetched_names}")
            
            target_commands = ['view_general_campaign', 'admin_view_all_campaign_points']
            for target in target_commands:
                if target in fetched_names:
                    print(f"SYNC_LOG: ✅ {target} confirmed synced to Discord")
                else:
                    print(f"SYNC_LOG: ❌ {target} NOT synced to Discord")
        except discord.Forbidden as forbidden_error:
            print(f"SYNC_LOG: 403 Forbidden - Bot lacks permissions: {forbidden_error}")
        except Exception as fetch_error:
            print(f"SYNC_LOG: Error fetching commands from Discord: {fetch_error}")

    except Exception as e:
        print(f"Error in on_ready: {e}")
        print(f"SYNC_LOG: on_ready error: {e}")
        import traceback
        traceback.print_exc()

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Handle application command errors"""
    command_name = getattr(interaction.command, 'name', 'unknown')
    print(f"SYNC_LOG: Command error for /{command_name}: {error}")
    
    try:
        if interaction.response.is_done():
            await interaction.followup.send(f"❌ An error occurred: {str(error)}", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ An error occurred: {str(error)}", ephemeral=True)
    except discord.HTTPException:
        pass  # Ignore if interaction is already handled
    print(f"Command error: {error}")



@bot.tree.command(name="debug_commands", description="Debug command sync issues (Admin only)")
@discord.app_commands.checks.has_permissions(administrator=True)
async def debug_commands(interaction: discord.Interaction):
    """Debug command to check command sync status"""
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Check local command tree
        local_commands = bot.tree.get_commands()
        local_names = [cmd.name for cmd in local_commands]
        
        # Check Discord's view of commands
        if TESTING:
            discord_commands = await bot.tree.fetch_commands(guild=dev_guild)
        else:
            discord_commands = await bot.tree.fetch_commands()
        discord_names = [cmd.name for cmd in discord_commands]
        
        # Check specific commands
        target_commands = ['view_general_campaign', 'admin_view_all_campaign_points']
        
        embed = discord.Embed(
            title="🔧 Command Sync Debug",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📋 Local Command Tree",
            value=f"**Count:** {len(local_commands)}\n**Commands:** {', '.join(local_names[:10])}{'...' if len(local_names) > 10 else ''}",
            inline=False
        )
        
        embed.add_field(
            name="🌐 Discord Commands",
            value=f"**Count:** {len(discord_commands)}\n**Commands:** {', '.join(discord_names[:10])}{'...' if len(discord_names) > 10 else ''}",
            inline=False
        )
        
        # Check target commands
        status_text = ""
        for cmd in target_commands:
            local_status = "✅" if cmd in local_names else "❌"
            discord_status = "✅" if cmd in discord_names else "❌"
            status_text += f"**{cmd}:** Local {local_status} | Discord {discord_status}\n"
        
        embed.add_field(
            name="🎯 Target Commands Status",
            value=status_text,
            inline=False
        )
        
        # Check cog status
        all_winners_cog = bot.get_cog('AllWinners')
        if all_winners_cog:
            cog_commands = all_winners_cog.get_app_commands()
            cog_names = [cmd.name for cmd in cog_commands]
            embed.add_field(
                name="🔧 AllWinners Cog",
                value=f"**Status:** Loaded ✅\n**Commands:** {len(cog_commands)}\n**Names:** {', '.join(cog_names)}",
                inline=False
            )
        else:
            embed.add_field(
                name="🔧 AllWinners Cog",
                value="**Status:** Not Found ❌",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Debug error: {str(e)}", ephemeral=True)



async def main():
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("Please set the DISCORD_TOKEN environment variable.")
        return

    async with bot: #load cogs here
        try:
            print("Loading cogs...")
            await bot.load_extension("cogs.db")
            print("✓ Loaded db")
            await bot.load_extension("cogs.basics")
            print("✓ Loaded basics")
            await bot.load_extension("cogs.setup")
            print("✓ Loaded setup")
            await bot.load_extension("cogs.time_manager")
            print("✓ Loaded time_manager")
            await bot.load_extension("cogs.elections")
            print("✓ Loaded elections")
            await bot.load_extension("cogs.polling")
            print("✓ Loaded polling")
            await bot.load_extension("cogs.all_signups")
            print("✓ Loaded all_signups")
            await bot.load_extension("cogs.all_winners")
            print("✓ Loaded all_winners")
            print("SYNC_LOG: all_winners cog loaded - checking for target commands...")
            
            # Check if the cog has our target commands
            all_winners_cog = bot.get_cog('AllWinners')
            if all_winners_cog:
                cog_commands = all_winners_cog.get_app_commands()
                cog_command_names = [cmd.name for cmd in cog_commands]
                print(f"SYNC_LOG: AllWinners cog has {len(cog_commands)} app commands: {cog_command_names}")
                
                target_commands = ['view_general_campaign', 'admin_view_all_campaign_points']
                for target in target_commands:
                    if target in cog_command_names:
                        print(f"SYNC_LOG: ✅ {target} found in AllWinners cog")
                    else:
                        print(f"SYNC_LOG: ❌ {target} NOT found in AllWinners cog")
            else:
                print("SYNC_LOG: ❌ AllWinners cog not found after loading")
            
            # Check command tree after all_winners load
            tree_commands_after_winners = bot.tree.get_commands()
            tree_names_after_winners = [cmd.name for cmd in tree_commands_after_winners]
            print(f"SYNC_LOG: Command tree after all_winners: {len(tree_commands_after_winners)} commands: {tree_names_after_winners}")
            
            # Ensure all_winners commands are in the global tree
            if all_winners_cog:
                for cmd in all_winners_cog.get_app_commands():
                    if cmd.name in ['view_general_campaign', 'admin_view_all_campaign_points']:
                        existing_cmd = bot.tree.get_command(cmd.name)
                        if not existing_cmd:
                            print(f"SYNC_LOG: Manually adding {cmd.name} to command tree")
                            bot.tree.add_command(cmd)
                        else:
                            print(f"SYNC_LOG: {cmd.name} already in command tree")
            
            # Final check of command tree before pres_campaign_actions loads
            pre_pres_commands = bot.tree.get_commands()
            pre_pres_names = [cmd.name for cmd in pre_pres_commands]
            print(f"SYNC_LOG: Commands in tree before pres_campaign_actions: {pre_pres_names}")
            
            target_commands = ['view_general_campaign', 'admin_view_all_campaign_points']
            for target in target_commands:
                if target in pre_pres_names:
                    print(f"SYNC_LOG: ✅ {target} confirmed before pres_campaign_actions")
                else:
                    print(f"SYNC_LOG: ❌ {target} missing before pres_campaign_actions")
            await bot.load_extension("cogs.party_management")
            print("✓ Loaded party_management")
            await bot.load_extension("cogs.presidential_signups")
            print("✓ Loaded presidential_signups_actions")
            await bot.load_extension("cogs.ideology")
            print("✓ Loaded ideology")
            
            # Check command tree after ideology load
            tree_commands_after_ideology = bot.tree.get_commands()
            tree_names_after_ideology = [cmd.name for cmd in tree_commands_after_ideology]
            print(f"SYNC_LOG: Command tree after ideology: {len(tree_commands_after_ideology)} commands: {tree_names_after_ideology}")
            
            target_commands = ['view_general_campaign', 'admin_view_all_campaign_points']
            for target in target_commands:
                if target in tree_names_after_ideology:
                    print(f"SYNC_LOG: ✅ {target} still in tree after ideology")
                else:
                    print(f"SYNC_LOG: ❌ {target} LOST after ideology load")
            await bot.load_extension("cogs.general_campaign_actions")
            print("✓ Loaded general_campaign_actions")
            await bot.load_extension("cogs.presidential_winners")
            print("✓ Loaded presidential_winners")
            await bot.load_extension("cogs.endorsements")
            print("✓ Loaded endorsements")
            await bot.load_extension("cogs.delegates")
            print("✓ Loaded delegates")
            await bot.load_extension("cogs.demographics")
            print("✓ Loaded demographics")
            await bot.load_extension("cogs.admin_central")
            print("✓ Loaded admin_central")
            await bot.load_extension("cogs.pres_campaign_actions")
            print("✓ Loaded pres_campaign_actions")
            await bot.load_extension("cogs.special_elections")
            print("✓ Loaded special_elections")
            await bot.load_extension("cogs.momentum")
            print("✓ Loaded momentum")
            print("All cogs loaded successfully!")
            print("SYNC_LOG: All cogs loaded - final command tree check...")
            
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
            
            # Final check of all commands in the tree
            # Always use global commands for the final check
            final_commands = bot.tree.get_commands()
            
            final_command_names = [cmd.name for cmd in final_commands]
            print(f"SYNC_LOG: Final command tree has {len(final_commands)} commands: {final_command_names}")
            
            target_commands = ['view_general_campaign', 'admin_view_all_campaign_points']
            missing_commands = []
            for target in target_commands:
                if target in final_command_names:
                    print(f"SYNC_LOG: ✅ {target} is ready for sync")
                else:
                    print(f"SYNC_LOG: ❌ {target} is missing from final command tree")
                    missing_commands.append(target)
                    
            # Final verification
            print(f"SYNC_LOG: Final verification - Global tree has {len(final_commands)} commands")
            for target in target_commands:
                if target in final_command_names:
                    print(f"SYNC_LOG: ✅ {target} confirmed in global tree")
                else:
                    print(f"SYNC_LOG: ❌ {target} missing from global tree")
            
            # Commands will be synced in on_ready event after bot connects
            print("SYNC_LOG: All cogs loaded - commands will sync when bot connects")
            
        except Exception as e:
            print(f"Error loading cogs: {e}")
            import traceback
            traceback.print_exc()
            return
        # Start the bot
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())