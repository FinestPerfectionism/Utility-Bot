import discord
from discord.ext import commands
from datetime import datetime, UTC

from constants import COLOR_RED
from .._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Sticker Delete Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class StickerDeleteCog(AuditCog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild: discord.Guild, before: list[discord.GuildSticker], after: list[discord.GuildSticker]) -> None:
        after_ids = {sticker.id for sticker in after}
        removed = [sticker for sticker in before if sticker.id not in after_ids]

        if not removed:
            return

        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return

        executor = await self.get_executor(guild, discord.AuditLogAction.sticker_delete)

        embed = discord.Embed(
            title="Sticker Deleted",
            color=COLOR_RED,
            timestamp = datetime.now(UTC)
        )

        for sticker in removed:
            embed.add_field(
                name="Sticker",
                value = f"`{sticker.name}`\n`{sticker.id}`",
                inline = True
            )

        if executor:
            embed.add_field(
                name="Deleted By",
                value = f"`{executor}`\n`{executor.id}`",
                inline = False
            )

        await self._enqueue(log_channel, embed)
