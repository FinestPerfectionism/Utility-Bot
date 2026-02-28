import discord
from discord.ext import commands

from typing import Any

from core.utils import (
    channel_display,
    format_attachments,
)
from core.state import AUTOMOD_DELETIONS

from constants import (
    DIRECTORSHIP_CATEGORY_ID,

    MESSAGE_DELETE_LOG_CHANNEL_ID,

    COLOR_RED,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Message Deletion
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
class MessageDeleteHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def is_directorship_channel(self, channel):
        if hasattr(channel, 'category_id') and channel.category_id == DIRECTORSHIP_CATEGORY_ID:
            return True
        if hasattr(channel, 'category') and channel.category and channel.category.id == DIRECTORSHIP_CATEGORY_ID:
            return True
        if hasattr(channel, 'parent') and channel.parent:
            if hasattr(channel.parent, 'category_id') and channel.parent.category_id == DIRECTORSHIP_CATEGORY_ID:
                return True
            if hasattr(channel.parent, 'category') and channel.parent.category and channel.parent.category.id == DIRECTORSHIP_CATEGORY_ID:
                return True
        return False

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.guild is None:
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
                if not isinstance(entry.target, (discord.User, discord.Member)):
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
            deleter = "Utility Bot: Auto-Moderation"
            AUTOMOD_DELETIONS.discard(message.id)
        elif deleter == "Unknown":
            deleter = "Self"
            
        embed = discord.Embed(
            title="Message Deleted",
            color=COLOR_RED,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(
            name="Author",
            value=f"`{message.author}`\n`{message.author.id}`",
            inline=True,
        )
        embed.add_field(
            name="Deleted By",
            value=deleter,
            inline=True,
        )
        embed.add_field(
            name="Channel",
            value=channel_display(message.channel),
            inline=True,
        )
        content = message.content or "[No content]"
        embed.add_field(
            name="Content",
            value=content[:1021] + "..." if len(content) > 1024 else content,
            inline=True,
        )
        embed.add_field(
            name="Attachments",
            value=format_attachments(message.attachments),
            inline=True,
        )
        await log_channel.send(embed=embed)

        embed.set_footer(text="Please note that the \"Deleted By\" section guesses by checking the audit log, and may not always be accurate")
        
async def setup(bot: commands.Bot):
    await bot.add_cog(MessageDeleteHandler(bot))