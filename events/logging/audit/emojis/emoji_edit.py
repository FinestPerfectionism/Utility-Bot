from collections.abc import Sequence
from datetime import UTC, datetime

import discord
from discord.ext import commands

from constants import COLOR_BLURPLE
from events.logging.audit._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Emoji Edit Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class EmojiEditCog(AuditCog):
    def __init__(self, bot : commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild: discord.Guild, before: Sequence[discord.Emoji], after: Sequence[discord.Emoji]) -> None:
        before_map = {emoji.id: emoji for emoji in before}
        after_map = {emoji.id: emoji for emoji in after}

        edited = [
            (before_map[eid], after_map[eid])
            for eid in before_map.keys() & after_map.keys()
            if before_map[eid].name != after_map[eid].name
        ]

        if not edited:
            return

        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return

        executor = await self.get_executor(guild, discord.AuditLogAction.emoji_update)

        embed = discord.Embed(
            title = "Emoji Edited",
            color = COLOR_BLURPLE,
            timestamp = datetime.now(UTC),
        )

        for before_emoji, after_emoji in edited:
            _ = embed.add_field(
                name = "Emoji",
                value = f"`{after_emoji.id}`\n{after_emoji}",
                inline = False,
            )
            _ = embed.add_field(
                name = "Name Changed",
                value = f"**Before:** `{before_emoji.name}`\n**After:** `{after_emoji.name}`",
                inline = False,
            )

        if executor:
            _ = embed.add_field(
                name = "Edited By",
                value = f"`{executor}`\n`{executor.id}`",
                inline = False,
            )

        await self._enqueue(log_channel, embed)
