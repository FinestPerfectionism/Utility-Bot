import discord
from discord.ext import commands
import asyncio
from datetime import datetime, UTC

from constants import COLOR_GREEN, COLOR_RED, COLOR_BLURPLE
from .._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Server Integrations Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class IntegrationsCog(AuditCog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_guild_integrations_update(self, guild: discord.Guild) -> None:
        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return

        executor = None
        action_type = None
        target_name = None

        try:
            await asyncio.sleep(0.5)
            async for entry in guild.audit_logs(limit=5):
                if entry.action in [
                    discord.AuditLogAction.integration_create,
                    discord.AuditLogAction.integration_update,
                    discord.AuditLogAction.integration_delete
                ]:
                    executor = entry.user
                    action_type = entry.action
                    if hasattr(entry.target, 'name'):
                        target_name = entry.target.name
                    break
        except discord.HTTPException as e:
            print(f"Error fetching integration audit log: {e}")

        if action_type == discord.AuditLogAction.integration_create:
            title = "Integration Added"
            color = COLOR_GREEN
        elif action_type == discord.AuditLogAction.integration_delete:
            title = "Integration Removed"
            color = COLOR_RED
        else:
            title = "Integration Updated"
            color = COLOR_BLURPLE

        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(
            name="Server",
            value=f"`{guild.name}`\n`{guild.id}`",
            inline=False
        )

        if target_name:
            embed.add_field(name="Integration", value=f"`{target_name}`", inline=False)

        if executor:
            embed.add_field(
                name="Action By",
                value=f"`{executor}`\n`{executor.id}`",
                inline=False
            )

        await self._enqueue(log_channel, embed)
