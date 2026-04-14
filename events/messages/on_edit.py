import contextlib
import re

import discord
from discord.ext import commands

from constants import (
    COLOR_GREY,
    CONTESTED_EMOJI_ID,
    COUNTING_CHANNEL_ID,
    DIRECTORSHIP_CATEGORY_ID,
    MESSAGE_EDIT_LOG_CHANNEL_ID,
    WAPPLE_CHAIN_CHANNEL_ID,
)
from core.utils import Messageable, channel_display, format_attachments

WAPPLE_EMOJIS = [
    "<:Wapple:1474915842071335098>",
    "<:WappleYellow:1474916545158189108>",
    "<:WappleGreen:1474916731532087569>",
    "<:WappleBlue:1474916471984623842>",
    "<:WappleHartwellWhite:1474916613232001117>",
    "<:applebruh:1478244953892192357>",
    "<:ex:1476672300467093626>",
    "<:susapple:1483533565005402144>",
]

WAPPLE_PATTERN = re.compile(rf"^({'|'.join(map(re.escape, WAPPLE_EMOJIS))}| )+$")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Message Editing
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class MessageEditHandler(commands.Cog):
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
    async def on_message_edit(
        self,
        before: discord.Message,
        after: discord.Message,
    ) -> None:

        if before.author.bot or before.guild is None:
            return

        if before.channel.id == COUNTING_CHANNEL_ID:
            from events.messages.on_send import MessageSendHandler
            counting_cog = self.bot.get_cog("MessageSendHandler")
            if isinstance(counting_cog, MessageSendHandler):
                last_id : int | None = counting_cog.state["last_message_id"]
                if (
                    last_id is not None
                    and before.id == last_id
                    and before.content != after.content
                ):
                    _ = await after.channel.send(
                        f"{CONTESTED_EMOJI_ID} **Warning!**\n"
                        f"{before.author.name} has edited their message. The next number is {counting_cog.state['count'] + 1}.",
                    )
            return

        if before.channel.id == WAPPLE_CHAIN_CHANNEL_ID:
            content = (after.content or "").strip()
            if not WAPPLE_PATTERN.fullmatch(content):
                with contextlib.suppress(discord.HTTPException):
                    await after.delete()
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
            title     = "Message Edited",
            color     = COLOR_GREY,
            timestamp = after.edited_at or discord.utils.utcnow(),
        )
        _ = embed.add_field(
            name   = "Edited By",
            value  = f"`{before.author}`\n`{before.author.id}`",
            inline = True,
        )
        _ = embed.add_field(
            name   = "Channel",
            value  = channel_display(before.channel),
            inline = True,
        )
        before_text = before.content or "[No content]"
        after_text = after.content or "[No content]"
        n_1024 = 1024
        _ = embed.add_field(
            name   = "Before",
            value  = before_text[:1021] + "..." if len(before_text) > n_1024 else before_text,
            inline = True,
        )
        _ = embed.add_field(
            name   = "After",
            value  = after_text[:1021] + "..." if len(after_text) > n_1024 else after_text,
            inline = True,
        )
        _ = embed.add_field(
            name   = "Attachments (After)",
            value  = format_attachments(after.attachments),
            inline = True,
        )
        _ = await log_channel.send(embed = embed)
        await self.bot.process_commands(after)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MessageEditHandler(bot))
