import discord
from discord import (
    Thread,
    TextChannel,
    ForumChannel
)
from discord.abc import GuildChannel, Messageable

from asyncio import Queue
import re
from datetime import timedelta
from typing import cast

from constants import (
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,
    BOT_OWNER_ID,
    STAFF_PROPOSALS_CHANNEL_ID,
    COLOR_YELLOW,
    COLOR_RED
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Helpers Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Queue Helper
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻ 

MESSAGE_LOG_QUEUE: Queue[discord.Embed] = Queue()

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Messageable Helper
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

__all__ = (
    "GuildChannel",
    "Messageable",
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Channel Display Helper
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

def channel_display(channel) -> str:
    if isinstance(channel, Thread):
        parent = channel.parent
        if isinstance(parent, ForumChannel):
            return f"{parent.mention} → {channel.mention}"
        if parent is not None:
            return f"{parent.mention} → {channel.mention}"
        return channel.mention

    if isinstance(channel, TextChannel):
        return channel.mention

    return "Unknown Channel"

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Format Attachments Helper
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

def format_attachments(
    attachments: list[discord.Attachment],
) -> str:
    if not attachments:
        return "None"
    return "\n".join(f"- {a.filename} ({a.url})" for a in attachments)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Resolve Forum Tags Helper
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

def resolve_forum_tags(
    forum: discord.ForumChannel,
    tag_ids: list[int],
) -> list[discord.ForumTag]:
    resolved: list[discord.ForumTag] = []

    for tag_id in tag_ids:
        tag = forum.get_tag(tag_id)
        if tag is None:
            raise ValueError(f"Forum tag not found: {tag_id}")
        resolved.append(tag)

    return resolved

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Parse Duration Helper
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

_TIME_REGEX = re.compile(r"(\d+)\s*(mo|d|h|m|s)", re.IGNORECASE)

def parse_duration(input_str: str) -> timedelta | None:
    matches = _TIME_REGEX.findall(input_str)
    if not matches:
        return None

    total_seconds = 0

    for value, unit in matches:
        value = int(value)
        unit = unit.lower()

        if unit == "mo":
            total_seconds += value * 28 * 24 * 60 * 60
        elif unit == "d":
            total_seconds += value * 24 * 60 * 60
        elif unit == "h":
            total_seconds += value * 60 * 60
        elif unit == "m":
            total_seconds += value * 60
        elif unit == "s":
            total_seconds += value

    return timedelta(seconds=total_seconds)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Error Helpers
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class MinorError(discord.ui.LayoutView):
    def __init__(self, texts: list[str], subtitle: str = "Invalid argument.", title: str = "Error!"):
        super().__init__()

        container = discord.ui.Container(accent_color=COLOR_YELLOW)

        container.add_item(
            discord.ui.TextDisplay(
                content=f"### {CONTESTED_EMOJI_ID} {title}\n-# {subtitle}"
            )
        )

        for i, text in enumerate(texts):
            if i > 0:
                container.add_item(
                    discord.ui.Separator(
                        visible=True,
                        spacing=discord.SeparatorSpacing.small
                    )
                )
            container.add_item(discord.ui.TextDisplay(content=text))

        self.add_item(container)


class MajorError(discord.ui.LayoutView):
    def __init__(
        self,
        texts: list[str],
        subtitle: str = f"Invalid IDs/Operation. Contact <@{BOT_OWNER_ID}>.",
        title: str = "Error!"
    ):
        super().__init__()

        container = discord.ui.Container(accent_color=COLOR_RED)

        container.add_item(
            discord.ui.TextDisplay(
                content=f"### {DENIED_EMOJI_ID} {title}\n-# {subtitle}"
            )
        )

        for i, text in enumerate(texts):
            if i > 0:
                container.add_item(
                    discord.ui.Separator(
                        visible=True,
                        spacing=discord.SeparatorSpacing.small
                    )
                )
            container.add_item(discord.ui.TextDisplay(content=text))

        self.add_item(container)


async def send_minor_error(
    interaction: discord.Interaction,
    texts: list[str] | str,
    subtitle: str = "Invalid argument.",
    title: str = "Error!"
):
    if isinstance(texts, str):
        texts = [texts]

    view = cast(discord.ui.View, MinorError(texts, subtitle, title))

    if interaction.response.is_done():
        await interaction.followup.send(
            content=" ",
            view=view,
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            content=" ",
            view=view,
            ephemeral=True,
        )


async def send_major_error(
    interaction: discord.Interaction,
    texts: list[str] | str,
    subtitle: str = f"Invalid IDs/Operation. Contact <@{BOT_OWNER_ID}>.",
    title: str = "Error!"
):
    if isinstance(texts, str):
        texts = [texts]

    view = cast(discord.ui.View, MajorError(texts, subtitle, title))

    if interaction.response.is_done():
        await interaction.followup.send(
            content=" ",
            view=view,
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            content=" ",
            view=view,
            ephemeral=True,
        )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Proposal Helpers
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

def assert_forum_thread(
    interaction: discord.Interaction
) -> tuple[discord.Thread, discord.ForumChannel]:
    if not isinstance(interaction.channel, discord.Thread):
        raise ValueError(
            "This command must be used inside a staff proposal thread."
        )

    thread: discord.Thread = interaction.channel

    if thread.parent_id != STAFF_PROPOSALS_CHANNEL_ID:
        raise ValueError(
            "This command must be used inside #staff-proposals."
        )

    if not isinstance(thread.parent, discord.ForumChannel):
        raise ValueError(
            "This thread is not attached to a forum."
        )

    return thread, thread.parent

def resolve_single_tag(
    forum: discord.ForumChannel,
    tag_id: int,
    label: str,
) -> discord.ForumTag:
    try:
        return resolve_forum_tags(forum, [tag_id])[0]
    except ValueError:
        raise ValueError(label)

def format_body(reason: str, notes: str | None):
    body = f"-# {reason}"
    if notes:
        body += f"\n-# **Notes:** {notes}"
    return body