import discord
from discord.ext import commands

from core.utils import (
    channel_display,
    format_attachments,
    Messageable
)

from constants import (
    MESSAGE_EDIT_LOG_CHANNEL_ID,
    COLOR_GREY,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Message Editing
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class MessageEditHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_edit(
        self,
        before: discord.Message,
        after: discord.Message,
    ):
        if before.author.bot or before.guild is None:
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
            name="Editor",
            value=f"{before.author} ({before.author.id})",
            inline=False,
        )
        embed.add_field(
            name="Channel",
            value=channel_display(before.channel),
            inline=False,
        )

        before_text = before.content or "[No content]"
        after_text = after.content or "[No content]"

        embed.add_field(
            name="Before",
            value=before_text[:1021] + "..." if len(before_text) > 1024 else before_text,
            inline=False,
        )
        embed.add_field(
            name="After",
            value=after_text[:1021] + "..." if len(after_text) > 1024 else after_text,
            inline=False,
        )
        embed.add_field(
            name="Attachments (After)",
            value=format_attachments(after.attachments),
            inline=False,
        )

        await log_channel.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(MessageEditHandler(bot))