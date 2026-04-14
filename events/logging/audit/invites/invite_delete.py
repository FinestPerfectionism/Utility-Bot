from datetime import UTC, datetime

import discord
from discord.ext import commands

from constants import COLOR_RED
from events.logging.audit._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Invite Delete Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class InviteDeleteCog(AuditCog):
    def __init__(self, bot : commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite) -> None:
        if not isinstance(invite.guild, discord.Guild):
            return

        log_channel: discord.TextChannel | None = await self.get_log_channel(invite.guild)
        if not log_channel:
            return

        embed: discord.Embed = discord.Embed(
            title     = "Invite Deleted",
            color     = COLOR_RED,
            timestamp = datetime.now(UTC),
        )

        _ = embed.add_field(name = "Code", value = f"`{invite.code}`", inline = True)

        channel_name: str = getattr(invite.channel, "name", "Unknown Channel")
        channel_id: str = str(getattr(invite.channel, "id", "Unknown ID"))

        _ = embed.add_field(
            name   = "Channel",
            value  = f"`{channel_name}`\n`{channel_id}`",
            inline = True,
        )

        if invite.uses is not None:
            _ = embed.add_field(name = "Uses", value = str(invite.uses), inline = True)

        await self._enqueue(log_channel, embed)
