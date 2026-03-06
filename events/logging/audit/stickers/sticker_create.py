import discord
from discord.ext import commands
from datetime import datetime, UTC

from constants import COLOR_GREEN
from .._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Sticker Create Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class StickerAddCog(AuditCog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild: discord.Guild, before, after) -> None:
        before_ids = {sticker.id for sticker in before}
        added = [sticker for sticker in after if sticker.id not in before_ids]

        if not added:
            return

        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return

        executor = await self.get_executor(guild, discord.AuditLogAction.sticker_create)

        embed = discord.Embed(
            title="Sticker Added",
            color=COLOR_GREEN,
            timestamp=datetime.now(UTC)
        )

        for sticker in added:
            embed.add_field(
                name="Sticker",
                value=f"`{sticker.name}`\n`{sticker.id}`",
                inline=True
            )

        if executor:
            embed.add_field(
                name="Added By",
                value=f"`{executor}`\n`{executor.id}`",
                inline=False
            )

        await self._enqueue(log_channel, embed)
