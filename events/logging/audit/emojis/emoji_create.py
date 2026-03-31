from collections.abc import Sequence
from datetime import UTC, datetime

import discord
from discord.ext import commands

from constants import COLOR_GREEN

from .._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Emoji Create Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class EmojiAddCog(AuditCog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild: discord.Guild, before: Sequence[discord.Emoji], after: Sequence[discord.Emoji]) -> None:
        before_ids = {emoji.id for emoji in before}
        added = [emoji for emoji in after if emoji.id not in before_ids]

        if not added:
            return

        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return

        executor = await self.get_executor(guild, discord.AuditLogAction.emoji_create)

        embed = discord.Embed(
            title = "Emoji Added",
            color = COLOR_GREEN,
            timestamp = datetime.now(UTC),
        )

        for emoji in added:
            _ = embed.add_field(
                name = "Emoji",
                value = f"`{emoji.name}`\n`{emoji.id}`\n{emoji}",
                inline = True,
            )

        if executor:
            _ = embed.add_field(
                name = "Added By",
                value = f"`{executor}`\n`{executor.id}`",
                inline = False,
            )

        await self._enqueue(log_channel, embed)
