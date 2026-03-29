import discord
from discord.ext import commands
from datetime import datetime, UTC

from constants import COLOR_GREEN
from .._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Thread Create Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ThreadCreateCog(AuditCog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread) -> None:
        if thread.parent and self.is_directorship_channel(thread.parent):
            return

        log_channel = await self.get_log_channel(thread.guild)
        if not log_channel:
            return

        parent = thread.parent
        if parent is None:
            return

        embed = discord.Embed(
            title="Thread Created",
            color=COLOR_GREEN,
            timestamp = datetime.now(UTC)
        )

        embed.add_field(
            name="Thread",
            value = f"`{thread.name}`\n`{thread.id}`",
            inline = True
        )
        embed.add_field(
            name="Parent Channel",
            value = f"`{parent.name}`\n`{parent.id}`",
            inline = True
        )

        if thread.owner:
            embed.add_field(
                name="Created By",
                value = f"`{thread.owner}`\n`{thread.owner.id}`",
                inline = False
            )

        embed.add_field(
            name="Auto Archive Duration",
            value = f"{thread.auto_archive_duration} min",
            inline = True
        )

        await self._enqueue(log_channel, embed)
