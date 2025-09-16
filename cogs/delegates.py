import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
import asyncio
from typing import Dict, List, Optional

class Delegates(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.delegate_check_loop.start()
        print("Delegates cog loaded successfully")

        # Primary schedule data from your file
        self.dnc_schedule = [
            {"order": 1, "month": 8, "day": 3, "state": "New Hampshire", "party": "Democrats", "delegates": 33},
            {"order": 2, "month": 8, "day": 3, "state": "South Carolina", "party": "Democrats", "delegates": 55},
            {"order": 3, "month": 8, "day": 4, "state": "Nevada", "party": "Democrats", "delegates": 36},
            {"order": 4, "month": 8, "day": 12, "state": "Michigan", "party": "Democrats", "delegates": 117},
            {"order": 5, "month": 9, "day": 5, "state": "Alabama", "party": "Democrats", "delegates": 52},
            {"order": 6, "month": 9, "day": 5, "state": "Samoa", "party": "Democrats", "delegates": 6},
            {"order": 7, "month": 9, "day": 5, "state": "Arkansas", "party": "Democrats", "delegates": 31},
            {"order": 8, "month": 9, "day": 5, "state": "California", "party": "Democrats", "delegates": 424},
            {"order": 9, "month": 9, "day": 5, "state": "Colorado", "party": "Democrats", "delegates": 72},
            {"order": 10, "month": 9, "day": 5, "state": "Iowa", "party": "Democrats", "delegates": 40},
            {"order": 11, "month": 9, "day": 5, "state": "Maine", "party": "Democrats", "delegates": 24},
            {"order": 12, "month": 9, "day": 5, "state": "Massachusetts", "party": "Democrats", "delegates": 92},
            {"order": 13, "month": 9, "day": 5, "state": "Minnesota", "party": "Democrats", "delegates": 75},
            {"order": 14, "month": 9, "day": 5, "state": "North Carolina", "party": "Democrats", "delegates": 116},
            {"order": 15, "month": 9, "day": 5, "state": "Oklahoma", "party": "Democrats", "delegates": 36},
            {"order": 16, "month": 9, "day": 5, "state": "Tennessee", "party": "Democrats", "delegates": 63},
            {"order": 17, "month": 9, "day": 5, "state": "Texas", "party": "Democrats", "delegates": 244},
            {"order": 18, "month": 9, "day": 5, "state": "Utah", "party": "Democrats", "delegates": 30},
            {"order": 19, "month": 9, "day": 5, "state": "Vermont", "party": "Democrats", "delegates": 16},
            {"order": 20, "month": 9, "day": 5, "state": "Virginia", "party": "Democrats", "delegates": 99},
            {"order": 21, "month": 9, "day": 6, "state": "Hawaii", "party": "Democrats", "delegates": 22},
            {"order": 22, "month": 9, "day": 12, "state": "Georgia", "party": "Democrats", "delegates": 108},
            {"order": 23, "month": 9, "day": 13, "state": "Mississippi", "party": "Democrats", "delegates": 35},
            {"order": 24, "month": 9, "day": 14, "state": "Marianas", "party": "Democrats", "delegates": 6},
            {"order": 25, "month": 9, "day": 15, "state": "Washington", "party": "Democrats", "delegates": 92},
            {"order": 26, "month": 9, "day": 16, "state": "Delaware", "party": "Democrats", "delegates": 19},
            {"order": 27, "month": 9, "day": 17, "state": "Florida", "party": "Democrats", "delegates": 224},
            {"order": 28, "month": 9, "day": 18, "state": "Arizona", "party": "Democrats", "delegates": 72},
            {"order": 29, "month": 9, "day": 19, "state": "Illinois", "party": "Democrats", "delegates": 147},
            {"order": 30, "month": 9, "day": 20, "state": "Kansas", "party": "Democrats", "delegates": 33},
            {"order": 31, "month": 9, "day": 21, "state": "Ohio", "party": "Democrats", "delegates": 127},
            {"order": 32, "month": 9, "day": 22, "state": "Louisiana", "party": "Democrats", "delegates": 48},
            {"order": 33, "month": 9, "day": 23, "state": "Missouri", "party": "Democrats", "delegates": 64},
            {"order": 34, "month": 9, "day": 24, "state": "North Dakota", "party": "Democrats", "delegates": 13},
            {"order": 35, "month": 9, "day": 25, "state": "Connecticut", "party": "Democrats", "delegates": 60},
            {"order": 36, "month": 9, "day": 26, "state": "New York", "party": "Democrats", "delegates": 268},
            {"order": 37, "month": 9, "day": 27, "state": "Rhode Island", "party": "Democrats", "delegates": 26},
            {"order": 38, "month": 9, "day": 28, "state": "Wisconsin", "party": "Democrats", "delegates": 82},
            {"order": 39, "month": 9, "day": 29, "state": "Alaska", "party": "Democrats", "delegates": 15},
            {"order": 40, "month": 9, "day": 30, "state": "Wyoming", "party": "Democrats", "delegates": 13},
            {"order": 41, "month": 10, "day": 3, "state": "Pennsylvania", "party": "Democrats", "delegates": 159},
            {"order": 42, "month": 10, "day": 5, "state": "Puerto Rico", "party": "Democrats", "delegates": 55},
            {"order": 43, "month": 10, "day": 7, "state": "Indiana", "party": "Democrats", "delegates": 79},
            {"order": 44, "month": 10, "day": 14, "state": "Maryland", "party": "Democrats", "delegates": 95},
            {"order": 45, "month": 10, "day": 15, "state": "Nebraska", "party": "Democrats", "delegates": 29},
            {"order": 46, "month": 10, "day": 16, "state": "West Virginia", "party": "Democrats", "delegates": 20},
            {"order": 47, "month": 10, "day": 21, "state": "Kentucky", "party": "Democrats", "delegates": 53},
            {"order": 48, "month": 10, "day": 22, "state": "Oregon", "party": "Democrats", "delegates": 66},
            {"order": 49, "month": 10, "day": 23, "state": "Idaho", "party": "Democrats", "delegates": 23},
            {"order": 50, "month": 11, "day": 4, "state": "District of Columbia", "party": "Democrats", "delegates": 20},
            {"order": 51, "month": 11, "day": 5, "state": "Montana", "party": "Democrats", "delegates": 20},
            {"order": 52, "month": 11, "day": 6, "state": "New Jersey", "party": "Democrats", "delegates": 126},
            {"order": 53, "month": 11, "day": 7, "state": "New Mexico", "party": "Democrats", "delegates": 34},
            {"order": 54, "month": 11, "day": 8, "state": "South Dakota", "party": "Democrats", "delegates": 16},
            {"order": 55, "month": 11, "day": 9, "state": "Guam", "party": "Democrats", "delegates": 7},
            {"order": 56, "month": 11, "day": 10, "state": "Virgin Islands", "party": "Democrats", "delegates": 7}
        ]

        self.gop_schedule = [
            {"order": 1, "month": 8, "day": 3, "state": "Iowa", "party": "Republican", "delegates": 40},
            {"order": 2, "month": 8, "day": 3, "state": "New Hampshire", "party": "Republican", "delegates": 22},
            {"order": 3, "month": 8, "day": 4, "state": "Nevada", "party": "Republican", "delegates": 26},
            {"order": 4, "month": 8, "day": 6, "state": "Virgin Islands", "party": "Republican", "delegates": 9},
            {"order": 5, "month": 8, "day": 13, "state": "South Carolina", "party": "Republican", "delegates": 50},
            {"order": 6, "month": 8, "day": 23, "state": "Michigan", "party": "Republican", "delegates": 55},
            {"order": 7, "month": 9, "day": 2, "state": "Idaho", "party": "Republican", "delegates": 32},
            {"order": 8, "month": 9, "day": 2, "state": "Missouri", "party": "Republican", "delegates": 54},
            {"order": 9, "month": 9, "day": 3, "state": "District of Columbia", "party": "Republican", "delegates": 19},
            {"order": 10, "month": 9, "day": 4, "state": "North Dakota", "party": "Republican", "delegates": 29},
            {"order": 11, "month": 9, "day": 5, "state": "Alabama", "party": "Republican", "delegates": 49},
            {"order": 12, "month": 9, "day": 5, "state": "Alaska", "party": "Republican", "delegates": 28},
            {"order": 13, "month": 9, "day": 5, "state": "Arkansas", "party": "Republican", "delegates": 40},
            {"order": 14, "month": 9, "day": 5, "state": "California", "party": "Republican", "delegates": 169},
            {"order": 15, "month": 9, "day": 5, "state": "Colorado", "party": "Republican", "delegates": 37},
            {"order": 16, "month": 9, "day": 5, "state": "Maine", "party": "Republican", "delegates": 20},
            {"order": 17, "month": 9, "day": 5, "state": "Massachusetts", "party": "Republican", "delegates": 40},
            {"order": 18, "month": 9, "day": 5, "state": "Minnesota", "party": "Republican", "delegates": 39},
            {"order": 19, "month": 9, "day": 5, "state": "North Carolina", "party": "Republican", "delegates": 74},
            {"order": 20, "month": 9, "day": 5, "state": "Oklahoma", "party": "Republican", "delegates": 43},
            {"order": 21, "month": 9, "day": 5, "state": "Tennessee", "party": "Republican", "delegates": 58},
            {"order": 22, "month": 9, "day": 5, "state": "Texas", "party": "Republican", "delegates": 161},
            {"order": 23, "month": 9, "day": 5, "state": "Utah", "party": "Republican", "delegates": 40},
            {"order": 24, "month": 9, "day": 5, "state": "Vermont", "party": "Republican", "delegates": 17},
            {"order": 25, "month": 9, "day": 5, "state": "Virginia", "party": "Republican", "delegates": 49},
            {"order": 26, "month": 9, "day": 8, "state": "Samoa", "party": "Republican", "delegates": 9},
            {"order": 27, "month": 9, "day": 12, "state": "Georgia", "party": "Republican", "delegates": 59},
            {"order": 28, "month": 9, "day": 13, "state": "Hawaii", "party": "Republican", "delegates": 19},
            {"order": 29, "month": 9, "day": 14, "state": "Mississippi", "party": "Republican", "delegates": 40},
            {"order": 30, "month": 9, "day": 15, "state": "Washington", "party": "Republican", "delegates": 43},
            {"order": 31, "month": 9, "day": 16, "state": "Marianas", "party": "Republican", "delegates": 9},
            {"order": 32, "month": 9, "day": 17, "state": "Guam", "party": "Republican", "delegates": 9},
            {"order": 33, "month": 9, "day": 18, "state": "Arizona", "party": "Republican", "delegates": 43},
            {"order": 34, "month": 9, "day": 19, "state": "Florida", "party": "Republican", "delegates": 125},
            {"order": 35, "month": 9, "day": 20, "state": "Illinois", "party": "Republican", "delegates": 64},
            {"order": 36, "month": 9, "day": 21, "state": "Kansas", "party": "Republican", "delegates": 39},
            {"order": 37, "month": 9, "day": 22, "state": "Ohio", "party": "Republican", "delegates": 79},
            {"order": 38, "month": 9, "day": 23, "state": "Louisiana", "party": "Republican", "delegates": 47},
            {"order": 39, "month": 9, "day": 24, "state": "Connecticut", "party": "Republican", "delegates": 28},
            {"order": 40, "month": 9, "day": 25, "state": "New York", "party": "Republican", "delegates": 91},
            {"order": 41, "month": 9, "day": 26, "state": "Rhode Island", "party": "Republican", "delegates": 19},
            {"order": 42, "month": 9, "day": 27, "state": "Wisconsin", "party": "Republican", "delegates": 41},
            {"order": 43, "month": 9, "day": 28, "state": "Wyoming", "party": "Republican", "delegates": 29},
            {"order": 44, "month": 9, "day": 29, "state": "Puerto Rico", "party": "Republican", "delegates": 23},
            {"order": 45, "month": 9, "day": 30, "state": "Pennsylvania", "party": "Republican", "delegates": 67},
            {"order": 46, "month": 10, "day": 7, "state": "Indiana", "party": "Republican", "delegates": 58},
            {"order": 47, "month": 10, "day": 14, "state": "Maryland", "party": "Republican", "delegates": 37},
            {"order": 48, "month": 10, "day": 15, "state": "Nebraska", "party": "Republican", "delegates": 36},
            {"order": 49, "month": 10, "day": 16, "state": "West Virginia", "party": "Republican", "delegates": 32},
            {"order": 50, "month": 10, "day": 10, "state": "Kentucky", "party": "Republican", "delegates": 46},
            {"order": 51, "month": 10, "day": 21, "state": "Oregon", "party": "Republican", "delegates": 31},
            {"order": 52, "month": 11, "day": 4, "state": "Montana", "party": "Republican", "delegates": 31},
            {"order": 53, "month": 11, "day": 5, "state": "New Jersey", "party": "Republican", "delegates": 12},
            {"order": 54, "month": 11, "day": 6, "state": "New Mexico", "party": "Republican", "delegates": 22},
            {"order": 55, "month": 11, "day": 7, "state": "Delaware", "party": "Republican", "delegates": 16},
            {"order": 56, "month": 11, "day": 8, "state": "South Dakota", "party": "Republican", "delegates": 29}
        ]

    def cog_unload(self):
        self.delegate_check_loop.cancel()

    def _get_delegates_config(self, guild_id: int):
        """Get or create delegates configuration for a guild"""
        col = self.bot.db["delegates_config"]
        config = col.find_one({"guild_id": guild_id})
        if not config:
            config = {
                "guild_id": guild_id,
                "called_states": [],  # List of states that have been called
                "delegate_totals": {},  # Candidate delegate totals
                "enabled": True,
                "paused": False, # Added paused state
                "last_check": datetime.utcnow()
            }
            col.insert_one(config)
        return col, config

    def _get_time_config(self, guild_id: int):
        """Get time configuration"""
        col = self.bot.db["time_configs"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _calculate_current_rp_time(self, time_config):
        """Calculate current RP time based on time manager configuration"""
        last_update = time_config["last_real_update"]
        current_real_time = datetime.utcnow()
        real_minutes_elapsed = (current_real_time - last_update).total_seconds() / 60

        minutes_per_rp_day = time_config["minutes_per_rp_day"]
        rp_days_elapsed = real_minutes_elapsed / minutes_per_rp_day

        current_rp_date = time_config["current_rp_date"] + timedelta(days=rp_days_elapsed)
        return current_rp_date

    def _get_presidential_candidates(self, guild_id: int, party: str, year: int):
        """Get presidential candidates for a specific party and year"""
        candidates = []
        
        print(f"Searching for candidates: party='{party}', year={year}, guild_id={guild_id}")
        
        # First check presidential_signups collection
        pres_col = self.bot.db["presidential_signups"]
        pres_config = pres_col.find_one({"guild_id": guild_id})
        
        if pres_config:
            print(f"Found presidential_signups config with {len(pres_config.get('candidates', []))} total candidates")
            for candidate in pres_config.get("candidates", []):
                candidate_party = candidate.get("party", "").lower()
                candidate_year = candidate.get("year", 0)
                candidate_office = candidate.get("office", "")
                
                print(f"  Checking candidate: {candidate.get('name')}, party='{candidate_party}', year={candidate_year}, office='{candidate_office}'")
                
                # More flexible party matching
                party_match = False
                if party.lower() == "democrats" or party.lower() == "democratic":
                    party_match = "democrat" in candidate_party
                elif party.lower() == "republicans" or party.lower() == "republican":
                    party_match = "republican" in candidate_party
                else:
                    party_match = candidate_party == party.lower()
                
                if (party_match and 
                    candidate_year == year and
                    candidate_office == "President"):
                    print(f"    -> MATCH! Adding {candidate.get('name')}")
                    candidates.append(candidate)
        else:
            print("No presidential_signups config found")
        
        print(f"Final result: Found {len(candidates)} presidential candidates")
        return candidates

    def _allocate_delegates(self, candidates: List[dict], total_delegates: int):
        """Allocate delegates proportionally based on candidate points"""
        if not candidates:
            return {}

        # Calculate total points
        total_points = sum(candidate.get("points", 0) for candidate in candidates)

        if total_points == 0:
            # If no points, allocate equally
            delegates_per_candidate = total_delegates // len(candidates)
            remaining = total_delegates % len(candidates)

            allocation = {}
            for i, candidate in enumerate(candidates):
                allocation[candidate["name"]] = delegates_per_candidate
                if i < remaining:
                    allocation[candidate["name"]] += 1
        else:
            # Proportional allocation based on points
            allocation = {}
            allocated_delegates = 0

            for candidate in candidates[:-1]:  # All but last candidate
                delegates = round((candidate.get("points", 0) / total_points) * total_delegates)
                allocation[candidate["name"]] = delegates
                allocated_delegates += delegates

            # Give remaining delegates to last candidate
            if candidates:
                last_candidate = candidates[-1]
                allocation[last_candidate["name"]] = total_delegates - allocated_delegates

        return allocation

    @tasks.loop(minutes=5)
    async def delegate_check_loop(self):
        """Check for states to call every 5 minutes"""
        try:
            # Get all guild configurations
            time_col = self.bot.db["time_configs"]
            time_configs = time_col.find({})

            for time_config in time_configs:
                guild_id = time_config["guild_id"]
                guild = self.bot.get_guild(guild_id)

                if not guild:
                    continue

                # Calculate current RP time
                current_rp_date = self._calculate_current_rp_time(time_config)
                current_phase = time_config.get("current_phase", "")
                current_year = current_rp_date.year

                # Auto-enable delegate system during presidential election years (odd years) and Primary Campaign phase
                delegates_col, delegates_config = self._get_delegates_config(guild_id)

                # Check if this is a presidential primary year (odd years) and Primary Campaign phase
                if current_year % 2 == 1 and current_phase == "Primary Campaign":
                    # Auto-enable delegate system if not already enabled
                    if not delegates_config.get("enabled", True):
                        delegates_col.update_one(
                            {"guild_id": guild_id},
                            {"$set": {"enabled": True}}
                        )
                        delegates_config["enabled"] = True
                        print(f"Auto-enabled delegate system for guild {guild_id} (Presidential primary year {current_year})")

                # Only check during Primary Campaign phase, if enabled, and not paused
                if (current_phase != "Primary Campaign" or 
                    not delegates_config.get("enabled", True) or
                    delegates_config.get("paused", False)):
                    continue

                # Only process delegates during presidential election years (odd years)
                if current_year % 2 != 1:
                    continue

                # Check both Democratic and Republican schedules
                # Only process if primary not already won
                primary_winners = delegates_config.get("primary_winners", {})

                if f"Democrats_{current_year}" not in primary_winners:
                    await self._check_and_call_states(
                        guild, guild_id, current_rp_date, current_year, 
                        self.dnc_schedule, "Democrats", delegates_config, delegates_col
                    )

                if f"Republican_{current_year}" not in primary_winners:
                    await self._check_and_call_states(
                        guild, guild_id, current_rp_date, current_year, 
                        self.gop_schedule, "Republican", delegates_config, delegates_col
                    )

        except Exception as e:
            print(f"Error in delegate check loop: {e}")

    def _calculate_current_rp_time(self, time_config):
        """Calculate current RP time based on time manager configuration"""
        last_update = time_config["last_real_update"]
        current_real_time = datetime.utcnow()
        real_minutes_elapsed = (current_real_time - last_update).total_seconds() / 60

        minutes_per_rp_day = time_config["minutes_per_rp_day"]
        rp_days_elapsed = real_minutes_elapsed / minutes_per_rp_day

        current_rp_date = time_config["current_rp_date"] + timedelta(days=rp_days_elapsed)
        return current_rp_date

    async def _check_and_call_states(self, guild, guild_id: int, current_rp_date, current_year: int, 
                                   schedule: List[dict], party: str, delegates_config: dict, delegates_col):
        """Check if any states should be called and call them"""
        for state_data in schedule:
            state_key = f"{state_data['state']}_{party}_{current_year}"

            # Skip if already called
            if state_key in delegates_config.get("called_states", []):
                continue

            # Create proper date objects for comparison
            try:
                state_date = datetime(current_year, state_data["month"], state_data["day"])
                current_date = datetime(current_rp_date.year, current_rp_date.month, current_rp_date.day)

                # Debug logging
                print(f"Checking {state_data['state']} ({party}): state_date={state_date.strftime('%Y-%m-%d')}, current_date={current_date.strftime('%Y-%m-%d')}")

                # Check if the state date has passed or is today
                if current_date >= state_date:
                    print(f"  -> Should call! {current_date} >= {state_date}")
                else:
                    print(f"  -> Not yet. {current_date} < {state_date}")
                    continue
            except ValueError as e:
                print(f"Date error for {state_data['state']} ({party}): {e}")
                continue

            # Check if the state date has passed or is today
            if current_date >= state_date:
                await self._call_state(
                    guild, guild_id, state_data, party, current_year, 
                    delegates_config, delegates_col
                )

    async def _call_state(self, guild, guild_id: int, state_data: dict, party: str, 
                         year: int, delegates_config: dict, delegates_col):
        """Call a state and allocate delegates"""
        state_name = state_data["state"]
        total_delegates = state_data["delegates"]
        state_key = f"{state_name}_{party}_{year}"

        # Get presidential candidates for this party
        candidates = self._get_presidential_candidates(guild_id, party, year)
        print(f"Found {len(candidates)} candidates for {party} in {year}")

        if not candidates:
            # No candidates, skip this state
            print(f"No candidates found for {party} in {year}, skipping state announcement")
            delegates_config["called_states"].append(state_key)
            delegates_col.update_one(
                {"guild_id": guild_id},
                {"$set": {"called_states": delegates_config["called_states"]}}
            )
            return

        # Allocate delegates
        allocation = self._allocate_delegates(candidates, total_delegates)
        print(f"Delegate allocation: {allocation}")

        # Update delegate totals
        if "delegate_totals" not in delegates_config:
            delegates_config["delegate_totals"] = {}

        for candidate_name, delegates in allocation.items():
            if candidate_name not in delegates_config["delegate_totals"]:
                delegates_config["delegate_totals"][candidate_name] = 0
            delegates_config["delegate_totals"][candidate_name] += delegates

        # Mark state as called
        delegates_config["called_states"].append(state_key)

        # Update database
        delegates_col.update_one(
            {"guild_id": guild_id},
            {
                "$set": {
                    "called_states": delegates_config["called_states"],
                    "delegate_totals": delegates_config["delegate_totals"]
                }
            }
        )

        # Check for primary winners after delegate allocation
        await self._check_primary_winners(guild, guild_id, party, year, delegates_config)

        # Send announcement
        print(f"Sending state announcement for {state_name} ({party})")
        await self._send_state_announcement(guild, state_name, party, total_delegates, allocation)

        # Update voice channel with current RP time if configured
        await self._update_voice_channel_time(guild)

    async def _check_primary_winners(self, guild, guild_id: int, party: str, year: int, delegates_config: dict):
        """Check if any candidate has reached the delegate threshold to win the primary"""
        delegate_totals = delegates_config.get("delegate_totals", {})

        # Set delegate thresholds - these are the actual thresholds needed to win
        if party == "Democrats":
            delegate_threshold = 1991  # Majority of 3979 total delegates
        elif party == "Republican":
            delegate_threshold = 1215  # Majority of 2429 total delegates  
        else:
            return  # No threshold for other parties

        print(f"Checking primary winners for {party} {year}: threshold = {delegate_threshold}")

        # Find candidates for this party
        candidates = self._get_presidential_candidates(guild_id, party, year)
        party_candidates = []
        for c in candidates:
            candidate_party = c.get("party", "").lower()
            if party.lower() == "democrats" or party.lower() == "democratic":
                party_match = "democrat" in candidate_party
            elif party.lower() == "republicans" or party.lower() == "republican":
                party_match = "republican" in candidate_party
            else:
                party_match = candidate_party == party.lower()
            
            if party_match:
                party_candidates.append(c)

        print(f"Found {len(party_candidates)} candidates for {party}")

        # Check if any candidate reached the threshold
        winner = None
        for candidate in party_candidates:
            candidate_delegates = delegate_totals.get(candidate["name"], 0)
            print(f"  {candidate['name']}: {candidate_delegates} delegates (need {delegate_threshold})")
            if candidate_delegates >= delegate_threshold:
                winner = candidate
                print(f"  -> WINNER! {candidate['name']} has reached the threshold!")
                break

        if winner:
            # Check if already declared winner to prevent duplicate announcements
            if "primary_winners" not in delegates_config:
                delegates_config["primary_winners"] = {}

            primary_key = f"{party}_{year}"
            if primary_key not in delegates_config["primary_winners"]:
                print(f"Declaring new primary winner: {winner['name']} for {party} {year}")
                delegates_config["primary_winners"][primary_key] = winner["name"]

                # Update presidential_winners
                await self._declare_primary_winner(guild, guild_id, winner, party, year)

                # Update database
                delegates_col = self.bot.db["delegates_config"]
                delegates_col.update_one(
                    {"guild_id": guild_id},
                    {"$set": {"primary_winners": delegates_config["primary_winners"]}}
                )
            else:
                print(f"Primary winner already declared for {party} {year}: {delegates_config['primary_winners'][primary_key]}")

    async def _declare_primary_winner(self, guild, guild_id: int, winner: dict, party: str, year: int):
        """Declare a primary winner and update presidential_winners"""
        # Get presidential winners config
        winners_col = self.bot.db["presidential_winners"]
        winners_config = winners_col.find_one({"guild_id": guild_id})

        if not winners_config:
            winners_config = {
                "guild_id": guild_id,
                "winners": {}
            }

        if "winners" not in winners_config:
            winners_config["winners"] = {}

        # Add winner to presidential_winners
        winners_config["winners"][party] = winner["name"]

        # Handle Independents separately - they automatically win
        signups_col = self.bot.db["presidential_signups"]
        signups_config = signups_col.find_one({"guild_id": guild_id})

        if signups_config:
            independent_candidates = [
                c for c in signups_config.get("candidates", [])
                if c.get("year") == year and c.get("office") == "President" 
                and c.get("party", "").lower() not in ["democrats", "democratic party", "republicans", "republican party"]
            ]

            if independent_candidates:
                # For multiple independents, we'll handle them in the "Others" category
                if len(independent_candidates) == 1:
                    winners_config["winners"]["Others"] = independent_candidates[0]["name"]
                else:
                    # Multiple independents - could be handled various ways
                    # For now, take the one with most points
                    best_independent = max(independent_candidates, key=lambda x: x.get("points", 0))
                    winners_config["winners"]["Others"] = best_independent["name"]

        # Update database
        winners_col.replace_one(
            {"guild_id": guild_id},
            winners_config,
            upsert=True
        )

        # Send primary winner announcement
        await self._send_primary_winner_announcement(guild, winner, party, year)

        # Update voice channel with current RP time
        await self._update_voice_channel_time(guild)

    async def _update_voice_channel_time(self, guild):
        """Update voice channel with current RP time if configured"""
        try:
            time_col, time_config = self._get_time_config(guild.id)
            if not time_config:
                return

            # Check if voice channel updates are enabled and channel is configured
            if (not time_config.get("update_voice_channels", True) or 
                not time_config.get("voice_channel_id")):
                return

            # Calculate current RP time
            current_rp_date = self._calculate_current_rp_time(time_config)
            date_string = current_rp_date.strftime("%B %d, %Y")

            # Get the voice channel
            channel = guild.get_channel(time_config["voice_channel_id"])
            if not channel or not hasattr(channel, 'edit'):
                return

            # Update channel name with current date
            new_name = f"📅 {date_string}"
            if channel.name != new_name:
                await channel.edit(name=new_name)
                print(f"Updated voice channel to: {new_name}")

        except Exception as e:
            print(f"Failed to update voice channel from delegates: {e}")
            pass  # Ignore errors to not disrupt delegate functionality

    async def _send_primary_winner_announcement(self, guild, winner: dict, party: str, year: int):
        """Send announcement when a primary winner is declared"""
        # DEBUG: Only allow the specific channel ID
        REQUIRED_CHANNEL_ID = 1380498828121346210
        print(f"DEBUG: _send_primary_winner_announcement called for guild {guild.id}, winner {winner['name']}, party {party}")
        
        # Find announcement channel - only use the specific channel ID
        channel = None

        # First check guild_configs (from setup.py)
        setup_col = self.bot.db["guild_configs"]
        setup_config = setup_col.find_one({"guild_id": guild.id})

        if setup_config:
            # Check announcement_channel_id first
            if setup_config.get("announcement_channel_id"):
                configured_channel_id = setup_config["announcement_channel_id"]
                print(f"DEBUG: Found configured announcement_channel_id: {configured_channel_id}")
                
                # Only use the specific channel ID
                if configured_channel_id == REQUIRED_CHANNEL_ID:
                    channel = guild.get_channel(configured_channel_id)
                    print(f"DEBUG: Using configured channel {channel} (ID: {configured_channel_id})")
                else:
                    print(f"DEBUG: WARNING - Configured channel ID {configured_channel_id} is not the required channel {REQUIRED_CHANNEL_ID}")
                    print(f"DEBUG: Falling back to required channel {REQUIRED_CHANNEL_ID}")

            # Then check announcement_channel (legacy support)
            if not channel and setup_config.get("announcement_channel"):
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

        # Create winner announcement embed
        party_color = discord.Color.blue() if party == "Democrats" else discord.Color.red()

        embed = discord.Embed(
            title=f"🏆 {party} Primary Winner Declared!",
            description=f"**{winner['name']}** has secured the {party} nomination for President!",
            color=party_color,
            timestamp=datetime.utcnow()
        )

        # Get current delegate count
        delegates_col, delegates_config = self._get_delegates_config(guild.id)
        delegate_totals = delegates_config.get("delegate_totals", {})
        winner_delegates = delegate_totals.get(winner["name"], 0)

        threshold = 1973 if party == "Democrats" else 1217

        embed.add_field(
            name="🗳️ Final Delegate Count",
            value=f"**{winner_delegates}** delegates (Required: {threshold})",
            inline=True
        )

        embed.add_field(
            name="🎯 Candidate Details",
            value=f"**Party:** {winner['party']}\n"
                  f"**Ideology:** {winner.get('ideology', 'N/A')}\n"
                  f"**Campaign Points:** {winner.get('points', 0):.2f}",
            inline=True
        )

        embed.add_field(
            name="📅 Next Steps",
            value=f"**{winner['name']}** will now move to the General Election phase.",
            inline=False
        )

        try:
            await channel.send(embed=embed)
            print(f"Primary winner announcement sent for {winner['name']} ({party}) to channel {channel.name}")
        except Exception as e:
            print(f"Failed to send primary winner announcement: {e}")
            pass  # Ignore if can't send message

    async def _send_state_announcement(self, guild, state_name: str, party: str, 
                                     total_delegates: int, allocation: dict):
        """Send announcement when a state is called"""
        # DEBUG: Only allow the specific channel ID
        REQUIRED_CHANNEL_ID = 1380498828121346210
        print(f"DEBUG: _send_state_announcement called for guild {guild.id}, state {state_name}, party {party}")
        
        # Find announcement channel - only use the specific channel ID
        channel = None

        # First check guild_configs (from setup.py)
        setup_col = self.bot.db["guild_configs"]
        setup_config = setup_col.find_one({"guild_id": guild.id})

        if setup_config:
            # Check announcement_channel_id first
            if setup_config.get("announcement_channel_id"):
                configured_channel_id = setup_config["announcement_channel_id"]
                print(f"DEBUG: Found configured announcement_channel_id: {configured_channel_id}")
                
                # Only use the specific channel ID
                if configured_channel_id == REQUIRED_CHANNEL_ID:
                    channel = guild.get_channel(configured_channel_id)
                    print(f"DEBUG: Using configured channel {channel} (ID: {configured_channel_id})")
                else:
                    print(f"DEBUG: WARNING - Configured channel ID {configured_channel_id} is not the required channel {REQUIRED_CHANNEL_ID}")
                    print(f"DEBUG: Falling back to required channel {REQUIRED_CHANNEL_ID}")

            # Then check announcement_channel (legacy support)
            if not channel and setup_config.get("announcement_channel"):
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

        # Create announcement embed
        party_color = discord.Color.blue() if party == "Democrats" else discord.Color.red()

        embed = discord.Embed(
            title=f"📢 {state_name} ({party}) Primary Called!",
            description=f"**{total_delegates} delegates** have been allocated!",
            color=party_color,
            timestamp=datetime.utcnow()
        )

        # Add allocation results
        results_text = ""
        for candidate_name, delegates in sorted(allocation.items(), key=lambda x: x[1], reverse=True):
            percentage = (delegates / total_delegates) * 100
            results_text += f"**{candidate_name}**: {delegates} delegates ({percentage:.1f}%)\n"

        embed.add_field(
            name="🗳️ Delegate Allocation",
            value=results_text,
            inline=False
        )

        try:
            await channel.send(embed=embed)
            print(f"State announcement sent for {state_name} ({party}) to channel {channel.name}")
        except Exception as e:
            print(f"Failed to send state announcement: {e}")
            pass  # Ignore if can't send message

    # Create command groups to reduce command count
    delegate_group = app_commands.Group(name="delegate", description="Delegate system commands")
    delegate_admin_group = app_commands.Group(name="admin", description="Admin delegate commands", parent=delegate_group, default_permissions=discord.Permissions(administrator=True))

    @delegate_admin_group.command(
        name="toggle_system",
        description="Enable or disable the automatic delegate system (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def toggle_delegate_system(self, interaction: discord.Interaction):
        delegates_col, delegates_config = self._get_delegates_config(interaction.guild.id)

        current_status = delegates_config.get("enabled", True)
        new_status = not current_status

        delegates_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"enabled": new_status}}
        )

        status_text = "enabled" if new_status else "disabled"
        await interaction.response.send_message(
            f"✅ Delegate system has been **{status_text}**.",
            ephemeral=True
        )

    @delegate_admin_group.command(
        name="pause_system",
        description="Pause or resume the automatic delegate checking (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def pause_delegate_system(self, interaction: discord.Interaction):
        """Pause or resume the automatic delegate checking system"""
        delegates_col, delegates_config = self._get_delegates_config(interaction.guild.id)

        current_paused = delegates_config.get("paused", False)
        new_paused = not current_paused

        delegates_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"paused": new_paused}}
        )

        status = "paused" if new_paused else "resumed"
        embed = discord.Embed(
            title="⏸️ Delegate System Paused" if new_paused else "▶️ Delegate System Resumed",
            description=f"Automatic delegate checking has been **{status}**.",
            color=discord.Color.orange() if new_paused else discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        if new_paused:
            embed.add_field(
                name="⚠️ Note",
                value="Delegate system will not call new states until resumed.",
                inline=False
            )
        else:
            embed.add_field(
                name="ℹ️ Note", 
                value="Delegate system will now check for states to call every 5 minutes.",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @delegate_admin_group.command(
        name="set_channel",
        description="Set the channel for delegate and primary winner announcements (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_delegate_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        """Set the announcement channel for delegate results and primary winners"""
        setup_col = self.bot.db["guild_configs"]
        setup_config = setup_col.find_one({"guild_id": interaction.guild.id})

        if not setup_config:
            setup_config = {"guild_id": interaction.guild.id}

        setup_config["announcement_channel_id"] = channel.id

        setup_col.replace_one(
            {"guild_id": interaction.guild.id},
            setup_config,
            upsert=True
        )

        await interaction.response.send_message(
            f"✅ Delegate announcement channel set to {channel.mention}",
            ephemeral=True
        )

    @delegate_admin_group.command(
        name="reset_delegates",
        description="Reset delegate counts for a specific party or all parties (Admin only)"
    )
    @app_commands.describe(
        party="Party to reset delegates for (Democrats, Republican, or All)",
        year="Year to reset delegates for (optional - uses current year if not specified)",
        confirm="Set to True to confirm the reset"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_delegates(
        self,
        interaction: discord.Interaction,
        party: str,
        year: int = None,
        confirm: bool = False
    ):
        """Reset delegate counts for specified party"""
        valid_parties = ["Democrats", "Republican", "All"]

        if party not in valid_parties:
            await interaction.response.send_message(
                f"❌ Invalid party. Must be one of: {', '.join(valid_parties)}",
                ephemeral=True
            )
            return

        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config:
            await interaction.response.send_message("❌ Time system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        delegates_col, delegates_config = self._get_delegates_config(interaction.guild.id)

        if not confirm:
            # Show warning and current delegate counts
            delegate_totals = delegates_config.get("delegate_totals", {})

            if party == "All":
                warning_text = f"⚠️ **Warning:** This will reset ALL delegate counts for {target_year}.\n\n"
                if delegate_totals:
                    warning_text += "**Current delegate counts:**\n"
                    for candidate_name, count in delegate_totals.items():
                        warning_text += f"• {candidate_name}: {count} delegates\n"
                else:
                    warning_text += "No delegates currently allocated.\n"
            else:
                # Find candidates for specific party
                signups_col = self.bot.db["presidential_signups"]
                signups_config = signups_col.find_one({"guild_id": interaction.guild.id})

                party_candidates = []
                if signups_config:
                    party_candidates = [
                        c["name"] for c in signups_config.get("candidates", [])
                        if c.get("year") == target_year and c.get("party", "").lower() == party.lower()
                    ]

                warning_text = f"⚠️ **Warning:** This will reset delegate counts for {party} party candidates in {target_year}.\n\n"
                if party_candidates and delegate_totals:
                    warning_text += f"**Current {party} delegate counts:**\n"
                    for candidate_name in party_candidates:
                        count = delegate_totals.get(candidate_name, 0)
                        if count > 0:
                            warning_text += f"• {candidate_name}: {count} delegates\n"
                else:
                    warning_text += f"No {party} delegates currently allocated.\n"

            warning_text += "\nTo confirm, run this command again with `confirm:True`"

            await interaction.response.send_message(warning_text, ephemeral=True)
            return

        # Perform the reset
        delegate_totals = delegates_config.get("delegate_totals", {})
        called_states = delegates_config.get("called_states", [])
        primary_winners = delegates_config.get("primary_winners", {})

        candidates_reset = []
        states_reset = []

        if party == "All":
            # Reset everything
            candidates_reset = list(delegate_totals.keys())
            states_reset = [state for state in called_states if f"_{target_year}" in state]

            # Clear all delegate totals
            delegates_config["delegate_totals"] = {}

            # Remove called states for target year
            delegates_config["called_states"] = [
                state for state in called_states 
                if f"_{target_year}" not in state
            ]

            # Initialize primary_winners if it doesn't exist
            if "primary_winners" not in delegates_config:
                delegates_config["primary_winners"] = {}

            # Remove primary winners for target year
            delegates_config["primary_winners"] = {
                key: value for key, value in delegates_config["primary_winners"].items()
                if not key.endswith(f"_{target_year}")
            }

        else:
            # Reset specific party
            signups_col = self.bot.db["presidential_signups"]
            signups_config = signups_col.find_one({"guild_id": interaction.guild.id})

            party_candidates = []
            if signups_config:
                party_candidates = [
                    c["name"] for c in signups_config.get("candidates", [])
                    if c.get("year") == target_year and c.get("party", "").lower() == party.lower()
                ]

            # Reset delegate totals for party candidates
            for candidate_name in party_candidates:
                if candidate_name in delegate_totals:
                    candidates_reset.append(candidate_name)
                    del delegates_config["delegate_totals"][candidate_name]

            # Remove called states for this party and year
            party_states = [
                state for state in called_states 
                if state.endswith(f"_{party}_{target_year}")
            ]
            states_reset = party_states

            delegates_config["called_states"] = [
                state for state in called_states 
                if not state.endswith(f"_{party}_{target_year}")
            ]

            # Initialize primary_winners if it doesn't exist
            if "primary_winners" not in delegates_config:
                delegates_config["primary_winners"] = {}

            # Remove primary winner for this party and year
            primary_key = f"{party}_{target_year}"
            if primary_key in delegates_config["primary_winners"]:
                del delegates_config["primary_winners"][primary_key]

        # Update database
        delegates_col.update_one(
            {"guild_id": interaction.guild.id},
            {
                "$set": {
                    "delegate_totals": delegates_config["delegate_totals"],
                    "called_states": delegates_config["called_states"],
                    "primary_winners": delegates_config["primary_winners"]
                }
            }
        )

        # Also reset presidential winners if primary winners were reset
        primary_winners_dict = delegates_config.get("primary_winners", {})
        if party == "All" or any(key.endswith(f"_{target_year}") for key in primary_winners_dict.keys()):
            winners_col = self.bot.db["presidential_winners"]
            winners_config = winners_col.find_one({"guild_id": interaction.guild.id})

            if winners_config:
                if party == "All":
                    # Reset all winners
                    winners_config["winners"] = {}
                else:
                    # Reset specific party winner
                    if party in winners_config.get("winners", {}):
                        del winners_config["winners"][party]

                winners_col.update_one(
                    {"guild_id": interaction.guild.id},
                    {"$set": {"winners": winners_config["winners"]}}
                )

        # Create response embed
        embed = discord.Embed(
            title="🔄 Delegate Reset Complete",
            description=f"Delegate counts have been reset for {party} party in {target_year}",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        if candidates_reset:
            embed.add_field(
                name="👥 Candidates Reset",
                value="\n".join([f"• {name}" for name in candidates_reset]),
                inline=True
            )

        embed.add_field(
            name="📊 States Reset",
            value=f"{len(states_reset)} states reset",
            inline=True
        )

        if party != "All":
            embed.add_field(
                name="🎯 Party",
                value=party,
                inline=True
            )

        embed.add_field(
            name="📅 Year",
            value=str(target_year),
            inline=True
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @delegate_admin_group.command(
        name="declare_independents",
        description="Force declare all independent candidates as winners (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def force_declare_independents(
        self,
        interaction: discord.Interaction,
        year: int = None
    ):
        """Manually declare independent candidates as primary winners"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Time system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        # Get presidential signups
        signups_col = self.bot.db["presidential_signups"]
        signups_config = signups_col.find_one({"guild_id": interaction.guild.id})

        if not signups_config:
            await interaction.response.send_message("❌ No presidential signups found.", ephemeral=True)
            return

        independent_candidates = [
            c for c in signups_config.get("candidates", [])
            if c.get("year") == target_year and c.get("office") == "President" 
            and c.get("party", "").lower() not in ["democrats", "democratic party", "republicans", "republican party"]
        ]

        if not independent_candidates:
            await interaction.response.send_message("❌ No independent candidates found.", ephemeral=True)
            return

        # Update presidential_winners
        winners_col = self.bot.db["presidential_winners"]
        winners_config = winners_col.find_one({"guild_id": interaction.guild.id})

        if not winners_config:
            winners_config = {
                "guild_id": interaction.guild.id, # Use interaction.guild.id here
                "winners": {}
            }

        if "winners" not in winners_config:
            winners_config["winners"] = {}

        if len(independent_candidates) == 1:
            winners_config["winners"]["Others"] = independent_candidates[0]["name"]
        else:
            # Multiple independents - take the one with most points
            best_independent = max(independent_candidates, key=lambda x: x.get("points", 0))
            winners_config["winners"]["Others"] = best_independent["name"]

        # Update database
        winners_col.replace_one(
            {"guild_id": interaction.guild.id},
            winners_config,
            upsert=True
        )

        winner_name = winners_config["winners"]["Others"]
        await interaction.response.send_message(
            f"✅ **{winner_name}** has been declared the Independent/Others primary winner for {target_year}!",
            ephemeral=True
        )

    @delegate_group.command(
        name="totals",
        description="View current delegate counts by party"
    )
    async def delegate_totals(self, interaction: discord.Interaction):
        """View current delegate totals for all candidates"""
        delegates_col, delegates_config = self._get_delegates_config(interaction.guild.id)
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Time system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        delegate_totals = delegates_config.get("delegate_totals", {})

        if not delegate_totals:
            await interaction.response.send_message("📊 No delegates have been allocated yet.", ephemeral=True)
            return

        # Get candidate info to group by party
        signups_col = self.bot.db["presidential_signups"]
        signups_config = signups_col.find_one({"guild_id": interaction.guild.id})

        candidates_by_party = {"Democrats": [], "Republican": [], "Others": []}

        if signups_config:
            for candidate in signups_config.get("candidates", []):
                if candidate.get("year") == current_year and candidate["name"] in delegate_totals:
                    party = candidate.get("party", "").lower()
                    if "democrat" in party:
                        candidates_by_party["Democrats"].append((candidate["name"], delegate_totals[candidate["name"]]))
                    elif "republican" in party:
                        candidates_by_party["Republican"].append((candidate["name"], delegate_totals[candidate["name"]]))
                    else:
                        candidates_by_party["Others"].append((candidate["name"], delegate_totals[candidate["name"]]))

        embed = discord.Embed(
            title="📊 Current Delegate Totals",
            description=f"Delegate counts for {current_year} primaries",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        # Sort candidates by delegate count within each party
        for party, candidates in candidates_by_party.items():
            if candidates:
                candidates.sort(key=lambda x: x[1], reverse=True)

                threshold = 1973 if party == "Democrats" else 1217 if party == "Republican" else 0
                party_text = ""

                for name, count in candidates:
                    party_text += f"**{name}**: {count} delegates\n"

                if threshold > 0:
                    party_text += f"\n*Needed to win: {threshold} delegates*"

                party_emoji = "🔵" if party == "Democrats" else "🔴" if party == "Republican" else "🟣"
                embed.add_field(
                    name=f"{party_emoji} {party}",
                    value=party_text,
                    inline=True
                )

        # Check for primary winners
        primary_winners = delegates_config.get("primary_winners", {})
        if primary_winners:
            winners_text = ""
            for key, winner in primary_winners.items():
                if f"_{current_year}" in key:
                    party = key.replace(f"_{current_year}", "")
                    winners_text += f"**{party}**: {winner}\n"

            if winners_text:
                embed.add_field(
                    name="🏆 Primary Winners",
                    value=winners_text,
                    inline=False
                )

        await interaction.response.send_message(embed=embed)

    @delegate_group.command(
        name="upcoming",
        description="See what primaries are coming up in the next month"
    )
    async def upcoming_primaries(self, interaction: discord.Interaction):
        """Show upcoming primaries in the next month"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Time system not configured.", ephemeral=True)
            return

        current_rp_date = self._calculate_current_rp_time(time_config)
        current_year = current_rp_date.year

        # Only show during presidential primary years (odd years)
        if current_year % 2 != 1:
            await interaction.response.send_message("📅 No presidential primaries scheduled this year.", ephemeral=True)
            return

        delegates_col, delegates_config = self._get_delegates_config(interaction.guild.id)
        called_states = delegates_config.get("called_states", [])

        upcoming_events = []

        # Check both party schedules
        for schedule, party in [(self.dnc_schedule, "Democrats"), (self.gop_schedule, "Republican")]:
            for state_data in schedule:
                state_key = f"{state_data['state']}_{party}_{current_year}"

                # Skip if already called
                if state_key in called_states:
                    continue

                # Check if within next 30 days (approximately one month)
                event_date = datetime(current_rp_date.year, state_data["month"], state_data["day"])
                days_until = (event_date - current_rp_date).days

                if 0 <= days_until <= 30:
                    upcoming_events.append({
                        "date": event_date,
                        "days_until": days_until,
                        "state": state_data["state"],
                        "party": party,
                        "delegates": state_data["delegates"]
                    })

        if not upcoming_events:
            await interaction.response.send_message("📅 No primaries scheduled in the next month.", ephemeral=True)
            return

        # Sort by date
        upcoming_events.sort(key=lambda x: x["date"])

        embed = discord.Embed(
            title="📅 Upcoming Primaries (Next Month)",
            description=f"Based on current RP date: {current_rp_date.strftime('%B %d, %Y')}",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        for event in upcoming_events:
            days_text = "Today" if event["days_until"] == 0 else f"In {event['days_until']} days"
            party_emoji = "🔵" if event["party"] == "Democrats" else "🔴"

            embed.add_field(
                name=f"{party_emoji} {event['state']} ({event['party']})",
                value=f"**Date:** {event['date'].strftime('%B %d')}\n"
                      f"**When:** {days_text}\n"
                      f"**Delegates:** {event['delegates']}",
                inline=True
            )

        await interaction.response.send_message(embed=embed)

    @delegate_group.command(
        name="schedule",
        description="View the full primary calendar for both parties"
    )
    async def primary_schedule(self, interaction: discord.Interaction, party: str = None):
        """Show the full primary schedule"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Time system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        delegates_col, delegates_config = self._get_delegates_config(interaction.guild.id)
        called_states = delegates_config.get("called_states", [])

        # Filter by party if specified
        schedules_to_show = []
        if party and party.lower() in ["democrats", "democratic"]:
            schedules_to_show = [("Democrats", self.dnc_schedule)]
        elif party and party.lower() in ["republicans", "republican"]:
            schedules_to_show = [("Republican", self.gop_schedule)]
        else:
            schedules_to_show = [("Democrats", self.dnc_schedule), ("Republican", self.gop_schedule)]

        embed = discord.Embed(
            title="📅 Primary Election Schedule",
            description=f"Presidential primary calendar for {current_year}",
            color=discord.Color.purple(),
            timestamp=datetime.utcnow()
        )

        for party_name, schedule in schedules_to_show:
            schedule_text = ""
            completed_count = 0
            total_delegates = 0

            # Sort by order
            sorted_schedule = sorted(schedule, key=lambda x: x["order"])

            for state_data in sorted_schedule[:15]:  # Show first 15 to avoid message limits
                state_key = f"{state_data['state']}_{party_name}_{current_year}"
                status = "✅" if state_key in called_states else "⏳"

                date_str = f"{state_data['month']}/{state_data['day']}"
                schedule_text += f"{status} **{state_data['state']}** - {date_str} ({state_data['delegates']} delegates)\n"

                if state_key in called_states:
                    completed_count += 1
                total_delegates += state_data['delegates']

            if len(schedule) > 15:
                schedule_text += f"... and {len(schedule) - 15} more states"

            party_emoji = "🔵" if party_name == "Democrats" else "🔴"
            embed.add_field(
                name=f"{party_emoji} {party_name} Primaries",
                value=f"**Progress:** {completed_count}/{len(schedule)} completed\n"
                      f"**Total Delegates:** {total_delegates}\n\n{schedule_text}",
                inline=False
            )

        embed.add_field(
            name="Legend",
            value="✅ = Completed\n⏳ = Upcoming",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @delegate_admin_group.command(
        name="call_state",
        description="Manually call a specific state primary (Admin only)"
    )
    @app_commands.describe(
        state="State name to call",
        party="Party (Democrats or Republican)",
        year="Year (optional - uses current year if not specified)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def force_call_state(
        self,
        interaction: discord.Interaction,
        state: str,
        party: str,
        year: int = None
    ):
        """Manually call a specific state primary"""
        valid_parties = ["Democrats", "Republican"]

        if party not in valid_parties:
            await interaction.response.send_message(
                f"❌ Invalid party. Must be one of: {', '.join(valid_parties)}",
                ephemeral=True
            )
            return

        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config:
            await interaction.response.send_message("❌ Time system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        # Find the state in the appropriate schedule
        schedule = self.dnc_schedule if party == "Democrats" else self.gop_schedule
        state_data = None

        for state_info in schedule:
            if state_info["state"].lower() == state.lower():
                state_data = state_info
                break

        if not state_data:
            await interaction.response.send_message(
                f"❌ State '{state}' not found in {party} primary schedule.",
                ephemeral=True
            )
            return

        delegates_col, delegates_config = self._get_delegates_config(interaction.guild.id)
        guild = interaction.guild

        # Check if already called
        state_key = f"{state_data['state']}_{party}_{target_year}"
        if state_key in delegates_config.get("called_states", []):
            await interaction.response.send_message(
                f"❌ {state_data['state']} ({party}) primary for {target_year} has already been called.",
                ephemeral=True
            )
            return

        # Call the state
        print(f"Force calling {state_data['state']} ({party}) for {target_year}")
        await self._call_state(
            guild, interaction.guild.id, state_data, party, target_year,
            delegates_config, delegates_col
        )

        await interaction.response.send_message(
            f"✅ Manually called **{state_data['state']}** ({party}) primary for {target_year}.\n"
            f"**Delegates allocated:** {state_data['delegates']}",
            ephemeral=True
        )

    @reset_delegates.autocomplete("party")
    async def party_autocomplete_reset_delegates(self, interaction: discord.Interaction, current: str):
        """Autocomplete for party parameter"""
        parties = ["Democrats", "Republican", "All"]
        return [app_commands.Choice(name=party, value=party) 
                for party in parties if current.lower() in party.lower()][:25]

    @primary_schedule.autocomplete("party")
    async def party_autocomplete_primary_schedule(self, interaction: discord.Interaction, current: str):
        """Autocomplete for party parameter in primary schedule"""
        parties = ["Democrats", "Republican"]
        return [app_commands.Choice(name=party, value=party) 
                for party in parties if current.lower() in party.lower()][:25]

    @force_call_state.autocomplete("party")
    async def party_autocomplete_force_call(self, interaction: discord.Interaction, current: str):
        """Autocomplete for party parameter in force call state"""
        parties = ["Democrats", "Republican"]
        return [app_commands.Choice(name=party, value=party) 
                for party in parties if current.lower() in party.lower()][:25]

    @force_call_state.autocomplete("state")
    async def state_autocomplete_force_call(self, interaction: discord.Interaction, current: str):
        """Autocomplete for state parameter in force call state"""
        # Get all states from both schedules
        all_states = set()
        for state_data in self.dnc_schedule:
            all_states.add(state_data["state"])
        for state_data in self.gop_schedule:
            all_states.add(state_data["state"])

        return [app_commands.Choice(name=state, value=state)
                for state in sorted(all_states) if current.lower() in state.lower()][:25]

    @delegate_admin_group.command(
        name="catchup_primaries",
        description="Call all missed primaries that should have already happened (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def catchup_primaries(
        self,
        interaction: discord.Interaction,
        party: str = "All",
        confirm: bool = False
    ):
        """Manually call all missed primaries that should have already happened"""
        valid_parties = ["Democrats", "Republican", "All"]

        if party not in valid_parties:
            await interaction.response.send_message(
                f"❌ Invalid party. Must be one of: {', '.join(valid_parties)}",
                ephemeral=True
            )
            return

        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config:
            await interaction.response.send_message("❌ Time system not configured.", ephemeral=True)
            return

        current_rp_date = self._calculate_current_rp_time(time_config)
        current_year = current_rp_date.year

        delegates_col, delegates_config = self._get_delegates_config(interaction.guild.id)
        called_states = delegates_config.get("called_states", [])

        # Find missed primaries
        missed_primaries = []
        schedules_to_check = []

        if party == "All":
            schedules_to_check = [("Democrats", self.dnc_schedule), ("Republican", self.gop_schedule)]
        elif party == "Democrats":
            schedules_to_check = [("Democrats", self.dnc_schedule)]
        else:
            schedules_to_check = [("Republican", self.gop_schedule)]

        for party_name, schedule in schedules_to_check:
            for state_data in schedule:
                state_key = f"{state_data['state']}_{party_name}_{current_year}"

                if state_key in called_states:
                    continue

                try:
                    state_date = datetime(current_year, state_data["month"], state_data["day"])
                    current_date = datetime(current_rp_date.year, current_rp_date.month, current_rp_date.day)

                    if current_date >= state_date:
                        missed_primaries.append({
                            "state": state_data["state"],
                            "party": party_name,
                            "date": state_date,
                            "delegates": state_data["delegates"],
                            "state_data": state_data
                        })
                except ValueError:
                    continue

        if not missed_primaries:
            await interaction.response.send_message("✅ No missed primaries found!", ephemeral=True)
            return

        if not confirm:
            missed_text = f"Found **{len(missed_primaries)}** missed primaries:\n\n"
            for primary in missed_primaries[:10]:  # Show first 10
                missed_text += f"• **{primary['state']}** ({primary['party']}) - {primary['date'].strftime('%m/%d')} ({primary['delegates']} delegates)\n"

            if len(missed_primaries) > 10:
                missed_text += f"... and {len(missed_primaries) - 10} more\n"

            missed_text += f"\nTo call all these primaries, run this command again with `confirm:True`"

            await interaction.response.send_message(missed_text, ephemeral=True)
            return

        # Call all missed primaries
        await interaction.response.defer(ephemeral=True)

        called_count = 0
        error_count = 0
        total_primaries = len(missed_primaries)

        # Send initial progress message
        await interaction.followup.send(
            f"🔄 Processing {total_primaries} missed primaries...",
            ephemeral=True
        )

        for i, primary in enumerate(missed_primaries):
            try:
                # Call the primary
                state_key = f"{primary['state']}_{primary['party']}_{current_year}"

                # Get the primary winner and delegate count
                winner_name = await self._determine_primary_winner(interaction.guild.id, primary['state'], primary['party'])
                delegate_count = primary['delegates']

                # Record the state call
                called_states.append(state_key)

                # Update delegate count for winner
                if winner_name:
                    delegates_col = self.bot.db["delegates"]
                    delegates_col.update_one(
                        {"guild_id": interaction.guild.id, "candidate": winner_name},
                        {"$inc": {"delegates": delegate_count}},
                        upsert=True
                    )

                    # Log the state call
                    state_calls_col = self.bot.db["state_calls"]
                    state_calls_col.insert_one({
                        "guild_id": interaction.guild.id,
                        "state": primary['state'],
                        "party": primary['party'],
                        "winner": winner_name,
                        "delegates": delegate_count,
                        "called_at": datetime.utcnow(),
                        "auto_call": True
                    })

                    called_count += 1

                # Update progress every 5 primaries
                if (i + 1) % 5 == 0:
                    await interaction.edit_original_response(
                        content=f"🔄 Progress: {i + 1}/{total_primaries} primaries processed..."
                    )

            except Exception as e:
                print(f"Error processing primary {primary['state']} {primary['party']}: {e}")
                error_count += 1

        # Update the called_states in delegates_config
        delegates_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"called_states": called_states}}
        )

        # Final result message
        result_message = f"✅ Processing complete!\n"
        result_message += f"**Successfully called:** {called_count} primaries\n"
        if error_count > 0:
            result_message += f"**Errors encountered:** {error_count} primaries\n"
        result_message += f"Check `/delegate totals` to see the updated results."

        await interaction.edit_original_response(content=result_message)

    async def _determine_primary_winner(self, guild_id: int, state: str, party: str) -> str:
        """Determine the winner of a primary based on current standings"""
        # Check if there are any signups for this state/party
        signups_col = self.bot.db["signups"]
        signups_config = signups_col.find_one({"guild_id": guild_id})

        if not signups_config:
            return None

        # Get current year
        time_col = self.bot.db["time_configs"]
        time_config = time_col.find_one({"guild_id": guild_id})
        current_year = time_config["current_rp_date"].year if time_config else 2024

        # Find candidates for this party
        party_candidates = []
        for candidate in signups_config.get("candidates", []):
            if (candidate.get("party", "").lower() == party.lower() and 
                candidate.get("year") == current_year):
                party_candidates.append(candidate)

        if not party_candidates:
            return None

        # For now, return the first candidate (could be enhanced with polling data)
        return party_candidates[0]["name"]

    @delegate_admin_group.command(
        name="transfer_delegates",
        description="Transfer delegates from one candidate to another (Admin only)"
    )
    @app_commands.describe(
        from_candidate="Candidate to transfer delegates from",
        to_candidate="Candidate to transfer delegates to",
        delegate_count="Number of delegates to transfer",
        reason="Reason for the transfer (optional)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def transfer_delegates(
        self,
        interaction: discord.Interaction,
        from_candidate: str,
        to_candidate: str,
        delegate_count: int,
        reason: str = "Admin transfer"
    ):
        """Transfer delegates between candidates"""
        if delegate_count <= 0:
            await interaction.response.send_message(
                "❌ Delegate count must be positive.",
                ephemeral=True
            )
            return

        delegates_col, delegates_config = self._get_delegates_config(interaction.guild.id)
        delegate_totals = delegates_config.get("delegate_totals", {})

        # Check if from_candidate exists and has enough delegates
        if from_candidate not in delegate_totals:
            await interaction.response.send_message(
                f"❌ Candidate '{from_candidate}' not found in delegate totals.",
                ephemeral=True
            )
            return

        current_delegates = delegate_totals[from_candidate]
        if current_delegates < delegate_count:
            await interaction.response.send_message(
                f"❌ {from_candidate} only has {current_delegates} delegates. Cannot transfer {delegate_count}.",
                ephemeral=True
            )
            return

        # Perform the transfer
        delegate_totals[from_candidate] -= delegate_count

        # Initialize to_candidate if they don't exist
        if to_candidate not in delegate_totals:
            delegate_totals[to_candidate] = 0

        delegate_totals[to_candidate] += delegate_count

        # Remove candidates with 0 delegates
        if delegate_totals[from_candidate] == 0:
            del delegate_totals[from_candidate]

        # Update database
        delegates_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"delegate_totals": delegate_totals}}
        )

        # Create response embed
        embed = discord.Embed(
            title="🔄 Delegates Transferred",
            description=f"Successfully transferred {delegate_count} delegates",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="📤 From",
            value=f"**{from_candidate}**\n{current_delegates} → {current_delegates - delegate_count} delegates",
            inline=True
        )

        embed.add_field(
            name="📥 To", 
            value=f"**{to_candidate}**\n{delegate_totals.get(to_candidate, 0) - delegate_count} → {delegate_totals.get(to_candidate, 0)} delegates",
            inline=True
        )

        embed.add_field(
            name="📋 Details",
            value=f"**Transferred:** {delegate_count} delegates\n**Reason:** {reason}",
            inline=False
        )

        embed.set_footer(text=f"Transfer executed by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Check if this transfer affects any primary winners
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if time_config:
            current_year = time_config["current_rp_date"].year

            # Check both parties for potential new winners
            for party in ["Democrats", "Republican"]:
                await self._check_primary_winners(
                    interaction.guild, interaction.guild.id, party, current_year, delegates_config
                )

    @transfer_delegates.autocomplete("from_candidate")
    async def from_candidate_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for from_candidate parameter"""
        delegates_col, delegates_config = self._get_delegates_config(interaction.guild.id)
        delegate_totals = delegates_config.get("delegate_totals", {})

        candidates = [name for name in delegate_totals.keys() if delegate_totals[name] > 0]
        return [app_commands.Choice(name=candidate, value=candidate)
                for candidate in candidates if current.lower() in candidate.lower()][:25]

    @transfer_delegates.autocomplete("to_candidate")
    async def to_candidate_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for to_candidate parameter - show all presidential candidates"""
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config:
            return []

        current_year = time_config["current_rp_date"].year

        # Get all presidential candidates for current year
        signups_col = self.bot.db["presidential_signups"]
        signups_config = signups_col.find_one({"guild_id": interaction.guild.id})

        candidates = []
        if signups_config:
            for candidate in signups_config.get("candidates", []):
                if (candidate.get("year") == current_year and 
                    candidate.get("office") == "President"):
                    candidates.append(candidate["name"])

        return [app_commands.Choice(name=candidate, value=candidate)
                for candidate in candidates if current.lower() in candidate.lower()][:25]

async def setup(bot):
    await bot.add_cog(Delegates(bot))