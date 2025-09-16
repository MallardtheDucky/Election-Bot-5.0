"""
Command Groups - Consolidates multiple commands into grouped subcommands to reduce Discord's 100 command limit
"""

import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

# Define main command groups
signup_group = app_commands.Group(name="signup", description="Candidate signup commands")
admin_signup_group = app_commands.Group(name="admin_signup", description="Admin signup management commands")
pres_campaign_group = app_commands.Group(name="pres_campaign", description="Presidential campaign commands")
pres_admin_group = app_commands.Group(name="pres_admin", description="Presidential admin commands")
pres_poll_group = app_commands.Group(name="pres_poll", description="Presidential polling commands")
economy_group = app_commands.Group(name="economy", description="Economy and business commands")

class CommandGroups(commands.Cog):
    """Consolidated command groups to reduce total command count"""
    
    def __init__(self, bot):
        self.bot = bot
        # Add command groups to this cog
        self.__cog_app_commands__ = [
            signup_group,
            admin_signup_group, 
            pres_campaign_group,
            pres_admin_group,
            pres_poll_group,
            economy_group
        ]
        print("Command Groups cog loaded successfully")

    # Signup Commands (from all_signups.py)
    @signup_group.command(name="register", description="Sign up as a candidate for election")
    async def signup_register(self, interaction: discord.Interaction):
        """Redirect to all_signups cog"""
        signups_cog = self.bot.get_cog('AllSignups')
        if signups_cog:
            # This would need to be implemented in the actual cog
            await interaction.response.send_message("Please use the individual signup commands for now.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Signup system not available.", ephemeral=True)

    @signup_group.command(name="view", description="View candidate signups")
    async def signup_view(self, interaction: discord.Interaction):
        """Redirect to all_signups cog"""
        signups_cog = self.bot.get_cog('AllSignups')
        if signups_cog:
            await interaction.response.send_message("Please use the individual signup commands for now.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Signup system not available.", ephemeral=True)

    @signup_group.command(name="withdraw", description="Withdraw your candidacy")
    async def signup_withdraw(self, interaction: discord.Interaction):
        """Redirect to all_signups cog"""
        signups_cog = self.bot.get_cog('AllSignups')
        if signups_cog:
            await interaction.response.send_message("Please use the individual signup commands for now.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Signup system not available.", ephemeral=True)

    @signup_group.command(name="my_details", description="View your signup details")
    async def signup_my_details(self, interaction: discord.Interaction):
        """Redirect to all_signups cog"""
        signups_cog = self.bot.get_cog('AllSignups')
        if signups_cog:
            await interaction.response.send_message("Please use the individual signup commands for now.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Signup system not available.", ephemeral=True)

    # Admin Signup Commands
    @admin_signup_group.command(name="remove_candidate", description="Remove a candidate (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_remove_candidate(self, interaction: discord.Interaction):
        """Redirect to all_signups cog"""
        await interaction.response.send_message("Please use the individual admin signup commands for now.", ephemeral=True)

    @admin_signup_group.command(name="clear_all", description="Clear all signups (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_clear_all(self, interaction: discord.Interaction):
        """Redirect to all_signups cog"""
        await interaction.response.send_message("Please use the individual admin signup commands for now.", ephemeral=True)

    @admin_signup_group.command(name="modify_candidate", description="Modify candidate info (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_modify_candidate(self, interaction: discord.Interaction):
        """Redirect to all_signups cog"""
        await interaction.response.send_message("Please use the individual admin signup commands for now.", ephemeral=True)

    # Presidential Campaign Commands
    @pres_campaign_group.command(name="signup", description="Sign up for President")
    async def pres_signup(self, interaction: discord.Interaction):
        """Redirect to presidential_signups cog"""
        pres_cog = self.bot.get_cog('PresidentialSignups')
        if pres_cog:
            await interaction.response.send_message("Please use the individual presidential signup commands for now.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Presidential signup system not available.", ephemeral=True)

    @pres_campaign_group.command(name="vp_signup", description="Sign up for Vice President")
    async def vp_signup(self, interaction: discord.Interaction):
        """Redirect to presidential_signups cog"""
        await interaction.response.send_message("Please use the individual VP signup commands for now.", ephemeral=True)

    @pres_campaign_group.command(name="accept_vp", description="Accept a VP candidate")
    async def accept_vp(self, interaction: discord.Interaction):
        """Redirect to presidential_signups cog"""
        await interaction.response.send_message("Please use the individual VP commands for now.", ephemeral=True)

    @pres_campaign_group.command(name="decline_vp", description="Decline a VP candidate")
    async def decline_vp(self, interaction: discord.Interaction):
        """Redirect to presidential_signups cog"""
        await interaction.response.send_message("Please use the individual VP commands for now.", ephemeral=True)

    @pres_campaign_group.command(name="withdraw", description="Withdraw from presidential race")
    async def pres_withdraw(self, interaction: discord.Interaction):
        """Redirect to presidential_signups cog"""
        await interaction.response.send_message("Please use the individual presidential commands for now.", ephemeral=True)

    # Presidential Admin Commands
    @pres_admin_group.command(name="cleanup_duplicates", description="Remove duplicate entries (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_cleanup_duplicates(self, interaction: discord.Interaction):
        """Redirect to presidential_signups cog"""
        await interaction.response.send_message("Please use the individual presidential admin commands for now.", ephemeral=True)

    @pres_admin_group.command(name="force_withdraw", description="Force withdraw candidate (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_force_withdraw(self, interaction: discord.Interaction):
        """Redirect to presidential_signups cog"""
        await interaction.response.send_message("Please use the individual presidential admin commands for now.", ephemeral=True)

    @pres_admin_group.command(name="view_points", description="View candidate points (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_view_points(self, interaction: discord.Interaction):
        """Redirect to presidential_signups cog"""
        await interaction.response.send_message("Please use the individual presidential admin commands for now.", ephemeral=True)

    # Presidential Polling Commands
    @pres_poll_group.command(name="private", description="Create private presidential poll")
    async def pres_private_poll(self, interaction: discord.Interaction):
        """Redirect to polling cog"""
        polling_cog = self.bot.get_cog('Polling')
        if polling_cog:
            await interaction.response.send_message("Please use the individual polling commands for now.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Polling system not available.", ephemeral=True)

    @pres_poll_group.command(name="media", description="Create media presidential poll")
    async def media_pres_poll(self, interaction: discord.Interaction):
        """Redirect to polling cog"""
        await interaction.response.send_message("Please use the individual polling commands for now.", ephemeral=True)

    # Economy Commands (consolidating business, stock, currency, etc.)
    @economy_group.command(name="balance", description="Check your balance")
    async def balance(self, interaction: discord.Interaction):
        """Redirect to currency_system cog"""
        currency_cog = self.bot.get_cog('CurrencySystem')
        if currency_cog:
            await interaction.response.send_message("Please use the individual balance commands for now.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Currency system not available.", ephemeral=True)

    @economy_group.command(name="transfer", description="Transfer money to another user")
    async def transfer(self, interaction: discord.Interaction):
        """Redirect to currency_system cog"""
        await interaction.response.send_message("Please use the individual transfer commands for now.", ephemeral=True)

    @economy_group.command(name="job", description="Work a job to earn money")
    async def job(self, interaction: discord.Interaction):
        """Redirect to currency_system cog"""
        await interaction.response.send_message("Please use the individual job commands for now.", ephemeral=True)

    @economy_group.command(name="business_register", description="Register a new business")
    async def business_register(self, interaction: discord.Interaction):
        """Redirect to business_management cog"""
        business_cog = self.bot.get_cog('BusinessManagement')
        if business_cog:
            await interaction.response.send_message("Please use the individual business commands for now.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Business system not available.", ephemeral=True)

    @economy_group.command(name="business_info", description="View business information")
    async def business_info(self, interaction: discord.Interaction):
        """Redirect to business_management cog"""
        await interaction.response.send_message("Please use the individual business commands for now.", ephemeral=True)

    @economy_group.command(name="stock_buy", description="Buy stocks")
    async def stock_buy(self, interaction: discord.Interaction):
        """Redirect to stock_market cog"""
        stock_cog = self.bot.get_cog('StockMarket')
        if stock_cog:
            await interaction.response.send_message("Please use the individual stock commands for now.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Stock market system not available.", ephemeral=True)

    @economy_group.command(name="stock_sell", description="Sell stocks")
    async def stock_sell(self, interaction: discord.Interaction):
        """Redirect to stock_market cog"""
        await interaction.response.send_message("Please use the individual stock commands for now.", ephemeral=True)

    @economy_group.command(name="portfolio", description="View your stock portfolio")
    async def portfolio(self, interaction: discord.Interaction):
        """Redirect to stock_market cog"""
        await interaction.response.send_message("Please use the individual portfolio commands for now.", ephemeral=True)

    @economy_group.command(name="market", description="View market information")
    async def market(self, interaction: discord.Interaction):
        """Redirect to stock_market cog"""
        await interaction.response.send_message("Please use the individual market commands for now.", ephemeral=True)

    @economy_group.command(name="pac_create", description="Create a PAC")
    async def pac_create(self, interaction: discord.Interaction):
        """Redirect to pac_system cog"""
        pac_cog = self.bot.get_cog('PACSystem')
        if pac_cog:
            await interaction.response.send_message("Please use the individual PAC commands for now.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ PAC system not available.", ephemeral=True)

    @economy_group.command(name="donation", description="Make a donation")
    async def donation(self, interaction: discord.Interaction):
        """Redirect to pac_system cog"""
        await interaction.response.send_message("Please use the individual donation commands for now.", ephemeral=True)

    @economy_group.command(name="tax_pay", description="Pay your taxes")
    async def tax_pay(self, interaction: discord.Interaction):
        """Redirect to tax_system cog"""
        tax_cog = self.bot.get_cog('TaxSystem')
        if tax_cog:
            await interaction.response.send_message("Please use the individual tax commands for now.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Tax system not available.", ephemeral=True)

    @economy_group.command(name="tax_history", description="View tax payment history")
    async def tax_history(self, interaction: discord.Interaction):
        """Redirect to tax_system cog"""
        await interaction.response.send_message("Please use the individual tax commands for now.", ephemeral=True)

async def setup(bot):
    """Setup function to add the cog"""
    cog = CommandGroups(bot)
    await bot.add_cog(cog)
    print("✅ Command groups registered successfully")