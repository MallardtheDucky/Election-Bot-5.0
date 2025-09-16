import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import random
import asyncio
from typing import Optional, List
from .presidential_winners import PRESIDENTIAL_STATE_DATA
from cogs.ideology import STATE_DATA



class GeneralCampaignActions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("General Campaign Actions cog loaded successfully")

    def _normalize_party_key(self, raw_party: str) -> str:
        """Normalize various party string formats to standard keys used by momentum.

        Returns one of: "Republican", "Democrat", "Independent".

        Examples that should map:
        - "Republican", "GOP", "R", "R-NE", "(R)", "Rep"
        - "Democrat", "Democratic", "D", "D-CA", "(D)", "Dem"
        Anything else -> "Independent".
        """
        try:
            if not raw_party or not isinstance(raw_party, str):
                return "Independent"

            party_lower = raw_party.strip().lower()

            # Common Republican indicators
            republican_markers = [
                "republican", "gop", "rep", "(r)", " r ", " r-", "-r", " r/", " r|", " r)"
            ]
            # Common Democrat indicators
            democrat_markers = [
                "democrat", "democratic", "dem", "(d)", " d ", " d-", "-d", " d/", " d|", " d)"
            ]

            # Fast explicit checks
            for marker in republican_markers:
                if marker in party_lower:
                    return "Republican"
            for marker in democrat_markers:
                if marker in party_lower:
                    return "Democrat"

            # Prefix letter with state like "R-NE" / "D-CA"
            if party_lower.startswith("r-") or party_lower == "r":
                return "Republican"
            if party_lower.startswith("d-") or party_lower == "d":
                return "Democrat"

            # Enclosed formats like "R)" or "(R-NE)"
            if party_lower.startswith("(r") or party_lower.endswith(")") and "(r" in party_lower:
                return "Republican"
            if party_lower.startswith("(d") or party_lower.endswith(")") and "(d" in party_lower:
                return "Democrat"

            return "Independent"
        except Exception:
            return "Independent"

    def _get_time_config(self, guild_id: int):
        """Get time configuration to check current phase"""
        try:
            col = self.bot.db["time_configs"]
            config = col.find_one({"guild_id": guild_id})
            return col, config
        except Exception as e:
            print(f"Error in _get_time_config: {e}")
            return self.bot.db["time_configs"], None

    def _get_signups_config(self, guild_id: int):
        """Get or create signups configuration"""
        try:
            col = self.bot.db["all_signups"]
            config = col.find_one({"guild_id": guild_id})
            if not config:
                config = {
                    "guild_id": guild_id,
                    "candidates": []
                }
                col.insert_one(config)
            return col, config
        except Exception as e:
            print(f"Error in _get_signups_config: {e}")
            return self.bot.db["all_signups"], {"guild_id": guild_id, "candidates": []}

    def _get_user_candidate(self, guild_id: int, user_id: int):
        """Get user's candidate information from signups"""
        try:
            time_col, time_config = self._get_time_config(guild_id)
            current_year = time_config["current_rp_date"].year if time_config else 2024

            # Check signups collection first (primary source)
            signups_col = self.bot.db["signups"]
            signups_config = signups_col.find_one({"guild_id": guild_id})

            if signups_config:
                for candidate in signups_config.get("candidates", []):
                    if (candidate.get("user_id") == user_id and 
                        candidate.get("year") == current_year):
                        return signups_col, candidate

            # Check all_signups collection as backup
            all_signups_col = self.bot.db["all_signups"]
            all_signups_config = all_signups_col.find_one({"guild_id": guild_id})

            if all_signups_config:
                for candidate in all_signups_config.get("candidates", []):
                    if (candidate.get("user_id") == user_id and 
                        candidate.get("year") == current_year):
                        return all_signups_col, candidate

            return signups_col, None
        except Exception as e:
            print(f"Error in _get_user_candidate: {e}")
            return self.bot.db["signups"], None

    def _get_candidate_by_name(self, guild_id: int, candidate_name: str):
        """Get candidate by name from signups, winners, or presidential signups"""
        try:
            if not candidate_name or not isinstance(candidate_name, str):
                return None, None
                
            time_col, time_config = self._get_time_config(guild_id)
            if not time_config:
                return None, None

            # Calculate current phase dynamically instead of relying on stored value
            from cogs.time_manager import TimeManager
            time_manager = self.bot.get_cog('TimeManager')
            if time_manager:
                current_rp_date, current_phase = time_manager._calculate_current_rp_time(time_config)
                current_year = current_rp_date.year
            else:
                current_year = time_config["current_rp_date"].year
                current_phase = time_config.get("current_phase", "")

            # Check both signups collections (prioritize based on phase)

            # 1. Check signups collection (used by all_signups.py - primary source for Primary Campaign)
            signups_col = self.bot.db["signups"]
            signups_config = signups_col.find_one({"guild_id": guild_id})
            if signups_config and "candidates" in signups_config:
                for candidate in signups_config["candidates"]:
                    if (candidate.get("name", "").lower() == candidate_name.lower() and
                        candidate.get("year") == current_year):
                        return signups_col, candidate

            # 2. Check all_signups collection (backup)
            all_signups_col, all_signups_config = self._get_signups_config(guild_id)
            if all_signups_config and "candidates" in all_signups_config:
                for candidate in all_signups_config["candidates"]:
                    if (candidate.get("name", "").lower() == candidate_name.lower() and
                        candidate.get("year") == current_year):
                        return all_signups_col, candidate

            # 3. Check presidential signups
            pres_col = self.bot.db["presidential_signups"]
            pres_config = pres_col.find_one({"guild_id": guild_id})
            if pres_config and "candidates" in pres_config:
                for candidate in pres_config.get("candidates", []):
                    if (candidate.get("name", "").lower() == candidate_name.lower() and
                        candidate.get("year") == current_year):
                        return pres_col, candidate

            # 4. Check winners if in general campaign or primary election
            if current_phase in ["General Campaign", "Primary Election"]:
                winners_col = self.bot.db["winners"]
                winners_config = winners_col.find_one({"guild_id": guild_id})
                if winners_config and "winners" in winners_config:
                    # For General Campaign/Primary Election, look for primary winners from the current election year
                    # Primary winners are stored with the election year (even years), not the signup year
                    for winner in winners_config["winners"]:
                        if (winner.get("candidate", "").lower() == candidate_name.lower() and
                            winner.get("year") == current_year and
                            winner.get("primary_winner", False)):
                            return winners_col, winner

            print(f"DEBUG: Could not find candidate '{candidate_name}' in any collection for year {current_year}")
            return None, None
        except Exception as e:
            print(f"Error in _get_candidate_by_name: {e}")
            return None, None


    def _get_buffs_debuffs_config(self, guild_id: int):
        """Get or create campaign buffs/debuffs configuration"""
        col = self.bot.db["campaign_buffs_debuffs"]
        config = col.find_one({"guild_id": guild_id})
        if not config:
            config = {
                "guild_id": guild_id,
                "active_effects": {}  # effect_id -> {effect_type, target_user_id, effect_name, multiplier, expires_at}
            }
            col.insert_one(config)
        return col, config

    def _apply_buff_debuff_multiplier_enhanced(self, base_points: float, user_id: int, guild_id: int, action_type: str) -> float:
        """Apply any active buffs or debuffs to the points gained with announcements"""
        try:
            buffs_col, buffs_config = self._get_buffs_debuffs_config(guild_id)

            active_effects = buffs_config.get("active_effects", {})
            multiplier = 1.0
            current_time = datetime.utcnow()

            # Clean up expired effects
            expired_effects = []
            for effect_id, effect in active_effects.items():
                if effect.get("expires_at", current_time) <= current_time:
                    expired_effects.append(effect_id)

            if expired_effects:
                for effect_id in expired_effects:
                    buffs_col.update_one(
                        {"guild_id": guild_id},
                        {"$unset": {f"active_effects.{effect_id}": ""}}
                    )

            for effect_id, effect in active_effects.items():
                # Check if effect applies to this user and action
                if (effect.get("target_user_id") == user_id and 
                    effect.get("expires_at") > current_time and
                    (not effect.get("action_types") or action_type in effect.get("action_types", []))):

                    effect_multiplier = effect.get("multiplier", 1.0)
                    if effect.get("effect_type") == "buff":
                        multiplier += (effect_multiplier - 1.0)
                    elif effect.get("effect_type") == "debuff":
                        multiplier *= effect_multiplier

            return base_points * max(0.1, multiplier)  # Minimum 10% effectiveness
        except Exception as e:
            print(f"Error in _apply_buff_debuff_multiplier_enhanced: {e}")
            return base_points  # Return original points if error occurs




    @app_commands.command(
        name="speech",
        description="Give a speech in a specific state with ideology alignment bonus"
    )
    @app_commands.describe(
        state="The state where you're giving the speech",
        ideology="Your campaign's ideological stance",
        target="The candidate who will receive benefits (optional)"
    )
    async def speech(
        self,
        interaction: discord.Interaction,
        state: str,
        ideology: str,
        target: Optional[str] = None
    ):
        """Give a speech with potential state and ideology bonus"""
        state_key = state.upper()

        # Check if state exists in STATE_DATA
        if state_key not in STATE_DATA:
            await interaction.response.send_message(
                f"❌ State '{state}' not found. Please enter a valid US state name.",
                ephemeral=True
            )
            return

        state_data = STATE_DATA[state_key]

        # Check if user has a registered candidate (optional)
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        # Use candidate name if registered, otherwise use display name
        candidate_name = candidate["name"] if candidate else interaction.user.display_name

        # If no target specified, require one when user is not a candidate
        if target is None:
            if candidate:
                target = candidate_name
            else:
                await interaction.response.send_message(
                    "❌ You must specify a target candidate to perform this action.",
                    ephemeral=True
                )
                return

        # Verify target candidate exists
        target_signups_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, target)
        if not target_candidate or not isinstance(target_candidate, dict):
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Check cooldown (1 hour)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "speech", 1):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "speech", 1)
            if remaining:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                await interaction.response.send_message(
                    f"❌ You must wait {hours}h {minutes}m before giving another speech.",
                    ephemeral=True
                )
                return

        # Send initial message asking for speech
        await interaction.response.send_message(
            f"🎤 **{candidate_name}**, please reply to this message with your campaign speech!\n\n"
            f"**Target:** {target}\n"
            f"**State:** {state.title()}\n"
            f"**Your Ideology:** {ideology}\n"
            f"**State Ideology:** {state_data.get('ideology', 'Unknown')}\n"
            f"**Requirements:**\n"
            f"• Speech content (700-3000 characters)\n"
            f"• Reply within 5 minutes\n\n"
            f"**Potential Bonus:** {'✅ Ideology match (+0.5%)' if state_data.get('ideology', '').lower() == ideology.lower() else '⚠️ No ideology match (+0.0%)'}"
        )

        # Get the response message
        response_message = await interaction.original_response()

        def check(message):
            return (message.author.id == interaction.user.id and 
                    message.reference and 
                    message.reference.message_id == response_message.id)

        try:
            # Wait for user to reply with speech
            reply_message = await self.bot.wait_for('message', timeout=300.0, check=check)

            speech_content = reply_message.content
            char_count = len(speech_content)

            # Check character limits
            if char_count < 700 or char_count > 3000:
                await reply_message.reply(f"❌ Speech must be 700-3000 characters. You wrote {char_count} characters.")
                return

            # Determine who pays stamina cost
            stamina_cost = 6.0
            stamina_user_id = self._determine_stamina_user(interaction.guild.id, interaction.user.id, target_candidate, stamina_cost)

            # Check if stamina user has enough stamina
            stamina_user_candidate = target_candidate if stamina_user_id == target_candidate.get("user_id") else None
            if not stamina_user_candidate and stamina_user_id != target_candidate.get("user_id"):
                # Get stamina user's candidate data
                _, stamina_user_candidate = self._get_user_candidate(interaction.guild.id, stamina_user_id)

            stamina_amount = stamina_user_candidate.get("stamina", 0) if stamina_user_candidate else 0
            if stamina_amount < stamina_cost:
                stamina_user_name = stamina_user_candidate.get("name", "Unknown") if stamina_user_candidate else "Unknown"
                await reply_message.reply(f"❌ {stamina_user_name} doesn't have enough stamina for this speech! They need at least {stamina_cost} stamina (current: {stamina_amount}).")
                return

            # Set cooldown after successful validation
            self._set_cooldown(interaction.guild.id, interaction.user.id, "speech")

            # Deduct stamina from the determined user
            self._deduct_stamina_from_user(interaction.guild.id, stamina_user_id, stamina_cost)

            # Check for ideology match
            ideology_match = False
            if state_data.get("ideology", "").lower() == ideology.lower():
                ideology_match = True

            # Calculate bonus based on character count and ideology match
            base_bonus = (char_count / 1000) * 0.5  # 0.5% per 1000 characters
            ideology_bonus = 0.5 if ideology_match else 0.0
            total_bonus = base_bonus + ideology_bonus

            # Get current phase
            time_col, time_config = self._get_time_config(interaction.guild.id)
            current_phase = time_config.get("current_phase", "") if time_config else ""

            # Update candidate stats based on phase
            if current_phase == "General Campaign" and target_candidate:
                # Update points in winners collection for General Campaign
                self._update_general_candidate_stats(
                    interaction.guild.id, 
                    target_candidate.get("user_id"), 
                    state_key, 
                    total_bonus, 
                    stamina_cost, 
                    0,  # corruption increase
                    target_candidate,
                    interaction.user.id
                )
            elif current_phase == "Primary Campaign" and target_candidate:
                # Add points to target candidate in all_signups for Primary Campaign
                target_signups_col.update_one(
                    {"guild_id": interaction.guild.id, "candidates.user_id": target_candidate.get("user_id")},
                    {"$inc": {"candidates.$.points": total_bonus}}
                )

            # Create response embed
            embed = discord.Embed(
                title=f"🎤 Campaign Speech in {state.title()}",
                description=f"**{candidate_name}** delivers a compelling speech!",
                color=discord.Color.green() if ideology_match else discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            # Truncate speech for display if too long
            display_speech = speech_content
            if len(display_speech) > 1000:
                display_speech = display_speech[:997] + "..."

            embed.add_field(
                name="📜 Speech Content",
                value=display_speech,
                inline=False
            )

            embed.add_field(
                name="🎯 Campaign Impact",
                value=f"**State:** {state.title()}\n"
                      f"**Your Ideology:** {ideology}\n"
                      f"**State Ideology:** {state_data.get('ideology', 'Unknown')}\n"
                      f"**Ideology Match:** {'✅ Yes (+0.5%)' if ideology_match else '❌ No (+0.0%)'}",
                inline=True
            )

            embed.add_field(
                name="📊 Speech Metrics",
                value=f"**Characters:** {char_count:,}\n"
                      f"**Base Bonus:** +{base_bonus:.2f}%\n"
                      f"**Ideology Bonus:** +{ideology_bonus:.2f}%\n"
                      f"**Total Bonus:** +{total_bonus:.2f}%\n"
                      f"**Stamina Cost:** -{stamina_cost}",
                inline=True
            )

            if ideology_match:
                embed.add_field(
                    name="🌟 Special Bonus",
                    value="Your ideology perfectly aligns with this state's political climate!",
                    inline=False
                )

            embed.set_footer(text="Next speech available in 1 hour")

            await reply_message.reply(embed=embed)

        except asyncio.TimeoutError:
            await interaction.edit_original_response(
                content=f"⏰ **{candidate_name}**, your speech timed out. Please use `/speech` again and reply with your speech within 5 minutes."
            )
        except Exception as e:
            await interaction.edit_original_response(
                content=f"❌ An error occurred while processing your speech. Please try again."
            )

    @speech.autocomplete("target")
    async def target_autocomplete_speech(self, interaction: discord.Interaction, current: str):
        return await self._get_candidate_choices_autocomplete(interaction, current)

    @speech.autocomplete("state")
    async def state_autocomplete_speech(self, interaction: discord.Interaction, current: str):
        states = list(STATE_DATA.keys())
        return [app_commands.Choice(name=state.title(), value=state)
                for state in states if current.upper() in state][:25]

    @speech.autocomplete("ideology")
    async def ideology_autocomplete_speech(self, interaction: discord.Interaction, current: str):
        """Provide autocomplete options for ideologies"""
        # Get all unique ideologies from STATE_DATA
        ideologies = set()
        for state_data in STATE_DATA.values():
            if "ideology" in state_data:
                ideologies.add(state_data["ideology"])

        ideology_list = sorted(list(ideologies))
        return [app_commands.Choice(name=ideology, value=ideology)
                for ideology in ideology_list if current.lower() in ideology.lower()][:25]

    @app_commands.command(
        name="donor",
        description="General campaign donor appeal in a U.S. state (400-3000 characters, +1% per 1000 chars)"
    )
    @app_commands.describe(
        state="U.S. state for donor appeal",
        target="The candidate who will receive benefits (optional)"
    )
    async def donor(self, interaction: discord.Interaction, state: str, target: Optional[str] = None):
        # Validate state
        state_upper = state.upper()
        if state_upper not in STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from valid US state names.",
                ephemeral=True
            )
            return

        # Check if user has a registered candidate (optional)
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        # Use candidate name if registered, otherwise use display name
        candidate_name = candidate["name"] if candidate else interaction.user.display_name

        # If no target specified, require one when user is not a candidate
        if target is None:
            if candidate:
                target = candidate_name
            else:
                await interaction.response.send_message(
                    "❌ You must specify a target candidate to perform this action.",
                    ephemeral=True
                )
                return

        # Verify target candidate exists
        target_signups_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, target)
        if not target_candidate or not isinstance(target_candidate, dict):
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Check cooldown (1 hour)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "donor", 1):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "donor", 1)
            if remaining:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                await interaction.response.send_message(
                    f"❌ You must wait {hours}h {minutes}m before making another donor appeal.",
                    ephemeral=True
                )
                return

        # Send initial message asking for donor appeal
        await interaction.response.send_message(
            f"💰 **{candidate_name}**, please reply to this message with your donor appeal!\n\n"
            f"**Target:** {target}\n"
            f"**State:** {state_upper}\n"
            f"**Requirements:**\n"
            f"• Donor appeal content (400-3000 characters)\n"
            f"• Reply within 5 minutes\n\n"
            f"**Effect:** Up to 3% boost based on length, +5 corruption, -5 stamina",
            ephemeral=False
        )

        # Get the response message
        response_message = await interaction.original_response()

        def check(message):
            return (message.author.id == interaction.user.id and 
                    message.reference and 
                    message.reference.message_id == response_message.id)

        try:
            # Wait for user to reply with donor appeal
            reply_message = await self.bot.wait_for('message', timeout=300.0, check=check)

            donor_appeal = reply_message.content
            char_count = len(donor_appeal)

            # Check character limits
            if char_count < 400:
                await reply_message.reply(f"❌ Donor appeal must be at least 400 characters. You wrote {char_count} characters.")
                return

            if char_count > 3000:
                await reply_message.reply(f"❌ Donor appeal must be no more than 3000 characters. You wrote {char_count} characters.")
                return

            # Determine who pays stamina cost
            stamina_cost = 5.0
            stamina_user_id = self._determine_stamina_user(interaction.guild.id, interaction.user.id, target_candidate, stamina_cost)

            # Check if stamina user has enough stamina
            stamina_user_candidate = target_candidate if stamina_user_id == target_candidate.get("user_id") else None
            if not stamina_user_candidate and stamina_user_id != target_candidate.get("user_id"):
                # Get stamina user's candidate data
                _, stamina_user_candidate = self._get_user_candidate(interaction.guild.id, stamina_user_id)

            stamina_amount = stamina_user_candidate.get("stamina", 0) if stamina_user_candidate else 0
            if stamina_amount < stamina_cost:
                stamina_user_name = stamina_user_candidate.get("name", "Unknown") if stamina_user_candidate else "Unknown"
                await reply_message.reply(f"❌ {stamina_user_name} doesn't have enough stamina for this donor appeal! They need at least {stamina_cost} stamina (current: {stamina_amount}).")
                return

            # Set cooldown after successful validation
            self._set_cooldown(interaction.guild.id, interaction.user.id, "donor")

            # Deduct stamina from the determined user
            self._deduct_stamina_from_user(interaction.guild.id, stamina_user_id, stamina_cost)

            # Calculate boost - 1% per 1000 characters  
            boost = (char_count / 1000) * 1.0
            boost = min(boost, 3.0)

            # Get current phase
            time_col, time_config = self._get_time_config(interaction.guild.id)
            current_phase = time_config.get("current_phase", "") if time_config else ""

            # Update candidate stats based on phase
            if current_phase == "General Campaign" and target_candidate:
                # Update points in winners collection for General Campaign
                self._update_general_candidate_stats(
                    interaction.guild.id, 
                    target_candidate.get("user_id"), 
                    state_upper, 
                    boost, 
                    stamina_cost, 
                    0,  # corruption increase
                    target_candidate,
                    interaction.user.id
                )
            elif current_phase == "Primary Campaign" and target_candidate:
                # Add points to target candidate in all_signups for Primary Campaign
                target_signups_col.update_one(
                    {"guild_id": interaction.guild.id, "candidates.user_id": target_candidate.get("user_id")},
                    {"$inc": {"candidates.$.points": boost}}
                )

            # Create response embed
            embed = discord.Embed(
                title="💰 General Campaign Donor Appeal",
                description=f"**{candidate_name}** makes a donor appeal for **{target}** in {state_upper}!",
                color=discord.Color.gold(),
                timestamp=datetime.utcnow()
            )

            # Truncate appeal for display if too long
            display_appeal = donor_appeal
            if len(display_appeal) > 800:
                display_appeal = display_appeal[:797] + "..."

            embed.add_field(
                name="📝 Donor Appeal",
                value=display_appeal,
                inline=False
            )

            # Get state ideology data
            state_data = STATE_DATA.get(state_upper, {})
            state_ideology = state_data.get("ideology", "Unknown")

            embed.add_field(
                name="📊 Campaign Impact",
                value=f"**Target:** {target}\n"
                      f"**State:** {state_upper}\n"
                      f"**State Ideology:** {state_ideology}\n"
                      f"**Boost:** +{boost:.2f}%\n"
                      f"**Corruption:** +5\n"
                      f"**Stamina Cost:** -{stamina_cost}\n"
                      f"**Characters:** {char_count:,}",
                inline=True
            )

            embed.add_field(
                name="⚠️ Warning",
                value="High corruption may lead to scandals!\nDonor appeals are high-risk, high-reward.",
                inline=True
            )

            embed.set_footer(text="Next donor appeal available in 1 hour")

            await reply_message.reply(embed=embed)

        except asyncio.TimeoutError:
            await interaction.edit_original_response(
                content=f"⏰ **{candidate_name}**, your donor appeal timed out. Please use `/donor` again and reply with your appeal within 5 minutes."
            )

    @donor.autocomplete("target")
    async def target_autocomplete_donor(self, interaction: discord.Interaction, current: str):
        return await self._get_candidate_choices_autocomplete(interaction, current)

    @donor.autocomplete("state")
    async def state_autocomplete_donor(self, interaction: discord.Interaction, current: str):
        states = list(STATE_DATA.keys())
        return [app_commands.Choice(name=state.title(), value=state)
                for state in states if current.upper() in state][:25]

    @app_commands.command(
        name="poster",
        description="Create a campaign poster in a U.S. state (0.25-0.5% points, 2 stamina)"
    )
    @app_commands.describe(
        state="U.S. state for campaign poster",
        target="The candidate who will receive benefits (optional)"
    )
    async def poster(
        self, 
        interaction: discord.Interaction, 
        state: str,
        image: discord.Attachment,
        target: Optional[str] = None
    ):
        # Validate state
        state_upper = state.upper()
        if state_upper not in STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from valid US state names.",
                ephemeral=True
            )
            return

        # Check if user has a registered candidate (optional)
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        # Use candidate name if registered, otherwise use display name
        candidate_name = candidate["name"] if candidate else interaction.user.display_name

        # If no target specified, require one when user is not a candidate
        if target is None:
            if candidate:
                target = candidate_name
            else:
                await interaction.response.send_message(
                    "❌ You must specify a target candidate to perform this action.",
                    ephemeral=True
                )
                return

        # Verify target candidate exists
        target_signups_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, target)
        if not target_candidate or not isinstance(target_candidate, dict):
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Check cooldown (1 hour)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "poster", 1):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "poster", 1)
            if remaining:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                await interaction.response.send_message(
                    f"❌ You must wait {hours}h {minutes}m before creating another poster.",
                    ephemeral=True
                )
                return

        # Defer the response early to prevent timeout
        await interaction.response.defer()

        # Check if attachment is an image
        if not image or not image.content_type or not image.content_type.startswith('image/'):
            await interaction.followup.send(
                "❌ Please upload an image file (PNG, JPG, GIF, etc.).",
                ephemeral=True
            )
            return

        # Check file size
        if image.size > 10 * 1024 * 1024:
            await interaction.followup.send(
                "❌ Image file too large! Maximum size is 10MB.",
                ephemeral=True
            )
            return

        # Determine who pays stamina cost
        stamina_cost = 2.0
        stamina_user_id = self._determine_stamina_user(interaction.guild.id, interaction.user.id, target_candidate, stamina_cost)

        # Check if stamina user has enough stamina
        stamina_user_candidate = target_candidate if stamina_user_id == target_candidate.get("user_id") else None
        if not stamina_user_candidate and stamina_user_id != target_candidate.get("user_id"):
            # Get stamina user's candidate data
            _, stamina_user_candidate = self._get_user_candidate(interaction.guild.id, stamina_user_id)

        stamina_amount = stamina_user_candidate.get("stamina", 0) if stamina_user_candidate else 0
        if stamina_amount < stamina_cost:
            stamina_user_name = stamina_user_candidate.get("name", "Unknown") if stamina_user_candidate else "Unknown"
            await interaction.followup.send(
                f"❌ {stamina_user_name} doesn't have enough stamina to create a poster! They need at least {stamina_cost} stamina (current: {stamina_amount}).",
                ephemeral=True
            )
            return

        # Set cooldown after successful validation
        self._set_cooldown(interaction.guild.id, interaction.user.id, "poster")

        # Deduct stamina from the determined user
        self._deduct_stamina_from_user(interaction.guild.id, stamina_user_id, stamina_cost)

        # Random polling boost between 0.25% and 0.5%
        polling_boost = random.uniform(0.25, 0.5)

        # Apply buff/debuff multipliers
        user_id = candidate.get("user_id") if candidate else interaction.user.id
        polling_boost = self._apply_buff_debuff_multiplier_enhanced(polling_boost, user_id, interaction.guild.id, "poster")

        # Get current phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        current_phase = time_config.get("current_phase", "") if time_config else ""

        # Update candidate stats based on phase
        if current_phase == "General Campaign" and target_candidate:
            # Update points in winners collection for General Campaign
            self._update_general_candidate_stats(
                interaction.guild.id, 
                target_candidate.get("user_id"), 
                state_upper, 
                polling_boost, 
                stamina_cost, 
                0,  # corruption increase
                target_candidate,
                interaction.user.id
            )
        elif current_phase == "Primary Campaign" and target_candidate:
            # Add points to target candidate in all_signups for Primary Campaign
            target_signups_col.update_one(
                {"guild_id": interaction.guild.id, "candidates.user_id": target_candidate.get("user_id")},
                {"$inc": {"candidates.$.points": polling_boost}}
            )

        embed = discord.Embed(
            title="🖼️ Campaign Poster",
            description=f"**{candidate_name}** creates campaign materials for **{target}** in {state_upper}!",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        # Check for state ideology match (if applicable)
        state_data = STATE_DATA.get(state_upper, {})
        state_ideology = state_data.get("ideology", "Unknown")

        embed.add_field(
            name="📊 Campaign Impact",
            value=f"**Target:** {target}\n"
                  f"**State:** {state_upper}\n"
                  f"**State Ideology:** {state_ideology}\n"
                  f"**Boost:** +{polling_boost:.2f}%\n"
                  f"**Stamina Cost:** -{stamina_cost}",
            inline=True
        )

        embed.add_field(
            name="📍 Distribution",
            value=f"Posted throughout {state_upper}\nsocial media and community events",
            inline=True
        )

        current_stamina = candidate.get('stamina', 100) if candidate and isinstance(candidate, dict) else 100
        embed.add_field(
            name="⚡ Current Stamina",
            value=f"{current_stamina - stamina_cost}/100",
            inline=True
        )

        embed.set_image(url=image.url)
        embed.set_footer(text="Next poster available in 1 hour")

        await interaction.followup.send(embed=embed)

    @poster.autocomplete("target")
    async def target_autocomplete_poster(self, interaction: discord.Interaction, current: str):
        return await self._get_candidate_choices_autocomplete(interaction, current)

    @poster.autocomplete("state")
    async def state_autocomplete_poster(self, interaction: discord.Interaction, current: str):
        states = list(STATE_DATA.keys())
        return [app_commands.Choice(name=state.title(), value=state)
                for state in states if current.upper() in state][:25]

    @app_commands.command(
        name="ad",
        description="Create a campaign video ad in a U.S. state (0.5-1% points, 3 stamina)"
    )
    @app_commands.describe(
        state="U.S. state for video ad",
        target="The candidate who will receive benefits (optional)"
    )
    async def ad(self, interaction: discord.Interaction, state: str, target: Optional[str] = None):
        # Validate state
        state_upper = state.upper()
        if state_upper not in STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from valid US state names.",
                ephemeral=True
            )
            return

        # Check if user has a registered candidate (optional)
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        # Use candidate name if registered, otherwise use display name
        candidate_name = candidate["name"] if candidate else interaction.user.display_name

        # If no target specified, require one when user is not a candidate
        if target is None:
            if candidate:
                target = candidate_name
            else:
                await interaction.response.send_message(
                    "❌ You must specify a target candidate to perform this action.",
                    ephemeral=True
                )
                return

        # Verify target candidate exists
        target_signups_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, target)
        if not target_candidate or not isinstance(target_candidate, dict):
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Check cooldown (1 hour)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "ad", 1):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "ad", 1)
            if remaining:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                await interaction.response.send_message(
                    f"❌ You must wait {hours}h {minutes}m before creating another ad.",
                    ephemeral=True
                )
                return

        # Send initial message asking for video
        await interaction.response.send_message(
            f"📺 **{candidate_name}**, please reply to this message with your campaign video!\n\n"
            f"**Target:** {target}\n"
            f"**State:** {state_upper}\n"
            f"**Requirements:**\n"
            f"• Video file (MP4, MOV, AVI, etc.)\n"
            f"• Maximum size: 25MB\n"
            f"• Reply within 5 minutes\n\n"
            f"**Effect:** 0.5-1% polling boost, -3 stamina",
            ephemeral=False
        )

        # Get the response message
        response_message = await interaction.original_response()

        def check(message):
            return (message.author.id == interaction.user.id and 
                    message.reference and 
                    message.reference.message_id == response_message.id and
                    len(message.attachments) > 0)

        try:
            # Wait for user to reply with attachment
            reply_message = await self.bot.wait_for('message', timeout=300.0, check=check)

            video = reply_message.attachments[0]

            # Check if attachment is a video
            if not video.content_type or not video.content_type.startswith('video/'):
                await reply_message.reply("❌ Please upload a video file (MP4 format preferred).")
                return

            # Check file size
            if video.size > 25 * 1024 * 1024:
                await reply_message.reply("❌ Video file too large! Maximum size is 25MB.")
                return

            # Determine who pays stamina cost
            stamina_cost = 3.0
            stamina_user_id = self._determine_stamina_user(interaction.guild.id, interaction.user.id, target_candidate, stamina_cost)

            # Check if stamina user has enough stamina
            stamina_user_candidate = target_candidate if stamina_user_id == target_candidate.get("user_id") else None
            if not stamina_user_candidate and stamina_user_id != target_candidate.get("user_id"):
                # Get stamina user's candidate data
                _, stamina_user_candidate = self._get_user_candidate(interaction.guild.id, stamina_user_id)

            stamina_amount = stamina_user_candidate.get("stamina", 0) if stamina_user_candidate else 0
            if stamina_amount < stamina_cost:
                stamina_user_name = stamina_user_candidate.get("name", "Unknown") if stamina_user_candidate else "Unknown"
                await reply_message.reply(f"❌ {stamina_user_name} doesn't have enough stamina to create an ad! They need at least {stamina_cost} stamina (current: {stamina_amount}).")
                return

            # Set cooldown after successful validation
            self._set_cooldown(interaction.guild.id, interaction.user.id, "ad")

            # Deduct stamina from the determined user
            self._deduct_stamina_from_user(interaction.guild.id, stamina_user_id, stamina_cost)

            # Random polling boost between 0.5% and 1%
            polling_boost = random.uniform(0.5, 1.0)

            # Apply buff/debuff multipliers
            user_id = candidate.get("user_id") if candidate else interaction.user.id
            polling_boost = self._apply_buff_debuff_multiplier_enhanced(polling_boost, user_id, interaction.guild.id, "ad")

            # Get current phase
            time_col, time_config = self._get_time_config(interaction.guild.id)
            current_phase = time_config.get("current_phase", "") if time_config else ""

            # Update candidate stats based on phase
            if current_phase == "General Campaign" and target_candidate:
                # Update points in winners collection for General Campaign
                self._update_general_candidate_stats(
                    interaction.guild.id, 
                    target_candidate.get("user_id"), 
                    state_upper, 
                    polling_boost, 
                    stamina_cost, 
                    0,  # corruption increase
                    target_candidate,
                    interaction.user.id
                )
            elif current_phase == "Primary Campaign" and target_candidate:
                # Add points to target candidate in all_signups for Primary Campaign
                target_signups_col.update_one(
                    {"guild_id": interaction.guild.id, "candidates.user_id": target_candidate.get("user_id")},
                    {"$inc": {"candidates.$.points": polling_boost}}
                )

            embed = discord.Embed(
                title="📺 Campaign Video Ad",
                description=f"**{candidate_name}** creates a campaign advertisement for **{target}** in {state_upper}!",
                color=discord.Color.purple(),
                timestamp=datetime.utcnow()
            )

            # Check for state ideology match (if applicable)
            state_data = STATE_DATA.get(state_upper, {})
            state_ideology = state_data.get("ideology", "Unknown")

            embed.add_field(
                name="📊 Ad Performance",
                value=f"**Target:** {target}\n"
                      f"**State:** {state_upper}\n"
                      f"**State Ideology:** {state_ideology}\n"
                      f"**Boost:** +{polling_boost:.2f}%\n"
                      f"**Stamina Cost:** -{stamina_cost}",
                inline=True
            )

            embed.add_field(
                name="📱 Reach",
                value=f"Broadcast across {state_upper}\nsocial media and local TV",
                inline=True
            )

            current_stamina = candidate.get('stamina', 100) if candidate and isinstance(candidate, dict) else 100
            embed.add_field(
                name="⚡ Current Stamina",
                value=f"{current_stamina - stamina_cost:.1f}/100",
                inline=True
            )

            embed.set_footer(text="Next ad available in 1 hour")

            await reply_message.reply(embed=embed)

        except asyncio.TimeoutError:
            await interaction.edit_original_response(
                content=f"⏰ **{candidate_name}**, your ad creation timed out. Please use `/ad` again and reply with your video within 5 minutes."
            )

    @ad.autocomplete("target")
    async def target_autocomplete_ad(self, interaction: discord.Interaction, current: str):
        return await self._get_candidate_choices_autocomplete(interaction, current)

    @ad.autocomplete("state")
    async def state_autocomplete_ad(self, interaction: discord.Interaction, current: str):
        states = list(STATE_DATA.keys())
        return [app_commands.Choice(name=state.title(), value=state)
                for state in states if current.upper() in state][:25]

    @app_commands.command(
        name="canvassing",
        description="Door-to-door canvassing in a U.S. state (0.1% points, 1 stamina, message required)"
    )
    @app_commands.describe(
        state="U.S. state for canvassing",
        canvassing_message="Your canvassing message (100-300 characters)",
        target="The candidate who will receive benefits (optional)"
    )
    async def canvassing(
        self,
        interaction: discord.Interaction,
        state: str,
        canvassing_message: str,
        target: Optional[str] = None
    ):
        # Validate state
        state_upper = state.upper()
        if state_upper not in STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from valid US state names.",
                ephemeral=True
            )
            return

        # Check if user has a registered candidate (optional)
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        # Use candidate name if registered, otherwise use display name
        candidate_name = candidate["name"] if candidate else interaction.user.display_name

        # If no target specified, require one when user is not a candidate
        if target is None:
            if candidate:
                target = candidate_name
            else:
                await interaction.response.send_message(
                    "❌ You must specify a target candidate to perform this action.",
                    ephemeral=True
                )
                return

        # Verify target candidate exists
        target_signups_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, target)
        if not target_candidate or not isinstance(target_candidate, dict):
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Check cooldown (1 hour)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "canvassing", 1):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "canvassing", 1)
            if remaining:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                await interaction.response.send_message(
                    f"❌ You must wait {hours}h {minutes}m before canvassing again.",
                    ephemeral=True
                )
                return

        # Check character limits for canvassing message
        char_count = len(canvassing_message)
        if char_count < 100 or char_count > 300:
            await interaction.response.send_message(
                f"❌ Canvassing message must be 100-300 characters. You wrote {char_count} characters.",
                ephemeral=True
            )
            return

        # Determine who pays stamina cost
        stamina_cost = 1.0
        stamina_user_id = self._determine_stamina_user(interaction.guild.id, interaction.user.id, target_candidate, stamina_cost)

        # Check if stamina user has enough stamina
        stamina_user_candidate = target_candidate if stamina_user_id == target_candidate.get("user_id") else None
        if not stamina_user_candidate and stamina_user_id != target_candidate.get("user_id"):
            # Get stamina user's candidate data
            _, stamina_user_candidate = self._get_user_candidate(interaction.guild.id, stamina_user_id)

        stamina_amount = stamina_user_candidate.get("stamina", 0) if stamina_user_candidate else 0
        if stamina_amount < stamina_cost:
            stamina_user_name = stamina_user_candidate.get("name", "Unknown") if stamina_user_candidate else "Unknown"
            await interaction.response.send_message(
                f"❌ {stamina_user_name} doesn't have enough stamina for canvassing! They need at least {stamina_cost} stamina (current: {stamina_amount}).",
                ephemeral=True
            )
            return

        # Set cooldown after successful validation
        self._set_cooldown(interaction.guild.id, interaction.user.id, "canvassing")

        # Deduct stamina from the determined user
        self._deduct_stamina_from_user(interaction.guild.id, stamina_user_id, stamina_cost)

        # Fixed polling boost of 0.1%
        polling_boost = 0.1

        # Apply buff/debuff multipliers
        user_id = candidate.get("user_id") if candidate else interaction.user.id
        polling_boost = self._apply_buff_debuff_multiplier_enhanced(polling_boost, user_id, interaction.guild.id, "canvassing")

        # Get current phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        current_phase = time_config.get("current_phase", "") if time_config else ""

        # Update candidate stats based on phase
        if current_phase == "General Campaign" and target_candidate:
            # Update points in winners collection for General Campaign
            self._update_general_candidate_stats(
                interaction.guild.id, 
                target_candidate.get("user_id"), 
                state_upper, 
                polling_boost, 
                stamina_cost, 
                0,  # corruption increase
                target_candidate,
                interaction.user.id
            )
        elif current_phase == "Primary Campaign" and target_candidate:
            # Add points to target candidate in all_signups for Primary Campaign
            target_signups_col.update_one(
                {"guild_id": interaction.guild.id, "candidates.user_id": target_candidate.get("user_id")},
                {"$inc": {"candidates.$.points": polling_boost}}
            )

        embed = discord.Embed(
            title="🚪 Door-to-Door Canvassing",
            description=f"**{candidate_name}** goes canvassing for **{target}** in {state_upper}!",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="💬 Canvassing Message",
            value=canvassing_message,
            inline=False
        )

        # Check for state ideology match (if applicable)
        state_data = STATE_DATA.get(state_upper, {})
        state_ideology = state_data.get("ideology", "Unknown")

        embed.add_field(
            name="📊 Campaign Impact",
            value=f"**Target:** {target}\n"
                  f"**State:** {state_upper}\n"
                  f"**State Ideology:** {state_ideology}\n"
                  f"**Boost:** +{polling_boost:.2f}%\n"
                  f"**Stamina Cost:** -1",
            inline=True
        )

        embed.add_field(
            name="🏘️ Ground Game",
            value=f"Door-to-door outreach in {state_upper}\nBuilding grassroots support",
            inline=True
        )

        current_stamina = candidate.get('stamina', 100) if candidate and isinstance(candidate, dict) else 100
        embed.add_field(
            name="⚡ Current Stamina",
            value=f"{current_stamina - stamina_cost}/100",
            inline=True
        )

        embed.set_footer(text="Next canvassing available in 1 hour")

        await interaction.response.send_message(embed=embed)

    @canvassing.autocomplete("target")
    async def target_autocomplete_canvassing(self, interaction: discord.Interaction, current: str):
        return await self._get_candidate_choices_autocomplete(interaction, current)

    @canvassing.autocomplete("state")
    async def state_autocomplete_canvassing(self, interaction: discord.Interaction, current: str):
        states = list(STATE_DATA.keys())
        return [app_commands.Choice(name=state.title(), value=state)
                for state in states if current.upper() in state][:25]

    async def _get_candidate_choices_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice]:
        """Helper to get candidate choices for autocompletion"""
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config:
            return []

        # Calculate current phase dynamically instead of relying on stored value
        from cogs.time_manager import TimeManager
        time_manager = self.bot.get_cog('TimeManager')
        if time_manager:
            current_rp_date, current_phase = time_manager._calculate_current_rp_time(time_config)
            current_year = current_rp_date.year
        else:
            current_year = time_config["current_rp_date"].year if time_config else 2024
            current_phase = time_config.get("current_phase", "")

        all_candidates = []

        print(f"DEBUG: Autocomplete - Phase: {current_phase}, Year: {current_year}")

        # Phase-specific logic: prioritize different collections based on current phase
        if current_phase == "Primary Campaign":
            # During Primary Campaign, prioritize signups collection (used by all_signups.py)
            print("DEBUG: Primary Campaign phase - checking signups collection")
            
            # 1. Check signups collection (primary source for Primary Campaign - used by all_signups.py)
            signups_col = self.bot.db["signups"]
            signups_config = signups_col.find_one({"guild_id": interaction.guild.id})

            if signups_config and "candidates" in signups_config:
                for candidate in signups_config["candidates"]:
                    if candidate.get("year") == current_year:
                        candidate_name = candidate.get("name")
                        if candidate_name:
                            all_candidates.append(candidate_name)
                            print(f"DEBUG: Added signup candidate: {candidate_name}")

            # 2. Check all_signups collection (backup)
            all_signups_col = self.bot.db["all_signups"]
            all_signups_config = all_signups_col.find_one({"guild_id": interaction.guild.id})

            if all_signups_config and "candidates" in all_signups_config:
                for candidate in all_signups_config["candidates"]:
                    if candidate.get("year") == current_year:
                        candidate_name = candidate.get("name")
                        if candidate_name and candidate_name not in all_candidates:
                            all_candidates.append(candidate_name)
                            print(f"DEBUG: Added all_signups candidate: {candidate_name}")

        elif current_phase in ["General Campaign", "Primary Election"]:
            # During General Campaign or Primary Election, prioritize winners collection
            print(f"DEBUG: {current_phase} phase - checking winners collection")
            
            # 1. Check winners collection for primary winners
            winners_col = self.bot.db["winners"]
            winners_config = winners_col.find_one({"guild_id": interaction.guild.id})

            if winners_config and "winners" in winners_config:
                # For General Campaign/Primary Election, look for primary winners from the current election year
                # Primary winners are stored with the election year (even years), not the signup year
                print(f"DEBUG: Checking winners for election year: {current_year}")
                for winner in winners_config["winners"]:
                    if (winner.get("year") == current_year and 
                        winner.get("primary_winner", False)):
                        candidate_name = winner.get("candidate")
                        if candidate_name:
                            all_candidates.append(candidate_name)
                            print(f"DEBUG: Added primary winner candidate: {candidate_name}")

            # 2. Check presidential winners
            pres_winners_col = self.bot.db["presidential_winners"]
            pres_winners_config = pres_winners_col.find_one({"guild_id": interaction.guild.id})

            if pres_winners_config:
                election_year = pres_winners_config.get("election_year", current_year)
                print(f"DEBUG: Presidential winners - election_year: {election_year}, current_year: {current_year}")
                if election_year == current_year:
                    winners_data = pres_winners_config.get("winners", {})
                    if isinstance(winners_data, dict):
                        for party, winner_name in winners_data.items():
                            if isinstance(winner_name, str) and winner_name not in all_candidates:
                                all_candidates.append(winner_name)
                                print(f"DEBUG: Added presidential winner: {winner_name} ({party})")

        else:
            # For other phases or unknown phases, check all collections
            print("DEBUG: Unknown phase - checking all collections")
            
            # Check signups collection first (primary source)
            signups_col = self.bot.db["signups"]
            signups_config = signups_col.find_one({"guild_id": interaction.guild.id})

            if signups_config and "candidates" in signups_config:
                for candidate in signups_config["candidates"]:
                    if candidate.get("year") == current_year:
                        candidate_name = candidate.get("name")
                        if candidate_name:
                            all_candidates.append(candidate_name)

            # Check all_signups collection (backup)
            all_signups_col = self.bot.db["all_signups"]
            all_signups_config = all_signups_col.find_one({"guild_id": interaction.guild.id})

            if all_signups_config and "candidates" in all_signups_config:
                for candidate in all_signups_config["candidates"]:
                    if candidate.get("year") == current_year:
                        candidate_name = candidate.get("name")
                        if candidate_name and candidate_name not in all_candidates:
                            all_candidates.append(candidate_name)

            # Check presidential signups
            pres_col = self.bot.db["presidential_signups"]
            pres_config = pres_col.find_one({"guild_id": interaction.guild.id})

            if pres_config and "candidates" in pres_config:
                for candidate in pres_config["candidates"]:
                    if candidate.get("year") == current_year:
                        candidate_name = candidate.get("name")
                        if candidate_name and candidate_name not in all_candidates:
                            all_candidates.append(candidate_name)

        # Debug: Log candidates found
        print(f"DEBUG: Found {len(all_candidates)} candidates for autocomplete: {all_candidates[:10]}...")

        # Remove duplicates while preserving order
        seen = set()
        unique_candidates = []
        for name in all_candidates:
            if name and name not in seen:
                seen.add(name)
                unique_candidates.append(name)

        # Filter candidates based on user input
        if current:
            filtered_candidates = [name for name in unique_candidates if current.lower() in name.lower()]
        else:
            filtered_candidates = unique_candidates

        # Sort alphabetically for better UX
        filtered_candidates.sort()

        # Debug: Log filtered results
        print(f"DEBUG: Filtered to {len(filtered_candidates)} candidates matching '{current}': {filtered_candidates[:5]}...")

        # Return up to 25 choices
        return [app_commands.Choice(name=name, value=name) for name in filtered_candidates[:25]]


    # --- Buff/Debuff Management Functions ---



    def _check_cooldown(self, guild_id: int, user_id: int, action_type: str, hours: int):
        """Check if user is on cooldown for an action"""
        try:
            cooldowns_col = self.bot.db["action_cooldowns"]
            cooldown_record = cooldowns_col.find_one({
                "guild_id": guild_id,
                "user_id": user_id,
                "action_type": action_type
            })

            if not cooldown_record:
                return True

            last_used = cooldown_record.get("last_used")
            if not last_used:
                return True

            time_since = datetime.utcnow() - last_used
            return time_since >= timedelta(hours=hours)
        except Exception as e:
            print(f"Error in _check_cooldown: {e}")
            return True  # Allow action if error occurs

    def _get_cooldown_remaining(self, guild_id: int, user_id: int, action_type: str, hours: int):
        """Get remaining cooldown time"""
        try:
            cooldowns_col = self.bot.db["action_cooldowns"]
            cooldown_record = cooldowns_col.find_one({
                "guild_id": guild_id,
                "user_id": user_id,
                "action_type": action_type
            })

            if not cooldown_record:
                return timedelta(0)

            last_used = cooldown_record.get("last_used")
            if not last_used:
                return timedelta(0)

            time_since = datetime.utcnow() - last_used
            cooldown_duration = timedelta(hours=hours)

            if time_since >= cooldown_duration:
                return timedelta(0)

            return cooldown_duration - time_since
        except Exception as e:
            print(f"Error in _get_cooldown_remaining: {e}")
            return timedelta(0)  # Return no cooldown if error occurs

    def _set_cooldown(self, guild_id: int, user_id: int, action_type: str):
        """Set cooldown for an action"""
        try:
            cooldowns_col = self.bot.db["action_cooldowns"]
            cooldowns_col.update_one(
                {"guild_id": guild_id, "user_id": user_id, "action_type": action_type},
                {"$set": {"last_used": datetime.utcnow()}},
                upsert=True
            )
        except Exception as e:
            print(f"Error in _set_cooldown: {e}")

    def _calculate_zero_sum_percentages(self, guild_id: int, seat_id: str):
        """Calculate zero-sum redistribution percentages for general election candidates"""
        try:
            # Get general election candidates (primary winners) for this seat
            winners_col = self.bot.db["winners"]
            winners_config = winners_col.find_one({"guild_id": guild_id})

            if not winners_config:
                return {}

            # Get current year
            time_col, time_config = self._get_time_config(guild_id)
            current_year = time_config["current_rp_date"].year if time_config else 2024
            current_phase = time_config.get("current_phase", "") if time_config else ""

            # Find all primary winners (general election candidates) for this seat
            # For general campaign, look for primary winners from the previous year if we're in an even year
            # Or current year if odd year
            primary_year = current_year - 1 if current_year % 2 == 0 else current_year

            seat_candidates = [
                w for w in winners_config["winners"]
                if w.get("seat_id") == seat_id and w.get("year") == primary_year and w.get("primary_winner", False)
            ]

            # If no primary winners found, fall back to all candidates for this seat in the current year
            if not seat_candidates:
                seat_candidates = [
                    w for w in winners_config["winners"]
                    if w.get("seat_id") == seat_id and w.get("year") == current_year
                ]

            if not seat_candidates:
                return {}

            # Calculate baseline percentages based on party alignment
            baseline_percentages = {}
            num_candidates = len(seat_candidates)

            # Count major parties
            major_parties = ["Democratic", "Republican", "Democratic Party", "Republican Party"]
            parties_present = set(candidate.get("party", "") for candidate in seat_candidates)
            major_parties_present = [party for party in major_parties if party in parties_present]
            
            # Check if we have the standard 3-party setup: Republican + Democratic + Independent
            has_republican = any("Republican" in party for party in parties_present)
            has_democratic = any("Democratic" in party for party in parties_present)
            has_independent = any("Independent" in party for party in parties_present)
            is_standard_three_way = has_republican and has_democratic and has_independent and len(parties_present) == 3

            if len(major_parties_present) == 2 or is_standard_three_way:
                # Standard two-party setup or three-party setup
                num_parties = len(parties_present)
                if num_parties == 2:
                    # Pure two-party race
                    for candidate in seat_candidates:
                        baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = 50.0
                else:
                    # Two major parties + others (40-40-20 for 3 parties)
                    remaining_percentage = 20.0  # 100 - 40 - 40
                    other_parties_count = num_parties - 2
                    other_party_percentage = remaining_percentage / other_parties_count if other_parties_count > 0 else 0

                    for candidate in seat_candidates:
                        party = candidate.get("party", "")
                        if (party in major_parties or 
                            "Republican" in party or 
                            "Democratic" in party):
                            baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = 40.0
                        else:
                            baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = other_party_percentage
            else:
                # No standard major party setup, split evenly
                for candidate in seat_candidates:
                    baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = 100.0 / num_candidates

            # Apply proportional redistribution with minimum floors
            final_percentages = {}

            # Define minimum percentage floors
            def get_minimum_floor(candidate):
                party = candidate.get('party', '').lower()
                if any(keyword in party for keyword in ['democrat', 'republican']):
                    return 25.0  # 25% minimum for major parties
                else:
                    return 2.0   # 2% minimum for independents/third parties

            # Calculate total campaign points across all candidates in this seat
            total_campaign_points = sum(candidate.get('points', 0.0) for candidate in seat_candidates)

            # Start with baseline percentages
            current_percentages = baseline_percentages.copy()

            # Apply campaign effects using proportional redistribution
            if total_campaign_points > 0:
                for candidate in seat_candidates:
                    candidate_name = candidate.get('candidate', candidate.get('name', ''))
                    candidate_points = candidate.get('points', 0.0)

                    if candidate_points > 0:
                        # This candidate gains points
                        points_gained = candidate_points

                        # Calculate total percentage that can be taken from other candidates
                        total_available_to_take = 0.0
                        for other_candidate in seat_candidates:
                            if other_candidate != candidate:
                                other_name = other_candidate.get('candidate', other_candidate.get('name', ''))
                                other_current = current_percentages[other_name]
                                other_minimum = get_minimum_floor(other_candidate)
                                available = max(0, other_current - other_minimum)
                                total_available_to_take += available

                        # Limit gains to what's actually available
                        actual_gain = min(points_gained, total_available_to_take)
                        current_percentages[candidate_name] += actual_gain

                        # Distribute losses proportionally among other candidates
                        if total_available_to_take > 0 and actual_gain > 0:
                            for other_candidate in seat_candidates:
                                if other_candidate != candidate:
                                    other_name = other_candidate.get('candidate', other_candidate.get('name', ''))
                                    other_current = current_percentages[other_name]
                                    other_minimum = get_minimum_floor(other_candidate)
                                    available = max(0, other_current - other_minimum)

                                    if available > 0:
                                        loss_proportion = available / total_available_to_take
                                        loss = actual_gain * loss_proportion
                                        current_percentages[other_name] -= loss

            # Ensure percentages sum to 100% and respect minimums
            total_percentage = sum(current_percentages.values())
            if total_percentage > 0:
                for candidate_name in current_percentages:
                    current_percentages[candidate_name] = (current_percentages[candidate_name] / total_percentage) * 100.0

            # Final verification and correction for floating point errors
            final_total = sum(current_percentages.values())
            if abs(final_total - 100.0) > 0.001:
                # Apply micro-adjustment to the largest percentage instead of equal distribution
                largest_candidate = max(current_percentages.keys(), key=lambda x: current_percentages[x])
                adjustment = 100.0 - final_total
                current_percentages[largest_candidate] += adjustment

            final_percentages = current_percentages
            return final_percentages
        except Exception as e:
            print(f"Error in _calculate_zero_sum_percentages: {e}")
            return {}

    def _update_general_candidate_stats(self, guild_id: int, user_id: int, state_name: str, 
                                       points_gained: float, stamina_cost: float = 0, 
                                       corruption_increase: int = 0, candidate_data: dict = None,
                                       action_user_id: int = None):
        """Update general candidate's points, stamina, and corruption in winners collection"""
        try:
            if not user_id or not state_name:
                print("Error: Missing required parameters in _update_general_candidate_stats")
                return
                
            time_col, time_config = self._get_time_config(guild_id)
            current_phase = time_config.get("current_phase", "") if time_config else ""

            if current_phase != "General Campaign":
                return

            # Apply momentum multiplier during General Campaign
            actual_points_gained = points_gained
            momentum_multiplier = 1.0

            # Get momentum multiplier
            momentum_cog = self.bot.get_cog('Momentum')
            if momentum_cog and candidate_data:
                momentum_col, momentum_config = momentum_cog._get_momentum_config(guild_id)

                # Determine party key
                party_key = self._normalize_party_key(candidate_data.get("party", ""))

                momentum_multiplier = momentum_cog._calculate_momentum_campaign_multiplier(state_name.upper(), party_key, momentum_config)
                actual_points_gained = points_gained * momentum_multiplier

                print(f"DEBUG: Applied momentum multiplier {momentum_multiplier:.2f}x to points: {points_gained:.2f} -> {actual_points_gained:.2f}")

            # Determine who pays the stamina cost
            stamina_deduction_user_id = user_id  # Default to target candidate

            if action_user_id and action_user_id != user_id:
                # Check if action user is a candidate with enough stamina
                winners_col = self.bot.db["winners"]
                winners_config = winners_col.find_one({"guild_id": guild_id})
                
                if winners_config and "winners" in winners_config:
                    for winner in winners_config["winners"]:
                        if winner.get("user_id") == action_user_id and winner.get("stamina", 0) >= stamina_cost:
                            stamina_deduction_user_id = action_user_id
                            break

            # Update candidate points in winners collection
            winners_col = self.bot.db["winners"]
            winners_col.update_one(
                {"guild_id": guild_id, "winners.user_id": user_id},
                {
                    "$inc": {
                        f"winners.$.state_points.{state_name.upper()}": actual_points_gained,
                        "winners.$.corruption": corruption_increase,
                        "winners.$.total_points": actual_points_gained
                    }
                }
            )

            # Deduct stamina from the determined user
            winners_col.update_one(
                {"guild_id": guild_id, "winners.user_id": stamina_deduction_user_id},
                {"$inc": {"winners.$.stamina": -stamina_cost}}
            )

            # Add momentum effects during General Campaign (use the boosted points)
            print(f"DEBUG: Adding momentum from general campaign stats update: {actual_points_gained} points in {state_name.upper()}")
            self._add_momentum_from_general_action(guild_id, user_id, state_name.upper(), actual_points_gained, candidate_data)

        except Exception as e:
            print(f"Error in _update_general_candidate_stats: {e}")
            import traceback
            traceback.print_exc()

    def _add_momentum_from_general_action(self, guild_id: int, user_id: int, state_name: str, points_gained: float, candidate_data: dict = None, target_name: str = None):
        """Adds momentum to a state based on general campaign actions."""
        try:
            if not user_id or not state_name or not points_gained:
                print("Error: Missing required parameters in _add_momentum_from_general_action")
                return
                
            # Check if we're in General Campaign phase
            time_col, time_config = self._get_time_config(guild_id)
            current_phase = time_config.get("current_phase", "") if time_config else ""

            if current_phase != "General Campaign":
                return

            # Use the momentum system from the momentum cog
            momentum_cog = self.bot.get_cog('Momentum')
            if not momentum_cog:
                return

            # Get momentum config
            momentum_col, momentum_config = momentum_cog._get_momentum_config(guild_id)

            # Determine which candidate's party to use for momentum
            target_candidate = candidate_data
            if target_name and (not candidate_data or target_name != candidate_data.get("name")):
                # Look for the target candidate in signups first (primary source)
                signups_col = self.bot.db["signups"]
                signups_config = signups_col.find_one({"guild_id": guild_id})

                if signups_config:
                    current_year = time_config["current_rp_date"].year if time_config else 2024
                    for candidate in signups_config.get("candidates", []):
                        if (candidate.get("name", "").lower() == target_name.lower() and 
                            candidate["year"] == current_year):
                            target_candidate = candidate
                            break

                # If not found, try all_signups collection
                if not target_candidate:
                    all_signups_col = self.bot.db["all_signups"]
                    all_signups_config = all_signups_col.find_one({"guild_id": guild_id})

                    if all_signups_config:
                        current_year = time_config["current_rp_date"].year if time_config else 2024
                        for candidate in all_signups_config.get("candidates", []):
                            if (candidate.get("name", "").lower() == target_name.lower() and 
                                candidate["year"] == current_year):
                                target_candidate = candidate
                                break

            # If we still don't have a target candidate, try to find them in winners (for General Campaign)
            if not target_candidate and target_name:
                winners_col = self.bot.db["winners"]
                winners_config = winners_col.find_one({"guild_id": guild_id})

                if winners_config and "winners" in winners_config:
                    current_year = time_config["current_rp_date"].year if time_config else 2024
                    for winner in winners_config["winners"]:
                        if (winner.get("candidate", "").lower() == target_name.lower() and 
                            winner.get("year") == current_year and
                            winner.get("primary_winner", False)):
                            # Create a temporary candidate dict with party info
                            target_candidate = {
                                "name": winner.get("candidate"),
                                "party": winner.get("party", "Independent")
                            }
                            break

            if not target_candidate or not isinstance(target_candidate, dict) or not target_candidate.get("party"):
                return

            # Determine party key
            party_key = self._normalize_party_key(target_candidate.get("party", ""))

            # Validate state name exists in momentum config
            if state_name not in momentum_config["state_momentum"]:
                return

            # Calculate campaign effectiveness multiplier based on current momentum
            current_momentum = momentum_config["state_momentum"].get(state_name, {}).get(party_key, 0.0)
            campaign_multiplier = momentum_cog._calculate_momentum_campaign_multiplier(state_name, party_key, momentum_config)

            # Apply momentum multiplier to the original campaign points
            boosted_points = points_gained * campaign_multiplier

            print(f"DEBUG: General campaign - Original points: {points_gained:.2f}, Momentum multiplier: {campaign_multiplier:.2f}x, Boosted points: {boosted_points:.2f}")

            # Calculate momentum gained
            momentum_gain_factor = 1.5  # Slightly less than presidential actions
            momentum_gained = boosted_points * momentum_gain_factor

            new_momentum = current_momentum + momentum_gained

            # Check for auto-collapse and apply if needed
            final_momentum, collapsed = momentum_cog._check_and_apply_auto_collapse(
                momentum_col, guild_id, state_name, party_key, new_momentum
            )

            if not collapsed:
                # Update momentum in database
                momentum_col.update_one(
                    {"guild_id": guild_id},
                    {
                        "$set": {
                            f"state_momentum.{state_name}.{party_key}": final_momentum,
                            f"state_momentum.{state_name}.last_updated": datetime.utcnow()
                        }
                    }
                )

                # Log the momentum gain event
                if momentum_gained > 0.1:
                    action_desc = f"General campaign action for {target_candidate.get('name', 'Unknown')} (+{points_gained:.1f} pts)"
                    momentum_cog._add_momentum_event(
                        momentum_col, guild_id, state_name, party_key,
                        momentum_gained, action_desc, user_id
                    )

        except Exception as e:
            print(f"Error in _add_momentum_from_general_action: {e}")

    def _determine_stamina_user(self, guild_id: int, user_id: int, target_candidate_data: dict, stamina_cost: float):
        """Determines whether the user or the target candidate pays the stamina cost."""
        try:
            # Get the user's candidate data
            _, user_candidate_data = self._get_user_candidate(guild_id, user_id)

            # If the user is a candidate and has enough stamina, they pay.
            if user_candidate_data and isinstance(user_candidate_data, dict) and user_candidate_data.get("stamina", 0) >= stamina_cost:
                return user_id

            # Otherwise, the target candidate pays if they exist and have enough stamina.
            if target_candidate_data and isinstance(target_candidate_data, dict) and target_candidate_data.get("stamina", 0) >= stamina_cost:
                return target_candidate_data.get("user_id")

            # If neither can pay, return the target's user ID as a fallback (though the action will likely fail).
            return target_candidate_data.get("user_id") if target_candidate_data else user_id
        except Exception as e:
            print(f"Error in _determine_stamina_user: {e}")
            return target_candidate_data.get("user_id") if target_candidate_data else user_id

    def _deduct_stamina_from_user(self, guild_id: int, user_id: int, cost: float):
        """Deducts stamina from a user's candidate profile."""
        try:
            # Try signups collection first (primary source)
            signups_col = self.bot.db["signups"]
            result = signups_col.update_one(
                {"guild_id": guild_id, "candidates.user_id": user_id},
                {"$inc": {"candidates.$.stamina": -cost}}
            )
            
            # If not found in signups, try all_signups collection
            if result.matched_count == 0:
                all_signups_col = self.bot.db["all_signups"]
                result = all_signups_col.update_one(
                    {"guild_id": guild_id, "candidates.user_id": user_id},
                    {"$inc": {"candidates.$.stamina": -cost}}
                )
                
                # If still not found, try winners collection (for General Campaign)
                if result.matched_count == 0:
                    winners_col = self.bot.db["winners"]
                    winners_col.update_one(
                        {"guild_id": guild_id, "winners.user_id": user_id},
                        {"$inc": {"winners.$.stamina": -cost}}
                    )
        except Exception as e:
            print(f"Error deducting stamina from user {user_id}: {e}")


async def setup(bot):
    await bot.add_cog(GeneralCampaignActions(bot))