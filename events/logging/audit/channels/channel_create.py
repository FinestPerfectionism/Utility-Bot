import discord
from discord.ext import commands
from datetime import datetime, UTC

from constants import COLOR_GREEN
from .._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Channel Create Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ChannelCreateCog(AuditCog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel) -> None:
        if self.is_directorship_channel(channel):
            return

        log_channel = await self.get_log_channel(channel.guild)
        if not log_channel:
            return

        executor = await self.get_executor(channel.guild, discord.AuditLogAction.channel_create, channel.id)

        embed = discord.Embed(
            title="Channel Created",
            color=COLOR_GREEN,
            timestamp=datetime.now(UTC)
        )

        channel_type = str(channel.type).replace('_', ' ').title()
        embed.add_field(
            name="Channel",
            value=f"`{channel.name}`\n`{channel.id}`",
            inline=True
        )
        embed.add_field(name="Type", value=channel_type, inline=True)

        if hasattr(channel, 'category') and channel.category:
            embed.add_field(
                name="Category",
                value=f"`{channel.category.name}`\n`{channel.category.id}`",
                inline=True
            )

        if hasattr(channel, 'position'):
            embed.add_field(name="Position", value=str(channel.position), inline=True)

        if executor:
            embed.add_field(
                name="Created By",
                value=f"`{executor}`\n`{executor.id}`",
                inline=False
            )

        await self._enqueue(log_channel, embed)