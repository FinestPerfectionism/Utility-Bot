import discord
from discord.ext import commands
from datetime import datetime, UTC

from constants import COLOR_GREEN
from .._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Role Create Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class RoleCreateCog(AuditCog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        log_channel = await self.get_log_channel(role.guild)
        if not log_channel:
            return

        executor = await self.get_executor(role.guild, discord.AuditLogAction.role_create, role.id)

        embed = discord.Embed(
            title="Role Created",
            color=COLOR_GREEN,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(
            name="Role",
            value=f"`{role.name}`\n`{role.id}`",
            inline=True
        )
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Position", value=str(role.position), inline=True)
        embed.add_field(name="Hoisted", value=str(role.hoist), inline=True)
        embed.add_field(name="Mentionable", value=str(role.mentionable), inline=True)

        if executor:
            embed.add_field(
                name="Created By",
                value=f"`{executor}`\n`{executor.id}`",
                inline=False
            )

        permissions_text = self.format_permissions(role.permissions)
        if len(permissions_text) > 1024:
            permissions_text = permissions_text[:1021] + "..."
        embed.add_field(name="Permissions", value=permissions_text, inline=False)

        await self._enqueue(log_channel, embed)
