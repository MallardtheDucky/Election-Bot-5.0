import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import random
from typing import Optional
from .presidential_winners import PRESIDENTIAL_STATE_DATA

class PresCampaignActionsSimple(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="pres_canvass", description="Presidential canvassing")
    async def pres_canvass(self, interaction: discord.Interaction, state: str, message: str):
        await interaction.response.send_message(f"Canvassing in {state}: {message}")

    @app_commands.command(name="pres_ad", description="Presidential ad")
    async def pres_ad(self, interaction: discord.Interaction, state: str):
        await interaction.response.send_message(f"Creating ad in {state}")

    @app_commands.command(name="pres_poster", description="Presidential poster")
    async def pres_poster(self, interaction: discord.Interaction, state: str, image: discord.Attachment):
        await interaction.response.send_message(f"Creating poster in {state}")

    @app_commands.command(name="pres_speech", description="Presidential speech")
    async def pres_speech(self, interaction: discord.Interaction, state: str, ideology: str):
        await interaction.response.send_message(f"Giving speech in {state} with {ideology} ideology")

async def setup(bot):
    await bot.add_cog(PresCampaignActionsSimple(bot))