import discord
from discord.ext import commands

from constants import GUILD_ID

from ._base  import leave_group
from .add    import LeaveAdd
from .remove import LeaveRemove

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LeaveAdd(bot))
    await bot.add_cog(LeaveRemove(bot))
    bot.tree.add_command(leave_group, guild=discord.Object(id=GUILD_ID))

async def teardown(bot: commands.Bot) -> None:
    bot.tree.remove_command(leave_group.name)