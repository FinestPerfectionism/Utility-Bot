import discord
from discord.ext import commands

from constants import (
    DIRECTOR_TASKS_CHANNEL_ID,
    STAFF_PROPOSALS_REVIEW_CHANNEL_ID,
    TICKET_CHANNEL_ID,
)
from core.permissions import is_director, is_moderator, is_staff_committee

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Thread Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ThreadCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def allowed_in_thread(self, ctx : commands.Context[commands.Bot]) -> bool:
        if not isinstance(ctx.channel, discord.Thread):
            return False

        if not isinstance(ctx.author, discord.Member):
            return False

        parent = ctx.channel.parent
        if parent is None:
            return False

        if parent.id == DIRECTOR_TASKS_CHANNEL_ID:
            return is_director(ctx.author)

        if parent.id == TICKET_CHANNEL_ID:
            return is_moderator(ctx.author)

        if parent.id == STAFF_PROPOSALS_REVIEW_CHANNEL_ID:
            return is_staff_committee(ctx.author)

        return False

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .lock/.l Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name = "lock",
        aliases=["l"],
    )
    async def lock(self, ctx : commands.Context[commands.Bot]) -> None:
        if not self.allowed_in_thread(ctx):
            return

        if not isinstance(ctx.channel, discord.Thread):
            return

        _ = await ctx.channel.edit(locked=True)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .close/.c Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name = "close",
        aliases=["c"],
    )
    async def close(self, ctx : commands.Context[commands.Bot]) -> None:
        if not self.allowed_in_thread(ctx):
            return

        if not isinstance(ctx.channel, discord.Thread):
            return

        _ = await ctx.channel.edit(archived=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ThreadCommands(bot))
