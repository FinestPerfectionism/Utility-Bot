from discord.ext import commands

from .add    import LeaveAdd
from .remove import LeaveRemove

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LeaveAdd(bot))
    await bot.add_cog(LeaveRemove(bot))