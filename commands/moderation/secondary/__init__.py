from typing import cast

from discord.ext import commands

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import UtilityBot

from .health import HealthCommands
from .lockdown import LockdownCommands
from .quarantine import QuarantineCommands

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HealthCommands(cast("UtilityBot", bot)))
    await bot.add_cog(LockdownCommands(cast("UtilityBot", bot)))
    await bot.add_cog(QuarantineCommands(cast("UtilityBot", bot)))