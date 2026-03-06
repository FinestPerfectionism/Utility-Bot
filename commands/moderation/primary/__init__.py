from typing import cast

from discord.ext import commands

from bot import UtilityBot

from .bans import BanCommands
from .kicks import KickCommands
from .timeouts import TimeoutCommands
from .purge import PurgeCommands

async def setup(bot: commands.Bot):
    await bot.add_cog(BanCommands(cast(UtilityBot, bot)))
    await bot.add_cog(KickCommands(cast(UtilityBot, bot)))
    await bot.add_cog(TimeoutCommands(cast(UtilityBot, bot)))
    await bot.add_cog(PurgeCommands(cast(UtilityBot, bot)))