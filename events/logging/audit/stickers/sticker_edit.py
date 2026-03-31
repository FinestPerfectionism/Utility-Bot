import discord
from discord.ext import commands
from datetime import datetime, UTC

from constants import COLOR_BLURPLE
from .._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Sticker Edit Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class StickerEditCog(AuditCog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild: discord.Guild, before: list[discord.GuildSticker], after: list[discord.GuildSticker]) -> None:
        before_map = {sticker.id: sticker for sticker in before}
        after_map = {sticker.id: sticker for sticker in after}

        edited = [
            (before_map[sid], after_map[sid])
            for sid in before_map.keys() & after_map.keys()
            if before_map[sid].name != after_map[sid].name
            or before_map[sid].description != after_map[sid].description
        ]

        if not edited:
            return

        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return

        executor = await self.get_executor(guild, discord.AuditLogAction.sticker_update)

        embed = discord.Embed(
            title = "Sticker Edited",
            color = COLOR_BLURPLE,
            timestamp = datetime.now(UTC)
        )

        for before_sticker, after_sticker in edited:
            _ = embed.add_field(
                name = "Sticker",
                value = f"`{after_sticker.id}`",
                inline = False
            )

            if before_sticker.name != after_sticker.name:
                _ = embed.add_field(
                    name = "Name Changed",
                    value = f"**Before:** `{before_sticker.name}`\n**After:** `{after_sticker.name}`",
                    inline = False
                )

            if before_sticker.description != after_sticker.description:
                _ = embed.add_field(
                    name = "Description Changed",
                    value = f"**Before:** `{before_sticker.description or 'None'}`\n**After:** `{after_sticker.description or 'None'}`",
                    inline = False
                )

        if executor:
            _ = embed.add_field(
                name = "Edited By",
                value = f"`{executor}`\n`{executor.id}`",
                inline = False
            )

        await self._enqueue(log_channel, embed)
