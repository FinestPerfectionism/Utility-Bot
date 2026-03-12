import discord
from discord.ext import commands
from constants import GUILD_ID
from ._base import leave_group
from .leave import Leave

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Leave(bot))

async def teardown(bot: commands.Bot) -> None:
    bot.tree.remove_command(leave_group.name, guild=discord.Object(id=GUILD_ID))