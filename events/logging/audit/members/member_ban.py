from datetime import UTC, datetime

import discord
from discord.ext import commands

from constants import COLOR_RED

from .._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Member Ban Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class MemberBanCog(AuditCog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User) -> None:
        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return

        executor = await self.get_executor(guild, discord.AuditLogAction.ban, user.id)

        embed = discord.Embed(
            title = "Member Banned",
            color = COLOR_RED,
            timestamp = datetime.now(UTC),
        )

        _ = embed.add_field(
            name = "User",
            value = f"`{user}`\n`{user.id}`",
            inline = True,
        )

        if executor:
            _ = embed.add_field(
                name = "Banned By",
                value = f"`{executor}`\n`{executor.id}`",
                inline = False,
            )

        await self._enqueue(log_channel, embed)
