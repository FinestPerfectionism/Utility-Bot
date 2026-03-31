import discord
from discord.ext import commands
from datetime import datetime, UTC

from constants import COLOR_RED
from .._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Role Delete Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class RoleDeleteCog(AuditCog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        log_channel = await self.get_log_channel(role.guild)
        if not log_channel:
            return

        executor = await self.get_executor(role.guild, discord.AuditLogAction.role_delete, role.id)

        embed = discord.Embed(
            title = "Role Deleted",
            color = COLOR_RED,
            timestamp = datetime.now(UTC)
        )

        _ = embed.add_field(
            name = "Role",
            value = f"`{role.name}`\n`{role.id}`",
            inline = True
        )
        _ = embed.add_field(name = "Color", value = str(role.color), inline = True)
        _ = embed.add_field(name = "Position", value = str(role.position), inline = True)

        if executor:
            _ = embed.add_field(
                name = "Deleted By",
                value = f"`{executor}`\n`{executor.id}`",
                inline = False
            )

        await self._enqueue(log_channel, embed)
