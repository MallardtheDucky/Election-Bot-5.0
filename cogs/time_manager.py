import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import pytz

class TimeManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.time_loop.start()  # Start the time loop
        print("Time Manager cog loaded successfully")

    # Create main time group
    time_group = app_commands.Group(name="time", description="Time management commands")

    # Create admin subgroup for time commands
    time_admin_group = app_commands.Group(name="admin", description="Admin time commands", parent=time_group)

    def cog_unload(self):
        self.time_loop.cancel()

    def _get_time_config(self, guild_id: int):
        """Get or create time configuration for a guild"""
        col = self.bot.db["time_configs"]
        config = col.find_one({"guild_id": guild_id})
        if not config:
            config = {
                "guild_id": guild_id,
                "minutes_per_rp_day": 28,  # Default: 28 minutes = 1 RP day
                "current_rp_date": datetime(1999, 2, 1),  # Start at signups phase
                "current_phase": "Signups",
                "cycle_year": 1999,
                "last_real_update": datetime.utcnow(),
                "last_stamina_regen": datetime(1999, 1, 1),  # Track last stamina regeneration
                "voice_channel_id": None,  # Specific voice channel to update
                "update_voice_channels": True,  # Enable voice updates by default
                "time_paused": False,  # Whether time progression is paused
                "phases": [
                    {"name": "Signups", "start_month": 2, "end_month": 8},
                    {"name": "Primary Campaign", "start_month": 9, "end_month": 12},
                    {"name": "Primary Election", "start_month": 1, "end_month": 2},
                    {"name": "General Campaign", "start_month": 3, "end_month": 10},
                    {"name": "General Election", "start_month": 11, "end_month": 12}
                ],
                "regions": [
                    "Columbia", "Cambridge", "Superior", "Austin", 
                    "Heartland", "Yellowstone", "Phoenix"
                ]
            }
            col.insert_one(config)
        return config

    def _calculate_current_rp_time(self, config):
        """Calculate current RP time based on real time elapsed"""
        last_update = config["last_real_update"]
        current_real_time = datetime.utcnow()
        real_minutes_elapsed = (current_real_time - last_update).total_seconds() / 60

        minutes_per_rp_day = config["minutes_per_rp_day"]
        rp_days_elapsed = real_minutes_elapsed / minutes_per_rp_day

        current_rp_date = config["current_rp_date"] + timedelta(days=rp_days_elapsed)

        # Determine current phase
        current_phase = self._get_current_phase(current_rp_date, config)

        return current_rp_date, current_phase

    def _get_current_phase(self, rp_date, config):
        """Determine which phase we're currently in"""
        month = rp_date.month
        year = rp_date.year

        # Determine if this is a primary year (odd) or general year (even)
        is_primary_year = year % 2 == 1  # Odd years are primary years
        is_general_year = year % 2 == 0  # Even years are general years

        for phase in config["phases"]:
            if phase["name"] in ["Signups", "Primary Campaign"] and is_primary_year:
                # Signups and Primary Campaign occur in odd years
                if month >= phase["start_month"] and month <= phase["end_month"]:
                    return phase["name"]
            elif phase["name"] in ["Primary Election", "General Campaign", "General Election"] and is_general_year:
                # Primary Election, General Campaign, and General Election occur in even years  
                if month >= phase["start_month"] and month <= phase["end_month"]:
                    return phase["name"]

        return "Between Phases"

    async def _reset_stamina_for_general_campaign(self, guild_id: int, year: int):
        """Resets stamina for all players in the general campaign phase."""
        # Reset general election candidates to 100 stamina
        signups_col = self.bot.db["all_signups"]
        signups_result = signups_col.update_many(
            {"guild_id": guild_id, "candidates.year": year},
            {"$set": {"candidates.$.stamina": 100}}
        )

        # Reset presidential candidates to 300 stamina
        pres_col = self.bot.db["presidential_signups"]
        pres_result = pres_col.update_many(
            {"guild_id": guild_id, "candidates.year": year},
            {"$set": {"candidates.$.stamina": 300}}
        )

        # Reset presidential winners to 300 stamina
        winners_col = self.bot.db["presidential_winners"]
        winners_result = winners_col.update_many(
            {"guild_id": guild_id, "winners.year": year},
            {"$set": {"winners.$.stamina": 300}}
        )

        print(f"Reset stamina for guild {guild_id} in year {year}: {signups_result.modified_count} general candidates, {pres_result.modified_count} presidential candidates, {winners_result.modified_count} presidential winners.")

    async def _regenerate_daily_stamina(self, guild_id: int):
        """Regenerate stamina for all candidates daily"""
        # Regenerate stamina for general election candidates in signups (30 per day, max 100)
        signups_col = self.bot.db["signups"]
        signups_config = signups_col.find_one({"guild_id": guild_id})

        if signups_config:
            for i, candidate in enumerate(signups_config.get("candidates", [])):
                current_stamina = candidate.get("stamina", 100)
                new_stamina = min(100, current_stamina + 30)  # Add 30, cap at 100

                signups_col.update_one(
                    {"guild_id": guild_id, f"candidates.{i}.user_id": candidate["user_id"]},
                    {"$set": {f"candidates.{i}.stamina": new_stamina}}
                )

        # Regenerate stamina for general winners (30 per day, max 100)
        winners_col = self.bot.db["winners"]
        winners_config = winners_col.find_one({"guild_id": guild_id})

        if winners_config:
            for i, winner in enumerate(winners_config.get("winners", [])):
                current_stamina = winner.get("stamina", 100)
                new_stamina = min(100, current_stamina + 30)  # Add 30, cap at 100

                winners_col.update_one(
                    {"guild_id": guild_id, f"winners.{i}.user_id": winner["user_id"]},
                    {"$set": {f"winners.{i}.stamina": new_stamina}}
                )

        # Regenerate stamina for presidential candidates (100 per day, max 300)
        pres_col = self.bot.db["presidential_signups"]
        pres_config = pres_col.find_one({"guild_id": guild_id})

        if pres_config:
            for i, candidate in enumerate(pres_config.get("candidates", [])):
                current_stamina = candidate.get("stamina", 300)
                new_stamina = min(300, current_stamina + 100)  # Add 100, cap at 300

                pres_col.update_one(
                    {"guild_id": guild_id, f"candidates.{i}.user_id": candidate["user_id"]},
                    {"$set": {f"candidates.{i}.stamina": new_stamina}}
                )

        # Regenerate stamina for presidential winners (100 per day, max 300)
        pres_winners_col = self.bot.db["presidential_winners"]
        pres_winners_config = pres_winners_col.find_one({"guild_id": guild_id})

        if pres_winners_config:
            # Handle winners stored as dictionary (party -> candidate name)
            winners_dict = pres_winners_config.get("winners", {})
            if isinstance(winners_dict, dict):
                # For dictionary format, we need to find candidates in presidential_signups
                for party, winner_name in winners_dict.items():
                    # Find the candidate in presidential signups to get their user_id
                    if pres_config:
                        for i, candidate in enumerate(pres_config.get("candidates", [])):
                            if (candidate.get("name") == winner_name and 
                                candidate.get("office") == "President"):
                                current_stamina = candidate.get("stamina", 300)
                                new_stamina = min(300, current_stamina + 100)

                                pres_col.update_one(
                                    {"guild_id": guild_id, f"candidates.{i}.user_id": candidate["user_id"]},
                                    {"$set": {f"candidates.{i}.stamina": new_stamina}}
                                )
            else:
                # Handle array format if exists
                for i, winner in enumerate(winners_dict):
                    if winner.get("office") in ["President", "Vice President"]:
                        current_stamina = winner.get("stamina", 300)
                        new_stamina = min(300, current_stamina + 100)

                        pres_winners_col.update_one(
                            {"guild_id": guild_id, f"winners.{i}.user_id": winner["user_id"]},
                            {"$set": {f"winners.{i}.stamina": new_stamina}}
                        )


    @tasks.loop(minutes=1)
    async def time_loop(self):
        """Update RP time every minute"""
        try:
            col = self.bot.db["time_configs"]
            configs = col.find({})

            for config in configs:
                # Skip time progression if paused
                if config.get("time_paused", False):
                    continue

                current_rp_date, current_phase = self._calculate_current_rp_time(config)
                guild = self.bot.get_guild(config["guild_id"])

                if not guild:
                    continue

                # Check if phase changed
                if current_phase != config["current_phase"]:
                    # Phase transition occurred
                    old_phase = config["current_phase"]
                    print(f"DEBUG: ACTUAL phase change detected for guild {guild.id}: {old_phase} -> {current_phase}")

                    # Update the phase in the database immediately to prevent duplicate events
                    col.update_one(
                        {"guild_id": config["guild_id"]},
                        {"$set": {"current_phase": current_phase}}
                    )

                    # Reset stamina when transitioning to General Campaign
                    if current_phase == "General Campaign":
                        await self._reset_stamina_for_general_campaign(config["guild_id"], current_rp_date.year)

                    # Dispatch event to elections cog for automatic handling
                    elections_cog = self.bot.get_cog("Elections")
                    if elections_cog:
                        await elections_cog.on_phase_change(
                            config["guild_id"], 
                            old_phase, 
                            current_phase, 
                            current_rp_date.year
                        )

                    # Dispatch event to all_winners cog for automatic handling
                    all_winners_cog = self.bot.get_cog("AllWinners")
                    if all_winners_cog:
                        await all_winners_cog.on_phase_change(
                            config["guild_id"], 
                            old_phase, 
                            current_phase, 
                            current_rp_date.year
                        )

                    # Dispatch event to presidential_winners cog for automatic handling
                    pres_winners_cog = self.bot.get_cog("PresidentialWinners")
                    if pres_winners_cog:
                        await pres_winners_cog.on_phase_change(
                            config["guild_id"], 
                            old_phase, 
                            current_phase, 
                            current_rp_date.year
                        )

                    # DEBUG: Only allow the specific channel ID for phase change announcements
                    REQUIRED_CHANNEL_ID = 1380498828121346210
                    print(f"DEBUG: Phase change announcement for guild {guild.id}, phase: {current_phase}")
                    
                    # Find announcement channel - only use the specific channel ID
                    channel = None
                    
                    # Check guild_configs for announcement channel
                    setup_col = self.bot.db["guild_configs"]
                    setup_config = setup_col.find_one({"guild_id": guild.id})
                    
                    # Check announcement_channel_id first
                    if setup_config and setup_config.get("announcement_channel_id"):
                        configured_channel_id = setup_config["announcement_channel_id"]
                        print(f"DEBUG: Found configured announcement_channel_id: {configured_channel_id}")
                        
                        # Only use the specific channel ID
                        if configured_channel_id == REQUIRED_CHANNEL_ID:
                            channel = guild.get_channel(configured_channel_id)
                            print(f"DEBUG: Using configured channel {channel} (ID: {configured_channel_id})")
                        else:
                            print(f"DEBUG: WARNING - Configured channel ID {configured_channel_id} is not the required channel {REQUIRED_CHANNEL_ID}")
                            print(f"DEBUG: Falling back to required channel {REQUIRED_CHANNEL_ID}")
                    
                    # Check announcement_channel (legacy support)
                    if not channel and setup_config and setup_config.get("announcement_channel"):
                        legacy_channel_id = setup_config["announcement_channel"]
                        print(f"DEBUG: Found legacy announcement_channel: {legacy_channel_id}")
                        
                        # Only use the specific channel ID
                        if legacy_channel_id == REQUIRED_CHANNEL_ID:
                            channel = guild.get_channel(legacy_channel_id)
                            print(f"DEBUG: Using legacy channel {channel} (ID: {legacy_channel_id})")
                        else:
                            print(f"DEBUG: WARNING - Legacy channel ID {legacy_channel_id} is not the required channel {REQUIRED_CHANNEL_ID}")

                    # Always try to use the required channel ID as fallback
                    if not channel:
                        channel = guild.get_channel(REQUIRED_CHANNEL_ID)
                        if channel:
                            print(f"DEBUG: Using fallback required channel {channel} (ID: {REQUIRED_CHANNEL_ID})")
                        else:
                            print(f"DEBUG: ERROR - Required channel {REQUIRED_CHANNEL_ID} not found in guild {guild.id}")
                            print(f"DEBUG: Setup config: {setup_config}")
                            return
                    
                    if channel:
                        embed = discord.Embed(
                            title="🗳️ Election Phase Change",
                            description=f"We have entered the **{current_phase}** phase!",
                            color=discord.Color.green(),
                            timestamp=datetime.utcnow()
                        )
                        embed.add_field(
                            name="Current RP Date", 
                            value=current_rp_date.strftime("%B %d, %Y"), 
                            inline=True
                        )
                        try:
                            await channel.send(embed=embed)
                            print(f"DEBUG: Phase change announcement sent to channel {channel.name} (ID: {channel.id})")
                        except Exception as e:
                            print(f"DEBUG: Failed to send phase change announcement: {e}")
                            pass  # Ignore if can't send message
                else:
                    # No phase change - just log for debugging
                    print(f"DEBUG: No phase change for guild {guild.id}, current phase: {current_phase}")

                # Check if 24 hours have passed for stamina regeneration
                last_stamina_regen = config.get("last_stamina_regen", datetime(1999, 1, 1))
                current_time = datetime.utcnow()
                hours_since_last_regen = (current_time - last_stamina_regen).total_seconds() / 3600

                if hours_since_last_regen >= 24:
                    # 24 hours have passed - regenerate stamina
                    await self._regenerate_daily_stamina(config["guild_id"])

                    # Update last regeneration time
                    col.update_one(
                        {"guild_id": config["guild_id"]},
                        {"$set": {"last_stamina_regen": current_time}}
                    )

                    print(f"Regenerated daily stamina for guild {config['guild_id']} after {hours_since_last_regen:.1f} hours")

                # Update database (phase already updated if it changed)
                col.update_one(
                    {"guild_id": config["guild_id"]},
                    {
                        "$set": {
                            "current_rp_date": current_rp_date,
                            "last_real_update": datetime.utcnow()
                        }
                    }
                )

                # Check if we need to auto-reset cycle (after General Election ends)
                if (current_phase == "General Election" and 
                    current_rp_date.month == 12 and current_rp_date.day >= 31):
                    # Auto-reset to next cycle (next odd year for signups)
                    next_year = current_rp_date.year + 1
                    new_rp_date = datetime(next_year, 2, 1)

                    col.update_one(
                        {"guild_id": config["guild_id"]},
                        {
                            "$set": {
                                "current_rp_date": new_rp_date,
                                "current_phase": "Signups",
                                "last_real_update": datetime.utcnow()
                            }
                        }
                    )

                    # Dispatch event to elections cog for new cycle automation
                    elections_cog = self.bot.get_cog("Elections")
                    if elections_cog:
                        await elections_cog.on_phase_change(
                            config["guild_id"], 
                            "General Election", 
                            "Signups", 
                            next_year
                        )

                    # Dispatch event to all_winners cog for new cycle automation
                    all_winners_cog = self.bot.get_cog("AllWinners")
                    if all_winners_cog:
                        await all_winners_cog.on_phase_change(
                            config["guild_id"], 
                            "General Election", 
                            "Signups", 
                            next_year
                        )

                    # Dispatch event to presidential_winners cog for new cycle automation
                    pres_winners_cog = self.bot.get_cog("PresidentialWinners")
                    if pres_winners_cog:
                        await pres_winners_cog.on_phase_change(
                            config["guild_id"], 
                            "General Election", 
                            "Signups", 
                            next_year
                        )

                    # Announce new cycle
                    channel = discord.utils.get(guild.channels, name="general") or guild.system_channel
                    if channel:
                        embed = discord.Embed(
                            title="🔄 New Election Cycle Started!",
                            description=f"The {next_year} election cycle has begun! We are now in the **Signups** phase.",
                            color=discord.Color.gold(),
                            timestamp=datetime.utcnow()
                        )
                        embed.add_field(
                            name="New RP Date", 
                            value=new_rp_date.strftime("%B %d, %Y"), 
                            inline=True
                        )
                        try:
                            await channel.send(embed=embed)
                        except:
                            pass

                # Update voice channel if enabled and configured
                if (config.get("update_voice_channels", True) and 
                    config.get("voice_channel_id")):
                    date_string = current_rp_date.strftime("%B %d, %Y")
                    channel = guild.get_channel(config["voice_channel_id"])
                    if channel and hasattr(channel, 'edit'):  # Check if it's a voice channel
                        try:
                            new_name = f"📅 {date_string}"
                            # Force update if names don't match or if there's a significant time difference
                            current_name = channel.name
                            should_update = (current_name != new_name or 
                                           not current_name.startswith("📅") or
                                           "1999" not in current_name)

                            if should_update:
                                await channel.edit(name=new_name)
                                print(f"Updated voice channel from '{current_name}' to: {new_name}")
                        except Exception as e:
                            print(f"Failed to update voice channel: {e}")
                            # Try again in next loop iteration
                            pass

        except Exception as e:
            print(f"Error in time loop: {e}")

    @time_loop.before_loop
    async def before_time_loop(self):
        await self.bot.wait_until_ready()


    @app_commands.checks.has_permissions(administrator=True)
    @time_admin_group.command( # Changed to time_admin_group
        name="set_current_time",
        description="Set the current RP date and time"
    )
    async def set_current_time(
        self, 
        interaction: discord.Interaction, 
        year: int, 
        month: int, 
        day: int = 1
    ):
        # Validate input
        if month < 1 or month > 12:
            await interaction.response.send_message(
                "❌ Month must be between 1 and 12.", 
                ephemeral=True
            )
            return

        if day < 1 or day > 31:
            await interaction.response.send_message(
                "❌ Day must be between 1 and 31.", 
                ephemeral=True
            )
            return

        try:
            new_date = datetime(year, month, day)
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid date provided.", 
                ephemeral=True
            )
            return

        config = self._get_time_config(interaction.guild.id)
        col = self.bot.db["time_configs"]

        # Determine the new phase
        new_phase = self._get_current_phase(new_date, config)

        # Update the configuration
        col.update_one(
            {"guild_id": interaction.guild.id},
            {
                "$set": {
                    "current_rp_date": new_date,
                    "current_phase": new_phase,
                    "last_real_update": datetime.utcnow()
                }
            }
        )

        embed = discord.Embed(
            title="🕒 RP Time Updated",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(
            name="New RP Date", 
            value=new_date.strftime("%B %d, %Y"), 
            inline=True
        )
        embed.add_field(name="Current Phase", value=new_phase, inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.checks.has_permissions(administrator=True)
    @time_admin_group.command( # Changed to time_admin_group
        name="set_time_scale",
        description="Set how many real minutes equal one RP day"
    )
    async def set_time_scale(
        self, 
        interaction: discord.Interaction, 
        minutes_per_day: int
    ):
        if minutes_per_day < 1 or minutes_per_day > 1440:
            await interaction.response.send_message(
                "❌ Minutes per day must be between 1 and 1440.", 
                ephemeral=True
            )
            return

        config = self._get_time_config(interaction.guild.id)
        col = self.bot.db["time_configs"]

        # Update current time before changing scale
        current_rp_date, current_phase = self._calculate_current_rp_time(config)

        col.update_one(
            {"guild_id": interaction.guild.id},
            {
                "$set": {
                    "minutes_per_rp_day": minutes_per_day,
                    "current_rp_date": current_rp_date,
                    "current_phase": current_phase,
                    "last_real_update": datetime.utcnow()
                }
            }
        )

        await interaction.response.send_message(
            f"✅ Time scale updated: {minutes_per_day} real minutes = 1 RP day",
            ephemeral=True
        )

    @app_commands.checks.has_permissions(administrator=True)
    @time_admin_group.command( # Changed to time_admin_group
        name="reset_cycle",
        description="Reset the election cycle to the beginning (Signups phase)"
    )
    async def reset_cycle(self, interaction: discord.Interaction):
        config = self._get_time_config(interaction.guild.id)
        col = self.bot.db["time_configs"]

        current_year = config["current_rp_date"].year
        # Find next odd year for signups
        next_signup_year = current_year + 1 if current_year % 2 == 0 else current_year + 2

        col.update_one(
            {"guild_id": interaction.guild.id},
            {
                "$set": {
                    "current_rp_date": datetime(next_signup_year, 2, 1),
                    "current_phase": "Signups",
                    "cycle_year": next_signup_year,
                    "last_real_update": datetime.utcnow()
                }
            }
        )

        await interaction.response.send_message(
            f"✅ Election cycle reset! Now in Signups phase for {next_signup_year} cycle.",
            ephemeral=True
        )

    @app_commands.command(
        name="show_regions",
        description="Show all available election regions"
    )
    async def show_regions(self, interaction: discord.Interaction):
        # Get regions from election configuration
        elections_col = self.bot.db["elections_config"]
        elections_config = elections_col.find_one({"guild_id": interaction.guild.id})

        if not elections_config:
            await interaction.response.send_message("❌ Election system not initialized. Use `/election info show_seats` to initialize.", ephemeral=True)
            return

        # Get regions from the elections config or extract unique states/regions from election seats
        regions = elections_config.get("regions")
        if not regions:
            regions = set()
            for seat in elections_config.get("seats", []):
                regions.add(seat["state"])
            regions = sorted(list(regions))

        if not regions:
            await interaction.response.send_message("❌ No election regions configured yet.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🗺️ Election Regions",
            description="\n".join([f"• {region}" for region in regions]),
            color=discord.Color.blue()
        )

        # Add seat count for each region
        region_counts = {}
        for seat in elections_config["seats"]:
            state = seat["state"]
            region_counts[state] = region_counts.get(state, 0) + 1

        details = ""
        for region in regions:
            details += f"**{region}**: {region_counts.get(region, 0)} seats\n"

        embed.add_field(
            name="📊 Seat Distribution",
            value=details,
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="show_phases",
        description="Show all election phases and their timing"
    )
    async def show_phases(self, interaction: discord.Interaction):
        col = self.bot.db["time_configs"]

        # Always get the latest config from database to ensure we show updated phases
        config = col.find_one({"guild_id": interaction.guild.id})
        if not config:
            # If no config exists, create one using _get_time_config
            config = self._get_time_config(interaction.guild.id)

        # Debug: Print what phases are actually in the config
        print(f"DEBUG - Guild ID: {interaction.guild.id}")
        print(f"DEBUG - Config found in DB: {config is not None}")
        print(f"DEBUG - Full config phases: {config.get('phases', [])}")

        # Force check if phases are still wrong
        signups_phase = None
        for phase in config.get('phases', []):
            print(f"  DEBUG - {phase['name']}: {phase['start_month']}-{phase['end_month']}")
            if phase['name'] == 'Signups':
                signups_phase = phase

        # If Signups phase is still wrong, force update it
        if signups_phase and signups_phase['end_month'] == 7:
            print("DEBUG - Found old Signups phase (2-7), force updating to (2-8)")
            # Force update the phases in database
            new_phases = [
                {"name": "Signups", "start_month": 2, "end_month": 8},
                {"name": "Primary Campaign", "start_month": 9, "end_month": 12},
                {"name": "Primary Election", "start_month": 1, "end_month": 2},
                {"name": "General Campaign", "start_month": 3, "end_month": 10},
                {"name": "General Election", "start_month": 11, "end_month": 12}
            ]
            col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"phases": new_phases}}
            )
            # Fetch the updated config
            config = col.find_one({"guild_id": interaction.guild.id})
            print(f"DEBUG - After force update, Signups phase: {[p for p in config['phases'] if p['name'] == 'Signups'][0]}")

        current_rp_date, current_phase = self._calculate_current_rp_time(config)

        embed = discord.Embed(
            title="🗓️ Current Election Phase",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        # Add current date and phase
        embed.add_field(
            name="Current Date", 
            value=current_rp_date.strftime("%B %d, %Y"), 
            inline=True
        )
        embed.add_field(
            name="Current Phase", 
            value=current_phase, 
            inline=True
        )
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Empty field for spacing

        # Add cycle schedule
        current_year = current_rp_date.year
        schedule_text = "📋 **Annual Election Cycle**\n\n"

        # Show current and next year phases
        for year_offset in [0, 1]:
            year = current_year + year_offset
            is_primary_year = year % 2 == 1
            is_general_year = year % 2 == 0

            if is_primary_year:
                year_phases = [p for p in config["phases"] if p["name"] in ["Signups", "Primary Campaign"]]
                schedule_text += f"**{year} (Primary Year)**\n"
            else:
                year_phases = [p for p in config["phases"] if p["name"] in ["Primary Election", "General Campaign", "General Election"]]
                schedule_text += f"**{year} (General Year)**\n"

            for phase in year_phases:
                if phase["name"] == current_phase and year == current_year:
                    phase_line = f"📍 {phase['name']} ⬅️ Current\n"
                else:
                    phase_line = f"{phase['name']}\n"
                phase_line += f"Months {phase['start_month']}-{phase['end_month']}\n"
                schedule_text += phase_line
            schedule_text += "\n"

        embed.add_field(name="\u200b", value=schedule_text, inline=False)

        # Add cycle info
        cycle_info = f"ℹ️ **Cycle Info**\n"
        cycle_info += f"Cycle Start Year: {config['cycle_year']}\n"
        cycle_info += f"Status: ▶️ Running"

        embed.add_field(name="\u200b", value=cycle_info, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.checks.has_permissions(administrator=True)
    @time_admin_group.command( # Changed to time_admin_group
        name="set_voice_channel",
        description="Set which voice channel to update with RP date"
    )
    async def set_voice_channel(
        self, 
        interaction: discord.Interaction, 
        channel: discord.VoiceChannel
    ):
        config = self._get_time_config(interaction.guild.id)
        col = self.bot.db["time_configs"]

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"voice_channel_id": channel.id}}
        )

        await interaction.response.send_message(
            f"✅ Voice channel set to {channel.mention}. It will be updated with the current RP date.",
            ephemeral=True
        )

    @app_commands.checks.has_permissions(administrator=True)
    @time_admin_group.command( # Changed to time_admin_group
        name="toggle_voice_updates",
        description="Toggle automatic voice channel name updates with current RP date"
    )
    async def toggle_voice_updates(self, interaction: discord.Interaction):
        config = self._get_time_config(interaction.guild.id)
        col = self.bot.db["time_configs"]

        current_setting = config.get("update_voice_channels", True)
        new_setting = not current_setting

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"update_voice_channels": new_setting}}
        )

        status = "enabled" if new_setting else "disabled"
        await interaction.response.send_message(
            f"✅ Voice channel date updates have been **{status}**.",
            ephemeral=True
        )

    @app_commands.checks.has_permissions(administrator=True)
    @time_admin_group.command( # Changed to time_admin_group
        name="update_voice_channel",
        description="Manually update the configured voice channel with current RP date"
    )
    async def update_voice_channel(self, interaction: discord.Interaction):
        config = self._get_time_config(interaction.guild.id)
        col = self.bot.db["time_configs"]

        if not config.get("voice_channel_id"):
            await interaction.response.send_message(
                "❌ No voice channel configured. Use `/set_voice_channel` first.",
                ephemeral=True
            )
            return

        current_rp_date, current_phase = self._calculate_current_rp_time(config)
        date_string = current_rp_date.strftime("%B %d, %Y")

        channel = interaction.guild.get_channel(config["voice_channel_id"])
        if not channel:
            await interaction.response.send_message(
                "❌ Configured voice channel not found.",
                ephemeral=True
            )
            return

        try:
            new_name = f"📅 {date_string}"
            await channel.edit(name=new_name)
            await interaction.response.send_message(
                f"✅ Updated {channel.mention} with date: **{date_string}**",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to update voice channel: {str(e)}",
                ephemeral=True
            )

    @app_commands.checks.has_permissions(administrator=True)
    @time_admin_group.command(
        name="pause_time",
        description="Pause or unpause RP time progression (Admin only)"
    )
    async def pause_time(self, interaction: discord.Interaction):
        config = self._get_time_config(interaction.guild.id)
        col = self.bot.db["time_configs"]

        current_paused = config.get("time_paused", False)
        new_paused = not current_paused

        # If unpausing, update the last_real_update to now to prevent time jumps
        update_data = {"time_paused": new_paused}
        if not new_paused:
            update_data["last_real_update"] = datetime.utcnow()

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": update_data}
        )

        status = "paused" if new_paused else "resumed"
        embed = discord.Embed(
            title="⏸️ Time Control" if new_paused else "▶️ Time Control",
            description=f"RP time progression has been **{status}**.",
            color=discord.Color.orange() if new_paused else discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        if new_paused:
            embed.add_field(
                name="⚠️ Note",
                value="Time will remain frozen until you run this command again to resume.",
                inline=False
            )
        else:
            embed.add_field(
                name="ℹ️ Note",
                value="Time progression has resumed from the current moment.",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.checks.has_permissions(administrator=True)
    @time_admin_group.command(
        name="regenerate_stamina",
        description="Manually regenerate stamina for all candidates (Admin only)"
    )
    async def regenerate_stamina(self, interaction: discord.Interaction):
        await self._regenerate_daily_stamina(interaction.guild.id)

        # Update last regeneration date with current real time
        col = self.bot.db["time_configs"]

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"last_stamina_regen": datetime.utcnow()}}
        )

        embed = discord.Embed(
            title="⚡ Stamina Regenerated",
            description="Manually regenerated stamina for all candidates.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="Regeneration Amounts",
            value="• General candidates: +30 stamina (max 100)\n• Presidential candidates: +100 stamina (max 300)",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.checks.has_permissions(administrator=True)
    @time_admin_group.command(
        name="force_sync_voice",
        description="Force sync the voice channel name with current RP date (Admin only)"
    )
    async def force_sync_voice(self, interaction: discord.Interaction):
        config = self._get_time_config(interaction.guild.id)

        if not config.get("voice_channel_id"):
            await interaction.response.send_message(
                "❌ No voice channel configured. Use `/time admin set_voice_channel` first.",
                ephemeral=True
            )
            return

        current_rp_date, current_phase = self._calculate_current_rp_time(config)
        date_string = current_rp_date.strftime("%B %d, %Y")

        channel = interaction.guild.get_channel(config["voice_channel_id"])
        if not channel:
            await interaction.response.send_message(
                "❌ Configured voice channel not found. It may have been deleted.",
                ephemeral=True
            )
            return

        if not hasattr(channel, 'edit'):
            await interaction.response.send_message(
                "❌ The configured channel is not a voice channel.",
                ephemeral=True
            )
            return

        try:
            new_name = f"📅 {date_string}"
            old_name = channel.name
            await channel.edit(name=new_name)

            embed = discord.Embed(
                title="🔄 Voice Channel Synced",
                description="Successfully updated voice channel with current RP date.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="Channel Updated",
                value=f"{channel.mention}",
                inline=True
            )

            embed.add_field(
                name="Old Name",
                value=f"`{old_name}`",
                inline=True
            )

            embed.add_field(
                name="New Name",
                value=f"`{new_name}`",
                inline=True
            )

            embed.add_field(
                name="Current RP Date",
                value=date_string,
                inline=False
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to update voice channel: {str(e)}",
                ephemeral=True
            )

    @app_commands.checks.has_permissions(administrator=True)
    @time_admin_group.command(
        name="update_phases",
        description="Update the phase configuration with new month ranges (Admin only)"
    )
    async def update_phases(self, interaction: discord.Interaction):
        config = self._get_time_config(interaction.guild.id)
        col = self.bot.db["time_configs"]

        # Update phases to your new configuration
        new_phases = [
            {"name": "Signups", "start_month": 2, "end_month": 8},
            {"name": "Primary Campaign", "start_month": 9, "end_month": 12},
            {"name": "Primary Election", "start_month": 1, "end_month": 2},
            {"name": "General Campaign", "start_month": 3, "end_month": 10},
            {"name": "General Election", "start_month": 11, "end_month": 12}
        ]

        # Update database with new phases
        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"phases": new_phases}}
        )

        # Get the updated config from database to calculate current phase correctly
        updated_config = col.find_one({"guild_id": interaction.guild.id})
        current_rp_date, current_phase = self._calculate_current_rp_time(updated_config)

        # Update current phase in database
        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"current_phase": current_phase}}
        )

        embed = discord.Embed(
            title="✅ Phase Configuration Updated",
            description="Phase month ranges have been updated and current phase recalculated.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        phase_text = ""
        for phase in new_phases:
            phase_text += f"**{phase['name']}:** Months {phase['start_month']}-{phase['end_month']}\n"

        embed.add_field(
            name="📅 New Phase Configuration",
            value=phase_text,
            inline=False
        )

        embed.add_field(
            name="🕒 Current Status",
            value=f"**Current Date:** {current_rp_date.strftime('%B %d, %Y')}\n**Current Phase:** {current_phase}",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(TimeManager(bot))