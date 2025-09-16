from discord.ext import commands
import discord
from discord import app_commands
from typing import List, Optional
from datetime import datetime

class CampaignPointsView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, sort_by: str, filter_state: str, filter_party: str, year: int, total_pages: int, current_page: int):
        super().__init__(timeout=300)
        self.interaction = interaction
        self.sort_by = sort_by
        self.filter_state = filter_state
        self.filter_party = filter_party
        self.year = year
        self.total_pages = total_pages
        self.current_page = current_page

        # Add page selector dropdown
        self.add_item(PageSelector(total_pages, current_page))

class PageSelector(discord.ui.Select):
    def __init__(self, total_pages: int, current_page: int):
        # Create options for page selection
        options = []

        # Show all pages if 25 or fewer, otherwise show smart selection
        if total_pages <= 25:
            for page in range(1, total_pages + 1):
                label = f"Page {page}"
                if page == current_page:
                    label += " (Current)"
                options.append(discord.SelectOption(
                    label=label,
                    value=str(page),
                    default=(page == current_page)
                ))
        else:
            # For many pages, show first few, current area, and last few
            pages_to_show = set()

            # First 3 pages
            pages_to_show.update(range(1, min(4, total_pages + 1)))

            # Current page and neighbors
            start = max(1, current_page - 2)
            end = min(total_pages + 1, current_page + 3)
            pages_to_show.update(range(start, end))

            # Last 3 pages
            pages_to_show.update(range(max(1, total_pages - 2), total_pages + 1))

            sorted_pages = sorted(pages_to_show)

            for page in sorted_pages:
                label = f"Page {page}"
                if page == current_page:
                    label += " (Current)"
                options.append(discord.SelectOption(
                    label=label,
                    value=str(page),
                    default=(page == current_page)
                ))

        super().__init__(
            placeholder=f"Jump to page... (Current: {current_page}/{total_pages})",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_page = int(self.values[0])
        await interaction.response.defer()

        # Get the cog and regenerate the page content
        cog = interaction.client.get_cog('AllWinners')
        if not cog:
            await interaction.followup.send("❌ Error: Cog not found", ephemeral=True)
            return

        # Get time and winners config
        time_col, time_config = cog._get_time_config(interaction.guild.id)
        if not time_config:
            await interaction.followup.send("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        current_phase = time_config.get("current_phase", "")
        target_year = self.view.year if self.view.year else current_year

        winners_col, winners_config = cog._get_winners_config(interaction.guild.id)

        # Get primary winners (candidates in general election)
        candidates = [
            w for w in winners_config.get("winners", [])
            if w["year"] == target_year and w.get("primary_winner", False)
        ]

        # Apply filters
        if self.view.filter_state:
            candidates = [c for c in candidates if self.view.filter_state.lower() == c.get("state", "").lower()]
        if self.view.filter_party:
            candidates = [c for c in candidates if self.view.filter_party.lower() in c.get("party", "").lower()]

        # Sort candidates
        if self.view.sort_by.lower() == "points":
            candidates.sort(key=lambda x: x.get("total_points", x.get("points", 0)), reverse=True)
        elif self.view.sort_by == "corruption":
            candidates.sort(key=lambda x: x.get("corruption", 0), reverse=True)
        elif self.view.sort_by == "seat":
            candidates.sort(key=lambda x: x.get("seat_id", ""))
        elif self.view.sort_by == "name":
            candidates.sort(key=lambda x: x.get("candidate", ""))

        # Calculate percentages for all candidates first
        unique_seats = list(set(c.get("seat_id") for c in candidates if c.get("seat_id")))
        seat_percentages_cache = {}
        for seat_id in unique_seats:
            if seat_id and seat_id != "N/A":
                try:
                    seat_percentages_cache[seat_id] = cog._calculate_zero_sum_percentages(interaction.guild.id, seat_id)
                except Exception as e:
                    seat_percentages_cache[seat_id] = {}

        for candidate in candidates:
            seat_id = candidate.get('seat_id')
            candidate_name = candidate.get('candidate', '')
            if seat_id in seat_percentages_cache:
                candidate['calculated_percentage'] = seat_percentages_cache[seat_id].get(candidate_name, 50.0)
            else:
                candidate['calculated_percentage'] = 50.0

        # Pagination
        candidates_per_page = 8
        total_pages = max(1, (len(candidates) + candidates_per_page - 1) // candidates_per_page)
        start_idx = (selected_page - 1) * candidates_per_page
        end_idx = start_idx + candidates_per_page
        page_candidates = candidates[start_idx:end_idx]

        # Create embed
        embed = discord.Embed(
            title=f"📊 {target_year} General Campaign Points",
            description=f"Sorted by {self.view.sort_by} • Page {selected_page}/{total_pages} • {len(candidates)} total candidates",
            color=discord.Color.purple(),
            timestamp=datetime.utcnow()
        )

        # Build candidate list
        candidate_list = ""
        for i, candidate in enumerate(page_candidates, start_idx + 1):
            total_points = candidate.get('total_points', 0)
            points = candidate.get('points', 0)
            actual_points = total_points if total_points > 0 else points
            percentage = candidate.get('calculated_percentage', 50.0)
            
            points_display = f"{actual_points:.2f} ({percentage:.1f}%)"
            
            candidate_list += f"**{i}.** {candidate.get('candidate', 'Unknown')} ({candidate.get('party', 'Unknown')})\n"
            candidate_list += f"   └ {candidate.get('seat_id', 'Unknown')} • Points: {points_display}\n"
            candidate_list += f"   └ Stamina: {candidate.get('stamina', 100)} • Corruption: {candidate.get('corruption', 0)}\n\n"

        embed.add_field(name=f"🏆 Candidates (Page {selected_page}/{total_pages})", value=candidate_list or "No candidates found", inline=False)

        # Add statistics
        if candidates:
            total_points = sum(c.get("points", 0) for c in candidates)
            total_votes = sum(c.get("votes", 0) for c in candidates)
            avg_corruption = sum(c.get("corruption", 0) for c in candidates) / len(candidates)

            embed.add_field(
                name="📈 Summary Statistics",
                value=f"**Total Candidates:** {len(candidates)}\n"
                      f"**Total Points:** {total_points:.2f}\n"
                      f"**Total Votes:** {total_votes:,}\n"
                      f"**Avg Corruption:** {avg_corruption:.1f}",
                inline=True
            )

        # Show filter info if applied
        filter_info = ""
        if self.view.filter_state:
            filter_info += f"State: {self.view.filter_state} • "
        if self.view.filter_party:
            filter_info += f"Party: {self.view.filter_party} • "
        if filter_info:
            embed.add_field(
                name="🔍 Active Filters",
                value=filter_info.rstrip(" • "),
                inline=True
            )

        # Navigation info
        navigation_info = f"**Page {selected_page} of {total_pages}**\n"
        if selected_page > 1:
            navigation_info += f"Use `page:{selected_page-1}` for previous page\n"
        if selected_page < total_pages:
            navigation_info += f"Use `page:{selected_page+1}` for next page\n"
        navigation_info += f"Showing candidates {start_idx + 1}-{min(end_idx, len(candidates))}"

        embed.add_field(
            name="📄 Navigation",
            value=navigation_info,
            inline=False
        )

        # Create new view with updated page
        new_view = CampaignPointsView(
            interaction,
            self.view.sort_by,
            self.view.filter_state,
            self.view.filter_party,
            self.view.year,
            total_pages,
            selected_page
        )

        await interaction.edit_original_response(embed=embed, view=new_view)

class GeneralCampaignRegionDropdown(discord.ui.Select):
    def __init__(self, regions, candidates_by_region, year):
        self.candidates_by_region = candidates_by_region
        self.year = year

        options = [
            discord.SelectOption(
                label="🌍 All Regions",
                description="View candidates from all regions",
                value="all",
                emoji="🌍"
            )
        ]

        # Add region options with candidate counts
        for region in sorted(regions.keys()):
            candidate_count = len(regions[region])
            options.append(
                discord.SelectOption(
                    label=f"📍 {region}",
                    description=f"{candidate_count} candidate{'s' if candidate_count != 1 else ''}",
                    value=region
                )
            )

        super().__init__(placeholder="Select a region to view candidates...", options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        try:
            selected_region = self.values[0]

            if selected_region == "all":
                # Show overview of all regions
                embed = discord.Embed(
                    title=f"🎯 {self.year} General Campaign - All Regions",
                    description="Primary winners advancing to general election",
                    color=discord.Color.purple(),
                    timestamp=datetime.utcnow()
                )

                # Add summary for each region
                for region, candidates in sorted(self.candidates_by_region.items()):
                    candidate_list = ""
                    for candidate in sorted(candidates, key=lambda x: x.get("points", 0), reverse=True)[:5]:
                        candidate_name = candidate.get('candidate', 'Unknown')
                        candidate_party = candidate.get('party', 'Unknown')
                        candidate_seat = candidate.get('seat_id', 'Unknown')
                        candidate_list += f"• **{candidate_name}** ({candidate_party}) - {candidate_seat}\n"

                    if len(candidates) > 5:
                        candidate_list += f"• ... and {len(candidates) - 5} more"

                    embed.add_field(
                        name=f"📍 {region} ({len(candidates)} candidates)",
                        value=candidate_list or "No candidates",
                        inline=True
                    )
            else:
                # Show detailed view for selected region
                candidates = self.candidates_by_region.get(selected_region, [])

                embed = discord.Embed(
                    title=f"🎯 {self.year} General Campaign - {selected_region}",
                    description=f"Primary winners from {selected_region} advancing to general election",
                    color=discord.Color.purple(),
                    timestamp=datetime.utcnow()
                )

                if not candidates:
                    embed.add_field(
                        name="📋 No Candidates",
                        value=f"No candidates found for {selected_region}",
                        inline=False
                    )
                else:
                    # Group candidates by seat for proper percentage calculation
                    seats_in_region = {}
                    for candidate in candidates:
                        seat_id = candidate.get("seat_id", "Unknown")
                        if seat_id not in seats_in_region:
                            seats_in_region[seat_id] = []
                        seats_in_region[seat_id].append(candidate)

                    candidate_list = ""
                    for seat_id, seat_candidates in sorted(seats_in_region.items()):
                        for candidate in sorted(seat_candidates, key=lambda x: x.get("candidate", "Unknown")):
                            # Safely get candidate data
                            candidate_name = candidate.get("candidate", "Unknown")
                            candidate_party = candidate.get("party", "Unknown")
                            candidate_office = candidate.get("office", "Unknown")
                            candidate_stamina = candidate.get("stamina", 100)
                            candidate_corruption = candidate.get("corruption", 0)
                            
                            # Get user mention
                            user_id = candidate.get("user_id")
                            user_mention = f"<@{user_id}>" if user_id else "No user"

                            candidate_list += (
                                f"**{candidate_name}** ({candidate_party})\n"
                                f"└ {seat_id} - {candidate_office}\n"
                                f"└ Stamina: {candidate_stamina} | Corruption: {candidate_corruption}\n"
                                f"└ {user_mention}\n\n"
                            )

                    # Handle long content by splitting into multiple fields
                    if len(candidate_list) > 1024:
                        parts = candidate_list.split('\n\n')
                        current_part = ""
                        part_num = 1

                        for part in parts:
                            if part.strip():  # Skip empty parts
                                if len(current_part + part + '\n\n') > 1024:
                                    if current_part.strip():
                                        embed.add_field(
                                            name=f"📊 Candidates (Part {part_num})",
                                            value=current_part.strip(),
                                            inline=False
                                        )
                                    current_part = part + '\n\n'
                                    part_num += 1
                                else:
                                    current_part += part + '\n\n'

                        if current_part.strip():
                            embed.add_field(
                                name=f"📊 Candidates (Part {part_num})" if part_num > 1 else "📊 Candidates",
                                value=current_part.strip(),
                                inline=False
                            )
                    else:
                        embed.add_field(
                            name="📊 Candidates",
                            value=candidate_list.strip() if candidate_list.strip() else "No candidates found",
                            inline=False
                        )

                    # Add region statistics
                    if candidates:
                        total_points = sum(c.get('points', 0) for c in candidates)
                        avg_stamina = sum(c.get('stamina', 100) for c in candidates) / len(candidates)
                        avg_corruption = sum(c.get('corruption', 0) for c in candidates) / len(candidates)

                        embed.add_field(
                            name="📈 Region Statistics",
                            value=f"**Total Candidates:** {len(candidates)}\n"
                                  f"**Average Stamina:** {avg_stamina:.1f}\n"
                                  f"**Average Corruption:** {avg_corruption:.1f}",
                            inline=False
                        )

            embed.set_footer(text=f"Use the dropdown to view other regions • Year: {self.year}")
            await interaction.response.edit_message(embed=embed, view=self.view)

        except Exception as e:
            print(f"Error in GeneralCampaignRegionDropdown callback: {e}")
            await interaction.response.send_message(
                f"❌ An error occurred while switching regions: {str(e)}", 
                ephemeral=True
            )

class GeneralCampaignRegionView(discord.ui.View):
    def __init__(self, regions, candidates_by_region, year):
        super().__init__(timeout=300)
        self.add_item(GeneralCampaignRegionDropdown(regions, candidates_by_region, year))

class AllWinners(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("All Winners cog loaded successfully")

    def _get_winners_config(self, guild_id: int):
        """Get or create winners configuration"""
        col = self.bot.db["winners"]
        config = col.find_one({"guild_id": guild_id})
        if not config:
            config = {
                "guild_id": guild_id,
                "winners": []
            }
            col.insert_one(config)
        return col, config

    def _get_signups_config(self, guild_id: int):
        """Get signups configuration"""
        col = self.bot.db["signups"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_elections_config(self, guild_id: int):
        """Get elections configuration"""
        col = self.bot.db["elections_config"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_time_config(self, guild_id: int):
        """Get time configuration"""
        col = self.bot.db["time_configs"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    @app_commands.command(
        name="admin_view_all_campaign_points",
        description="View all candidate points in general campaign phase (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_view_all_campaign_points(
        self,
        interaction: discord.Interaction,
        sort_by: str = "points",
        filter_state: str = None,
        filter_party: str = None,
        year: int = None,
        page: int = 1
    ):
        # Create a quick initial response
        embed = discord.Embed(
            title=f"📊 {year if year else 'Current'} General Campaign Points",
            description="🔄 Loading candidate data...",
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        try:
            time_col, time_config = self._get_time_config(interaction.guild.id)
            if not time_config:
                await interaction.edit_original_response(content="❌ Election system not configured.")
                return
        except Exception as e:
            await interaction.edit_original_response(content=f"❌ Database error: {str(e)}")
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year
        winners_col, winners_config = self._get_winners_config(interaction.guild.id)

        # Get primary winners (candidates in general election)
        candidates = [
            w for w in winners_config.get("winners", [])
            if w["year"] == target_year and w.get("primary_winner", False)
        ]

        if not candidates:
            await interaction.edit_original_response(content=f"❌ No general election candidates found for {target_year}.")
            return

        # Apply filters
        if filter_state:
            candidates = [c for c in candidates if filter_state.lower() == c.get("state", "").lower()]
        if filter_party:
            candidates = [c for c in candidates if filter_party.lower() in c.get("party", "").lower()]

        if not candidates:
            await interaction.edit_original_response(content="❌ No candidates found with those filters.")
            return

        # Pre-calculate percentages for all candidates
        current_phase = time_config.get("current_phase", "")
        unique_seats = list(set(c.get("seat_id") for c in candidates if c.get("seat_id")))
        seat_percentages_cache = {}

        for seat_id in unique_seats:
            if seat_id and seat_id != "N/A":
                try:
                    seat_percentages_cache[seat_id] = self._calculate_zero_sum_percentages(interaction.guild.id, seat_id)
                except Exception as e:
                    print(f"Error calculating percentages for seat {seat_id}: {e}")
                    seat_percentages_cache[seat_id] = {}

        # Apply calculated percentages to candidates
        for candidate in candidates:
            seat_id = candidate.get('seat_id')
            candidate_name = candidate.get('candidate', '')
            if seat_id in seat_percentages_cache:
                candidate['calculated_percentage'] = seat_percentages_cache[seat_id].get(candidate_name, 50.0)
            else:
                candidate['calculated_percentage'] = 50.0

        # Sort candidates
        if sort_by.lower() == "points":
            candidates.sort(key=lambda x: x.get("total_points", x.get("points", 0)), reverse=True)
        elif sort_by.lower() == "corruption":
            candidates.sort(key=lambda x: x.get("corruption", 0), reverse=True)
        elif sort_by.lower() == "percentage":
            candidates.sort(key=lambda x: x.get("calculated_percentage", 50.0), reverse=True)
        else:
            candidates.sort(key=lambda x: x.get("candidate", "").lower())

        # Create embed
        embed = discord.Embed(
            title=f"📊 {target_year} General Campaign Points",
            description=f"Sorted by {sort_by} • {len(candidates)} candidates • Phase: {current_phase}",
            color=discord.Color.purple()
        )

        # Pagination - 8 candidates per page
        candidates_per_page = 8
        total_pages = max(1, (len(candidates) + candidates_per_page - 1) // candidates_per_page)
        current_page = min(page, total_pages)
        start_idx = (current_page - 1) * candidates_per_page
        end_idx = start_idx + candidates_per_page
        page_candidates = candidates[start_idx:end_idx]

        candidate_list = ""
        for i, candidate in enumerate(page_candidates, start_idx + 1):
            total_points = candidate.get('total_points', 0)
            points = candidate.get('points', 0)
            actual_points = total_points if total_points > 0 else points
            percentage = candidate.get('calculated_percentage', 50.0)
            
            points_display = f"{actual_points:.2f} ({percentage:.1f}%)"
            party_short = candidate.get('party', 'Unknown')[:3]
            
            candidate_list += f"**{i}.** {candidate.get('candidate', 'Unknown')} ({party_short})\n"
            candidate_list += f"{candidate.get('seat_id', 'Unknown')} • {points_display} • S:{candidate.get('stamina', 100)}\n\n"

        embed.add_field(name=f"🏆 Candidates (Page {current_page}/{total_pages})", value=candidate_list or "No candidates found", inline=False)
        
        # Summary statistics - use total_points if available
        total_points = sum(c.get("total_points", c.get("points", 0)) for c in candidates)
        total_votes = sum(c.get("votes", 0) for c in candidates)
        avg_corruption = sum(c.get("corruption", 0) for c in candidates) / len(candidates) if candidates else 0
        avg_percentage = sum(c.get("calculated_percentage", 50.0) for c in candidates) / len(candidates) if candidates else 50.0

        embed.add_field(
            name="📈 Summary Statistics",
            value=f"**Total Candidates:** {len(candidates)}\n"
                  f"**Total Points:** {total_points:.2f}\n"
                  f"**Avg Percentage:** {avg_percentage:.1f}%\n"
                  f"**Page:** {current_page}/{total_pages}",
            inline=True
        )
        
        if filter_state or filter_party:
            filter_info = ""
            if filter_state:
                filter_info += f"State: {filter_state} • "
            if filter_party:
                filter_info += f"Party: {filter_party} • "
            embed.add_field(name="🔍 Filters", value=filter_info.rstrip(" • "), inline=True)

        # Create view with pagination if multiple pages
        view = None
        if total_pages > 1:
            view = CampaignPointsView(interaction, sort_by, filter_state, filter_party, target_year, total_pages, current_page)

        try:
            await interaction.edit_original_response(content=None, embed=embed, view=view)
        except discord.NotFound:
            print("Interaction expired, cannot send response")
        except Exception as e:
            print(f"Error sending response: {e}")

    @admin_view_all_campaign_points.autocomplete("filter_state")
    async def campaign_filter_state_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for state filter"""
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config:
            return []

        current_year = time_config["current_rp_date"].year
        winners_col, winners_config = self._get_winners_config(interaction.guild.id)
        if not winners_config:
            return []

        states = set()
        for winner in winners_config.get("winners", []):
            if winner.get("year") == current_year and winner.get("state"):
                states.add(winner["state"])

        return [app_commands.Choice(name=state, value=state)
                for state in sorted(states) if current.lower() in state.lower()][:25]

    @admin_view_all_campaign_points.autocomplete("filter_party")
    async def campaign_filter_party_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for party filter"""
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config:
            return []

        current_year = time_config["current_rp_date"].year
        winners_col, winners_config = self._get_winners_config(interaction.guild.id)
        if not winners_config:
            return []

        parties = set()
        for winner in winners_config.get("winners", []):
            if winner.get("year") == current_year and winner.get("party"):
                parties.add(winner["party"])

        return [app_commands.Choice(name=party, value=party)
                for party in sorted(parties) if current.lower() in party.lower()][:25]

    @admin_view_all_campaign_points.autocomplete("sort_by")
    async def campaign_sort_by_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for sort options"""
        sort_options = ["points", "corruption", "stamina", "name", "party", "state"]
        return [app_commands.Choice(name=option, value=option)
                for option in sort_options if current.lower() in option.lower()][:25]

    @app_commands.command(
        name="view_general_campaign",
        description="View all candidates currently in the general campaign phase"
    )
    async def view_general_campaign(self, interaction: discord.Interaction, year: int = None):
        # Respond immediately to avoid timeout
        embed = discord.Embed(
            title="🎯 General Campaign Candidates",
            description="🔄 Loading candidate data...",
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed)
        
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config:
            await interaction.edit_original_response(content="❌ Election system not configured.")
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year
        winners_col, winners_config = self._get_winners_config(interaction.guild.id)

        # Get primary winners (candidates in general campaign)
        general_candidates = [
            w for w in winners_config.get("winners", [])
            if w["year"] == target_year and w.get("primary_winner", False)
        ]

        if not general_candidates:
            await interaction.edit_original_response(content=f"📋 No candidates found in general campaign for {target_year}.")
            return

        # Group by state
        states = {}
        for candidate in general_candidates:
            state = candidate["state"]
            if state not in states:
                states[state] = []
            states[state].append(candidate)

        embed = discord.Embed(
            title=f"🎯 {target_year} General Campaign Candidates",
            description=f"Found {len(general_candidates)} candidates in {len(states)} states",
            color=discord.Color.purple()
        )

        # Show summary by state
        summary_text = ""
        for state, candidates in sorted(states.items()):
            summary_text += f"**{state}:** {len(candidates)} candidate{'s' if len(candidates) != 1 else ''}\n"

        embed.add_field(name="📊 By State", value=summary_text, inline=False)
        
        # Create view with region dropdown
        view = GeneralCampaignRegionView(states, states, target_year)
        await interaction.edit_original_response(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_phase_change(self, guild_id: int, old_phase: str, new_phase: str, current_year: int):
        """Handle phase changes and process primary winners"""
        if old_phase == "Primary Campaign" and new_phase == "Primary Election":
            # Process signups from the current year for primary elections
            # In odd years (1999), process 1999 signups for 2000 elections
            # In even years (2000), process signups from the same year
            if current_year % 2 == 1:  # Odd year (1999)
                signup_year = current_year
                election_year = current_year + 1
            else:  # Even year (2000)
                signup_year = current_year - 1
                election_year = current_year

            await self._process_primary_winners(guild_id, signup_year, election_year)

        elif old_phase == "Primary Election" and new_phase == "General Campaign":
            # Ensure primary winners are ready for general campaign
            # Use the current year as election year for finding primary winners
            await self._ensure_general_campaign_candidates(guild_id, current_year)

    def _calculate_ideology_points(self, winner, state_data, region_medians, state_to_seat):
        """Calculate ideology-based baseline percentage for a candidate based on their seat and party"""
        seat_id = winner["seat_id"]
        party = winner["party"]
        office = winner["office"]

        # Map party names to ideology data keys
        party_mapping = {
            "Republican Party": "republican",
            "Democratic Party": "democrat",
            "Independent": "other"
        }

        ideology_key = party_mapping.get(party)
        if not ideology_key:
            return 20.0  # Unknown party gets 20% baseline

        if "District" in office:
            # For House representatives, use specific state data
            # Find the state for this seat
            target_state = None
            for state, rep_seat in state_to_seat.items():
                if rep_seat == seat_id:
                    target_state = state
                    break

            if target_state and target_state in state_data:
                return state_data[target_state][ideology_key]
            else:
                return 20.0  # Fallback if state not found

        elif office in ["Senate", "Governor"]:
            # For Senate/Governor, use regional medians
            region = winner["region"]
            if region in region_medians:
                return region_medians[region][ideology_key]
            else:
                return 20.0  # Fallback if region not found

        else:
            # For other offices (President, VP, etc.), default baseline
            return 25.0

    def _calculate_zero_sum_percentages(self, guild_id: int, seat_id: str):
        """Calculate final percentages for candidates in a seat with zero-sum redistribution"""
        winners_col, winners_config = self._get_winners_config(guild_id)
        time_col, time_config = self._get_time_config(guild_id)
        current_year = time_config["current_rp_date"].year

        # Find all primary winners for this seat for the current year
        seat_candidates = [
            w for w in winners_config.get("winners", [])
            if w["seat_id"] == seat_id and w["year"] == current_year and w.get("primary_winner", False)
        ]

        if not seat_candidates:
            return {}

        # Count parties and determine baseline percentages
        parties = {}
        for candidate in seat_candidates:
            party = candidate["party"]
            if party not in parties:
                parties[party] = []
            parties[party].append(candidate)

        num_parties = len(parties)
        major_parties = ["Republican Party", "Democratic Party"]

        # Determine baseline percentages based on party composition
        baseline_percentages = {}
        major_parties_present = sum(1 for p in parties.keys() if p in major_parties)
        
        if num_parties == 2:
            # 50-50 split (Democrat + Republican)
            for party in parties.keys():
                baseline_percentages[party] = 50.0
        elif num_parties == 3:
            # 40-40-20 split (Democrat + Republican + Independent)
            if major_parties_present == 2:
                for party in parties.keys():
                    if party in major_parties:
                        baseline_percentages[party] = 40.0
                    else:
                        baseline_percentages[party] = 20.0
            else:
                # If not standard Dem-Rep-Ind, split evenly
                for party in parties.keys():
                    baseline_percentages[party] = 100.0 / 3
        else:
            # For other numbers of parties, split evenly
            for party in parties.keys():
                baseline_percentages[party] = 100.0 / num_parties

        # Calculate each candidate's raw change
        raw_changes = {}
        B = 100.0  # Total baseline percentage

        for candidate in seat_candidates:
            party = candidate["party"]
            candidate_name = candidate["candidate"]
            candidate_points = candidate.get("total_points", candidate.get("points", 0.0))
            points_change = float(candidate_points)
            corruption_penalty = candidate.get("corruption", 0) * 0.1
            raw_change = points_change - corruption_penalty
            raw_changes[candidate_name] = raw_change

        # Calculate net change across all candidates
        net_change_s = sum(raw_changes.values())

        # Apply zero-sum redistribution formula
        final_percentages = {}
        for candidate in seat_candidates:
            party = candidate["party"]
            candidate_name = candidate["candidate"]
            baseline_bi = baseline_percentages[party]
            raw_change_ai = raw_changes[candidate_name]
            redistribution = (baseline_bi / B) * net_change_s
            final_percentage = baseline_bi + raw_change_ai - redistribution
            final_percentage = max(0.1, final_percentage)
            final_percentages[candidate_name] = final_percentage

        # Normalize to 100%
        total_percentage = sum(final_percentages.values())
        if total_percentage > 0:
            for candidate_name in final_percentages:
                final_percentages[candidate_name] = (final_percentages[candidate_name] / total_percentage) * 100.0

        return final_percentages

    def _calculate_zero_sum_percentages(self, guild_id: int, seat_id: str):
        """Calculate final percentages for candidates in a seat with zero-sum redistribution"""
        winners_col, winners_config = self._get_winners_config(guild_id)

        time_col, time_config = self._get_time_config(guild_id)
        current_year = time_config["current_rp_date"].year

        # Find all primary winners for this seat for the current year
        seat_candidates = [
            w for w in winners_config.get("winners", [])
            if w["seat_id"] == seat_id and w["year"] == current_year and w.get("primary_winner", False)
        ]

        if not seat_candidates:
            print(f"DEBUG: No seat candidates found for {seat_id}")
            return {}

        print(f"DEBUG: Found {len(seat_candidates)} candidates for seat {seat_id}")
        for c in seat_candidates:
            print(f"  - {c.get('candidate', 'Unknown')} ({c.get('party', 'Unknown')})")

        # Count parties and determine baseline percentages
        parties = {}
        for candidate in seat_candidates:
            party = candidate["party"]
            if party not in parties:
                parties[party] = []
            parties[party].append(candidate)

        num_parties = len(parties)
        major_parties = ["Republican Party", "Democratic Party"]

        # Determine baseline percentages based on party composition
        baseline_percentages = {}
        major_parties_present = sum(1 for p in parties.keys() if p in major_parties)
        
        # Check if we have the standard 3-party setup: Republican + Democratic + Independent
        has_republican = any("Republican" in party for party in parties.keys())
        has_democratic = any("Democratic" in party for party in parties.keys())
        has_independent = any("Independent" in party for party in parties.keys())
        is_standard_three_way = has_republican and has_democratic and has_independent and num_parties == 3

        if num_parties == 2:
            # 50-50 split (Democrat + Republican)
            for party in parties.keys():
                baseline_percentages[party] = 50.0
        elif num_parties == 3:
            # 40-40-20 split (Democrat + Republican + Independent)
            if major_parties_present == 2 or is_standard_three_way:
                for party in parties.keys():
                    if party in major_parties or "Republican" in party or "Democratic" in party:
                        baseline_percentages[party] = 40.0
                    else:
                        baseline_percentages[party] = 20.0
            else:
                # If not standard Dem-Rep-Ind, split evenly
                for party in parties.keys():
                    baseline_percentages[party] = 100.0 / 3
        elif num_parties == 4:
            # 40-40-10-10 split (Democrat + Republican + Independent + Independent)
            if major_parties_present == 2:
                for party in parties.keys():
                    if party in major_parties:
                        baseline_percentages[party] = 40.0
                    else:
                        baseline_percentages[party] = 10.0
            else:
                # If not standard setup, split evenly
                for party in parties.keys():
                    baseline_percentages[party] = 25.0
        else:
            # For other numbers of parties, split evenly
            for party in parties.keys():
                baseline_percentages[party] = 100.0 / num_parties

        # Step 1: Calculate each candidate's raw change (a_i)
        raw_changes = {}
        B = 100.0  # Total baseline percentage

        for candidate in seat_candidates:
            party = candidate["party"]
            candidate_name = candidate["candidate"]

            # Use general campaign points when available; fall back to primary points
            candidate_points = candidate.get("total_points", candidate.get("points", 0.0))

            # Treat points as direct percentage movement (no extreme downscaling)
            # and apply a small corruption penalty
            points_change = float(candidate_points)
            corruption_penalty = candidate.get("corruption", 0) * 0.1
            raw_change = points_change - corruption_penalty

            raw_changes[candidate_name] = raw_change

        # Step 2: Calculate net change across all candidates (s)
        net_change_s = sum(raw_changes.values())

        # Step 3: Apply zero-sum redistribution formula
        final_percentages = {}

        for candidate in seat_candidates:
            party = candidate["party"]
            candidate_name = candidate["candidate"]

            # Final_i = b_i + a_i - (b_i / B) * s
            baseline_bi = baseline_percentages[party]
            raw_change_ai = raw_changes[candidate_name]
            redistribution = (baseline_bi / B) * net_change_s

            final_percentage = baseline_bi + raw_change_ai - redistribution

            # Ensure minimum percentage (optional guardrail)
            final_percentage = max(0.1, final_percentage)
            final_percentages[candidate_name] = final_percentage

        # COMPLETE 100% NORMALIZATION - Force total to exactly 100%
        total_percentage = sum(final_percentages.values())
        if total_percentage > 0:
            for candidate_name in final_percentages:
                final_percentages[candidate_name] = (final_percentages[candidate_name] / total_percentage) * 100.0

        # Final verification and correction for floating point errors
        final_total = sum(final_percentages.values())
        if abs(final_total - 100.0) > 0.001:
            # Apply micro-adjustment to the largest percentage
            largest_candidate = max(final_percentages.keys(), key=lambda x: final_percentages[x])
            adjustment = 100.0 - final_total
            final_percentages[largest_candidate] += adjustment

        print(f"DEBUG: Final percentages for {seat_id}: {final_percentages}")
        return final_percentages

    def _calculate_baseline_percentage(self, guild_id: int, seat_id: str, candidate_party: str):
        """Calculate baseline starting percentage for general election based on party distribution"""
        # Get all primary winners for this seat
        winners_col, winners_config = self._get_winners_config(guild_id)

        if not winners_config:
            return 50.0

        # Get current year
        time_col, time_config = self._get_time_config(guild_id)
        current_year = time_config["current_rp_date"].year if time_config else 2024

        # Find all primary winners for this seat
        seat_winners = [
            w for w in winners_config["winners"]
            if w["seat_id"] == seat_id and w["year"] == current_year and w.get("primary_winner", False)
        ]

        if not seat_winners:
            return 50.0

        # Count unique parties
        parties = set(winner["party"] for winner in seat_winners)
        num_parties = len(parties)
        major_parties = {"Democratic Party", "Republican Party"}

        # Check how many major parties are present
        major_parties_present = major_parties.intersection(parties)
        num_major_parties = len(major_parties_present)

        # Calculate baseline percentages based on party specifications
        if num_parties == 1:
            return 100.0  # Uncontested
        elif num_parties == 2:
            # Only works if both are major parties (Democrat + Republican)
            if num_major_parties == 2:
                return 50.0  # 50-50 split for Dem-Rep
            else:
                # If not both major parties, split evenly
                return 50.0
        elif num_parties == 3:
            # Democrat + Republican + Independent = 40-40-20
            if num_major_parties == 2:
                if candidate_party in major_parties:
                    return 40.0  # Democrat or Republican gets 40%
                else:
                    return 20.0  # Independent gets 20%
            else:
                # If not standard Dem-Rep-Ind, split evenly
                return 100.0 / 3
        elif num_parties == 4:
            # Democrat + Republican + Independent + Independent = 40-40-10-10
            if num_major_parties == 2:
                if candidate_party in major_parties:
                    return 40.0  # Democrat or Republican gets 40%
                else:
                    return 10.0  # Each Independent gets 10%
            else:
                # If not standard setup, split evenly
                return 25.0
        else:
            # For 5+ parties, split evenly
            return 100.0 / num_parties

    async def _process_primary_winners(self, guild_id: int, signup_year: int, election_year: int = None):
        """Process primary winners from signups"""
        if election_year is None:
            # Default logic: if signup_year is odd (1999), election_year is next even year (2000)
            # if signup_year is even (2000), election_year is the same year (2000)
            if signup_year % 2 == 1:  # Odd year
                election_year = signup_year + 1
            else:  # Even year
                election_year = signup_year

        signups_col, signups_config = self._get_signups_config(guild_id)
        winners_col, winners_config = self._get_winners_config(guild_id)

        if not signups_config:
            return

        # Get all candidates for the signup year (previous year for even election years)
        candidates = [c for c in signups_config.get("candidates", []) if c["year"] == signup_year]

        # Group candidates by seat and party
        seat_party_groups = {}
        for candidate in candidates:
            seat_id = candidate["seat_id"]
            party = candidate["party"]
            key = f"{seat_id}_{party}"

            if key not in seat_party_groups:
                seat_party_groups[key] = []
            seat_party_groups[key].append(candidate)

        primary_winners = []

        # Import ideology data for seat-based points
        try:
            from cogs.ideology import STATE_DATA, calculate_region_medians, STATE_TO_SEAT
        except ImportError:
            print("Could not import ideology data. Ideology-based points will not be calculated.")
            STATE_DATA, calculate_region_medians, STATE_TO_SEAT = {}, lambda: {}, {}

        # Get region medians for senate/governor seats
        region_medians = calculate_region_medians()

        # Determine winner for each party in each seat
        for key, party_candidates in seat_party_groups.items():
            if len(party_candidates) == 1:
                # Only one candidate, automatic winner
                winner = party_candidates[0]
            else:
                # Multiple candidates, highest points wins
                winner = max(party_candidates, key=lambda x: x.get("points", 0))

            # Calculate baseline percentage for general election
            baseline_percentage = self._calculate_baseline_percentage(guild_id, winner["seat_id"], winner["party"])

            # Create winner entry
            winner_entry = {
                "year": election_year,  # Use election year, not signup year
                "user_id": winner["user_id"],
                "office": winner["office"],
                "state": winner.get("region", "Unknown State"), # Use 'region' from signup if available
                "seat_id": winner["seat_id"],
                "candidate": winner["name"],
                "party": winner["party"],
                "points": 0.0,  # Reset campaign points for general election
                "baseline_percentage": baseline_percentage,  # Store ideology-based baseline
                "votes": 0,   # To be input by admins
                "corruption": winner.get("corruption", 0),  # Keep corruption level
                "final_score": 0,  # Calculated later
                "stamina": winner.get("stamina", 100),
                "winner": False,  # TBD after general election
                "phase": "Primary Winner",
                "primary_winner": True,
                "general_winner": False,
                "created_date": datetime.utcnow()
            }

            primary_winners.append(winner_entry)

        # Add winners to database
        if primary_winners:
            if "winners" not in winners_config:
                winners_config["winners"] = []
            winners_config["winners"].extend(primary_winners)
            winners_col.update_one(
                {"guild_id": guild_id},
                {"$set": {"winners": winners_config["winners"]}}
            )

        # Send announcement
        guild = self.bot.get_guild(guild_id)
        if guild:
            await self._announce_primary_results(guild, primary_winners, election_year)

    async def _announce_primary_results(self, guild: discord.Guild, winners: List[dict], year: int):
        """Announce primary election results"""
        # DEBUG: Only allow the specific channel ID
        REQUIRED_CHANNEL_ID = 1380498828121346210
        print(f"DEBUG: _announce_primary_results called for guild {guild.id}, year {year}, {len(winners)} winners")
        
        # Get announcement channel - only use the specific channel ID
        setup_col = self.bot.db["guild_configs"]
        setup_config = setup_col.find_one({"guild_id": guild.id})
        
        channel = None
        
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

        # Group winners by state for better display
        states = {}
        for winner in winners:
            state = winner["state"]
            if state not in states:
                states[state] = []
            states[state].append(winner)

        embed = discord.Embed(
            title=f"🗳️ {year} Primary Election Results!",
            description="The following candidates have won their party primaries and advance to the General Campaign:",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        for state, state_winners in sorted(states.items()):
            winner_text = ""
            for winner in state_winners:
                winner_text += f"**{winner['candidate']}** ({winner['party']})\n"
                winner_text += f"└ {winner['seat_id']} - {winner['office']}\n\n"

            embed.add_field(
                name=f"📍 {state}",
                value=winner_text,
                inline=True
            )

        embed.add_field(
            name="🎯 What's Next?",
            value=f"These {len(winners)} candidates will now compete in the General Campaign!\n"
                  f"Points have been reset to 0 for the general campaign phase.",
            inline=False
        )

        try:
            await channel.send(embed=embed)
        except Exception as e:
            print(f"Error sending primary results announcement: {e}")

    async def _ensure_general_campaign_candidates(self, guild_id: int, current_year: int):
        """Ensure primary winners are properly transitioned to general campaign"""
        winners_col, winners_config = self._get_winners_config(guild_id)

        # For general campaign phase, we need to look for primary winners
        # If current_year is even (2000), we look for primary winners from the same year
        # If current_year is odd (1999), we look for primary winners from the same year
        primary_winners = [
            w for w in winners_config.get("winners", [])
            if w.get("year") == current_year and w.get("primary_winner", False)
        ]

        if not primary_winners:
            print(f"No primary winners found for general campaign transition in guild {guild_id} for year {current_year}")
            return

        # Reset points and stamina for general campaign
        updated_count = 0
        for i, winner in enumerate(winners_config["winners"]):
            if (winner.get("year") == current_year and
                winner.get("primary_winner", False) and
                winner.get("phase") != "General Campaign"):

                winners_config["winners"][i]["points"] = 0.0  # Reset points for general campaign
                winners_config["winners"][i]["stamina"] = 100  # Reset stamina
                winners_config["winners"][i]["phase"] = "General Campaign"
                updated_count += 1

        if updated_count > 0:
            winners_col.update_one(
                {"guild_id": guild_id},
                {"$set": {"winners": winners_config["winners"]}}
            )
            print(f"Updated {updated_count} primary winners for general campaign in guild {guild_id}")

        # Also ensure presidential candidates are transitioned
        await self._ensure_presidential_general_campaign_candidates(guild_id, current_year)

    async def _ensure_presidential_general_campaign_candidates(self, guild_id: int, current_year: int):
        """Ensure presidential primary winners are transitioned to general campaign"""
        # Get presidential signups and check for primary winners
        pres_signups_col = self.bot.db["presidential_signups"]
        pres_signups_config = pres_signups_col.find_one({"guild_id": guild_id})

        if not pres_signups_config:
            return

        # Get presidential winners from the presidential_winners collection
        pres_winners_col = self.bot.db["presidential_winners"]
        pres_winners_config = pres_winners_col.find_one({"guild_id": guild_id})

        if not pres_winners_config or not pres_winners_config.get("winners"):
            return

        # Reset points and stamina for presidential candidates in general campaign
        candidates_updated = []
        for i, candidate in enumerate(pres_signups_config.get("candidates", [])):
            if (candidate.get("year") == current_year and
                candidate.get("office") in ["President", "Vice President"] and
                candidate.get("phase") != "General Campaign"):

                # Check if this candidate is a primary winner
                candidate_party = candidate.get("party", "")
                candidate_name = candidate.get("name", "")

                # Map party names for presidential winners
                party_key = None
                if "Democratic" in candidate_party:
                    party_key = "Democrats"
                elif "Republican" in candidate_party:
                    party_key = "Republican"
                else:
                    party_key = "Others"

                if party_key and pres_winners_config["winners"].get(party_key) == candidate_name:
                    # This candidate is a primary winner, reset for general campaign
                    pres_signups_config["candidates"][i]["points"] = 0.0
                    pres_signups_config["candidates"][i]["stamina"] = 300  # Presidential candidates get higher stamina
                    pres_signups_config["candidates"][i]["phase"] = "General Campaign"
                    candidates_updated.append(candidate_name)

        if candidates_updated:
            pres_signups_col.update_one(
                {"guild_id": guild_id},
                {"$set": {"candidates": pres_signups_config["candidates"]}}
            )
            print(f"Updated {len(candidates_updated)} presidential primary winners for general campaign: {candidates_updated}")

class PrimaryWinnersDropdown(discord.ui.Select):
    def __init__(self, primary_winners, target_year, current_year):
        self.primary_winners = primary_winners
        self.target_year = target_year
        self.current_year = current_year
        
        # Get unique states/regions
        states = sorted(set(winner["state"] for winner in primary_winners))
        
        options = [
            discord.SelectOption(
                label="All Regions",
                description="Show all primary winners",
                value="all"
            )
        ]
        
        # Add state options
        for state in states:
            state_winners = [w for w in primary_winners if w["state"] == state]
            options.append(discord.SelectOption(
                label=f"{state} ({len(state_winners)} winners)",
                description=f"Show winners from {state}",
                value=state
            ))
        
        super().__init__(placeholder="Select a region to filter...", options=options)

    async def callback(self, interaction: discord.Interaction):
        try:
            embed = self.view.get_embed(self.values[0])
            await interaction.response.edit_message(embed=embed, view=self.view)
        except discord.NotFound:
            await interaction.followup.send("The interaction has expired. Please run the command again.", ephemeral=True)

class PrimaryWinnersView(discord.ui.View):
    def __init__(self, primary_winners, target_year, current_year):
        super().__init__(timeout=300)
        self.primary_winners = primary_winners
        self.target_year = target_year
        self.current_year = current_year
        self.add_item(PrimaryWinnersDropdown(primary_winners, target_year, current_year))

    def get_embed(self, filter_region: str) -> discord.Embed:
        # Filter winners by region if specified
        if filter_region == "all":
            filtered_winners = self.primary_winners
        else:
            filtered_winners = [w for w in self.primary_winners if w["state"] == filter_region]
        
        if not filtered_winners:
            embed = discord.Embed(
                title=f"🏆 {self.target_year} Primary Election Winners",
                description="No winners found for the selected region.",
                color=discord.Color.gold(),
                timestamp=datetime.utcnow()
            )
            return embed

        # Group by state
        states = {}
        for winner in filtered_winners:
            state = winner["state"]
            if state not in states:
                states[state] = []
            states[state].append(winner)

        if self.current_year % 2 == 0 and not self.target_year:  # Even year, showing previous year's winners
            description_text = f"Candidates from {self.target_year} primaries advancing to {self.current_year} General Campaign"
        else:
            description_text = f"Candidates advancing to the General Campaign"

        embed = discord.Embed(
            title=f"🏆 {self.target_year} Primary Election Winners",
            description=description_text,
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        # Sort states alphabetically
        for state, state_winners in sorted(states.items()):
            winner_list = ""
            for winner in state_winners:
                # Create a more compact format to avoid length issues
                winner_info = f"**{winner['candidate']}** ({winner['party']})\n"
                winner_info += f"└ {winner['seat_id']} - {winner['office']}\n"
                winner_info += f"└ Points: {winner.get('points', 0):.1f} | Stamina: {winner.get('stamina', 100)}\n"
                winner_info += f"└ Baseline: {winner.get('baseline_percentage', 0):.1f}%\n\n"
                
                # Check if adding this winner would exceed the limit
                if len(winner_list) + len(winner_info) > 1000:  # Leave some buffer
                    winner_list += f"... and {len(state_winners) - state_winners.index(winner)} more winners"
                    break
                winner_list += winner_info

            embed.add_field(
                name=f"📍 {state} ({len(state_winners)} winners)",
                value=winner_list,
                inline=True
            )

        embed.add_field(
            name="📊 Summary",
            value=f"**Total Primary Winners:** {len(filtered_winners)}\n"
                  f"**States Represented:** {len(states)}",
            inline=False
        )

        return embed

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

async def setup(bot):
    await bot.add_cog(AllWinners(bot))
