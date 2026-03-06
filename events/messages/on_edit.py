import discord
from discord.ext import commands

from core.utils import (
    channel_display,
    format_attachments,
    Messageable
)

from constants import (
    DIRECTORSHIP_CATEGORY_ID,

    MESSAGE_EDIT_LOG_CHANNEL_ID,

    COLOR_GREY,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Message Editing
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class MessageEditHandler(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def is_directorship_channel(self, channel: discord.abc.Messageable) -> bool:
        return (
            isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel))
            and channel.category_id == DIRECTORSHIP_CATEGORY_ID
        ) or (
            isinstance(channel, discord.Thread)
            and getattr(channel.parent, "category_id", None) == DIRECTORSHIP_CATEGORY_ID
        )

    @commands.Cog.listener()
    async def on_message_edit(
        self,
        before: discord.Message,
        after: discord.Message,
    ) -> None:
        
        if before.author.bot or before.guild is None:
            return

        if self.is_directorship_channel(before.channel):
            return

        before_files = [a.url for a in before.attachments]
        after_files = [a.url for a in after.attachments]
        
        if before.content == after.content and before_files == after_files:
            return
            
        log_channel = before.guild.get_channel(MESSAGE_EDIT_LOG_CHANNEL_ID)
        if not isinstance(log_channel, Messageable):
            return
            
        embed = discord.Embed(
            title="Message Edited",
            color=COLOR_GREY,
            timestamp=after.edited_at or discord.utils.utcnow(),
        )
        embed.add_field(
            name="Edited By",
            value=f"`{before.author}`\n`{before.author.id}`",
            inline=True,
        )
        embed.add_field(
            name="Channel",
            value=channel_display(before.channel),
            inline=True,
        )
        before_text = before.content or "[No content]"
        after_text = after.content or "[No content]"
        embed.add_field(
            name="Before",
            value=before_text[:1021] + "..." if len(before_text) > 1024 else before_text,
            inline=True,
        )
        embed.add_field(
            name="After",
            value=after_text[:1021] + "..." if len(after_text) > 1024 else after_text,
            inline=True,
        )
        embed.add_field(
            name="Attachments (After)",
            value=format_attachments(after.attachments),
            inline=True,
        )
        await log_channel.send(embed=embed)

        await self.bot.process_commands(after)
        
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MessageEditHandler(bot))