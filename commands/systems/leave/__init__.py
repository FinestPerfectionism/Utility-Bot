from discord.ext import commands

from .add    import setup as setup_add
from .remove import setup as setup_remove

async def setup(bot: commands.Bot) -> None:
    await setup_add(bot)
    await setup_remove(bot)