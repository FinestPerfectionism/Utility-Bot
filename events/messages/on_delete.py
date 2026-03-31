from typing import Any

import discord
from discord.ext import commands

from constants import (
    COLOR_RED,
    CONTESTED_EMOJI_ID,
    COUNTING_CHANNEL_ID,
    DIRECTORSHIP_CATEGORY_ID,
    MESSAGE_DELETE_LOG_CHANNEL_ID,
)
from core.state import AUTOMOD_DELETIONS
from core.utils import (
    channel_display,
    format_attachments,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Message Deletion
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class MessageDeleteHandler(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def is_directorship_channel(self, channel: discord.abc.Messageable) -> bool:
        return (
            isinstance(channel, discord.TextChannel | discord.VoiceChannel | discord.StageChannel)
            and channel.category_id == DIRECTORSHIP_CATEGORY_ID
        ) or (
            isinstance(channel, discord.Thread)
            and getattr(channel.parent, "category_id", None) == DIRECTORSHIP_CATEGORY_ID
        )

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None:
            return

        if message.channel.id == COUNTING_CHANNEL_ID:
            from events.messages.on_send import MessageSendHandler
            counting_cog = self.bot.get_cog("MessageSendHandler")
            if isinstance(counting_cog, MessageSendHandler):
                last_id: int | None = counting_cog.state["last_message_id"]
                if last_id is not None and message.id == last_id:
                    _ = await message.channel.send(
                        f"{CONTESTED_EMOJI_ID} **Warning!**\n"
                        f"{message.author.name} has deleted their message. The next number is {counting_cog.state['count'] + 1}.",
                    )
            return

        if self.is_directorship_channel(message.channel):
            return

        log_channel = message.guild.get_channel(MESSAGE_DELETE_LOG_CHANNEL_ID)
        if not isinstance(log_channel, discord.abc.Messageable):
            return

        deleter = "Unknown"
        try:
            async for entry in message.guild.audit_logs(
                limit=5,
                action=discord.AuditLogAction.message_delete,
            ):
                if not isinstance(entry.target, discord.User | discord.Member):
                    continue
                if entry.target.id != message.author.id:
                    continue
                extra: Any = entry.extra
                channel = getattr(extra, "channel", None)
                if not isinstance(channel, discord.abc.GuildChannel):
                    continue
                if channel.id != message.channel.id:
                    continue
                if (discord.utils.utcnow() - entry.created_at).total_seconds() > 5:
                    continue
                if entry.user:
                    deleter = f"`{entry.user}`\n`{entry.user.id}`"
                break
        except (discord.Forbidden, discord.HTTPException):
            pass

        if message.id in AUTOMOD_DELETIONS:
            deleter = "UB Auto-Moderation"
            AUTOMOD_DELETIONS.discard(message.id)
        elif deleter == "Unknown":
            deleter = "Self"

        embed = discord.Embed(
            title     = "Message Deleted",
            color     = COLOR_RED,
            timestamp = discord.utils.utcnow(),
        )
        _ = embed.add_field(
            name   = "Author",
            value  = f"`{message.author}`\n`{message.author.id}`",
            inline = True,
        )
        _ = embed.add_field(
            name   = "Deleted By",
            value  = deleter,
            inline = True,
        )
        _ = embed.add_field(
            name   = "Channel",
            value  = channel_display(message.channel),
            inline = True,
        )
        content = message.content or "[No content, likely an embed or attachment]"
        display_content = (content[:1021] + "...") if len(content) > 1024 else content
        _ = embed.add_field(
            name   = "Content",
            value  = display_content,
            inline = True,
        )
        _ = embed.add_field(
            name   = "Attachments",
            value  = format_attachments(message.attachments),
            inline = True,
        )
        _ = embed.set_footer(text='Please note that the "Deleted By" section guesses by checking the audit log, and may not always be accurate')
        _ = await log_channel.send(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MessageDeleteHandler(bot))
