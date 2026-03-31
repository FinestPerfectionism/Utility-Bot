from datetime import UTC, datetime

import discord
from discord.ext import commands

from constants import COLOR_BLURPLE

from .._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Thread Edit Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ThreadEditCog(AuditCog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread) -> None:
        if after.parent and self.is_directorship_channel(after.parent):
            return

        log_channel = await self.get_log_channel(after.guild)
        if not log_channel:
            return

        changes: list[
            tuple[
                str,
                str | int | None,
                str | int | None,
            ]
        ] = []

        if before.name != after.name:
            changes.append(("Name", before.name, after.name))

        if before.archived != after.archived:
            changes.append(("Archived", str(before.archived), str(after.archived)))

        if before.locked != after.locked:
            changes.append(("Locked", str(before.locked), str(after.locked)))

        if before.auto_archive_duration != after.auto_archive_duration:
            changes.append((
                "Auto Archive Duration",
                f"{before.auto_archive_duration} min",
                f"{after.auto_archive_duration} min",
            ))

        if not changes:
            return

        embed = discord.Embed(
            title = "Thread Updated",
            color=COLOR_BLURPLE,
            timestamp = datetime.now(UTC),
        )

        _ = embed.add_field(
            name = "Thread",
            value = f"`{after.name}`\n`{after.id}`",
            inline = False,
        )

        change_name: str
        before_val: str | int | None
        after_val:  str | int | None
        for change_name, before_val, after_val in changes:
            _ = embed.add_field(
                name = f"{change_name} Changed",
                value = f"**Before:** `{before_val}`\n**After:** `{after_val}`",
                inline = False,
            )

        await self._enqueue(log_channel, embed)
