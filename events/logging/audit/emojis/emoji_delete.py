import discord
from discord.ext import commands
from datetime import datetime, UTC

from constants import COLOR_RED
from .._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Emoji Delete Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class EmojiDeleteCog(AuditCog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild: discord.Guild, before, after) -> None:
        after_ids = {emoji.id for emoji in after}
        removed = [emoji for emoji in before if emoji.id not in after_ids]

        if not removed:
            return

        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return

        executor = await self.get_executor(guild, discord.AuditLogAction.emoji_delete)

        embed = discord.Embed(
            title="Emoji Deleted",
            color=COLOR_RED,
            timestamp=datetime.now(UTC)
        )

        for emoji in removed:
            embed.add_field(
                name="Emoji",
                value=f"`{emoji.name}`\n`{emoji.id}`",
                inline=True
            )

        if executor:
            embed.add_field(
                name="Deleted By",
                value=f"`{executor}`\n`{executor.id}`",
                inline=False
            )

        await self._enqueue(log_channel, embed)
