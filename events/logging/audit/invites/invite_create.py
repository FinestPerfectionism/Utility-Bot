import discord
from discord.ext import commands
from datetime import datetime, UTC

from constants import COLOR_GREEN
from .._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Invite Create Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class InviteCreateCog(AuditCog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite) -> None:
        if not isinstance(invite.guild, discord.Guild):
            return

        log_channel: discord.TextChannel | None = await self.get_log_channel(invite.guild)
        if not log_channel:
            return

        embed: discord.Embed = discord.Embed(
            title="Invite Created",
            color=COLOR_GREEN,
            timestamp = datetime.now(UTC)
        )

        embed.add_field(name="Code", value = f"`{invite.code}`", inline = True)

        channel_name: str = getattr(invite.channel, 'name', 'Unknown Channel')
        channel_id: str = str(getattr(invite.channel, 'id', 'Unknown ID'))

        embed.add_field(
            name="Channel",
            value = f"`{channel_name}`\n`{channel_id}`",
            inline = True
        )

        if invite.inviter:
            embed.add_field(
                name="Created By",
                value = f"`{invite.inviter}`\n`{invite.inviter.id}`",
                inline = False
            )

        embed.add_field(
            name="Expires In",
            value = f"{invite.max_age}s" if invite.max_age else "Never",
            inline = True
        )
        embed.add_field(
            name="Max Uses",
            value = str(invite.max_uses) if invite.max_uses else "Unlimited",
            inline = True
        )
        embed.add_field(name="Temporary", value = str(invite.temporary), inline = True)

        await self._enqueue(log_channel, embed)
