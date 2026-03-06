from typing import cast

from discord.ext import commands

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import UtilityBot

from .bans import BanCommands
from .kicks import KickCommands
from .timeouts import TimeoutCommands
from .purge import PurgeCommands
from .notes import NoteCommands

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BanCommands(cast("UtilityBot", bot)))
    await bot.add_cog(KickCommands(cast("UtilityBot", bot)))
    await bot.add_cog(TimeoutCommands(cast("UtilityBot", bot)))
    await bot.add_cog(PurgeCommands(cast("UtilityBot", bot)))
    await bot.add_cog(NoteCommands(cast("UtilityBot", bot)))