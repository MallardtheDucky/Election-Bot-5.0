import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import random
from typing import Optional, List
from .ideology import STATE_DATA

class Polling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("Polling cog loaded successfully")

    # Simplified polling structure
    poll_group = app_commands.Group(name="poll", description="Polling commands")

    # Combine admin and info into single manage group
    poll_manage_group = app_commands.Group(name="manage", description="Poll management commands", parent=poll_group, default_permissions=discord.Permissions(administrator=True))


    def _get_signups_config(self, guild_id: int):
        """Get signups configuration"""
        col = self.bot.db["signups"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_winners_config(self, guild_id: int):
        """Get winners configuration"""
        col = self.bot.db["winners"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_time_config(self, guild_id: int):
        """Get time configuration to check current phase"""
        col = self.bot.db["time_configs"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_user_candidate(self, guild_id: int, user_id: int):
        """Get user's candidate information based on current phase"""
        time_col, time_config = self._get_time_config(guild_id)
        current_phase = time_config.get("current_phase", "") if time_config else ""
        current_year = time_config["current_rp_date"].year if time_config else 2024

        if current_phase == "General Campaign":
            # Look in winners collection for general campaign
            winners_col = self.bot.db["winners"]
            winners_config = winners_col.find_one({"guild_id": guild_id})

            if not winners_config:
                return None, None

            # For general campaign, look for primary winners from the current election year
            for winner in winners_config["winners"]:
                if (winner["user_id"] == user_id and
                    winner.get("primary_winner", False) and
                    winner["year"] == current_year):
                    return winners_col, winner

            return winners_col, None

        else:
            # Look in signups collection for primary campaign
            signups_col, signups_config = self._get_signups_config(guild_id)

            if not signups_config:
                return None, None

            for candidate in signups_config["candidates"]:
                if candidate["user_id"] == user_id and candidate["year"] == current_year:
                    return signups_col, candidate

            return signups_col, None

    def _get_candidate_by_name(self, guild_id: int, candidate_name: str):
        """Get candidate by name based on current phase"""
        time_col, time_config = self._get_time_config(guild_id)
        current_phase = time_config.get("current_phase", "") if time_config else ""
        current_year = time_config["current_rp_date"].year if time_config else 2024

        if current_phase == "General Campaign":
            # First check presidential signups directly for presidential candidates
            pres_signups_col = self.bot.db["presidential_signups"]
            pres_signups_config = pres_signups_col.find_one({"guild_id": guild_id})

            if pres_signups_config:
                # Try multiple signup years to be safe
                possible_years = [current_year, current_year - 1, current_year - 2]

                for signup_year in possible_years:
                    for candidate in pres_signups_config.get("candidates", []):
                        if (candidate["name"].lower() == candidate_name.lower() and 
                            candidate["year"] == signup_year and
                            candidate["office"] == "President"):
                            return pres_signups_col, candidate

            # Also check presidential winners collection
            pres_winners_col = self.bot.db["presidential_winners"]
            pres_winners_config = pres_winners_col.find_one({"guild_id": guild_id})

            if pres_winners_config:
                winners_data = pres_winners_config.get("winners", {})
                if isinstance(winners_data, dict):
                    # Check if this candidate is a primary winner
                    for party, winner_name in winners_data.items():
                        if isinstance(winner_name, str) and winner_name.lower() == candidate_name.lower():
                            # Get full candidate data from presidential signups
                            if pres_signups_config:
                                election_year = pres_winners_config.get("election_year", current_year)
                                signup_year = election_year - 1 if election_year % 2 == 0 else election_year

                                for candidate in pres_signups_config.get("candidates", []):
                                    if (candidate["name"].lower() == candidate_name.lower() and 
                                        candidate["year"] == signup_year and
                                        candidate["office"] == "President"):
                                        return pres_signups_col, candidate

            # If not presidential, look in regular winners collection
            winners_col = self.bot.db["winners"]
            winners_config = winners_col.find_one({"guild_id": guild_id})

            if winners_config:
                # Primary winners are stored with the election year (current year during General Campaign)
                for winner in winners_config["winners"]:
                    if (winner.get("candidate", "").lower() == candidate_name.lower() and
                        winner.get("primary_winner", False) and
                        winner["year"] == current_year):
                        return winners_col, winner

            return None, None
        else:
            # Look in signups collection for primary campaign (including presidential)
            signups_col, signups_config = self._get_signups_config(guild_id)
            if signups_config:
                for candidate in signups_config["candidates"]:
                    if candidate["name"].lower() == candidate_name.lower() and candidate["year"] == current_year:
                        return signups_col, candidate

            # Also check presidential signups
            pres_signups_col = self.bot.db["presidential_signups"]
            pres_signups_config = pres_signups_col.find_one({"guild_id": guild_id})
            if pres_signups_config:
                for candidate in pres_signups_config.get("candidates", []):
                    if (candidate["name"].lower() == candidate_name.lower() and 
                        candidate["year"] == current_year):
                        return pres_signups_col, candidate

            return None, None

    def _calculate_zero_sum_percentages(self, guild_id: int, seat_id: str):
        """Calculate zero-sum redistribution percentages for general election candidates"""
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
        # For general campaign, look for primary winners from the current election year
        seat_candidates = [
            w for w in winners_config["winners"]
            if w["seat_id"] == seat_id and w["year"] == current_year and w.get("primary_winner", False)
        ]

        # If no primary winners found, fall back to all candidates for this seat in the current year
        if not seat_candidates:
            seat_candidates = [
                w for w in winners_config["winners"]
                if w["seat_id"] == seat_id and w["year"] == current_year
            ]

        if not seat_candidates:
            return {}

        # Get momentum effects if in General Campaign phase and this is a presidential race
        momentum_effects = {}
        if (current_phase == "General Campaign" and
            any(c.get("office") in ["President", "Vice President"] for c in seat_candidates)):
            momentum_effects = self._get_momentum_effects_for_candidates(guild_id, seat_candidates)

        # Get state name from seat_id for momentum calculation
        state_name = self._extract_state_from_seat_id(seat_id)

        # Determine baseline percentages based on number of candidates and parties
        num_candidates = len(seat_candidates)
        parties = set(candidate["party"] for candidate in seat_candidates)
        num_parties = len(parties)

        # Count major parties (Democrat and Republican)
        major_parties = {"Democrat", "Republican", "Democratic Party", "Republican Party"}
        major_parties_present = len([p for p in parties if p in major_parties])
        
        # Check if we have the standard 3-party setup: Republican + Democratic + Independent
        has_republican = any("Republican" in party for party in parties)
        has_democratic = any("Democratic" in party for party in parties)
        has_independent = any("Independent" in party for party in parties)
        is_standard_three_way = has_republican and has_democratic and has_independent and num_parties == 3

        # Set baseline percentages based on number of parties
        baseline_percentages = {}

        if num_parties == 2:
            # Two parties: 50-50 split
            for candidate in seat_candidates:
                baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = 50.0
        elif num_parties == 3:
            # Three parties: 40-40-20 (if Dem+Rep+other) or equal split
            if major_parties_present == 2 or is_standard_three_way:
                for candidate in seat_candidates:
                    if candidate["party"] in major_parties or "Republican" in candidate["party"] or "Democratic" in candidate["party"]:
                        baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = 40.0
                    else:
                        baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = 20.0
            else:
                # Equal split if not standard Dem-Rep-other
                for candidate in seat_candidates:
                    baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = 100.0 / 3
        elif num_parties == 4:
            # Four parties: 40-40-10-10 (if Dem+Rep+two others) or equal split
            if major_parties_present == 2:
                for candidate in seat_candidates:
                    if candidate["party"] in major_parties:
                        baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = 40.0
                    else:
                        baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = 10.0
            else:
                # Equal split if not standard setup
                for candidate in seat_candidates:
                    baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = 25.0
        else:
            # 5+ parties: prioritize taking from other/independents
            if major_parties_present == 2:
                # Democrat + Republican + multiple others: 40-40 for major, split remainder among others
                remaining_percentage = 20.0  # 100 - 40 - 40
                other_parties_count = num_parties - 2
                other_party_percentage = remaining_percentage / other_parties_count if other_parties_count > 0 else 0

                for candidate in seat_candidates:
                    if candidate["party"] in major_parties:
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
                    if total_available_to_take > 0:
                        for other_candidate in seat_candidates:
                            if other_candidate != candidate:
                                other_name = other_candidate.get('candidate', other_candidate.get('name', ''))
                                other_current = current_percentages[other_name]
                                other_minimum = get_minimum_floor(other_candidate)
                                available = max(0, other_current - other_minimum)

                                if available > 0:
                                    proportional_loss = (available / total_available_to_take) * actual_gain
                                    current_percentages[other_name] -= proportional_loss

        # Apply momentum effects if available
        for candidate in seat_candidates:
            candidate_name = candidate.get('candidate', candidate.get('name', ''))
            momentum_effect = momentum_effects.get(candidate_name, 0.0)
            current_percentages[candidate_name] += momentum_effect

        # Ensure minimum floors are respected
        for candidate in seat_candidates:
            candidate_name = candidate.get('candidate', candidate.get('name', ''))
            minimum_floor = get_minimum_floor(candidate)
            current_percentages[candidate_name] = max(current_percentages[candidate_name], minimum_floor)

        # COMPLETE 100% NORMALIZATION - Force total to exactly 100%
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

    def _get_momentum_effects_for_candidates(self, guild_id: int, candidates: list) -> dict:
        """Get momentum effects for presidential candidates"""
        try:
            momentum_col = self.bot.db["momentum_config"]
            momentum_config = momentum_col.find_one({"guild_id": guild_id})

            if not momentum_config:
                return {}

            momentum_effects = {}

            for candidate in candidates:
                candidate_name = candidate.get('candidate', candidate.get('name', ''))
                candidate_party = candidate.get('party', '')

                # Convert party name to standard format
                if "republican" in candidate_party.lower():
                    party_key = "Republican"
                elif "democrat" in candidate_party.lower():
                    party_key = "Democrat"
                else:
                    party_key = "Independent"

                # Calculate national momentum effect (average across all states where they're campaigning)
                total_momentum = 0.0
                state_count = 0

                # Get candidate's state points to determine which states they've campaigned in
                state_points = candidate.get("state_points", {})
                if state_points:
                    for state_name, points in state_points.items():
                        if points > 0:  # Only count states where they've campaigned
                            state_momentum = momentum_config["state_momentum"].get(state_name, {}).get(party_key, 0.0)
                            momentum_effect = self._calculate_momentum_effect_on_polling(state_name, party_key, momentum_config)
                            total_momentum += momentum_effect
                            state_count += 1

                if state_count > 0:
                    avg_momentum_effect = total_momentum / state_count
                else:
                    avg_momentum_effect = 0.0

                momentum_effects[candidate_name] = avg_momentum_effect

            return momentum_effects

        except Exception as e:
            print(f"Error calculating momentum effects: {e}")
            return {}

    def _extract_state_from_seat_id(self, seat_id: str) -> str:
        """Extract state name from seat ID for momentum calculations"""
        # For presidential races, we need to handle them differently
        if seat_id in ["US-PRES", "US-VP"]:
            return "NATIONAL"  # Special handling for national races

        # For other seats, extract state code (e.g., "SEN-CA-1" -> "CA")
        parts = seat_id.split("-")
        if len(parts) >= 2:
            state_code = parts[1]
            # Map state codes to full names if needed
            state_code_to_name = {
                "CA": "CALIFORNIA", "TX": "TEXAS", "NY": "NEW YORK",
                "FL": "FLORIDA", "PA": "PENNSYLVANIA", "IL": "ILLINOIS",
                "OH": "OHIO", "GA": "GEORGIA", "NC": "NORTH CAROLINA",
                "MI": "MICHIGAN", "NJ": "NEW JERSEY", "VA": "VIRGINIA",
                "WA": "WASHINGTON", "AZ": "ARIZONA", "MA": "MASSACHUSETTS",
                "TN": "TENNESSEE", "IN": "INDIANA", "MO": "MISSOURI",
                "MD": "MARYLAND", "WI": "WISCONSIN", "CO": "COLORADO",
                "MN": "MINNESOTA", "SC": "SOUTH CAROLINA", "AL": "ALABAMA",
                "LA": "LOUISIANA", "KY": "KENTUCKY", "OR": "OREGON",
                "OK": "OKLAHOMA", "CT": "CONNECTICUT", "IA": "IOWA",
                "MS": "MISSISSIPPI", "AR": "ARKANSAS", "KS": "KANSAS",
                "UT": "UTAH", "NV": "NEVADA", "NM": "NEW MEXICO",
                "WV": "WEST VIRGINIA", "NE": "NEBRASKA", "ID": "IDAHO",
                "HI": "HAWAII", "ME": "MAINE", "NH": "NEW HAMPSHIRE",
                "RI": "RHODE ISLAND", "MT": "MONTANA", "DE": "DELAWARE",
                "SD": "SOUTH DAKOTA", "ND": "NORTH DAKOTA", "AK": "ALASKA",
                "VT": "VERMONT", "WY": "WYOMING"
            }
            return state_code_to_name.get(state_code, state_code)

        return "UNKNOWN"

    def _calculate_momentum_effect_on_polling(self, state: str, party: str, momentum_config: dict) -> float:
        """Calculate how momentum affects polling percentages"""
        state_momentum = momentum_config["state_momentum"].get(state, {})
        party_momentum = state_momentum.get(party, 0.0)

        # Convert momentum to polling percentage change
        # Each 10 points of momentum = ~1% polling change
        polling_effect = party_momentum / 10.0

        # Cap the effect to prevent extreme swings
        return max(-15.0, min(15.0, polling_effect))


    def _calculate_poll_result(self, actual_percentage: float, margin_of_error: float = 7.0) -> float:
        """Calculate poll result with margin of error"""
        # Apply random variation within margin of error
        variation = random.uniform(-margin_of_error, margin_of_error)
        poll_result = actual_percentage + variation

        # Ensure result stays within reasonable bounds (0-100%)
        poll_result = max(0.1, min(99.9, poll_result))

        return poll_result

    # Commands under /poll group
    @poll_group.command(
        name="candidate",
        description="Conduct an NPC poll for a specific candidate (shows polling with 7% margin of error)"
    )
    @app_commands.describe(candidate_name="The candidate to poll (leave blank to poll yourself)")
    async def poll(self, interaction: discord.Interaction, candidate_name: Optional[str] = None):
        # Check if we're in a campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config.get("current_phase", "") not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Polls can only be conducted during campaign phases.",
                ephemeral=True
            )
            return

        current_phase = time_config.get("current_phase", "")

        # If no candidate specified, check if user is a candidate
        if not candidate_name:
            signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)
            if not candidate:
                await interaction.response.send_message(
                    "❌ You must specify a candidate name or be a registered candidate yourself.",
                    ephemeral=True
                )
                return
            candidate_name = candidate.get('candidate') or candidate.get('name')

        # Get the candidate
        signups_col, candidate = self._get_candidate_by_name(interaction.guild.id, candidate_name)
        if not candidate:
            await interaction.response.send_message(
                f"❌ Candidate '{candidate_name}' not found.",
                ephemeral=True
            )
            return

        # Calculate actual polling percentage
        candidate_display_name = candidate.get('candidate') or candidate.get('name')

        if current_phase == "General Campaign":
            # For general campaign, use zero-sum percentages
            zero_sum_percentages = self._calculate_zero_sum_percentages(interaction.guild.id, candidate["seat_id"])
            actual_percentage = zero_sum_percentages.get(candidate_display_name, 50.0)
        else:
            # For primary campaign, calculate based on points relative to competition
            # Get all candidates for same seat and party
            if current_phase == "Primary Campaign":
                signups_col, signups_config = self._get_signups_config(interaction.guild.id)
                if signups_config:
                    current_year = time_config["current_rp_date"].year
                    seat_party_candidates = [
                        c for c in signups_config["candidates"]
                        if (c["seat_id"] == candidate["seat_id"] and
                            c["party"] == candidate["party"] and
                            c["year"] == current_year)
                    ]

                    if len(seat_party_candidates) == 1:
                        actual_percentage = 85.0  # Unopposed in primary
                    else:
                        # Calculate relative position based on points
                        total_points = sum(c.get('points', 0) for c in seat_party_candidates)
                        if total_points == 0:
                            actual_percentage = 100.0 / len(seat_party_candidates)  # Even split
                        else:
                            candidate_points = candidate.get('points', 0)
                            actual_percentage = (candidate_points / total_points) * 100.0
                            # Ensure minimum viable percentage
                            actual_percentage = max(15.0, actual_percentage)
                else:
                    actual_percentage = 50.0
            else:
                actual_percentage = 50.0

        # Apply margin of error
        poll_result = self._calculate_poll_result(actual_percentage, margin_of_error=7.0)

        # Generate random polling organization
        polling_orgs = [
            "Mason-Dixon Polling", "Quinnipiac University", "Marist Poll",
            "Suffolk University", "Emerson College", "Public Policy Polling",
            "SurveyUSA", "Ipsos/Reuters", "YouGov", "Rasmussen Reports",
            "CNN/SSRS", "Fox News Poll", "ABC News/Washington Post",
            "CBS News/YouGov", "NBC News/Washington Post"
        ]

        polling_org = random.choice(polling_orgs)

        # Generate sample size and date
        sample_size = random.randint(400, 1200)
        days_ago = random.randint(1, 5)

        embed = discord.Embed(
            title="📊 NPC Poll Results",
            description=f"Latest polling data for **{candidate_display_name}**",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="🎯 Candidate",
            value=f"**{candidate_display_name}** ({candidate['party']})\n"
                  f"Running for: {candidate['seat_id']}\n"
                  f"Office: {candidate['office']}\n"
                  f"Region: {candidate.get('region') or candidate.get('state', 'Unknown')}",
            inline=True
        )

        # Create visual progress bar
        def create_progress_bar(percentage, width=20):
            filled = int((percentage / 100) * width)
            empty = width - filled
            return "█" * filled + "░" * empty

        # Get party abbreviation
        party_abbrev = candidate['party'][0] if candidate['party'] else "I"

        progress_bar = create_progress_bar(poll_result)

        embed.add_field(
            name="📈 Poll Results",
            value=f"**{party_abbrev} - {candidate['party']}**\n"
                  f"{progress_bar} **{poll_result:.1f}%**\n"
                  f"Phase: {current_phase}",
            inline=True
        )

        embed.add_field(
            name="📋 Poll Details",
            value=f"**Polling Organization:** {polling_org}\n"
                  f"**Sample Size:** {sample_size:,} likely voters\n"
                  f"**Margin of Error:** ±7.0%\n"
                  f"**Field Period:** {days_ago} day{'s' if days_ago > 1 else ''} ago",
            inline=False
        )

        # Add context based on phase
        if current_phase == "Primary Campaign":
            # Show primary competition context
            signups_col, signups_config = self._get_signups_config(interaction.guild.id)
            if signups_config:
                current_year = time_config["current_rp_date"].year
                primary_competitors = [
                    c for c in signups_config["candidates"]
                    if (c["seat_id"] == candidate["seat_id"] and
                        c["party"] == candidate["party"] and
                        c["year"] == current_year)
                ]

                if len(primary_competitors) > 1:
                    embed.add_field(
                        name="🔍 Primary Context",
                        value=f"Competing against {len(primary_competitors) - 1} other {candidate['party']} candidate{'s' if len(primary_competitors) > 1 else ''} in the primary",
                        inline=False
                    )
        else:
            # Show general election context
            zero_sum_percentages = self._calculate_zero_sum_percentages(interaction.guild.id, candidate["seat_id"])
            if len(zero_sum_percentages) > 1:
                embed.add_field(
                    name="🔍 General Election Context",
                    value=f"Competing against {len(zero_sum_percentages) - 1} other candidate{'s' if len(zero_sum_percentages) > 2 else ''} in the general election",
                    inline=False
                )

        embed.add_field(
            name="⚠️ Disclaimer",
            value="This is a simulated poll with a ±7% margin of error. Results may not reflect actual campaign performance.",
            inline=False
        )

        embed.set_footer(text=f"Poll conducted by {polling_org}")

        await interaction.response.send_message(embed=embed)

    @poll_group.command(
        name="state",
        description="Conduct an NPC poll for all parties in a specific state, showing Rep/Dem/Independent support."
    )
    @app_commands.describe(state="The state to poll (e.g., 'California', 'NY')")
    async def state_poll(self, interaction: discord.Interaction, state: str):
        # Check if we're in a campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config.get("current_phase", "") not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Polls can only be conducted during campaign phases.",
                ephemeral=True
            )
            return

        current_phase = time_config.get("current_phase", "")
        current_year = time_config["current_rp_date"].year

        # Use STATE_DATA to get base percentages for Republican, Democrat, and Independent
        state_info = STATE_DATA.get(state.upper())  # STATE_DATA uses uppercase keys

        if not state_info:
            await interaction.response.send_message(
                f"❌ State data not found for '{state}'. Cannot determine party base percentages.",
                ephemeral=True
            )
            return

        # Get base party percentages from STATE_DATA
        republican_base = state_info.get("republican", 33.0)
        democrat_base = state_info.get("democrat", 33.0)
        independent_base = state_info.get("other", 34.0)

        # Calculate poll results with margin of error
        poll_results = {
            "Republican": self._calculate_poll_result(republican_base),
            "Democrat": self._calculate_poll_result(democrat_base),
            "Independent": self._calculate_poll_result(independent_base)
        }

        # Sort results for display
        sorted_results = sorted(poll_results.items(), key=lambda item: item[1], reverse=True)

        # Generate polling details
        polling_orgs = [
            "Statewide Polling Inc.", "Political Analytics", "Voter Insight Group",
            "State University Poll", "Regional Polling Institute"
        ]
        polling_org = random.choice(polling_orgs)
        sample_size = random.randint(800, 2500)
        days_ago = random.randint(2, 6)

        embed = discord.Embed(
            title=f"📊 State Poll: {state}",
            description=f"**Party Support Breakdown** • {current_phase} ({current_year})",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        # Create visual progress bar function
        def create_progress_bar(percentage, width=20):
            filled = int((percentage / 100) * width)
            empty = width - filled
            return "█" * filled + "░" * empty

        results_text = ""
        for party, poll_percentage in sorted_results:
            # Party abbreviations
            party_abbrev = "R" if party == "Republican" else ("D" if party == "Democrat" else "I")

            progress_bar = create_progress_bar(poll_percentage)
            results_text += f"**{party_abbrev} - {party}**\n"
            results_text += f"{progress_bar} **{poll_percentage:.1f}%**\n\n"

        embed.add_field(
            name="📈 Party Support",
            value=results_text,
            inline=False
        )

        embed.add_field(
            name="📋 Poll Details",
            value=f"**Polling Organization:** {polling_org}\n"
                  f"**Sample Size:** {sample_size:,} likely voters\n"
                  f"**Margin of Error:** ±7.0%\n"
                  f"**Field Period:** {days_ago} day{'s' if days_ago > 1 else ''} ago",
            inline=False
        )

        embed.add_field(
            name="⚠️ Disclaimer",
            value="This is a simulated poll with a ±7% margin of error. Results may not reflect actual campaign performance.",
            inline=False
        )

        embed.set_footer(text=f"Poll conducted by {polling_org}")

        await interaction.response.send_message(embed=embed)

    @poll_group.command(
        name="private_seat",
        description="Conduct a private poll for a specific seat (3% margin of error, costs 1 stamina, candidates only)"
    )
    @app_commands.describe(
        seat_id="The seat to poll (e.g., 'SEN-CA-1', 'CA-GOV')",
        candidate_name="Specific candidate to highlight (leave blank to highlight yourself)"
    )
    async def private_seat_poll(self, interaction: discord.Interaction, seat_id: str, candidate_name: Optional[str] = None):
        # Check if user is a candidate
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config.get("current_phase", "") not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Polls can only be conducted during campaign phases.",
                ephemeral=True
            )
            return

        current_phase = time_config.get("current_phase", "")
        current_year = time_config["current_rp_date"].year

        # Check if user is a valid candidate
        user_candidate = None

        # Check in signups
        signups_col, signups_config = self._get_signups_config(interaction.guild.id)
        if signups_config:
            for candidate in signups_config["candidates"]:
                if candidate["user_id"] == interaction.user.id and candidate["year"] == current_year:
                    user_candidate = candidate
                    break

        # Check in winners if general campaign
        if not user_candidate and current_phase == "General Campaign":
            winners_col = self.bot.db["winners"]
            winners_config = winners_col.find_one({"guild_id": interaction.guild.id})
            if winners_config:
                # Primary winners are stored with the election year (current year during General Campaign)
                for winner in winners_config["winners"]:
                    if (winner["user_id"] == interaction.user.id and
                        winner.get("primary_winner", False) and
                        winner["year"] == current_year):
                        user_candidate = winner
                        break

        # Check in presidential signups
        if not user_candidate:
            pres_col = self.bot.db["presidential_signups"]
            pres_config = pres_col.find_one({"guild_id": interaction.guild.id})
            if pres_config:
                for candidate in pres_config.get("candidates", []):
                    if (candidate["user_id"] == interaction.user.id and
                        candidate["year"] == current_year):
                        user_candidate = candidate
                        break

        if not user_candidate:
            await interaction.response.send_message(
                "❌ Only active candidates can use private polling.",
                ephemeral=True
            )
            return

        # Check stamina
        current_stamina = user_candidate.get("stamina", 0)
        if current_stamina < 1:
            await interaction.response.send_message(
                "❌ You need at least 1 stamina to conduct a private poll.",
                ephemeral=True
            )
            return

        # Deduct stamina
        if user_candidate in signups_config.get("candidates", []):
            for i, candidate in enumerate(signups_config["candidates"]):
                if candidate["user_id"] == interaction.user.id and candidate["year"] == current_year:
                    signups_config["candidates"][i]["stamina"] = max(0, current_stamina - 1)
                    signups_col.update_one(
                        {"guild_id": interaction.guild.id},
                        {"$set": {"candidates": signups_config["candidates"]}}
                    )
                    break
        elif current_phase == "General Campaign" and "winners" in locals():
            winners_col.update_one(
                {"guild_id": interaction.guild.id, "winners.user_id": interaction.user.id},
                {"$inc": {"winners.$.stamina": -1}}
            )
        elif "pres_config" in locals():
            pres_col.update_one(
                {"guild_id": interaction.guild.id, "candidates.user_id": interaction.user.id},
                {"$inc": {"candidates.$.stamina": -1}}
            )

        # If no candidate specified, check if user is a candidate in this seat
        highlighted_candidate = None
        if not candidate_name:
            if user_candidate and user_candidate.get("seat_id", "").upper() == seat_id.upper():
                candidate_name = user_candidate.get('candidate') or user_candidate.get('name')
                highlighted_candidate = user_candidate

        # Get all candidates for the specified seat
        seat_candidates = []

        if current_phase == "General Campaign":
            winners_col = self.bot.db["winners"]
            winners_config = winners_col.find_one({"guild_id": interaction.guild.id})
            if winners_config:
                # Primary winners are stored with the election year (current year during General Campaign)
                seat_candidates = [
                    w for w in winners_config["winners"]
                    if (w["seat_id"].upper() == seat_id.upper() and
                        w.get("primary_winner", False) and
                        w["year"] == current_year)
                ]
        else:
            if signups_config:
                seat_candidates = [
                    c for c in signups_config["candidates"]
                    if (c["seat_id"].upper() == seat_id.upper() and
                        c["year"] == current_year)
                ]

        if not seat_candidates:
            await interaction.response.send_message(
                f"❌ No candidates found for seat '{seat_id}' in the current {current_phase.lower()}.",
                ephemeral=True
            )
            return

        # Find highlighted candidate if specified by name
        if candidate_name and not highlighted_candidate:
            for candidate in seat_candidates:
                candidate_display_name = candidate.get('candidate') or candidate.get('name')
                if candidate_display_name.lower() == candidate_name.lower():
                    highlighted_candidate = candidate
                    break

        # Calculate polling percentages (same logic as regular seat poll but with 3% margin of error)
        poll_results = []

        if current_phase == "General Campaign":
            zero_sum_percentages = self._calculate_zero_sum_percentages(interaction.guild.id, seat_id)
            for candidate in seat_candidates:
                candidate_name = candidate.get('candidate') or candidate.get('name')
                actual_percentage = zero_sum_percentages.get(candidate_name, 50.0)
                poll_result = self._calculate_poll_result(actual_percentage, margin_of_error=3.0)
                poll_results.append({
                    "candidate": candidate,
                    "name": candidate_name,
                    "actual": actual_percentage,
                    "poll": poll_result,
                    "is_highlighted": candidate == highlighted_candidate
                })
            # Normalize general election private poll percentages to sum to 100
            total_poll = sum(r["poll"] for r in poll_results) or 0.0
            if total_poll > 0:
                # Scale to 100 and round to one decimal place
                for r in poll_results:
                    r["poll"] = round((r["poll"] * 100.0) / total_poll, 1)

                # Adjust rounding drift to ensure exact 100.0 total
                drift = round(100.0 - sum(r["poll"] for r in poll_results), 1)
                if abs(drift) >= 0.1:
                    # Assign drift to the top polling candidate pre-sort to preserve intent
                    max_item = max(poll_results, key=lambda x: x["poll"]) if poll_results else None
                    if max_item is not None:
                        max_item["poll"] = round(max_item["poll"] + drift, 1)
        else:
            parties = {}
            for candidate in seat_candidates:
                party = candidate["party"]
                if party not in parties:
                    parties[party] = []
                parties[party].append(candidate)

            for party, party_candidates in parties.items():
                if len(party_candidates) == 1:
                    candidate = party_candidates[0]
                    candidate_name = candidate.get('candidate') or candidate.get('name')
                    actual_percentage = 85.0
                    poll_result = self._calculate_poll_result(actual_percentage, margin_of_error=3.0)
                    poll_results.append({
                        "candidate": candidate,
                        "name": candidate_name,
                        "poll": poll_result,
                        "actual": actual_percentage,
                        "party": party,
                        "is_highlighted": candidate == highlighted_candidate
                    })
                else:
                    total_points = sum(c.get('points', 0) for c in party_candidates)
                    for candidate in party_candidates:
                        candidate_name = candidate.get('candidate') or candidate.get('name')
                        if total_points == 0:
                            actual_percentage = 100.0 / len(party_candidates)
                        else:
                            candidate_points = candidate.get('points', 0)
                            actual_percentage = (candidate_points / total_points) * 100.0
                            actual_percentage = max(15.0, actual_percentage)

                        poll_result = self._calculate_poll_result(actual_percentage, margin_of_error=3.0)
                        poll_results.append({
                            "candidate": candidate,
                            "name": candidate_name,
                            "poll": poll_result,
                            "actual": actual_percentage,
                            "party": party,
                            "is_highlighted": candidate == highlighted_candidate
                        })

        poll_results.sort(key=lambda x: x["poll"], reverse=True)

        # Generate polling details
        polling_orgs = [
            "Internal Campaign Research", "Private Polling Firm", "Campaign Analytics",
            "Strategic Polling Group", "Confidential Research LLC"
        ]
        polling_org = random.choice(polling_orgs)
        sample_size = random.randint(800, 2000)
        days_ago = random.randint(1, 3)

        seat_info = seat_candidates[0]

        embed = discord.Embed(
            title=f"🔒 Private Seat Poll: {seat_id}",
            description=f"**{seat_info['office']}** in **{seat_info.get('region') or seat_info.get('state', 'Unknown')}** • {current_phase} ({current_year})",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        def create_progress_bar(percentage, width=20):
            filled = int((percentage / 100) * width)
            empty = width - filled
            return "█" * filled + "░" * empty

        if current_phase == "General Campaign":
            results_text = ""
            for i, result in enumerate(poll_results, 1):
                highlight = "👑 " if result["is_highlighted"] else ""
                candidate_party = result['candidate'].get('party', '')
                party_abbrev = candidate_party[0] if candidate_party else "I"
                progress_bar = create_progress_bar(result['poll'])

                results_text += f"**{i}. {highlight}{result['name']}**\n"
                results_text += f"**{party_abbrev} - {candidate_party or 'Independent'}**\n"
                results_text += f"{progress_bar} **{result['poll']:.1f}%**\n\n"

            embed.add_field(
                name="🗳️ General Election Results",
                value=results_text,
                inline=False
            )
        else:
            parties_displayed = {}
            for result in poll_results:
                party = result["party"]
                if party not in parties_displayed:
                    parties_displayed[party] = []
                parties_displayed[party].append(result)

            for party, party_results in parties_displayed.items():
                party_text = ""
                party_abbrev = party[0] if party else "I"

                for i, result in enumerate(party_results, 1):
                    highlight = "👑 " if result["is_highlighted"] else ""
                    progress_bar = create_progress_bar(result['poll'])

                    party_text += f"**{i}. {highlight}{result['name']}**\n"
                    party_text += f"**{party_abbrev} - {party}**\n"
                    party_text += f"{progress_bar} **{result['poll']:.1f}%**\n\n"

                embed.add_field(
                    name=f"🎗️ {party} Primary",
                    value=party_text,
                    inline=True
                )

        embed.add_field(
            name="📋 Poll Details",
            value=f"**Polling Organization:** {polling_org}\n"
                  f"**Sample Size:** {sample_size:,} likely voters\n"
                  f"**Margin of Error:** ±3.0%\n"
                  f"**Field Period:** {days_ago} day{'s' if days_ago > 1 else ''} ago\n"
                  f"**Stamina Cost:** 1 (Remaining: {current_stamina - 1})",
            inline=False
        )

        embed.add_field(
            name="🔒 Privacy Notice",
            value="Private poll shows simulated support with a ±3% margin of error. Internal metrics are not disclosed.",
            inline=False
        )

        embed.set_footer(text=f"Private poll conducted by {polling_org}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @poll_group.command(
        name="media_seat",
        description="Conduct a media poll for a specific seat (10% margin of error, free, anyone can use)"
    )
    @app_commands.describe(
        seat_id="The seat to poll (e.g., 'SEN-CA-1', 'CA-GOV')",
        candidate_name="Specific candidate to highlight (optional)"
    )
    async def media_seat_poll(self, interaction: discord.Interaction, seat_id: str, candidate_name: Optional[str] = None):
        # Check if we're in a campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config.get("current_phase", "") not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Polls can only be conducted during campaign phases.",
                ephemeral=True
            )
            return

        current_phase = time_config.get("current_phase", "")
        current_year = time_config["current_rp_date"].year

        # Get all candidates for the specified seat (same logic as regular seat poll)
        seat_candidates = []
        highlighted_candidate = None

        if current_phase == "General Campaign":
            winners_col = self.bot.db["winners"]
            winners_config = winners_col.find_one({"guild_id": interaction.guild.id})
            if winners_config:
                # Primary winners are stored with the election year (current year during General Campaign)
                seat_candidates = [
                    w for w in winners_config["winners"]
                    if (w["seat_id"].upper() == seat_id.upper() and
                        w.get("primary_winner", False) and
                        w["year"] == current_year)
                ]
        else:
            signups_col, signups_config = self._get_signups_config(interaction.guild.id)
            if signups_config:
                seat_candidates = [
                    c for c in signups_config["candidates"]
                    if (c["seat_id"].upper() == seat_id.upper() and
                        c["year"] == current_year)
                ]

        if not seat_candidates:
            await interaction.response.send_message(
                f"❌ No candidates found for seat '{seat_id}' in the current {current_phase.lower()}.",
                ephemeral=True
            )
            return

        # Find highlighted candidate if specified by name
        if candidate_name:
            for candidate in seat_candidates:
                candidate_display_name = candidate.get('candidate') or candidate.get('name')
                if candidate_display_name.lower() == candidate_name.lower():
                    highlighted_candidate = candidate
                    break

        # Calculate polling percentages with 10% margin of error
        poll_results = []

        if current_phase == "General Campaign":
            zero_sum_percentages = self._calculate_zero_sum_percentages(interaction.guild.id, seat_id)
            for candidate in seat_candidates:
                candidate_name = candidate.get('candidate') or candidate.get('name')
                actual_percentage = zero_sum_percentages.get(candidate_name, 50.0)
                poll_result = self._calculate_poll_result(actual_percentage, margin_of_error=10.0)
                poll_results.append({
                    "candidate": candidate,
                    "name": candidate_name,
                    "poll": poll_result,
                    "is_highlighted": candidate == highlighted_candidate
                })

            # Normalize general election media poll percentages to sum to 100
            total_poll = sum(r["poll"] for r in poll_results) or 0.0
            if total_poll > 0:
                # Scale to 100 and round to one decimal place
                for r in poll_results:
                    r["poll"] = round((r["poll"] * 100.0) / total_poll, 1)

                # Adjust rounding drift to ensure exact 100.0 total
                drift = round(100.0 - sum(r["poll"] for r in poll_results), 1)
                if abs(drift) >= 0.1:
                    # Assign drift to the top polling candidate pre-sort to preserve intent
                    max_item = max(poll_results, key=lambda x: x["poll"]) if poll_results else None
                    if max_item is not None:
                        max_item["poll"] = round(max_item["poll"] + drift, 1)
        else:
            parties = {}
            for candidate in seat_candidates:
                party = candidate["party"]
                if party not in parties:
                    parties[party] = []
                parties[party].append(candidate)

            for party, party_candidates in parties.items():
                if len(party_candidates) == 1:
                    candidate = party_candidates[0]
                    candidate_name = candidate.get('candidate') or candidate.get('name')
                    actual_percentage = 85.0
                    poll_result = self._calculate_poll_result(actual_percentage, margin_of_error=10.0)
                    poll_results.append({
                        "candidate": candidate,
                        "name": candidate_name,
                        "poll": poll_result,
                        "party": party,
                        "is_highlighted": candidate == highlighted_candidate
                    })
                else:
                    total_points = sum(c.get('points', 0) for c in party_candidates)
                    for candidate in party_candidates:
                        candidate_name = candidate.get('candidate') or candidate.get('name')
                        if total_points == 0:
                            actual_percentage = 100.0 / len(party_candidates)
                        else:
                            candidate_points = candidate.get('points', 0)
                            actual_percentage = (candidate_points / total_points) * 100.0
                            actual_percentage = max(15.0, actual_percentage)

                        poll_result = self._calculate_poll_result(actual_percentage, margin_of_error=10.0)
                        poll_results.append({
                            "candidate": candidate,
                            "name": candidate_name,
                            "poll": poll_result,
                            "party": party,
                            "is_highlighted": candidate == highlighted_candidate
                        })

            # Normalize primary media poll percentages within each party to sum to 100
            # Build mapping party -> list of indices in poll_results
            party_to_indices = {}
            for idx, r in enumerate(poll_results):
                party_to_indices.setdefault(r.get("party"), []).append(idx)

            for party, idx_list in party_to_indices.items():
                total_poll = sum(poll_results[i]["poll"] for i in idx_list) or 0.0
                if total_poll > 0:
                    for i in idx_list:
                        poll_results[i]["poll"] = round((poll_results[i]["poll"] * 100.0) / total_poll, 1)

                    drift = round(100.0 - sum(poll_results[i]["poll"] for i in idx_list), 1)
                    if abs(drift) >= 0.1:
                        max_i = max(idx_list, key=lambda j: poll_results[j]["poll"]) if idx_list else None
                        if max_i is not None:
                            poll_results[max_i]["poll"] = round(poll_results[max_i]["poll"] + drift, 1)

        poll_results.sort(key=lambda x: x["poll"], reverse=True)

        # Generate media polling details
        polling_orgs = [
            "Channel 7 News", "Daily Herald", "Political Weekly", "State News Network",
            "Independent Media Group", "Public Broadcasting", "News Radio 101.5", "City Tribune"
        ]
        polling_org = random.choice(polling_orgs)
        sample_size = random.randint(400, 800)
        days_ago = random.randint(2, 7)

        seat_info = seat_candidates[0]

        embed = discord.Embed(
            title=f"📺 Media Poll: {seat_id}",
            description=f"**{seat_info['office']}** in **{seat_info.get('region') or seat_info.get('state', 'Unknown')}** • {current_phase} ({current_year})",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        def create_progress_bar(percentage, width=20):
            filled = int((percentage / 100) * width)
            empty = width - filled
            return "█" * filled + "░" * empty

        if current_phase == "General Campaign":
            results_text = ""
            for i, result in enumerate(poll_results, 1):
                highlight = "👑 " if result["is_highlighted"] else ""
                party_abbrev = result['candidate']['party'][0] if result['candidate']['party'] else "I"
                progress_bar = create_progress_bar(result['poll'])

                # Lookup actual percentage from zero-sum calculation for consistency with admin view
                zero_sum_percentages = self._calculate_zero_sum_percentages(interaction.guild.id, seat_id)
                actual_percentage = zero_sum_percentages.get(result['name'], 50.0)

                results_text += f"**{i}. {highlight}{result['name']}**\n"
                results_text += f"**{party_abbrev} - {result['candidate']['party']}**\n"
                results_text += f"{progress_bar} **{result['poll']:.1f}%**\n\n"

            embed.add_field(
                name="🗳️ General Election Results",
                value=results_text,
                inline=False
            )
        else:
            parties_displayed = {}
            for result in poll_results:
                party = result["party"]
                if party not in parties_displayed:
                    parties_displayed[party] = []
                parties_displayed[party].append(result)

            for party, party_results in parties_displayed.items():
                party_text = ""
                party_abbrev = party[0] if party else "I"

                for i, result in enumerate(party_results, 1):
                    highlight = "👑 " if result["is_highlighted"] else ""
                    progress_bar = create_progress_bar(result['poll'])

                    party_text += f"**{i}. {highlight}{result['name']}**\n"
                    party_text += f"**{party_abbrev} - {party}**\n"
                    party_text += f"{progress_bar} **{result['poll']:.1f}%**\n\n"

                embed.add_field(
                    name=f"🎗️ {party} Primary",
                    value=party_text,
                    inline=True
                )

        embed.add_field(
            name="📋 Poll Details",
            value=f"**Polling Organization:** {polling_org}\n"
                  f"**Sample Size:** {sample_size:,} likely voters\n"
                  f"**Margin of Error:** ±10.0%\n"
                  f"**Field Period:** {days_ago} day{'s' if days_ago > 1 else ''} ago",
            inline=False
        )

        embed.add_field(
            name="📰 Disclaimer",
            value="Media poll shows simulated support with a ±10% margin of error. Internal metrics are not disclosed.",
            inline=False
        )

        embed.set_footer(text=f"Media poll by {polling_org}")

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="pres_private_poll",
        description="Conduct a private poll for presidential candidates in a U.S. state (3% margin of error, costs 1 stamina)"
    )
    @app_commands.describe(
        state="U.S. state to poll for presidential candidates",
        candidate_name="Specific presidential candidate to highlight (optional)"
    )
    async def pres_private_poll(self, interaction: discord.Interaction, state: str, candidate_name: Optional[str] = None):
        # Validate and format state
        try:
            from .presidential_winners import PRESIDENTIAL_STATE_DATA
        except ImportError:
            # Fallback if import fails
            PRESIDENTIAL_STATE_DATA = {}

        state_upper = state.upper()
        if state_upper not in PRESIDENTIAL_STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from: {', '.join(sorted(PRESIDENTIAL_STATE_DATA.keys()))}",
                ephemeral=True
            )
            return

        # Check if user is a candidate
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config.get("current_phase", "") not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Polls can only be conducted during campaign phases.",
                ephemeral=True
            )
            return

        current_phase = time_config.get("current_phase", "")
        current_year = time_config["current_rp_date"].year

        # Check if user is a valid presidential candidate
        user_candidate = None

        # Check in presidential signups
        pres_col = self.bot.db["presidential_signups"]
        pres_config = pres_col.find_one({"guild_id": interaction.guild.id})
        if pres_config:
            for candidate in pres_config.get("candidates", []):
                if (candidate["user_id"] == interaction.user.id and
                    candidate["year"] == current_year and
                    candidate["office"] == "President"):
                    user_candidate = candidate
                    break

        # Initialize winners_col here to avoid UnboundLocalError
        winners_col = self.bot.db["winners"]
        winners_config = None

        # Check in winners if general campaign
        if not user_candidate and current_phase == "General Campaign":
            winners_config = winners_col.find_one({"guild_id": interaction.guild.id})
            if winners_config:
                # Primary winners are stored with the election year (current year during General Campaign)
                for winner in winners_config["winners"]:
                    if (winner["user_id"] == interaction.user.id and
                        winner.get("primary_winner", False) and
                        winner["year"] == current_year and
                        winner.get("office") == "President"):
                        user_candidate = winner
                        break

        if not user_candidate:
            await interaction.response.send_message(
                "❌ Only active presidential candidates can use private presidential polling.",
                ephemeral=True
            )
            return

        # Check stamina
        current_stamina = user_candidate.get("stamina", 0)
        if current_stamina < 1:
            await interaction.response.send_message(
                "❌ You need at least 1 stamina to conduct a private poll.",
                ephemeral=True
            )
            return

        # Deduct stamina
        if current_phase == "General Campaign" and winners_config:
            winners_col.update_one(
                {"guild_id": interaction.guild.id, "winners.user_id": interaction.user.id},
                {"$inc": {"winners.$.stamina": -1}}
            )
        else:
            pres_col.update_one(
                {"guild_id": interaction.guild.id, "candidates.user_id": interaction.user.id},
                {"$inc": {"candidates.$.stamina": -1}}
            )

        # Get all presidential candidates
        presidential_candidates = []
        highlighted_candidate = None

        if current_phase == "General Campaign":
            # Get presidential winners from presidential_winners collection
            pres_winners_col = self.bot.db["presidential_winners"]
            pres_winners_config = pres_winners_col.find_one({"guild_id": interaction.guild.id})

            if pres_winners_config and pres_winners_config.get("winners"):
                party_winners = pres_winners_config.get("winners", [])
                stored_election_year = pres_winners_config.get("election_year")

                # Determine the signup year based on the stored election year
                if stored_election_year:
                    signup_year = stored_election_year - 1
                else:
                    # Fallback to old logic
                    signup_year = current_year - 1 if current_year % 2 == 0 else current_year

                # Get full candidate data from presidential signups
                if pres_config:
                    for party, winner_name in party_winners.items():
                        for candidate in pres_config.get("candidates", []):
                            if (candidate["name"] == winner_name and 
                                candidate["year"] == signup_year and 
                                candidate["office"] == "President"):
                                # Mark this candidate as a primary winner
                                candidate["is_primary_winner"] = True
                                candidate["primary_winner_party"] = party
                                candidate["election_year"] = stored_election_year or current_year
                                presidential_candidates.append(candidate)
                                break

            # If no winners from presidential_winners, check all_winners system as fallback
            if not presidential_candidates and winners_config:
                # Find presidential primary winners in all_winners system
                # Primary winners are stored with the election year (current year during General Campaign)
                presidential_winners = [
                    w for w in winners_config.get("winners", [])
                    if (w.get("office") == "President" and 
                        w.get("year") == current_year and 
                        w.get("primary_winner", False))
                ]

                # Get full candidate data from presidential signups
                if pres_config and presidential_winners:
                    for winner in presidential_winners:
                        winner_name = winner.get("candidate")
                        for candidate in pres_config.get("candidates", []):
                            if (candidate["name"] == winner_name and 
                                candidate["year"] == current_year and 
                                candidate["office"] == "President"):
                                # Add winner data to candidate for display
                                candidate["winner_data"] = winner
                                presidential_candidates.append(candidate)
                                break

        else:
            # Primary campaign - get all presidential candidates
            if pres_config:
                presidential_candidates = [
                    c for c in pres_config.get("candidates", [])
                    if (c["year"] == current_year and c["office"] == "President")
                ]

        if not presidential_candidates:
            await interaction.response.send_message(
                f"❌ No presidential candidates found for the current {current_phase.lower()}.",
                ephemeral=True
            )
            return

        # Find highlighted candidate if specified by name
        if candidate_name:
            for candidate in presidential_candidates:
                candidate_display_name = candidate.get('name')
                if candidate_display_name and candidate_display_name.lower() == candidate_name.lower():
                    highlighted_candidate = candidate
                    break

        # Calculate polling percentages with 3% margin of error
        poll_results = []

        if current_phase == "General Campaign":
            # Use state-specific baseline data for more accurate polling
            state_data = PRESIDENTIAL_STATE_DATA.get(state_upper, {
                "republican": 33.0, "democrat": 33.0, "other": 34.0
            })

            # Get momentum config
            momentum_col = self.bot.db["momentum_config"]
            momentum_config = momentum_col.find_one({"guild_id": interaction.guild.id})
            if not momentum_config:
                momentum_config = {}

            for candidate in presidential_candidates:
                candidate_name = candidate.get('name')
                candidate_party = candidate.get('party', '').lower()

                # Determine party alignment for baseline calculations
                if "republican" in candidate_party:
                    baseline_percentage = state_data.get("republican", 33.0)
                elif "democrat" in candidate_party:
                    baseline_percentage = state_data.get("democrat", 33.0)
                else:
                    baseline_percentage = state_data.get("other", 34.0)

                # Add campaign points if available
                state_points = candidate.get("state_points", {})
                campaign_boost = state_points.get(state_upper, 0.0)

                # Calculate actual percentage (baseline + campaign effects)
                actual_percentage = baseline_percentage + campaign_boost

                # Apply momentum effects
                momentum_effect = self._calculate_momentum_effect_on_polling(state_upper, candidate_party, momentum_config)
                actual_percentage += momentum_effect

                # Apply margin of error for realistic polling
                poll_percentage = self._calculate_poll_result(actual_percentage, 3.0)

                poll_results.append({
                    "name": candidate_name,
                    "party": candidate.get('party', 'Independent'),
                    "percentage": round(poll_percentage, 1),
                    "actual_percentage": round(actual_percentage, 1),
                    "is_highlighted": candidate == highlighted_candidate
                })
        else:
            # Primary campaign logic (same as media_pres_poll)
            parties = {}
            for candidate in presidential_candidates:
                party = candidate.get("party", "Independent")
                if party not in parties:
                    parties[party] = []
                parties[party].append(candidate)

            for party, party_candidates in parties.items():
                if len(party_candidates) == 1:
                    candidate = party_candidates[0]
                    candidate_name = candidate.get('name')
                    actual_percentage = 85.0
                    poll_result = self._calculate_poll_result(actual_percentage, margin_of_error=3.0)

                    poll_results.append({
                        "candidate": candidate,
                        "name": candidate_name,
                        "poll": poll_result,
                        "actual": actual_percentage,
                        "party": party,
                        "is_highlighted": candidate == highlighted_candidate
                    })
                else:
                    total_points = sum(c.get('points', 0) for c in party_candidates)
                    for candidate in party_candidates:
                        candidate_name = candidate.get('name')

                        if total_points == 0:
                            actual_percentage = 100.0 / len(party_candidates)
                        else:
                            candidate_points = candidate.get('points', 0)
                            actual_percentage = (candidate_points / total_points) * 100.0
                            actual_percentage = max(15.0, actual_percentage)

                        poll_result = self._calculate_poll_result(actual_percentage, margin_of_error=3.0)

                        poll_results.append({
                            "candidate": candidate,
                            "name": candidate_name,
                            "poll": poll_result,
                            "actual": actual_percentage,
                            "party": party,
                            "is_highlighted": candidate == highlighted_candidate
                        })

        poll_results.sort(key=lambda x: x["poll"], reverse=True)

        # Get state baseline data
        state_data = PRESIDENTIAL_STATE_DATA.get(state_upper, {})
        baseline_rep = state_data.get("republican", 33.0)
        baseline_dem = state_data.get("democrat", 33.0)
        baseline_other = state_data.get("other", 34.0)

        # Generate private polling details
        polling_orgs = [
            "Internal Campaign Research", "Private Polling Firm", "Campaign Analytics",
            "Strategic Polling Group", "Confidential Research LLC"
        ]
        polling_org = random.choice(polling_orgs)
        sample_size = random.randint(800, 2000)
        days_ago = random.randint(1, 3)

        embed = discord.Embed(
            title=f"🔒 Private Presidential Poll: {state_upper}",
            description=f"**Presidential Race in {state_upper}** • {current_phase} ({current_year})",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        def create_progress_bar(percentage, width=20):
            filled = int((percentage / 100) * width)
            empty = width - filled
            return "█" * filled + "░" * empty

        if current_phase == "General Campaign":
            # General election - show all candidates together with actual percentages
            results_text = ""
            for i, result in enumerate(poll_results, 1):
                highlight = "👑 " if result["is_highlighted"] else ""
                party_abbrev = result['party'][0] if result.get('party') else "I"
                progress_bar = create_progress_bar(result['percentage'])

                results_text += f"**{i}. {highlight}{result['name']}**\n"
                results_text += f"**{party_abbrev} - {result.get('party', 'Independent')}**\n"
                results_text += f"{progress_bar} **{result['percentage']}%** (Actual: ~{result['actual_percentage']}%) \n\n"

            embed.add_field(
                name="🇺🇸 Presidential General Election",
                value=results_text,
                inline=False
            )
        else:
            # Primary campaign - group by party
            parties_displayed = {}
            for result in poll_results:
                party = result.get("party", "Independent")
                if party not in parties_displayed:
                    parties_displayed[party] = []
                parties_displayed[party].append(result)

            for party, party_results in parties_displayed.items():
                party_text = ""
                party_abbrev = party[0] if party else "I"

                for i, result in enumerate(party_results, 1):
                    highlight = "👑 " if result["is_highlighted"] else ""
                    progress_bar = create_progress_bar(result['poll'])

                    party_text += f"**{i}. {highlight}{result['name']}**\n"
                    party_text += f"**{party_abbrev} - {party}**\n"
                    party_text += f"{progress_bar} **{result['poll']:.1f}%** \n\n"

                embed.add_field(
                    name=f"🎗️ {party} Primary",
                    value=party_text,
                    inline=True
                )

        # Add state context
        embed.add_field(
            name=f"📍 {state_upper} Context",
            value=f"**Baseline Republican:** {baseline_rep:.1f}%\n"
                  f"**Baseline Democrat:** {baseline_dem:.1f}%\n"
                  f"**Baseline Other:** {baseline_other:.1f}%",
            inline=True
        )

        embed.add_field(
            name="📋 Poll Details",
            value=f"**Polling Organization:** {polling_org}\n"
                  f"**Sample Size:** {sample_size:,} likely voters\n"
                  f"**Margin of Error:** ±3.0%\n"
                  f"**Field Period:** {days_ago} day{'s' if days_ago > 1 else ''} ago\n"
                  f"**Stamina Cost:** 1 (Remaining: {current_stamina - 1})",
            inline=False
        )

        embed.add_field(
            name="🔒 Privacy Notice",
            value="Private poll shows simulated support with a ±3% margin of error. Internal metrics are not disclosed.",
            inline=False
        )

        embed.set_footer(text=f"Private poll conducted by {polling_org}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="media_pres_poll",
        description="Conduct a media poll for presidential candidates in a U.S. state (10% margin of error)"
    )
    @app_commands.describe(
        state="U.S. state to poll for presidential candidates",
        candidate_name="Specific presidential candidate to highlight (optional)"
    )
    async def media_pres_poll(self, interaction: discord.Interaction, state: str, candidate_name: Optional[str] = None):
        # Validate and format state
        # Import PRESIDENTIAL_STATE_DATA from the presidential campaigns module
        try:
            from .presidential_winners import PRESIDENTIAL_STATE_DATA
        except ImportError:
            # Fallback if import fails
            PRESIDENTIAL_STATE_DATA = {}

        state_upper = state.upper()
        if state_upper not in PRESIDENTIAL_STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from: {', '.join(sorted(PRESIDENTIAL_STATE_DATA.keys()))}",
                ephemeral=True
            )
            return

        # Check if we're in a campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config.get("current_phase", "") not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Polls can only be conducted during campaign phases.",
                ephemeral=True
            )
            return

        current_phase = time_config.get("current_phase", "")
        current_year = time_config["current_rp_date"].year

        # Get presidential candidates
        pres_candidates = []
        highlighted_candidate = None

        if current_phase == "General Campaign":
            # Check if presidential_winners collection has an election_year that matches target_year
            pres_winners_col = self.bot.db["presidential_winners"]
            pres_winners_config = pres_winners_col.find_one({"guild_id": interaction.guild.id})

            if pres_winners_config and pres_winners_config.get("winners"):
                party_winners = pres_winners_config.get("winners", [])
                stored_election_year = pres_winners_config.get("election_year")

                # Determine the signup year based on the stored election year
                if stored_election_year:
                    signup_year = stored_election_year - 1
                else:
                    # Fallback to old logic
                    signup_year = current_year - 1 if current_year % 2 == 0 else current_year

                pres_col = self.bot.db["presidential_signups"]
                pres_config = pres_col.find_one({"guild_id": interaction.guild.id})

                if pres_config:
                    for party, winner_name in party_winners.items():
                        for candidate in pres_config.get("candidates", []):
                            if (candidate["name"] == winner_name and 
                                candidate["year"] == signup_year and 
                                candidate["office"] == "President"):
                                # Mark this candidate as a primary winner
                                candidate["is_primary_winner"] = True
                                candidate["primary_winner_party"] = party
                                candidate["election_year"] = stored_election_year or current_year
                                pres_candidates.append(candidate)
                                break

            # If no winners from presidential_winners, check all_winners system as fallback
            if not pres_candidates:
                winners_col = self.bot.db["winners"]
                winners_config = winners_col.find_one({"guild_id": interaction.guild.id})

                if winners_config and winners_config.get("winners"):
                    # Find presidential primary winners in all_winners system
                    # Primary winners are stored with the election year (current year during General Campaign)
                    presidential_winners = [
                        w for w in winners_config.get("winners", [])
                        if (w.get("office") == "President" and 
                            w.get("year") == current_year and 
                            w.get("primary_winner", False))
                    ]

                    # Get full candidate data from presidential signups
                    pres_col = self.bot.db["presidential_signups"]
                    pres_config = pres_col.find_one({"guild_id": interaction.guild.id})

                    if pres_config and presidential_winners:
                        for winner in presidential_winners:
                            winner_name = winner.get("candidate")
                            for candidate in pres_config.get("candidates", []):
                                if (candidate["name"] == winner_name and 
                                    candidate["year"] == current_year and 
                                    candidate["office"] == "President"):
                                    # Add winner data to candidate for display
                                    candidate["winner_data"] = winner
                                    pres_candidates.append(candidate)
                                    break

            # If still no candidates found, show all registered candidates with note
            if not pres_candidates:
                # For fallback, use the stored election year if available, otherwise use current_year
                fallback_signup_year = signup_year if 'signup_year' in locals() else (current_year - 1 if current_year % 2 == 0 else current_year)

                pres_col = self.bot.db["presidential_signups"]
                pres_config = pres_col.find_one({"guild_id": interaction.guild.id})

                if pres_config:
                    pres_candidates = [
                        c for c in pres_config.get("candidates", [])
                        if c.get("year") == fallback_signup_year and c.get("office") == "President"
                    ]
        else:
            # Look in presidential signups for primary campaign
            pres_col = self.bot.db["presidential_signups"]
            pres_config = pres_col.find_one({"guild_id": interaction.guild.id})
            if pres_config:
                pres_candidates = [
                    c for c in pres_config.get("candidates", [])
                    if (c.get("year") == current_year and
                        c.get("office") == "President")
                ]

        if not pres_candidates:
            await interaction.response.send_message(
                f"❌ No presidential candidates found for the current {current_phase.lower()}.",
                ephemeral=True
            )
            return

        # Find highlighted candidate if specified by name
        if candidate_name:
            for candidate in pres_candidates:
                candidate_display_name = candidate.get('name')
                if candidate_display_name and candidate_display_name.lower() == candidate_name.lower():
                    highlighted_candidate = candidate
                    break

        # Calculate polling percentages with 10% margin of error
        poll_results = []

        if current_phase == "General Campaign":
            # Use state-specific baseline data for general election polling
            state_data = PRESIDENTIAL_STATE_DATA.get(state_upper, {
                "republican": 33.0, "democrat": 33.0, "other": 34.0
            })

            # Get momentum config
            momentum_col = self.bot.db["momentum_config"]
            momentum_config = momentum_col.find_one({"guild_id": interaction.guild.id})
            if not momentum_config:
                momentum_config = {}

            for candidate in pres_candidates:
                candidate_name = candidate.get('name')
                candidate_party = candidate.get('party', '').lower()

                # Determine party alignment for baseline calculations
                if "republican" in candidate_party:
                    baseline_percentage = state_data.get("republican", 33.0)
                elif "democrat" in candidate_party:
                    baseline_percentage = state_data.get("democrat", 33.0)
                else:
                    baseline_percentage = state_data.get("other", 34.0)

                # Add campaign points if available
                state_points = candidate.get("state_points", {})
                campaign_boost = state_points.get(state_upper, 0.0)

                # Calculate actual percentage (baseline + campaign effects)
                actual_percentage = baseline_percentage + campaign_boost

                # Apply momentum effects
                momentum_effect = self._calculate_momentum_effect_on_polling(state_upper, candidate_party, momentum_config)
                actual_percentage += momentum_effect

                # Apply margin of error for realistic polling
                poll_result = self._calculate_poll_result(actual_percentage, margin_of_error=10.0)

                poll_results.append({
                    "candidate": candidate,
                    "name": candidate_name,
                    "poll": poll_result,
                    "is_highlighted": candidate == highlighted_candidate
                })
        else:
            # Primary campaign - group by party
            parties = {}
            for candidate in pres_candidates:
                party = candidate.get("party", "Independent")
                if party not in parties:
                    parties[party] = []
                parties[party].append(candidate)

            for party, party_candidates in parties.items():
                if len(party_candidates) == 1:
                    candidate = party_candidates[0]
                    candidate_name = candidate.get('name')
                    actual_percentage = 85.0
                    poll_result = self._calculate_poll_result(actual_percentage, margin_of_error=10.0)

                    poll_results.append({
                        "candidate": candidate,
                        "name": candidate_name,
                        "poll": poll_result,
                        "party": party,
                        "is_highlighted": candidate == highlighted_candidate
                    })
                else:
                    total_points = sum(c.get('points', 0) for c in party_candidates)
                    for candidate in party_candidates:
                        candidate_name = candidate.get('name')

                        if total_points == 0:
                            actual_percentage = 100.0 / len(party_candidates)
                        else:
                            candidate_points = candidate.get('points', 0)
                            actual_percentage = (candidate_points / total_points) * 100.0
                            actual_percentage = max(15.0, actual_percentage)

                        poll_result = self._calculate_poll_result(actual_percentage, margin_of_error=10.0)

                        poll_results.append({
                            "candidate": candidate,
                            "name": candidate_name,
                            "poll": poll_result,
                            "party": party,
                            "is_highlighted": candidate == highlighted_candidate
                        })

        poll_results.sort(key=lambda x: x["poll"], reverse=True)

        # Get state baseline data for display
        state_data = PRESIDENTIAL_STATE_DATA.get(state_upper, {})
        baseline_rep = state_data.get("republican", 33.0)
        baseline_dem = state_data.get("democrat", 33.0)
        baseline_other = state_data.get("other", 34.0)

        # Generate media polling details
        polling_orgs = [
            "Channel 7 News", "Daily Herald", "Political Weekly", "State News Network",
            "Independent Media Group", "Public Broadcasting", "News Radio 101.5", "City Tribune"
        ]
        polling_org = random.choice(polling_orgs)
        sample_size = random.randint(400, 800)
        days_ago = random.randint(2, 7)

        embed = discord.Embed(
            title=f"📺 Media Presidential Poll: {state_upper}",
            description=f"**Presidential Race in {state_upper}** • {current_phase} ({current_year})",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        def create_progress_bar(percentage, width=20):
            filled = int((percentage / 100) * width)
            empty = width - filled
            return "█" * filled + "░" * empty

        if current_phase == "General Campaign":
            # General election - show all candidates together
            results_text = ""
            for i, result in enumerate(poll_results, 1):
                highlight = "👑 " if result["is_highlighted"] else ""
                party_abbrev = result['candidate'].get('party', 'I')[0] if result['candidate'].get('party') else "I"
                progress_bar = create_progress_bar(result['poll'])

                results_text += f"**{i}. {highlight}{result['name']}**\n"
                results_text += f"**{party_abbrev} - {result['candidate'].get('party', 'Independent')}**\n"
                results_text += f"{progress_bar} **{result['poll']:.1f}%**\n\n"

            embed.add_field(
                name="🇺🇸 Presidential General Election",
                value=results_text,
                inline=False
            )
        else:
            # Primary campaign - group by party
            parties_displayed = {}
            for result in poll_results:
                party = result.get("party", "Independent")
                if party not in parties_displayed:
                    parties_displayed[party] = []
                parties_displayed[party].append(result)

            for party, party_results in parties_displayed.items():
                party_text = ""
                party_abbrev = party[0] if party else "I"

                for i, result in enumerate(party_results, 1):
                    highlight = "👑 " if result["is_highlighted"] else ""
                    progress_bar = create_progress_bar(result['poll'])

                    party_text += f"**{i}. {highlight}{result['name']}**\n"
                    party_text += f"**{party_abbrev} - {party}**\n"
                    party_text += f"{progress_bar} **{result['poll']:.1f}%**\n\n"

                embed.add_field(
                    name=f"🎗️ {party} Primary",
                    value=party_text,
                    inline=True
                )

        # Add state context
        embed.add_field(
            name=f"📍 {state_upper} Context",
            value=f"**Baseline Republican:** {baseline_rep:.1f}%\n"
                  f"**Baseline Democrat:** {baseline_dem:.1f}%\n"
                  f"**Baseline Other:** {baseline_other:.1f}%",
            inline=True
        )

        embed.add_field(
            name="📋 Poll Details",
            value=f"**Polling Organization:** {polling_org}\n"
                  f"**Sample Size:** {sample_size:,} likely voters\n"
                  f"**Margin of Error:** ±10.0%\n"
                  f"**Field Period:** {days_ago} day{'s' if days_ago > 1 else ''} ago",
            inline=False
        )

        embed.add_field(
            name="📺 Media Notice",
            value="This is a media-sponsored poll available to the general public. Results have a wider margin of error and factor in state political alignment.",
            inline=False
        )

        embed.set_footer(text=f"Media poll conducted by {polling_org}")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="pres_private_poll",
        description="Conduct a private poll for presidential candidates (3% margin of error, costs 1 stamina)"
    )
    @app_commands.describe(
        state="U.S. state to poll for presidential candidates",
        candidate_name="Specific presidential candidate to highlight (optional)"
    )
    async def pres_private_poll(self, interaction: discord.Interaction, state: str, candidate_name: Optional[str] = None):
        # Import PRESIDENTIAL_STATE_DATA
        try:
            from .presidential_winners import PRESIDENTIAL_STATE_DATA
        except ImportError:
            PRESIDENTIAL_STATE_DATA = {}

        state_upper = state.upper()
        if state_upper not in PRESIDENTIAL_STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from: {', '.join(sorted(PRESIDENTIAL_STATE_DATA.keys()))}",
                ephemeral=True
            )
            return

        # Check if user is a candidate
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config.get("current_phase", "") not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Polls can only be conducted during campaign phases.",
                ephemeral=True
            )
            return

        current_phase = time_config.get("current_phase", "")
        current_year = time_config["current_rp_date"].year

        # Check if user is a valid presidential candidate
        user_candidate = None

        # Check in presidential signups
        pres_col = self.bot.db["presidential_signups"]
        pres_config = pres_col.find_one({"guild_id": interaction.guild.id})
        if pres_config:
            for candidate in pres_config.get("candidates", []):
                if (candidate["user_id"] == interaction.user.id and
                    candidate["year"] == current_year and
                    candidate["office"] == "President"):
                    user_candidate = candidate
                    break

        # Initialize winners_col here to avoid UnboundLocalError
        winners_col = self.bot.db["winners"]
        winners_config = None

        # Check in winners if general campaign
        if not user_candidate and current_phase == "General Campaign":
            winners_config = winners_col.find_one({"guild_id": interaction.guild.id})
            if winners_config:
                # Primary winners are stored with the election year (current year during General Campaign)
                for winner in winners_config["winners"]:
                    if (winner["user_id"] == interaction.user.id and
                        winner.get("primary_winner", False) and
                        winner["year"] == current_year and
                        winner.get("office") == "President"):
                        user_candidate = winner
                        break

        if not user_candidate:
            await interaction.response.send_message(
                "❌ Only active presidential candidates can use private presidential polling.",
                ephemeral=True
            )
            return

        # Check stamina
        current_stamina = user_candidate.get("stamina", 0)
        if current_stamina < 1:
            await interaction.response.send_message(
                "❌ You need at least 1 stamina to conduct a private poll.",
                ephemeral=True
            )
            return

        # Deduct stamina
        if current_phase == "General Campaign" and winners_config:
            winners_col.update_one(
                {"guild_id": interaction.guild.id, "winners.user_id": interaction.user.id},
                {"$inc": {"winners.$.stamina": -1}}
            )
        else:
            pres_col.update_one(
                {"guild_id": interaction.guild.id, "candidates.user_id": interaction.user.id},
                {"$inc": {"candidates.$.stamina": -1}}
            )

        # Get all presidential candidates
        presidential_candidates = []
        highlighted_candidate = None

        if current_phase == "General Campaign":
            # Get presidential winners from presidential_winners collection
            pres_winners_col = self.bot.db["presidential_winners"]
            pres_winners_config = pres_winners_col.find_one({"guild_id": interaction.guild.id})

            if pres_winners_config and pres_winners_config.get("winners"):
                party_winners = pres_winners_config.get("winners", [])
                stored_election_year = pres_winners_config.get("election_year")

                # Determine the signup year based on the stored election year
                if stored_election_year:
                    signup_year = stored_election_year - 1
                else:
                    # Fallback to old logic
                    signup_year = current_year - 1 if current_year % 2 == 0 else current_year

                # Get full candidate data from presidential signups
                if pres_config:
                    for party, winner_name in party_winners.items():
                        for candidate in pres_config.get("candidates", []):
                            if (candidate["name"] == winner_name and 
                                candidate["year"] == signup_year and 
                                candidate["office"] == "President"):
                                # Mark this candidate as a primary winner
                                candidate["is_primary_winner"] = True
                                candidate["primary_winner_party"] = party
                                candidate["election_year"] = stored_election_year or current_year
                                presidential_candidates.append(candidate)
                                break

            # If no winners from presidential_winners, check all_winners system as fallback
            if not presidential_candidates and winners_config:
                # Find presidential primary winners in all_winners system
                # Primary winners are stored with the election year (current year during General Campaign)
                presidential_winners = [
                    w for w in winners_config.get("winners", [])
                    if (w.get("office") == "President" and 
                        w.get("year") == current_year and 
                        w.get("primary_winner", False))
                ]

                # Get full candidate data from presidential signups
                if pres_config and presidential_winners:
                    for winner in presidential_winners:
                        winner_name = winner.get("candidate")
                        for candidate in pres_config.get("candidates", []):
                            if (candidate["name"] == winner_name and 
                                candidate["year"] == current_year and 
                                candidate["office"] == "President"):
                                # Add winner data to candidate for display
                                candidate["winner_data"] = winner
                                presidential_candidates.append(candidate)
                                break

        else:
            # Primary campaign - get all presidential candidates
            if pres_config:
                presidential_candidates = [
                    c for c in pres_config.get("candidates", [])
                    if (c["year"] == current_year and c["office"] == "President")
                ]

        if not presidential_candidates:
            await interaction.response.send_message(
                f"❌ No presidential candidates found for the current {current_phase.lower()}.",
                ephemeral=True
            )
            return

        # Find highlighted candidate if specified by name
        if candidate_name:
            for candidate in presidential_candidates:
                candidate_display_name = candidate.get('name')
                if candidate_display_name and candidate_display_name.lower() == candidate_name.lower():
                    highlighted_candidate = candidate
                    break

        # Calculate polling percentages with 3% margin of error
        poll_results = []

        if current_phase == "General Campaign":
            # Use state-specific baseline data for more accurate polling
            state_data = PRESIDENTIAL_STATE_DATA.get(state_upper, {
                "republican": 33.0, "democrat": 33.0, "other": 34.0
            })

            # Get momentum config
            momentum_col = self.bot.db["momentum_config"]
            momentum_config = momentum_col.find_one({"guild_id": interaction.guild.id})
            if not momentum_config:
                momentum_config = {}

            for candidate in presidential_candidates:
                candidate_name = candidate.get('name')
                candidate_party = candidate.get('party', '').lower()

                # Determine party alignment for baseline calculations
                if "republican" in candidate_party:
                    baseline_percentage = state_data.get("republican", 33.0)
                elif "democrat" in candidate_party:
                    baseline_percentage = state_data.get("democrat", 33.0)
                else:
                    baseline_percentage = state_data.get("other", 34.0)

                # Add campaign points if available
                state_points = candidate.get("state_points", {})
                campaign_boost = state_points.get(state_upper, 0.0)

                # Calculate actual percentage (baseline + campaign effects)
                actual_percentage = baseline_percentage + campaign_boost

                # Apply momentum effects
                momentum_effect = self._calculate_momentum_effect_on_polling(state_upper, candidate_party, momentum_config)
                actual_percentage += momentum_effect

                # Apply margin of error for realistic polling
                poll_percentage = self._calculate_poll_result(actual_percentage, 3.0)

                poll_results.append({
                    "name": candidate_name,
                    "party": candidate.get('party', 'Independent'),
                    "percentage": round(poll_percentage, 1),
                    "actual_percentage": round(actual_percentage, 1),
                    "is_highlighted": candidate == highlighted_candidate
                })
        else:
            # Primary campaign logic (same as media_pres_poll)
            parties = {}
            for candidate in presidential_candidates:
                party = candidate.get("party", "Independent")
                if party not in parties:
                    parties[party] = []
                parties[party].append(candidate)

            for party, party_candidates in parties.items():
                if len(party_candidates) == 1:
                    candidate = party_candidates[0]
                    candidate_name = candidate.get('name')
                    actual_percentage = 85.0
                    poll_result = self._calculate_poll_result(actual_percentage, margin_of_error=3.0)

                    poll_results.append({
                        "candidate": candidate,
                        "name": candidate_name,
                        "poll": poll_result,
                        "actual": actual_percentage,
                        "party": party,
                        "is_highlighted": candidate == highlighted_candidate
                    })
                else:
                    total_points = sum(c.get('points', 0) for c in party_candidates)
                    for candidate in party_candidates:
                        candidate_name = candidate.get('name')

                        if total_points == 0:
                            actual_percentage = 100.0 / len(party_candidates)
                        else:
                            candidate_points = candidate.get('points', 0)
                            actual_percentage = (candidate_points / total_points) * 100.0
                            actual_percentage = max(15.0, actual_percentage)

                        poll_result = self._calculate_poll_result(actual_percentage, margin_of_error=3.0)

                        poll_results.append({
                            "candidate": candidate,
                            "name": candidate_name,
                            "poll": poll_result,
                            "actual": actual_percentage,
                            "party": party,
                            "is_highlighted": candidate == highlighted_candidate
                        })

        poll_results.sort(key=lambda x: x["poll"], reverse=True)

        # Get state baseline data
        state_data = PRESIDENTIAL_STATE_DATA.get(state_upper, {})
        baseline_rep = state_data.get("republican", 33.0)
        baseline_dem = state_data.get("democrat", 33.0)
        baseline_other = state_data.get("other", 34.0)

        # Generate private polling details
        polling_orgs = [
            "Internal Campaign Research", "Private Polling Firm", "Campaign Analytics",
            "Strategic Polling Group", "Confidential Research LLC"
        ]
        polling_org = random.choice(polling_orgs)
        sample_size = random.randint(800, 2000)
        days_ago = random.randint(1, 3)

        embed = discord.Embed(
            title=f"🔒 Private Presidential Poll: {state_upper}",
            description=f"**Presidential Race in {state_upper}** • {current_phase} ({current_year})",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        def create_progress_bar(percentage, width=20):
            filled = int((percentage / 100) * width)
            empty = width - filled
            return "█" * filled + "░" * empty

        if current_phase == "General Campaign":
            # General election - show all candidates together with actual percentages
            results_text = ""
            for i, result in enumerate(poll_results, 1):
                highlight = "👑 " if result["is_highlighted"] else ""
                party_abbrev = result['party'][0] if result.get('party') else "I"
                progress_bar = create_progress_bar(result['percentage'])

                results_text += f"**{i}. {highlight}{result['name']}**\n"
                results_text += f"**{party_abbrev} - {result.get('party', 'Independent')}**\n"
                results_text += f"{progress_bar} **{result['percentage']}%** (Actual: ~{result['actual_percentage']}%) \n\n"

            embed.add_field(
                name="🇺🇸 Presidential General Election",
                value=results_text,
                inline=False
            )
        else:
            # Primary campaign - group by party
            parties_displayed = {}
            for result in poll_results:
                party = result.get("party", "Independent")
                if party not in parties_displayed:
                    parties_displayed[party] = []
                parties_displayed[party].append(result)

            for party, party_results in parties_displayed.items():
                party_text = ""
                party_abbrev = party[0] if party else "I"

                for i, result in enumerate(party_results, 1):
                    highlight = "👑 " if result["is_highlighted"] else ""
                    progress_bar = create_progress_bar(result['poll'])

                    party_text += f"**{i}. {highlight}{result['name']}**\n"
                    party_text += f"**{party_abbrev} - {party}**\n"
                    party_text += f"{progress_bar} **{result['poll']:.1f}%** \n\n"

                embed.add_field(
                    name=f"🎗️ {party} Primary",
                    value=party_text,
                    inline=True
                )

        # Add state context
        embed.add_field(
            name=f"📍 {state_upper} Context",
            value=f"**Baseline Republican:** {baseline_rep:.1f}%\n"
                  f"**Baseline Democrat:** {baseline_dem:.1f}%\n"
                  f"**Baseline Other:** {baseline_other:.1f}%",
            inline=True
        )

        embed.add_field(
            name="📋 Poll Details",
            value=f"**Polling Organization:** {polling_org}\n"
                  f"**Sample Size:** {sample_size:,} likely voters\n"
                  f"**Margin of Error:** ±3.0%\n"
                  f"**Field Period:** {days_ago} day{'s' if days_ago > 1 else ''} ago\n"
                  f"**Stamina Cost:** 1 (Remaining: {current_stamina - 1})",
            inline=False
        )

        embed.add_field(
            name="🔒 Privacy Notice",
            value="Private poll shows simulated support with a ±3% margin of error. Internal metrics are not disclosed.",
            inline=False
        )

        embed.set_footer(text=f"Private poll conducted by {polling_org}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Add autocomplete for pres_private_poll
    @pres_private_poll.autocomplete("state")
    async def state_autocomplete_pres_private_poll(self, interaction: discord.Interaction, current: str):
        try:
            from .presidential_winners import PRESIDENTIAL_STATE_DATA
            states = list(PRESIDENTIAL_STATE_DATA.keys())
            filtered_states = [state for state in states if current.upper() in state.upper()]
            return [app_commands.Choice(name=state, value=state) for state in filtered_states[:25]]
        except ImportError:
            return []

    @pres_private_poll.autocomplete("candidate_name")
    async def candidate_autocomplete_pres_private_poll(self, interaction: discord.Interaction, current: str):
        """Get presidential candidate choices for autocomplete"""
        try:
            # Get time config for current year/phase context
            time_col, time_config = self._get_time_config(interaction.guild.id)

            if not time_config:
                return []

            current_year = time_config["current_rp_date"].year
            current_phase = time_config.get("current_phase", "")
            candidate_names = []

            if current_phase == "General Campaign":
                # Check presidential_winners collection first
                pres_col = self.bot.db["presidential_winners"]
                pres_config = pres_col.find_one({"guild_id": interaction.guild.id})

                if pres_config:
                    winners_data = pres_config.get("winners", [])

                    if isinstance(winners_data, dict):
                        candidate_names.extend([name for name in winners_data.values() if isinstance(name, str)])
                    elif isinstance(winners_data, list):
                        # Primary winners are stored with the election year (current year during General Campaign)
                        for winner in winners_data:
                            if (isinstance(winner, dict) and
                                winner.get("primary_winner", False) and
                                winner.get("year") == current_year and
                                winner.get("office") == "President"):
                                candidate_names.append(winner.get("name", ""))

                # Fallback to all_winners if no candidates found
                if not candidate_names:
                    winners_col = self.bot.db["winners"]
                    winners_config = winners_col.find_one({"guild_id": interaction.guild.id})
                    if winners_config:
                        # Primary winners are stored with the election year (current year during General Campaign)
                        for winner in winners_config.get("winners", []):
                            if (winner.get("office") == "President" and
                                winner.get("primary_winner", False) and
                                winner.get("year") == current_year):
                                candidate_names.append(winner.get("candidate", ""))
            else:
                # For primary campaign, show all registered candidates
                pres_col = self.bot.db["presidential_signups"]
                pres_config = pres_col.find_one({"guild_id": interaction.guild.id})
                if pres_config:
                    for candidate in pres_config.get("candidates", []):
                        if (candidate.get("year") == current_year and
                            candidate.get("office") == "President"):
                            candidate_names.append(candidate.get("name", ""))

            # Filter by current input
            if current:
                filtered_names = [name for name in candidate_names if current.lower() in name.lower()]
            else:
                filtered_names = candidate_names

            return [app_commands.Choice(name=name, value=name) for name in filtered_names[:25]]

        except Exception as e:
            print(f"Error in candidate autocomplete: {e}")
            return []

    # Add autocomplete for media_pres_poll
    @media_pres_poll.autocomplete("state")
    async def state_autocomplete_media_pres_poll(self, interaction: discord.Interaction, current: str):
        try:
            from .presidential_winners import PRESIDENTIAL_STATE_DATA
            states = list(PRESIDENTIAL_STATE_DATA.keys())
            filtered_states = [state for state in states if current.upper() in state.upper()]
            return [app_commands.Choice(name=state, value=state) for state in filtered_states[:25]]
        except ImportError:
            return []

    @media_pres_poll.autocomplete("candidate_name")
    async def candidate_autocomplete_media_pres_poll(self, interaction: discord.Interaction, current: str):
        """Get presidential candidate choices for autocomplete"""
        try:
            # Get time config for current year/phase context
            time_col, time_config = self._get_time_config(interaction.guild.id)

            if not time_config:
                return []

            current_year = time_config["current_rp_date"].year
            current_phase = time_config.get("current_phase", "")
            candidate_names = []

            if current_phase == "General Campaign":
                # First check winners collection for primary winners
                winners_col = self.bot.db["winners"]
                winners_config = winners_col.find_one({"guild_id": interaction.guild.id})
                if winners_config:
                    # Primary winners are stored with the election year (current year during General Campaign)
                    for winner in winners_config.get("winners", []):
                        if (winner.get("office") == "President" and
                            winner.get("primary_winner", False) and
                            winner.get("year") == current_year):
                            candidate_names.append(winner.get("candidate", ""))

                # If no candidates found, try presidential_winners collection
                if not candidate_names:
                    pres_col = self.bot.db["presidential_winners"]
                    pres_config = pres_col.find_one({"guild_id": interaction.guild.id})
                    if pres_config:
                        winners_data = pres_config.get("winners", [])

                        if isinstance(winners_data, list):
                            for winner in winners_data:
                                if (isinstance(winner, dict) and
                                    winner.get("primary_winner", False) and
                                    winner.get("year") == current_year and
                                    winner.get("office") == "President"):
                                    candidate_names.append(winner.get("name", ""))
                        elif isinstance(winners_data, dict):
                            candidate_names.extend([name for name in winners_data.values() if isinstance(name, str)])
            else:
                # For primary campaign, show all registered candidates
                pres_col = self.bot.db["presidential_signups"]
                pres_config = pres_col.find_one({"guild_id": interaction.guild.id})
                if pres_config:
                    for candidate in pres_config.get("candidates", []):
                        if (candidate.get("year") == current_year and
                            candidate.get("office") == "President"):
                            candidate_names.append(candidate.get("name", ""))

            # Filter by current input
            if current:
                filtered_names = [name for name in candidate_names if current.lower() in name.lower()]
            else:
                filtered_names = candidate_names

            return [app_commands.Choice(name=name, value=name) for name in filtered_names[:25]]

        except Exception as e:
            print(f"Error in candidate autocomplete: {e}")
            return []


async def setup(bot):
    await bot.add_cog(Polling(bot))