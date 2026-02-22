import discord
from discord.ext import commands
from discord import app_commands

import random

from core.utils import send_minor_error

from constants import (
    BOT_OWNER_ID,
    HOLY_FATHER_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Miscellaneous Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class MiscCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /femboy Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="femboy",
        description="Such a good little utility kitten."
    )
    async def femboy(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(
            "i-i'm such a submissive wittle kitty UwU. *snuggles* I hewp cwose proposals... naa~~"
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ~super_secret_command Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name="super_secret_command"
    )
    async def super_secret_command(self, ctx: commands.Context):
        author_id = ctx.author.id

        if author_id == BOT_OWNER_ID:
            await ctx.send(
                "This is a super super secret command that is used by people that will use it super super secretly."
            )
            return

        if author_id == HOLY_FATHER_ID:
            await ctx.send(
                "Hello daddy! <:puppy3:1464256700344303771> This is a super super secret command that is used by people that will use it super super secretly."
            )
            return

        await ctx.send(
            "Hmm… I don’t think you’re super super secret enough to use this super super secret command."
        ) 

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /roulette Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="roulette",
        description="Have fun..."
    )
    async def roulette(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user

        if guild is None:
            await send_minor_error(
                interaction,
                "This command can only be used in a server.",
                subtitle="Bad command environment."
            )
            return

        await interaction.response.defer(ephemeral=False)

        chamber = random.randint(1, 6)

        if chamber == 1:
            try:
                await guild.ban(
                    member,
                    reason="Played a stupid game, won a stupid prize."
                )
                await interaction.followup.send(
                    "<a:CatShoot:1466460098955313294> *Click,* ***BAM***."
                )
            except discord.Forbidden:
                await interaction.followup.send(
                    "*Click,* ***Ba***… wait… the gun’s jammed!"
                )
        else:
            await interaction.followup.send(
                "*Click.* You live."
            )

async def setup(bot: commands.Bot):
    cog = MiscCommands(bot)
    await bot.add_cog(cog)