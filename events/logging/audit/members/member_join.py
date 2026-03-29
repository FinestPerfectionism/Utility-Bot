import discord
from discord.ext import commands
from datetime import datetime, UTC

from constants import COLOR_GREEN
from .._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Member Join Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class MemberJoinCog(AuditCog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        log_channel = await self.get_log_channel(member.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Member Joined",
            color=COLOR_GREEN,
            timestamp = datetime.now(UTC)
        )

        embed.add_field(
            name="Member",
            value = f"`{member}`\n`{member.id}`",
            inline = True
        )
        embed.add_field(
            name="Account Created",
            value = discord.utils.format_dt(member.created_at, style='R'),
            inline = True
        )

        await self._enqueue(log_channel, embed)
