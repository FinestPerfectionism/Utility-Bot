import discord
from discord.ext import commands
import asyncio
from datetime import datetime, UTC

from constants import COLOR_YELLOW
from .._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Member Remove Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class MemberRemoveCog(AuditCog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        log_channel = await self.get_log_channel(member.guild)
        if not log_channel:
            return

        executor = None
        was_kicked = False

        try:
            await asyncio.sleep(0.5)
            async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
                if entry.target.id == member.id:
                    executor = entry.user
                    was_kicked = True
                    break
        except discord.HTTPException as e:
            print(f"Error fetching audit log: {e}")

        embed = discord.Embed(
            title="Member Kicked" if was_kicked else "Member Left",
            color=COLOR_YELLOW,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(
            name="Member",
            value=f"`{member}`\n`{member.id}`",
            inline=True
        )

        if member.joined_at:
            embed.add_field(
                name="Joined Server",
                value=discord.utils.format_dt(member.joined_at, style='R'),
                inline=True
            )

        if executor:
            embed.add_field(
                name="Kicked By",
                value=f"`{executor}`\n`{executor.id}`",
                inline=False
            )

        await self._enqueue(log_channel, embed)
