import discord
from discord.ext import commands
from datetime import datetime, UTC

from constants import COLOR_RED
from .._base import AuditCog, AuditQueue


class ThreadDeleteCog(AuditCog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread) -> None:
        if thread.parent and self.is_directorship_channel(thread.parent):
            return

        log_channel = await self.get_log_channel(thread.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Thread Deleted",
            color=COLOR_RED,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(
            name="Thread",
            value=f"`{thread.name}`\n`{thread.id}`",
            inline=True
        )
        embed.add_field(
            name="Parent Channel",
            value=f"`{thread.parent.name}`\n`{thread.parent.id}`",
            inline=True
        )

        await self._enqueue(log_channel, embed)
