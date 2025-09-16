from discord.ext import commands
import discord
from discord import app_commands
from typing import List, Optional
from datetime import datetime

class CampaignPointsPaginationView(discord.ui.View):
    def __init__(self, interaction, sort_by, filter_region, filter_party, year, total_pages, current_page=1):
        super().__init__(timeout=300)
        self.interaction = interaction
        self.sort_by = sort_by
        self.filter_region = filter_region
        self.filter_party = filter_party
        self.year = year
        self.total_pages = total_pages
        self.current_page = current_page

        # Add dropdown for page selection
        if total_pages > 1:
            self.add_item(PageSelectDropdown(total_pages, current_page))

    async def on_timeout(self):
        # Disable all items when the view times out
        for item in self.children:
            item.disabled = True
        try:
            await self.interaction.edit_original_response(view=self)
        except:
            pass

class PageSelectDropdown(discord.ui.Select):
    def __init__(self, total_pages, current_page):
        self.total_pages = total_pages

        options = []
        for i in range(1, min(total_pages + 1, 26)):  # Discord limit of 25 options
            label = f"Page {i}"
            if i == current_page:
                label += " (Current)"
            options.append(discord.SelectOption(label=label, value=str(i)))

        super().__init__(placeholder="Select a page...", options=options)

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()

            selected_page = int(self.values[0])

            # Get the main cog to access the command logic
            signups_cog = interaction.client.get_cog('AllSignups')
            if not signups_cog:
                await interaction.followup.send("❌ Error: AllSignups cog not found.", ephemeral=True)
                return

            # Get time configuration
            time_col, time_config = signups_cog._get_time_config(interaction.guild.id)
            if not time_config:
                await interaction.followup.send("❌ Election system not configured.", ephemeral=True)
                return

            current_phase = time_config.get("current_phase", "")
            target_year = self.view.year

            # Get signups configuration
            signups_col, signups_config = signups_cog._get_signups_config(interaction.guild.id)

            # Filter candidates by year
            candidates = [c for c in signups_config["candidates"] if c["year"] == target_year]

            if not candidates:
                await interaction.followup.send(f"❌ No candidates found for {target_year}.", ephemeral=True)
                return

            # Apply filters and sorting (same logic as in main command)
            filtered_candidates = candidates
            if self.view.filter_region:
                filtered_candidates = [c for c in filtered_candidates if c["region"].lower() == self.view.filter_region.lower()]
            if self.view.filter_party:
                filtered_candidates = [c for c in filtered_candidates if self.view.filter_party.lower() in c["party"].lower()]

            if not filtered_candidates:
                await interaction.followup.send("❌ No candidates found with those filters.", ephemeral=True)
                return

            # Sort candidates
            if self.view.sort_by.lower() == "points":
                filtered_candidates.sort(key=lambda x: x["points"], reverse=True)
            elif self.view.sort_by.lower() == "corruption":
                filtered_candidates.sort(key=lambda x: x["corruption"], reverse=True)
            elif self.view.sort_by.lower() == "stamina":
                filtered_candidates.sort(key=lambda x: x["stamina"], reverse=True)
            elif self.view.sort_by.lower() == "seat":
                filtered_candidates.sort(key=lambda x: x["seat_id"])
            else:
                filtered_candidates.sort(key=lambda x: x["name"].lower())

            # Pagination
            candidates_per_page = 10
            total_candidates = len(filtered_candidates)
            total_pages = max(1, (total_candidates + candidates_per_page - 1) // candidates_per_page)
            page = max(1, min(selected_page, total_pages))

            start_idx = (page - 1) * candidates_per_page
            end_idx = start_idx + candidates_per_page
            page_candidates = filtered_candidates[start_idx:end_idx]

            # Create embed (same logic as main command)
            filter_text = ""
            if self.view.filter_region:
                filter_text += f" • Region: {self.view.filter_region}"
            if self.view.filter_party:
                filter_text += f" • Party: {self.view.filter_party}"

            embed = discord.Embed(
                title=f"📊 {target_year} Primary Campaign Points",
                description=f"Sorted by {self.view.sort_by} • Page {page}/{total_pages} • {total_candidates} total candidates{filter_text}",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )

            # Build candidate list
            candidate_entries = []
            for i, candidate in enumerate(page_candidates, start_idx + 1):
                user = interaction.guild.get_member(candidate["user_id"])
                user_mention = user.mention if user else f"User ID: {candidate['user_id']}"

                entry = (
                    f"**{i}.** {candidate['name']} ({candidate['party']})\n"
                    f"   └ {candidate['seat_id']} • Points: {candidate['points']:.2f}\n"
                    f"   └ Stamina: {candidate['stamina']} • Corruption: {candidate['corruption']} • {user_mention}\n\n"
                )
                candidate_entries.append(entry)

            # Split candidates into multiple fields if needed
            current_field = ""
            field_count = 1

            for entry in candidate_entries:
                if len(current_field + entry) > 1020:
                    embed.add_field(
                        name=f"🏆 Candidates (Part {field_count})" if field_count > 1 else "🏆 Candidates",
                        value=current_field.strip(),
                        inline=False
                    )
                    current_field = entry
                    field_count += 1
                else:
                    current_field += entry

            if current_field:
                embed.add_field(
                    name=f"🏆 Candidates (Part {field_count})" if field_count > 1 else "🏆 Candidates",
                    value=current_field.strip(),
                    inline=False
                )

            # Add statistics and navigation
            seat_counts = {}
            for candidate in filtered_candidates:
                seat_id = candidate["seat_id"]
                seat_counts[seat_id] = seat_counts.get(seat_id, 0) + 1

            # Show most competitive seats
            competitive_seats = sorted(seat_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            competitive_text = ""
            for seat_id, count in competitive_seats:
                if count > 1:
                    competitive_text += f"**{seat_id}:** {count} candidates\n"

            if competitive_text:
                embed.add_field(
                    name="🔥 Most Competitive Seats",
                    value=competitive_text,
                    inline=True
                )

            # Add summary statistics
            total_points = sum(c["points"] for c in filtered_candidates)
            avg_points = total_points / len(filtered_candidates) if filtered_candidates else 0
            avg_corruption = sum(c["corruption"] for c in filtered_candidates) / len(filtered_candidates) if filtered_candidates else 0
            avg_stamina = sum(c["stamina"] for c in filtered_candidates) / len(filtered_candidates) if filtered_candidates else 0

            embed.add_field(
                name="📈 Summary Statistics",
                value=f"**Total Candidates:** {len(filtered_candidates)}\n"
                      f"**Total Points:** {total_points:.2f}\n"
                      f"**Avg Corruption:** {avg_corruption:.1f}\n"
                      f"**Avg Stamina:** {avg_stamina:.1f}",
                inline=True
            )

            navigation_info = f"Page {page}/{total_pages}"
            if page > 1:
                prev_start = max(1, start_idx - candidates_per_page + 1)
                navigation_info += f" • Previous page shows candidates {prev_start}-{start_idx}"
            if page < total_pages:
                next_start = end_idx + 1
                next_end = min(total_candidates, end_idx + candidates_per_page)
                navigation_info += f" • Next page shows candidates {next_start}-{next_end}"

            navigation_info += f"\nShowing candidates {start_idx + 1}-{min(end_idx, total_candidates)}"

            embed.add_field(
                name="📄 Navigation",
                value=navigation_info,
                inline=False
            )

            # Create new view with updated page - this is the key fix
            new_view = CampaignPointsPaginationView(
                interaction,
                self.view.sort_by,
                self.view.filter_region,
                self.view.filter_party,
                self.view.year,
                total_pages,
                page  # Pass the selected page as current_page
            )

            # Use edit_original_response instead of followup to maintain the same message
            try:
                await interaction.edit_original_response(embed=embed, view=new_view)
            except discord.NotFound:
                # If edit fails, fall back to followup
                await interaction.followup.send(embed=embed, view=new_view, ephemeral=True)

        except Exception as e:
            print(f"Error in dropdown callback: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send("❌ An error occurred while changing pages.", ephemeral=True)


# Define command groups at module level
signup_group = app_commands.Group(name="signup", description="Candidate signup commands")
admin_signup_group = app_commands.Group(name="admin_signup", description="Admin signup management commands")

class AllSignups(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("All Signups cog loaded successfully")

    def _get_time_config(self, guild_id: int):
        """Get time configuration to check current phase"""
        col = self.bot.db["time_configs"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_elections_config(self, guild_id: int):
        """Get elections configuration"""
        col = self.bot.db["elections_config"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_signups_config(self, guild_id: int):
        """Get or create signups configuration"""
        col = self.bot.db["signups"]
        config = col.find_one({"guild_id": guild_id})
        if not config:
            config = {
                "guild_id": guild_id,
                "candidates": []
            }
            col.insert_one(config)
        return col, config

    async def party_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for party names from database"""
        # Get parties from database
        parties_col = self.bot.db["parties_config"]
        parties_config = parties_col.find_one({"guild_id": interaction.guild.id})

        if not parties_config:
            # Return default parties if no config exists
            parties = ["Democratic Party", "Republican Party", "Independent"]
        else:
            parties = [party["name"] for party in parties_config["parties"]]

        # Filter parties based on current input
        filtered_parties = [
            party for party in parties
            if current.lower() in party.lower()
        ]

        # Return up to 25 choices (Discord limit)
        return [
            app_commands.Choice(name=party, value=party)
            for party in filtered_parties[:25]
        ]

    def _get_available_seats_in_region(self, guild_id: int, region: str) -> List[dict]:
        """Get all seats that are up for election in the specified region"""
        elections_col, elections_config = self._get_elections_config(guild_id)

        if not elections_config or not elections_config.get("seats"):
            return []

        # Get current RP year for election cycle checking
        time_col, time_config = self._get_time_config(guild_id)
        current_year = time_config["current_rp_date"].year if time_config else 2024

        available_seats = []
        for seat in elections_config["seats"]:
            # Check if seat is in the region
            if seat["state"].lower() != region.lower():
                continue

            # Check if seat should be up for election this cycle
            should_be_up = False

            if seat.get("up_for_election"):
                should_be_up = True
            elif seat.get("term_end"):
                # For seats with set term end dates, check if they expire next year (election year)
                # When in 1999 (odd year), we're preparing for 2000 elections
                election_year = current_year + 1 if current_year % 2 == 1 else current_year
                if seat["term_end"].year == election_year:
                    should_be_up = True
            elif not seat.get("current_holder"):
                # Vacant seat - check if it should be up this cycle
                should_be_up = self._should_seat_be_up_for_election(seat, current_year)
            else:
                # Seat has a holder but no explicit term end - check standard cycle
                should_be_up = self._should_seat_be_up_for_election(seat, current_year)

            if should_be_up:
                available_seats.append(seat)

        return available_seats

    def _get_regions_from_elections(self, guild_id: int) -> List[str]:
        """Get available regions from elections config"""
        elections_col, elections_config = self._get_elections_config(guild_id)

        if not elections_config or not elections_config.get("seats"):
            return []

        regions = set()
        for seat in elections_config["seats"]:
            if seat["state"] != "National":  # Exclude National for regional signups
                regions.add(seat["state"])

        return sorted(list(regions))

    def _should_seat_be_up_for_election(self, seat, current_year):
        """Determine if a seat should be up for election based on standard cycles"""
        office = seat["office"]
        seat_id = seat["seat_id"]

        # For signups in odd years, we're preparing for elections in the next even year
        # For even years, we're in the actual election year
        if current_year % 2 == 1:  # Odd years (signup years)
            election_year = current_year + 1  # Elections happen next year
        else:  # Even years (election years)
            election_year = current_year  # Elections happen this year

        if office == "Senate":
            # Senate elections every 6 years, staggered into 3 classes
            # Use seat number to create staggered pattern
            seat_num = int(seat_id.split("-")[-1]) if seat_id.split("-")[-1].isdigit() else 1

            # Simplified staggered cycle - ensure there are always seats up for election
            if seat_num % 3 == 1:  # Class 1 seats
                return election_year % 6 == 0  # 2000, 2006, 2012, etc.
            elif seat_num % 3 == 2:  # Class 2 seats
                return (election_year - 2) % 6 == 0  # 1998, 2004, 2010, etc.
            else:  # Class 3 seats
                return (election_year - 4) % 6 == 0  # 1996, 2002, 2008, etc.

        elif office == "Governor":
            # Governor elections every 4 years
            return election_year % 4 == 0  # 2000, 2004, 2008, etc.
        elif "District" in office:
            # House elections every 2 years (every even year)
            return election_year % 2 == 0  # All even years
        elif seat["state"] == "National":
            # Presidential elections every 4 years
            return election_year % 4 == 0  # 2000, 2004, 2008, etc.

        return False

    def _get_regions_from_elections(self, guild_id: int) -> List[str]:
        """Get available regions from elections config"""
        elections_col, elections_config = self._get_elections_config(guild_id)

        if not elections_config or not elections_config.get("seats"):
            return []

        regions = set()
        for seat in elections_config["seats"]:
            if seat["state"] != "National":  # Exclude National for regional signups
                regions.add(seat["state"])

        return sorted(list(regions))

    async def region_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for region selection"""
        regions = self._get_regions_from_elections(interaction.guild.id)

        # Filter regions based on current input
        filtered_regions = [
            region for region in regions
            if current.lower() in region.lower()
        ]

        # Return up to 25 choices (Discord limit)
        return [
            app_commands.Choice(name=region, value=region)
            for region in filtered_regions[:25]
        ]

    @app_commands.command(
        name="signup_register",
        description="Sign up as a candidate for election (only during signup phase)"
    )
    @app_commands.describe(
        name="Your candidate name",
        party="Political party affiliation",
        region="Region/state you want to run in"
    )
    @app_commands.autocomplete(party=party_autocomplete)
    @app_commands.autocomplete(region=region_autocomplete)
    async def signup(
        self,
        interaction: discord.Interaction,
        name: str,
        party: str,
        region: str
    ):
        # Check if we're in signup phase
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message(
                "❌ Election system not configured. Please contact an administrator.",
                ephemeral=True
            )
            return

        current_phase = time_config.get("current_phase", "")
        if current_phase != "Signups":
            await interaction.response.send_message(
                f"❌ Candidate signups are only available during the Signup phase. Current phase: **{current_phase}**",
                ephemeral=True
            )
            return

        # Validate region
        available_regions = self._get_regions_from_elections(interaction.guild.id)
        if region not in available_regions:
            regions_text = ", ".join(available_regions) if available_regions else "None available"
            await interaction.response.send_message(
                f"❌ Invalid region. Available regions: {regions_text}",
                ephemeral=True
            )
            return

        # Get available seats in the region
        available_seats = self._get_available_seats_in_region(interaction.guild.id, region)

        if not available_seats:
            await interaction.response.send_message(
                f"❌ No seats are currently up for election in {region}.",
                ephemeral=True
            )
            return

        # Check if user already has a signup for this election cycle
        signups_col, signups_config = self._get_signups_config(interaction.guild.id)
        current_year = time_config["current_rp_date"].year

        existing_signup = None
        for candidate in signups_config["candidates"]:
            if (candidate["user_id"] == interaction.user.id and
                candidate["year"] == current_year):
                existing_signup = candidate
                break

        if existing_signup:
            await interaction.response.send_message(
                f"❌ You are already signed up as **{existing_signup['name']}** ({existing_signup['party']}) for {existing_signup['region']} - {existing_signup['office']} in {current_year}.",
                ephemeral=True
            )
            return

        # Check if user has a presidential signup
        pres_col = self.bot.db["presidential_signups"]
        pres_config = pres_col.find_one({"guild_id": interaction.guild.id})
        if pres_config:
            for candidate in pres_config.get("candidates", []):
                if (candidate["user_id"] == interaction.user.id and
                    candidate["year"] == current_year):
                    await interaction.response.send_message(
                        f"❌ You are already signed up for the presidential race as **{candidate['name']}** ({candidate['office']}) in {current_year}. You cannot sign up for both presidential and regular elections.",
                        ephemeral=True
                    )
                    return

            # Check if user has pending VP requests
            for vp_request in pres_config.get("pending_vp_requests", []):
                if (vp_request["user_id"] == interaction.user.id and
                    vp_request["year"] == current_year and
                    vp_request["status"] == "pending"):
                    await interaction.response.send_message(
                        f"❌ You have a pending VP request with **{vp_request['presidential_candidate']}** for {current_year}. You cannot sign up for regular elections while you have pending VP requests.",
                        ephemeral=True
                    )
                    return

        # Validate party role if configured
        party_cog = self.bot.get_cog("PartyManagement")
        if party_cog:
            is_valid, error_msg = party_cog.validate_user_party_role(interaction.user, party, interaction.guild.id)
            if not is_valid:
                await interaction.response.send_message(f"❌ {error_msg}", ephemeral=True)
                return

        # Create embed showing available seats
        embed = discord.Embed(
            title=f"🗳️ Available Seats in {region}",
            description=f"Select which seat you'd like to run for as **{name}** ({party})",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        # Group seats by office type for better display
        seat_groups = {}
        for seat in available_seats:
            office_type = seat["office"]
            if office_type == "Senate":
                group_name = "🏛️ Senate"
            elif office_type == "Governor":
                group_name = "🏛️ Governor"
            elif "District" in office_type:
                group_name = f"🏛️ House - {office_type}"
            else:
                group_name = f"🏛️ {office_type}"

            if group_name not in seat_groups:
                seat_groups[group_name] = []
            seat_groups[group_name].append(seat)

        for group_name, seats in seat_groups.items():
            seat_info = ""
            for seat in seats:
                incumbent = seat.get("current_holder", "Open Seat")
                term_years = seat.get("term_years", "?")
                seat_info += f"**{seat['seat_id']}** ({term_years}yr term)\n"
                seat_info += f"Current: {incumbent}\n\n"

            embed.add_field(
                name=group_name,
                value=seat_info,
                inline=True
            )

        embed.add_field(
            name="📋 Your Details",
            value=f"**Name:** {name}\n**Party:** {party}\n**Region:** {region}",
            inline=False
        )

        # Create dropdown for seat selection
        class SeatSelect(discord.ui.Select):
            def __init__(self, available_seats, candidate_info):
                self.candidate_info = candidate_info

                options = []
                for seat in available_seats:
                    incumbent_text = f" (vs {seat.get('current_holder', 'Open')})" if seat.get('current_holder') else " (Open Seat)"
                    description = f"{seat['office']}, {seat['state']} - {seat['term_years']}yr term{incumbent_text}"

                    options.append(discord.SelectOption(
                        label=seat['seat_id'],
                        description=description[:100],  # Discord limit
                        value=seat['seat_id']
                    ))

                super().__init__(
                    placeholder="Choose a seat to run for...",
                    min_values=1,
                    max_values=1,
                    options=options
                )

            async def callback(self, interaction):
                selected_seat_id = self.values[0]

                # Find the selected seat
                selected_seat = None
                for seat in available_seats:
                    if seat['seat_id'] == selected_seat_id:
                        selected_seat = seat
                        break

                if not selected_seat:
                    await interaction.response.send_message("❌ Error: Seat not found", ephemeral=True)
                    return

                # Prevent selecting self as VP (assuming VP is represented by a specific seat or role not explicitly handled here,
                # but this is a placeholder for such logic if it were implemented. For now, we focus on the presidential signup conflict.)
                # A more robust VP check would require knowing the VP seat_id or role.

                # Create candidate entry (primary phase)
                new_candidate = {
                    "user_id": interaction.user.id,
                    "name": self.candidate_info["name"],
                    "party": self.candidate_info["party"],
                    "region": selected_seat["state"],
                    "seat_id": selected_seat["seat_id"],
                    "office": selected_seat["office"],
                    "year": self.candidate_info["year"],
                    "signup_date": datetime.utcnow(),
                    "points": 30.0,  # Starting campaign points - everyone starts at 30
                    "stamina": 100,
                    "corruption": 0,
                    "phase": "Primary Campaign"
                }

                signups_config["candidates"].append(new_candidate)

                signups_col.update_one(
                    {"guild_id": interaction.guild.id},
                    {"$set": {"candidates": signups_config["candidates"]}}
                )

                # Create success embed
                success_embed = discord.Embed(
                    title="✅ Signup Successful!",
                    description=f"You have successfully signed up for the {self.candidate_info['year']} election!",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )

                success_embed.add_field(
                    name="📋 Your Campaign",
                    value=f"**Name:** {self.candidate_info['name']}\n"
                          f"**Party:** {self.candidate_info['party']}\n"
                          f"**Seat:** {selected_seat_id}\n"
                          f"**Office:** {selected_seat['office']}\n"
                          f"**Region:** {self.candidate_info['region']}\n"
                          f"**Term:** {selected_seat['term_years']} years",
                    inline=True
                )

                success_embed.add_field(
                    name="📊 Starting Stats",
                    value=f"**Stamina:** {new_candidate['stamina']}\n"
                          f"**Points:** {new_candidate['points']:.2f}\n"
                          f"**Corruption:** {new_candidate['corruption']}\n"
                          f"**Phase:** Primary Campaign",
                    inline=True
                )

                incumbent_text = ""
                if selected_seat.get("current_holder"):
                    incumbent_text = f"\n\n**Current Holder:** {selected_seat['current_holder']}"

                success_embed.add_field(
                    name="🎯 Election Info",
                    value=f"**Election Year:** {self.candidate_info['year']}\n"
                          f"**Current Phase:** Signups{incumbent_text}",
                    inline=False
                )

                await interaction.response.edit_message(embed=success_embed, view=None)

        class SeatView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=300)  # 5 minute timeout
                self.add_item(SeatSelect(available_seats, {
                    "name": name,
                    "party": party,
                    "region": region,
                    "year": current_year
                }))

            async def on_timeout(self):
                # Disable the view when it times out
                for item in self.children:
                    item.disabled = True

        view = SeatView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(
        name="signup_view",
        description="View candidate signups for a specific year"
    )
    @app_commands.describe(
        year="Year to view signups for (defaults to current RP year)",
        region="Filter by specific region (optional)"
    )
    @app_commands.autocomplete(region=region_autocomplete)
    async def view_signups(self, interaction: discord.Interaction, year: int = None, region: str = None):
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message(
                "❌ Election system not configured.",
                ephemeral=True
            )
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year
        signups_col, signups_config = self._get_signups_config(interaction.guild.id)

        # Filter candidates for target year
        current_candidates = [
            c for c in signups_config["candidates"]
            if c["year"] == target_year
        ]

        # Apply region filter if specified
        if region:
            current_candidates = [
                c for c in current_candidates
                if c["region"].lower() == region.lower()
            ]

        # Debug information for admins
        if not current_candidates:
            total_candidates = len(signups_config["candidates"])
            all_years = list(set(c["year"] for c in signups_config["candidates"])) if signups_config["candidates"] else []

            if region:
                debug_text = f"📋 No candidates found for **{region}** in the {target_year} election."
                # Show available regions
                all_candidates_year = [c for c in signups_config["candidates"] if c["year"] == target_year]
                available_regions = list(set(c["region"] for c in all_candidates_year))
                if available_regions:
                    debug_text += f"\n\n🌍 **Available regions for {target_year}:** {', '.join(sorted(available_regions))}"
            else:
                debug_text = f"📋 No candidates have signed up for the {target_year} election yet."
                if total_candidates > 0:
                    debug_text += f"\n\n🔍 **Debug Info:**\n"
                    debug_text += f"• Total candidates in database: {total_candidates}\n"
                    debug_text += f"• Years with candidates: {sorted(all_years)}\n"
                    debug_text += f"• Looking for year: {target_year}"

            await interaction.response.send_message(debug_text, ephemeral=True)
            return

        # Create embed with region filtering info
        title = f"🗳️ {target_year} Primary Campaign Signups"
        if region:
            title += f" - {region}"

        description = f"Current phase: **{time_config.get('current_phase', 'Unknown')}** • Only campaign points matter in primary phase"
        if region:
            description += f"\n🔍 Filtered by region: **{region}**"

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        if region:
            # Show only the filtered region in a single organized view
            candidate_list = ""
            # Sort candidates by seat_id for better organization
            sorted_candidates = sorted(current_candidates, key=lambda x: x['seat_id'])

            for candidate in sorted_candidates:
                candidate_list += f"**{candidate['name']}** ({candidate['party']})\n"
                candidate_list += f"└ {candidate['seat_id']} - {candidate['office']}\n\n"

            # Split long candidate lists into multiple fields if needed
            if len(candidate_list) > 1020:  # Leave some buffer for Discord's 1024 limit
                parts = candidate_list.split('\n\n')[:-1]  # Remove empty last part
                current_part = ""
                part_num = 1

                for part in parts:
                    part_with_newlines = part + '\n\n'
                    if len(current_part + part_with_newlines) > 1020:
                        # Add the current field and start a new one
                        embed.add_field(
                            name=f"📍 {region} Candidates (Part {part_num})" if part_num > 1 else f"📍 {region} Candidates",
                            value=current_part.strip(),
                            inline=False
                        )
                        current_part = part_with_newlines
                        part_num += 1
                    else:
                        current_part += part_with_newlines

                # Add any remaining candidates
                if current_part:
                    embed.add_field(
                        name=f"📍 {region} Candidates (Part {part_num})" if part_num > 1 else f"📍 {region} Candidates",
                        value=current_part.strip(),
                        inline=False
                    )
            else:
                embed.add_field(
                    name=f"📍 {region} Candidates",
                    value=candidate_list if candidate_list else "No candidates found",
                    inline=False
                )
        else:
            # Group by region for better display when showing all regions
            regions = {}
            for candidate in current_candidates:
                candidate_region = candidate["region"]
                if candidate_region not in regions:
                    regions[candidate_region] = []
                regions[candidate_region].append(candidate)

            # Sort regions alphabetically and display each in a field
            for region_name in sorted(regions.keys()):
                candidates = regions[region_name]
                candidate_list = ""

                # Sort candidates within each region by seat_id
                sorted_candidates = sorted(candidates, key=lambda x: x['seat_id'])

                for candidate in sorted_candidates:
                    candidate_list += f"**{candidate['name']}** ({candidate['party']})\n"
                    candidate_list += f"└ {candidate['seat_id']} - {candidate['office']}\n\n"

                # Split long region lists into multiple fields if needed
                if len(candidate_list) > 1020:  # Leave some buffer for Discord's 1024 limit
                    parts = candidate_list.split('\n\n')[:-1]  # Remove empty last part
                    current_part = ""
                    part_num = 1

                    for part in parts:
                        part_with_newlines = part + '\n\n'
                        if len(current_part + part_with_newlines) > 1020:
                            # Add the current field and start a new one
                            embed.add_field(
                                name=f"📍 {region_name} (Part {part_num})" if part_num > 1 else f"📍 {region_name}",
                                value=current_part.strip(),
                                inline=True
                            )
                            current_part = part_with_newlines
                            part_num += 1
                        else:
                            current_part += part_with_newlines

                    # Add any remaining candidates
                    if current_part:
                        embed.add_field(
                            name=f"📍 {region_name} (Part {part_num})" if part_num > 1 else f"📍 {region_name}",
                            value=current_part.strip(),
                            inline=True
                        )
                else:
                    embed.add_field(
                        name=f"📍 {region_name}",
                        value=candidate_list,
                        inline=True
                    )

        # Add summary information
        if region:
            embed.add_field(
                name="📊 Region Summary",
                value=f"**Candidates in {region}:** {len(current_candidates)}",
                inline=False
            )
        else:
            regions_count = len(set(c["region"] for c in current_candidates))
            embed.add_field(
                name="📊 Total Summary",
                value=f"**Total Candidates:** {len(current_candidates)}\n"
                      f"**Regions with Candidates:** {regions_count}",
                inline=False
            )

        # Add view controls if there are multiple regions available
        if not region:
            all_regions = sorted(set(c["region"] for c in current_candidates))
            if len(all_regions) > 1:
                embed.add_field(
                    name="🔍 Filter Options",
                    value=f"Use the `region` parameter to filter by a specific region.\n"
                          f"**Available regions:** {', '.join(all_regions)}",
                    inline=False
                )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="signup_withdraw",
        description="Withdraw your candidacy from the current election"
    )
    async def withdraw_signup(self, interaction: discord.Interaction):
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message(
                "❌ Election system not configured.",
                ephemeral=True
            )
            return

        current_year = time_config["current_rp_date"].year
        current_phase = time_config.get("current_phase", "")
        signups_col, signups_config = self._get_signups_config(interaction.guild.id)

        # Find user's signup
        user_signup = None
        signup_index = None
        for i, candidate in enumerate(signups_config["candidates"]):
            if (candidate["user_id"] == interaction.user.id and
                candidate["year"] == current_year):
                user_signup = candidate
                signup_index = i
                break

        if not user_signup:
            await interaction.response.send_message(
                "❌ You don't have an active signup for this election.",
                ephemeral=True
            )
            return

        # Remove the signup
        signups_config["candidates"].pop(signup_index)
        signups_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"candidates": signups_config["candidates"]}}
        )

        await interaction.response.send_message(
            f"✅ Successfully withdrew your candidacy for **{user_signup['seat_id']}** ({user_signup['office']}, {user_signup['region']}) during the **{current_phase}** phase.",
            ephemeral=True
        )

    @app_commands.command(
        name="signup_my_details",
        description="View your current signup details"
    )
    async def my_signup(self, interaction: discord.Interaction):
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message(
                "❌ Election system not configured.",
                ephemeral=True
            )
            return

        current_year = time_config["current_rp_date"].year
        current_phase = time_config.get("current_phase", "")
        signups_col, signups_config = self._get_signups_config(interaction.guild.id)

        # If we're in the General Campaign phase, check winners collection first
        if current_phase == "General Campaign":
            winners_col = self.bot.db["winners"]
            winners_config = winners_col.find_one({"guild_id": interaction.guild.id})

            if winners_config and winners_config.get("winners"):
                user_winner = None
                for w in winners_config["winners"]:
                    if w.get("user_id") == interaction.user.id and w.get("year") == current_year:
                        user_winner = w
                        break

                if user_winner:
                    embed = discord.Embed(
                        title="📋 Your General Campaign Details",
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )

                    embed.add_field(
                        name="👤 Candidate Info",
                        value=f"**Name:** {user_winner.get('candidate', 'Unknown')}\n"
                              f"**Party:** {user_winner.get('party', 'Unknown')}\n"
                              f"**Region:** {user_winner.get('state', 'Unknown')}",
                        inline=True
                    )

                    embed.add_field(
                        name="🏛️ Running For",
                        value=f"**Seat:** {user_winner.get('seat_id', 'Unknown')}\n"
                              f"**Office:** {user_winner.get('office', 'Unknown')}\n"
                              f"**Year:** {user_winner.get('year', current_year)}",
                        inline=True
                    )

                    embed.add_field(
                        name="📊 Campaign Stats",
                        value=f"**Stamina:** {user_winner.get('stamina', 0)}\n"
                              f"**Points:** {float(user_winner.get('points', 0.0)):.2f}\n"
                              f"**Corruption:** {user_winner.get('corruption', 0)}\n"
                              f"**Baseline %:** {float(user_winner.get('baseline_percentage', 0.0)):.1f}\n"
                              f"**Votes:** {user_winner.get('votes', 0)}",
                        inline=True
                    )

                    embed.add_field(
                        name="📅 Status",
                        value=f"**Phase:** {user_winner.get('phase', 'General Campaign')}\n"
                              f"**Primary Winner:** {'Yes' if user_winner.get('primary_winner', False) else 'No'}\n"
                              f"**General Winner:** {'Yes' if user_winner.get('general_winner', False) else 'TBD'}",
                        inline=False
                    )

                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

        # Find user's signup
        user_signup = None
        for candidate in signups_config["candidates"]:
            if (candidate["user_id"] == interaction.user.id and
                candidate["year"] == current_year):
                user_signup = candidate
                break

        if not user_signup:
            await interaction.response.send_message(
                "❌ You don't have an active signup for this election.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📋 Your Campaign Details",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="👤 Candidate Info",
            value=f"**Name:** {user_signup['name']}\n"
                  f"**Party:** {user_signup['party']}\n"
                  f"**Region:** {user_signup['region']}",
            inline=True
        )

        embed.add_field(
            name="🏛️ Running For",
            value=f"**Seat:** {user_signup['seat_id']}\n"
                  f"**Office:** {user_signup['office']}\n"
                  f"**Year:** {user_signup['year']}",
            inline=True
        )

        embed.add_field(
            name="📊 Campaign Stats",
            value=f"**Stamina:** {user_signup['stamina']}\n"
                  f"**Points:** {user_signup['points']:.2f}\n"
                  f"**Corruption:** {user_signup['corruption']}",
            inline=True
        )

        embed.add_field(
            name="📅 Status",
            value=f"**Phase:** {user_signup.get('phase', 'Primary Campaign')}\n"
                  f"**Winner:** {'Yes' if user_signup.get('winner', False) else 'TBD'}",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="admin_signup_remove_candidate",
        description="Remove a specific candidate from signups (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_remove_candidate(
        self,
        interaction: discord.Interaction,
        candidate_name: str,
        year: int = None
    ):
        """Remove a candidate by name"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message(
                "❌ Election system not configured.",
                ephemeral=True
            )
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        signups_col, signups_config = self._get_signups_config(interaction.guild.id)

        # Find candidate
        candidate_found = None
        for i, candidate in enumerate(signups_config["candidates"]):
            if (candidate["name"].lower() == candidate_name.lower() and
                candidate["year"] == target_year):
                candidate_found = i
                break

        if candidate_found is None:
            await interaction.response.send_message(
                f"❌ Candidate '{candidate_name}' not found for {target_year}.",
                ephemeral=True
            )
            return

        removed_candidate = signups_config["candidates"].pop(candidate_found)

        signups_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"candidates": signups_config["candidates"]}}
        )

        await interaction.response.send_message(
            f"✅ Removed candidate **{removed_candidate['name']}** ({removed_candidate['party']}) "
            f"from {removed_candidate['seat_id']} - {removed_candidate['office']}",
            ephemeral=True
        )

    @app_commands.command(
        name="admin_signup_clear_all",
        description="Clear all candidate signups for a specific year (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_clear_all_signups(
        self,
        interaction: discord.Interaction,
        year: int = None,
        confirm: bool = False
    ):
        """Clear all signups for a specific year"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message(
                "❌ Election system not configured.",
                ephemeral=True
            )
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        signups_col, signups_config = self._get_signups_config(interaction.guild.id)

        # Count signups for target year
        year_signups = [c for c in signups_config["candidates"] if c["year"] == target_year]

        if not year_signups:
            await interaction.response.send_message(
                f"❌ No signups found for {target_year}.",
                ephemeral=True
            )
            return

        if not confirm:
            await interaction.response.send_message(
                f"⚠️ **Warning:** This will remove all {len(year_signups)} candidate signups for {target_year}.\n"
                f"To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        # Remove all signups for target year
        signups_config["candidates"] = [
            c for c in signups_config["candidates"] if c["year"] != target_year
        ]

        signups_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"candidates": signups_config["candidates"]}}
        )

        await interaction.response.send_message(
            f"✅ Cleared {len(year_signups)} candidate signups for {target_year}.",
            ephemeral=True
        )

    @app_commands.command(
        name="admin_signup_modify_candidate",
        description="Modify a candidate's information (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_modify_candidate(
        self,
        interaction: discord.Interaction,
        candidate_name: str,
        field: str,
        new_value: str,
        year: int = None
    ):
        """Modify candidate fields like party, stamina, points, corruption"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message(
                "❌ Election system not configured.",
                ephemeral=True
            )
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        signups_col, signups_config = self._get_signups_config(interaction.guild.id)

        # Find candidate
        candidate_found = None
        for i, candidate in enumerate(signups_config["candidates"]):
            if (candidate["name"].lower() == candidate_name.lower() and
                candidate["year"] == target_year):
                candidate_found = i
                break

        if candidate_found is None:
            await interaction.response.send_message(
                f"❌ Candidate '{candidate_name}' not found for {target_year}.",
                ephemeral=True
            )
            return

        # Validate field and value
        valid_fields = ["party", "stamina", "points", "corruption", "phase", "winner"]

        if field.lower() not in valid_fields:
            await interaction.response.send_message(
                f"❌ Invalid field. Valid options: {', '.join(valid_fields)}",
                ephemeral=True
            )
            return

        old_value = signups_config["candidates"][candidate_found].get(field.lower(), "None")

        try:
            if field.lower() in ["stamina", "points", "corruption"]:
                new_value = int(new_value)
                if field.lower() == "stamina" and (new_value < 0 or new_value > 100):
                    raise ValueError("Stamina must be between 0 and 100")
                if field.lower() == "corruption" and new_value < 0:
                    raise ValueError("Corruption cannot be negative")
            elif field.lower() == "winner":
                new_value = new_value.lower() in ["true", "yes", "1"]

            signups_config["candidates"][candidate_found][field.lower()] = new_value

            signups_col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"candidates": signups_config["candidates"]}}
            )

            await interaction.response.send_message(
                f"✅ Updated {field} for **{candidate_name}**: {old_value} → {new_value}",
                ephemeral=True
            )

        except ValueError as e:
            await interaction.response.send_message(f"❌ Invalid value: {str(e)}", ephemeral=True)

    @app_commands.command(
        name="admin_signup_bulk_update",
        description="Bulk update candidate stats (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_bulk_update_candidates(
        self,
        interaction: discord.Interaction,
        field: str,
        value: str,
        filter_party: str = None,
        filter_region: str = None,
        year: int = None
    ):
        """Bulk update multiple candidates at once"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message(
                "❌ Election system not configured.",
                ephemeral=True
            )
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        signups_col, signups_config = self._get_signups_config(interaction.guild.id)

        # Validate field
        valid_fields = ["stamina", "points", "corruption", "phase"]

        if field.lower() not in valid_fields:
            await interaction.response.send_message(
                f"❌ Invalid field. Valid options: {', '.join(valid_fields)}",
                ephemeral=True
            )
            return

        try:
            if field.lower() in ["stamina", "points", "corruption"]:
                new_value = int(value)
            else:
                new_value = value

            updated_candidates = []

            for i, candidate in enumerate(signups_config["candidates"]):
                if candidate["year"] != target_year:
                    continue

                should_update = True
                if filter_party and candidate["party"].lower() != filter_party.lower():
                    should_update = False
                if filter_region and candidate["region"].lower() != filter_region.lower():
                    should_update = False

                if should_update:
                    signups_config["candidates"][i][field.lower()] = new_value
                    updated_candidates.append(candidate["name"])

            if updated_candidates:
                signups_col.update_one(
                    {"guild_id": interaction.guild.id},
                    {"$set": {"candidates": signups_config["candidates"]}}
                )

            filters_text = ""
            if filter_party:
                filters_text += f" (Party: {filter_party})"
            if filter_region:
                filters_text += f" (Region: {filter_region})"

            await interaction.response.send_message(
                f"✅ Updated {field} to {new_value} for {len(updated_candidates)} candidates{filters_text}:\n" +
                "\n".join([f"• {name}" for name in updated_candidates[:10]]) +
                (f"\n• ... and {len(updated_candidates) - 10} more" if len(updated_candidates) > 10 else ""),
                ephemeral=True
            )

        except ValueError as e:
            await interaction.response.send_message(f"❌ Invalid value: {str(e)}", ephemeral=True)

    @app_commands.command(
        name="admin_signup_export",
        description="Export candidate signups as text (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_export_signups(
        self,
        interaction: discord.Interaction,
        year: int = None,
        format_type: str = "csv"
    ):
        """Export signup data"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message(
                "❌ Election system not configured.",
                ephemeral=True
            )
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        signups_col, signups_config = self._get_signups_config(interaction.guild.id)

        # Filter by year
        candidates = [c for c in signups_config["candidates"] if c["year"] == target_year]

        if not candidates:
            await interaction.response.send_message(
                f"❌ No signups found for {target_year}.",
                ephemeral=True
            )
            return

        if format_type.lower() == "csv":
            lines = ["name,party,seat_id,office,region,stamina,points,corruption,phase,winner"]
            for candidate in candidates:
                lines.append(
                    f"{candidate['name']},{candidate['party']},{candidate['seat_id']},"
                    f"{candidate['office']},{candidate['region']},{candidate['stamina']},"
                    f"{candidate['points']:.2f},{candidate['corruption']},{candidate.get('phase', 'Primary Campaign')},"
                    f"{candidate.get('winner', False)}"
                )
            export_text = "\n".join(lines)
        else:
            # Text format
            export_lines = []
            for candidate in candidates:
                export_lines.append(
                    f"{candidate['name']} ({candidate['party']}) - {candidate['seat_id']} "
                    f"({candidate['office']}, {candidate['region']}) | "
                    f"S:{candidate['stamina']} P:{candidate['points']:.2f} C:{candidate['corruption']} "
                    f"Phase:{candidate.get('phase', 'Primary Campaign')} Winner:{candidate.get('winner', False)}"
                )
            export_text = "\n".join(export_lines)

        # Handle long responses
        if len(export_text) > 1900:
            chunk_size = 1900
            chunks = [export_text[i:i+chunk_size] for i in range(0, len(export_text), chunk_size)]

            await interaction.response.send_message(
                f"📊 {target_year} Signups Export ({format_type.upper()}) - Part 1/{len(chunks)}:\n```\n{chunks[0]}\n```",
                ephemeral=True
            )

            for i, chunk in enumerate(chunks[1:], 2):
                await interaction.followup.send(
                    f"📊 Part {i}/{len(chunks)}:\n```\n{chunk}\n```",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                f"📊 {target_year} Signups Export ({format_type.upper()}):\n```\n{export_text}\n```",
                ephemeral=True
            )

    @app_commands.command(
        name="admin_signup_view_points",
        description="View all candidate points and rankings (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_view_points(
        self,
        interaction: discord.Interaction,
        sort_by: str = "points",
        filter_region: str = None,
        filter_party: str = None,
        year: int = None
    ):
        """View candidate points with sorting and filtering options"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message(
                "❌ Election system not configured.",
                ephemeral=True
            )
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        signups_col, signups_config = self._get_signups_config(interaction.guild.id)

        # Filter by year
        candidates = [c for c in signups_config["candidates"] if c["year"] == target_year]

        if not candidates:
            await interaction.response.send_message(
                f"❌ No candidates found for {target_year}.",
                ephemeral=True
            )
            return

        # Apply filters
        filtered_candidates = candidates
        if filter_region:
            filtered_candidates = [c for c in filtered_candidates if c["region"].lower() == filter_region.lower()]
        if filter_party:
            filtered_candidates = [c for c in filtered_candidates if filter_party.lower() == filter_party.lower()]

        if not filtered_candidates:
            filters_text = ""
            if filter_region:
                filters_text += f" in {filter_region}"
            if filter_party:
                filters_text += f" from {filter_party}"

            await interaction.response.send_message(
                f"❌ No candidates found{filters_text} for {target_year}.",
                ephemeral=True
            )
            return

        # Sort candidates
        valid_sort_options = ["points", "stamina", "corruption", "name", "party", "region"]
        if sort_by.lower() not in valid_sort_options:
            await interaction.response.send_message(
                f"❌ Invalid sort option. Valid options: {', '.join(valid_sort_options)}",
                ephemeral=True
            )
            return

        if sort_by.lower() == "name":
            sorted_candidates = sorted(filtered_candidates, key=lambda x: x["name"].lower())
        elif sort_by.lower() == "party":
            sorted_candidates = sorted(filtered_candidates, key=lambda x: x["party"].lower())
        elif sort_by.lower() == "region":
            sorted_candidates = sorted(filtered_candidates, key=lambda x: x["region"].lower())
        else:
            # For numeric fields, sort in descending order (highest first)
            sorted_candidates = sorted(filtered_candidates, key=lambda x: x[sort_by.lower()], reverse=True)

        # Create embed
        embed = discord.Embed(
            title=f"📊 {target_year} Candidate Rankings",
            description=f"Sorted by: **{sort_by.title()}** {'(Descending)' if sort_by.lower() in ['points', 'stamina', 'corruption'] else '(A-Z)'}",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        # Add filter info if applied
        filter_info = []
        if filter_region:
            filter_info.append(f"Region: {filter_region}")
        if filter_party:
            filter_info.append(f"Party: {filter_party}")

        if filter_info:
            embed.add_field(
                name="🔍 Filters Applied",
                value=" | ".join(filter_info),
                inline=False
            )

        # Group candidates by region for better display
        regions = {}
        for candidate in sorted_candidates:
            region = candidate["region"]
            if region not in regions:
                regions[region] = []
            regions[region].append(candidate)

        for region, region_candidates in sorted(regions.items()):
            candidate_list = ""
            for i, candidate in enumerate(region_candidates, 1):
                # Determine ranking emoji
                if sort_by.lower() == "points":
                    if i == 1:
                        rank_emoji = "🥇"
                    elif i == 2:
                        rank_emoji = "🥈"
                    elif i == 3:
                        rank_emoji = "🥉"
                    else:
                        rank_emoji = f"#{i}"
                else:
                    rank_emoji = f"#{i}"

                candidate_list += f"{rank_emoji} **{candidate['name']}** ({candidate['party']})\n"
                candidate_list += f"└ Points: {candidate['points']:.2f} | Stamina: {candidate['stamina']} | Corruption: {candidate['corruption']}\n"
                candidate_list += f"└ {candidate['seat_id']} - {candidate['office']}\n\n"

            # Split long field values if needed
            if len(candidate_list) > 1024:
                parts = candidate_list.split('\n\n')
                current_part = ""
                part_num = 1

                for part in parts:
                    if len(current_part + part + '\n\n') > 1024:
                        embed.add_field(
                            name=f"📍 {region} (Part {part_num})" if part_num > 1 else f"📍 {region}",
                            value=current_part,
                            inline=True
                        )
                        current_part = part + '\n\n'
                        part_num += 1
                    else:
                        current_part += part + '\n\n'

                if current_part:
                    embed.add_field(
                        name=f"📍 {region} (Part {part_num})" if part_num > 1 else f"📍 {region}",
                        value=current_part,
                        inline=True
                    )
            else:
                embed.add_field(
                    name=f"📍 {region}",
                    value=candidate_list,
                    inline=True
                )

        # Add summary statistics
        total_points = sum(c["points"] for c in filtered_candidates)
        avg_points = total_points / len(filtered_candidates) if filtered_candidates else 0
        max_points = max(c["points"] for c in filtered_candidates) if filtered_candidates else 0
        min_points = min(c["points"] for c in filtered_candidates) if filtered_candidates else 0

        embed.add_field(
            name="📈 Statistics",
            value=f"**Total Candidates:** {len(filtered_candidates)}\n"
                  f"**Average Points:** {avg_points:.2f}\n"
                  f"**Highest Points:** {max_points:.2f}\n"
                  f"**Lowest Points:** {min_points:.2f}",
            inline=False
        )

        # Check if embed is too large and split if necessary
        embed_dict = embed.to_dict()
        embed_length = len(str(embed_dict))

        if embed_length > 5500:  # Leave buffer under 6000 limit
            # Split the fields into multiple embeds
            fields = embed.fields
            embed.clear_fields()

            # Send first embed with initial fields
            max_fields_per_embed = len(fields) // 2 if len(fields) > 10 else 10

            for i in range(min(max_fields_per_embed, len(fields))):
                embed.add_field(name=fields[i].name, value=fields[i].value, inline=fields[i].inline)

            await interaction.response.send_message(embed=embed, ephemeral=True)

            # Send remaining fields in follow-up embeds
            remaining_fields = fields[max_fields_per_embed:]

            while remaining_fields:
                follow_embed = discord.Embed(
                    title=f"{embed.title} (continued)",
                    color=embed.color
                )

                # Add up to 25 fields per embed (Discord limit)
                chunk = remaining_fields[:25]
                remaining_fields = remaining_fields[25:]

                for field in chunk:
                    follow_embed.add_field(name=field.name, value=field.value, inline=field.inline)

                await interaction.followup.send(embed=follow_embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)


    @signup_group.command(
        name="admin_view_campaign_points",
        description="View all candidate points in primary campaign phase (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_view_campaign_points(
        self,
        interaction: discord.Interaction,
        sort_by: str = "points",
        filter_region: str = None,
        filter_party: str = None,
        year: int = None,
        page: int = 1
    ):
        """View candidate points with sorting and filtering options"""
        # Defer immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)

        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.followup.send("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        signups_col, signups_config = self._get_signups_config(interaction.guild.id)

        # Filter by year
        candidates = [c for c in signups_config["candidates"] if c["year"] == target_year]

        if not candidates:
            await interaction.followup.send(f"❌ No candidates found for {target_year}.", ephemeral=True)
            return

        # Apply filters
        filtered_candidates = candidates

        if filter_region:
            filtered_candidates = [c for c in filtered_candidates if c["region"].lower() == filter_region.lower()]

        if filter_party:
            filtered_candidates = [c for c in filtered_candidates if filter_party.lower() in c["party"].lower()]

        if not filtered_candidates:
            await interaction.followup.send("❌ No candidates found with those filters.", ephemeral=True)
            return

        # Sort candidates
        if sort_by.lower() == "points":
            filtered_candidates.sort(key=lambda x: x["points"], reverse=True)
        elif sort_by.lower() == "corruption":
            filtered_candidates.sort(key=lambda x: x["corruption"], reverse=True)
        elif sort_by.lower() == "stamina":
            filtered_candidates.sort(key=lambda x: x["stamina"], reverse=True)
        elif sort_by.lower() == "seat":
            filtered_candidates.sort(key=lambda x: x["seat_id"])
        else:
            filtered_candidates.sort(key=lambda x: x["name"].lower())

        # Pagination settings - reduced to handle field length limits better
        candidates_per_page = 10
        total_candidates = len(filtered_candidates)
        total_pages = max(1, (total_candidates + candidates_per_page - 1) // candidates_per_page)

        if page < 1:
            page = 1
        elif page > total_pages:
            page = total_pages

        start_idx = (page - 1) * candidates_per_page
        end_idx = start_idx + candidates_per_page
        page_candidates = filtered_candidates[start_idx:end_idx]

        # Create embed
        filter_text = ""
        if filter_region:
            filter_text += f" • Region: {filter_region}"
        if filter_party:
            filter_text += f" • Party: {filter_party}"

        embed = discord.Embed(
            title=f"📊 {target_year} Primary Campaign Points",
            description=f"Sorted by {sort_by} • Page {page}/{total_pages} • {total_candidates} total candidates{filter_text}",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        # Build candidate list for this page, handling field length limits
        candidate_entries = []
        for i, candidate in enumerate(page_candidates, start_idx + 1):
            user = interaction.guild.get_member(candidate["user_id"])
            user_mention = user.mention if user else f"User ID: {candidate['user_id']}"

            entry = (
                f"**{i}.** {candidate['name']} ({candidate['party']})\n"
                f"   └ {candidate['seat_id']} • Points: {candidate['points']:.2f}\n"
                f"   └ Stamina: {candidate['stamina']} • Corruption: {candidate['corruption']} • {user_mention}\n\n"
            )
            candidate_entries.append(entry)

        # Split candidates into multiple fields if needed (Discord 1024 char limit per field)
        current_field = ""
        field_count = 1

        for entry in candidate_entries:
            # Check if adding this entry would exceed the limit
            if len(current_field + entry) > 1020:  # Leave some buffer
                # Add the current field and start a new one
                embed.add_field(
                    name=f"🏆 Candidates (Part {field_count})" if field_count > 1 else "🏆 Candidates",
                    value=current_field.strip(),
                    inline=False
                )
                current_field = entry
                field_count += 1
            else:
                current_field += entry

        # Add any remaining candidates
        if current_field:
            embed.add_field(
                name=f"🏆 Candidates (Part {field_count})" if field_count > 1 else "🏆 Candidates",
                value=current_field.strip(),
                inline=False
            )

        # Find most competitive seats
        seat_counts = {}
        for candidate in filtered_candidates:
            seat_id = candidate["seat_id"]
            seat_counts[seat_id] = seat_counts.get(seat_id, 0) + 1

        # Sort seats by number of candidates (most competitive first)
        competitive_seats = sorted(seat_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        competitive_text = ""
        for seat_id, count in competitive_seats:
            if count > 1:  # Only show seats with more than 1 candidate
                competitive_text += f"**{seat_id}:** {count} candidates\n"

        if competitive_text:
            embed.add_field(
                name="🔥 Most Competitive Seats",
                value=competitive_text,
                inline=True
            )

        # Add summary statistics
        total_points = sum(c["points"] for c in filtered_candidates)
        avg_points = total_points / len(filtered_candidates) if filtered_candidates else 0
        avg_corruption = sum(c["corruption"] for c in filtered_candidates) / len(filtered_candidates) if filtered_candidates else 0
        avg_stamina = sum(c["stamina"] for c in filtered_candidates) / len(filtered_candidates) if filtered_candidates else 0

        embed.add_field(
            name="📈 Summary Statistics",
            value=f"**Total Candidates:** {len(filtered_candidates)}\n"
                  f"**Total Points:** {total_points:.2f}\n"
                  f"**Avg Corruption:** {avg_corruption:.1f}\n"
                  f"**Avg Stamina:** {avg_stamina:.1f}",
            inline=True
        )

        # Add navigation info
        navigation_info = f"Page {page}/{total_pages}"
        if page > 1:
            navigation_info += f" • Previous page shows candidates {max(1, start_idx - candidates_per_page + 1)}-{start_idx}"
        if page < total_pages:
            next_start = end_idx + 1
            next_end = min(total_candidates, end_idx + candidates_per_page)
            navigation_info += f" • Next page shows candidates {next_start}-{next_end}"

        navigation_info += f"\nShowing candidates {start_idx + 1}-{min(end_idx, total_candidates)}"

        embed.add_field(
            name="📄 Navigation",
            value=navigation_info,
            inline=False
        )

        # Create dropdown for quick navigation if many pages
        if total_pages > 1:
            view = CampaignPointsPaginationView(interaction, sort_by, filter_region, filter_party, year, total_pages, page)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

    @admin_view_points.autocomplete("filter_region")
    async def filter_region_autocomplete(self, interaction: discord.Interaction, current: str):
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config:
            return []

        current_year = time_config["current_rp_date"].year
        signups_col, signups_config = self._get_signups_config(interaction.guild.id)

        regions = set()
        for candidate in signups_config["candidates"]:
            if candidate["year"] == current_year:
                regions.add(candidate["region"])

        return [app_commands.Choice(name=region, value=region)
                for region in sorted(regions) if current.lower() in region.lower()][:25]

    @admin_view_points.autocomplete("filter_party")
    async def filter_party_autocomplete(self, interaction: discord.Interaction, current: str):
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config:
            return []

        current_year = time_config["current_rp_date"].year
        signups_col, signups_config = self._get_signups_config(interaction.guild.id)

        parties = set()
        for candidate in signups_config["candidates"]:
            if candidate["year"] == current_year:
                parties.add(candidate["party"])

        return [app_commands.Choice(name=party, value=party)
                for party in sorted(parties) if current.lower() in party.lower()][:25]

    @admin_view_campaign_points.autocomplete("sort_by")
    async def campaign_sort_autocomplete(self, interaction: discord.Interaction, current: str):
        sort_options = ["points", "corruption", "stamina", "seat", "name"]
        return [app_commands.Choice(name=option, value=option)
                for option in sort_options if current.lower() in option.lower()][:25]

    @admin_view_campaign_points.autocomplete("filter_region")
    async def campaign_filter_region_autocomplete(self, interaction: discord.Interaction, current: str):
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config:
            return []

        current_year = time_config["current_rp_date"].year
        signups_col, signups_config = self._get_signups_config(interaction.guild.id)

        regions = set()
        for candidate in signups_config["candidates"]:
            if candidate["year"] == current_year:
                regions.add(candidate["region"])

        return [app_commands.Choice(name=region, value=region)
                for region in sorted(regions) if current.lower() in region.lower()][:25]

    @admin_view_campaign_points.autocomplete("filter_party")
    async def campaign_filter_party_autocomplete(self, interaction: discord.Interaction, current: str):
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config:
            return []

        current_year = time_config["current_rp_date"].year
        signups_col, signups_config = self._get_signups_config(interaction.guild.id)

        parties = set()
        for candidate in signups_config["candidates"]:
            if candidate["year"] == current_year:
                parties.add(candidate["party"])

        return [app_commands.Choice(name=party, value=party)
                for party in sorted(parties) if current.lower() in party.lower()][:25]


    @app_commands.command(
        name="admin_signup_seat_competition",
        description="View all candidates competing for a specific seat (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_view_seat_competition(
        self,
        interaction: discord.Interaction,
        seat_id: str,
        year: int = None
    ):
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        signups_col, signups_config = self._get_signups_config(interaction.guild.id)

        # Find candidates for this seat
        seat_candidates = [
            c for c in signups_config["candidates"]
            if c["year"] == target_year and c["seat_id"].lower() == seat_id.lower()
        ]

        if not seat_candidates:
            await interaction.response.send_message(
                f"❌ No candidates found for seat '{seat_id}' in {target_year}.",
                ephemeral=True
            )
            return

        # Sort by points
        seat_candidates.sort(key=lambda x: x["points"], reverse=True)

        # Get seat info
        seat_info = seat_candidates[0]  # They all have same seat info

        embed = discord.Embed(
            title=f"🏛️ Competition for {seat_id}",
            description=f"**{seat_info['office']}** in **{seat_info['region']}** ({target_year})",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        # Group by party
        parties = {}
        for candidate in seat_candidates:
            party = candidate["party"]
            if party not in parties:
                parties[party] = []
            parties[party].append(candidate)

        for party, party_candidates in parties.items():
            party_candidates.sort(key=lambda x: x["points"], reverse=True)

            party_text = ""
            for i, candidate in enumerate(party_candidates, 1):
                user = interaction.guild.get_member(candidate["user_id"])
                user_mention = user.mention if user else candidate["name"]

                leader_indicator = " 👑" if i == 1 and len(party_candidates) > 1 else ""
                party_text += (
                    f"**{i}.** {candidate['name']}{leader_indicator}\n"
                    f"   └ Points: {candidate['points']:.2f} • Stamina: {candidate['stamina']} • "
                    f"Corruption: {candidate['corruption']}\n"
                    f"   └ {user_mention}\n\n"
                )

            embed.add_field(
                name=f"🎗️ {party} ({len(party_candidates)})",
                value=party_text[:1024],
                inline=False
            )

        # Overall leader
        overall_leader = seat_candidates[0]
        embed.add_field(
            name="🥇 Current Leader",
            value=f"**{overall_leader['name']}** ({overall_leader['party']})\n"
                  f"Points: {overall_leader['points']:.2f}",
            inline=True
        )

        embed.add_field(
            name="📊 Competition Stats",
            value=f"**Total Candidates:** {len(seat_candidates)}\n"
                  f"**Parties Represented:** {len(parties)}\n"
                  f"**Point Spread:** {seat_candidates[0]['points']:.2f} - {seat_candidates[-1]['points']:.2f}",
            inline=True
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="admin_signup_process_to_winners",
        description="Process current signups to winners (moves to all_winners.py) (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_process_to_winners(
        self,
        interaction: discord.Interaction,
        year: int = None,
        confirm: bool = False
    ):
        """Process signups and move winners to all_winners.py"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        signups_col, signups_config = self._get_signups_config(interaction.guild.id)

        # Count candidates for target year
        candidates = [c for c in signups_config["candidates"] if c["year"] == target_year]

        if not candidates:
            await interaction.response.send_message(
                f"❌ No signups found for {target_year}.",
                ephemeral=True
            )
            return

        if not confirm:
            await interaction.response.send_message(
                f"⚠️ **Warning:** This will process {len(candidates)} candidates from {target_year} signups.\n"
                f"Primary winners will be determined and moved to the winners system with ideology-based points.\n"
                f"To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        # Trigger the all_winners processing
        winners_cog = self.bot.get_cog("AllWinners")
        if winners_cog:
            await winners_cog._process_primary_winners(interaction.guild.id, target_year)
            await interaction.response.send_message(
                f"✅ Successfully processed {len(candidates)} candidates for {target_year}!\n"
                f"Primary winners have been determined and moved to the winners system.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Winners system not available. Make sure all_winners.py is loaded.",
                ephemeral=True
            )

    @app_commands.command(
        name="admin_signup_leaderboard",
        description="Show top candidates by points across all regions (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_leaderboard(
        self,
        interaction: discord.Interaction,
        top_count: int = 10,
        year: int = None
    ):
        """Show overall leaderboard of top candidates"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message(
                "❌ Election system not configured.",
                ephemeral=True
            )
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        signups_col, signups_config = self._get_signups_config(interaction.guild.id)

        # Filter by year and sort by points (descending)
        candidates = [c for c in signups_config["candidates"] if c["year"] == target_year]
        sorted_candidates = sorted(candidates, key=lambda x: x["points"], reverse=True)

        if not sorted_candidates:
            await interaction.response.send_message(
                f"❌ No candidates found for {target_year}.",
                ephemeral=True
            )
            return

        # Limit to requested count
        top_count = min(max(1, top_count), 25)  # Between 1 and 25
        top_candidates = sorted_candidates[:top_count]

        embed = discord.Embed(
            title=f"🏆 {target_year} Election Leaderboard",
            description=f"Top {len(top_candidates)} candidates by polling points",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        leaderboard_text = ""
        for i, candidate in enumerate(top_candidates, 1):
            # Medal emojis for top 3
            if i == 1:
                rank_emoji = "🥇"
            elif i == 2:
                rank_emoji = "🥈"
            elif i == 3:
                rank_emoji = "🥉"
            else:
                rank_emoji = f"#{i}"

            leaderboard_text += f"{rank_emoji} **{candidate['name']}** ({candidate['party']})\n"
            leaderboard_text += f"└ **{candidate['points']:.2f} points** | {candidate['region']} | {candidate['office']}\n"
            leaderboard_text += f"└ Stamina: {candidate['stamina']} | Corruption: {candidate['corruption']}\n\n"

        embed.add_field(
            name="🏅 Rankings",
            value=leaderboard_text,
            inline=False
        )

        # Add competition stats
        total_candidates = len(sorted_candidates)
        if total_candidates > top_count:
            embed.add_field(
                name="📊 Competition Stats",
                value=f"**Showing:** Top {top_count} of {total_candidates} candidates\n"
                      f"**Points Range:** {top_candidates[0]['points']:.2f} - {top_candidates[-1]['points']:.2f}\n"
                      f"**Total Points (All):** {sum(c['points'] for c in sorted_candidates):.2f}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="admin_signup_user",
        description="Sign up a user as a candidate for any race (Admin only - bypasses phase restrictions)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        user="The user to sign up as a candidate",
        name="Candidate name (optional - defaults to user's display name)",
        party="Political party affiliation",
        region="Region/state the candidate will run in",
        seat_id="Specific seat ID to run for (e.g., SEN-CO-1, CA-GOV)"
    )
    @app_commands.autocomplete(party=party_autocomplete)
    @app_commands.autocomplete(region=region_autocomplete)
    async def admin_signup_user(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        party: str,
        region: str,
        seat_id: str,
        name: str = None
    ):
        """Admin command to sign up any user for any race, bypassing normal restrictions"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message(
                "❌ Election system not configured. Please contact an administrator.",
                ephemeral=True
            )
            return

        current_year = time_config["current_rp_date"].year
        candidate_name = name if name else user.display_name

        # Validate region
        available_regions = self._get_regions_from_elections(interaction.guild.id)
        if region not in available_regions:
            regions_text = ", ".join(available_regions) if available_regions else "None available"
            await interaction.response.send_message(
                f"❌ Invalid region. Available regions: {regions_text}",
                ephemeral=True
            )
            return

        # Get available seats in the region
        available_seats = self._get_available_seats_in_region(interaction.guild.id, region)

        # Find the specific seat
        selected_seat = None
        for seat in available_seats:
            if seat['seat_id'].upper() == seat_id.upper():
                selected_seat = seat
                break

        if not selected_seat:
            available_seat_ids = [seat['seat_id'] for seat in available_seats]
            if available_seat_ids:
                await interaction.response.send_message(
                    f"❌ Seat '{seat_id}' not found or not available in {region}.\n"
                    f"Available seats: {', '.join(available_seat_ids)}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ No seats are currently available in {region}.",
                    ephemeral=True
                )
            return

        # Determine current phase for appropriate starting stats
        current_phase = time_config.get("current_phase", "")

        # During General Campaign phase, add directly to all_winners as a primary winner
        if current_phase == "General Campaign":
            # Get all_winners configuration
            winners_col = self.bot.db["winners"]
            winners_config = winners_col.find_one({"guild_id": interaction.guild.id})
            if not winners_config:
                winners_config = {
                    "guild_id": interaction.guild.id,
                    "winners": []
                }
                winners_col.insert_one(winners_config)

            # Check if user already has a winner entry for this year
            for winner in winners_config.get("winners", []):
                if winner.get("user_id") == user.id and winner.get("year") == current_year:
                    await interaction.response.send_message(
                        f"❌ {user.mention} is already registered as **{winner['candidate']}** for {winner['seat_id']} in the general campaign.",
                        ephemeral=True
                    )
                    return

            # Determine political party category
            party_lower = party.lower()
            if "republican" in party_lower:
                political_party = "Republican Party"
            elif "democrat" in party_lower:
                political_party = "Democratic Party"
            else:
                political_party = "Independents"

            # Create winner entry directly in all_winners
            winner_entry = {
                "year": current_year,
                "user_id": user.id,
                "office": selected_seat["office"],
                "state": selected_seat["state"],
                "seat_id": seat_id,
                "candidate": candidate_name,
                "party": party,
                "political_party": political_party,
                "points": 0.0,  # Reset for general campaign
                "baseline_percentage": 50.0,  # Default baseline
                "votes": 0,
                "corruption": 0,
                "final_score": 0,
                "stamina": 100,
                "winner": False,
                "phase": "General Campaign",
                "primary_winner": True,
                "general_winner": False,
                "created_date": datetime.utcnow()
            }

            winners_config["winners"].append(winner_entry)

            winners_col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"winners": winners_config["winners"]}}
            )

            await interaction.response.send_message(
                f"✅ Successfully added {user.mention} as **{candidate_name}** ({party}) for **{seat_id}** to the general campaign!",
                ephemeral=True
            )

        else:
            # During primary phases, add to signups as normal
            # Get signups configuration
            signups_col, signups_config = self._get_signups_config(interaction.guild.id)

            # Check if user already has a signup for this election cycle
            existing_signup = None
            for candidate in signups_config["candidates"]:
                if (candidate["user_id"] == user.id and
                    candidate["year"] == current_year):
                    existing_signup = candidate
                    break

            if existing_signup:
                await interaction.response.send_message(
                    f"❌ {user.mention} is already signed up as **{existing_signup['name']}** ({existing_signup['party']}) for {existing_signup['region']} - {existing_signup['office']} in {current_year}.",
                    ephemeral=True
                )
                return

            # Create candidate entry
            new_candidate = {
                "user_id": user.id,
                "name": candidate_name,
                "party": party,
                "region": selected_seat["state"],
                "seat_id": selected_seat["seat_id"],
                "office": selected_seat["office"],
                "year": current_year,
                "signup_date": datetime.utcnow(),
                "points": 0.0,  # Start with 0 points for primary
                "stamina": 100,
                "corruption": 0,
                "phase": current_phase
            }

            signups_config["candidates"].append(new_candidate)

            signups_col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"candidates": signups_config["candidates"]}}
            )

            # Create success embed
            success_embed = discord.Embed(
                title="✅ Admin Signup Successful!",
                description=f"Successfully signed up {user.mention} for the {current_year} election!",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )

            success_embed.add_field(
                name="📋 Campaign Details",
                value=f"**Name:** {candidate_name}\n"
                      f"**User:** {user.mention}\n"
                      f"**Party:** {party}\n"
                      f"**Seat:** {selected_seat['seat_id']}\n"
                      f"**Office:** {selected_seat['office']}\n"
                      f"**Region:** {region}\n"
                      f"**Term:** {selected_seat['term_years']} years",
                inline=True
            )

            success_embed.add_field(
                name="📊 Starting Stats",
                value=f"**Stamina:** {new_candidate['stamina']}\n"
                      f"**Points:** {new_candidate['points']:.2f}\n"
                      f"**Corruption:** {new_candidate['corruption']}\n"
                      f"**Phase:** {current_phase}",
                inline=True
            )

            incumbent_text = ""
            if selected_seat.get("current_holder"):
                incumbent_text = f"\n\n**Current Holder:** {selected_seat['current_holder']}"

            success_embed.add_field(
                name="🎯 Election Info",
                value=f"**Election Year:** {current_year}\n"
                      f"**Current Phase:** {current_phase}{incumbent_text}",
                inline=False
            )

            success_embed.add_field(
                name="⚠️ Admin Override",
                value="This signup was created by an administrator and bypassed normal phase restrictions.",
                inline=False
            )

            await interaction.response.send_message(embed=success_embed, ephemeral=True)

    @app_commands.command(
        name="admin_signup_reset_primary",
        description="Reset primary election by clearing all candidate signups (Admin only - DESTRUCTIVE)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_reset_primary_election(
        self,
        interaction: discord.Interaction,
        year: int = None,
        confirm: bool = False
    ):
        """Reset primary election by clearing all signups"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        signups_col, signups_config = self._get_signups_config(interaction.guild.id)

        # Count signups for target year
        year_signups = [c for c in signups_config["candidates"] if c["year"] == target_year]

        if not year_signups:
            await interaction.response.send_message(
                f"❌ No candidate signups found for {target_year}.",
                ephemeral=True
            )
            return

        if not confirm:
            await interaction.response.send_message(
                f"⚠️ **DANGER:** This will completely reset the {target_year} primary election!\n"
                f"• Remove ALL {len(year_signups)} candidate signups\n"
                f"• Clear all campaign points, stamina, and corruption data\n"
                f"• Cannot be undone!\n\n"
                f"To confirm this destructive action, run with `confirm:True`",
                ephemeral=True
            )
            return

        # Remove all signups for target year
        signups_config["candidates"] = [
            c for c in signups_config["candidates"] if c["year"] != target_year
        ]

        signups_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"candidates": signups_config["candidates"]}}
        )

        await interaction.response.send_message(
            f"✅ **Primary Election Reset Complete!**\n"
            f"• Removed {len(year_signups)} candidate signups for {target_year}\n"
            f"• All primary campaign data has been cleared\n"
            f"• Candidates can now sign up again from scratch",
            ephemeral=True
        )


async def setup(bot):
    cog = AllSignups(bot)
    
    # Only add command groups if they haven't been added by command_groups.py
    try:
        bot.tree.add_command(signup_group)
    except Exception as e:
        if "already registered" not in str(e).lower():
            raise e
        print(f"signup group already registered (likely by command_groups.py)")
    
    try:
        bot.tree.add_command(admin_signup_group)
    except Exception as e:
        if "already registered" not in str(e).lower():
            raise e
        print(f"admin_signup group already registered (likely by command_groups.py)")
    
    await bot.add_cog(cog)