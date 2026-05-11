from asyncio import Queue

import discord
from discord import ForumChannel, TextChannel, Thread
from discord.ui import LayoutView, Separator

from constants import STAFF_PROPOSALS_CHANNEL_ID

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Helpers Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Layout Helpers
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class VLSeparator(Separator[LayoutView]):
    def __init__(self):
        super().__init__(
            visible = True,
            spacing = discord.SeparatorSpacing.large,
        )

class VSSeparator(Separator[LayoutView]):
    def __init__(self):
        super().__init__(
            visible = True,
            spacing = discord.SeparatorSpacing.small,
        )

class LSeparator(Separator[LayoutView]):
    def __init__(self):
        super().__init__(
            visible = False,
            spacing = discord.SeparatorSpacing.large,
        )

class SSeparator(Separator[LayoutView]):
    def __init__(self):
        super().__init__(
            visible = False,
            spacing = discord.SeparatorSpacing.small,
        )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Queue Helper
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

MESSAGE_LOG_QUEUE : Queue[discord.Embed] = Queue()

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Channel Display Helper
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

def channel_display(channel : discord.abc.Messageable | discord.abc.GuildChannel) -> str:
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

def format_attachments(attachments : list[discord.Attachment]) -> str:
    if not attachments:
        return "None"
    return "\n".join(f"- {a.filename} ({a.url})" for a in attachments)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Proposal Helpers
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

def resolve_forum_tags(
    forum   : discord.ForumChannel,
    tag_ids : list[int],
) -> list[discord.ForumTag]:
    resolved : list[discord.ForumTag] = []

    for tag_id in tag_ids:
        tag = forum.get_tag(tag_id)
        if tag is None:
            string = f"Forum tag not found: {tag_id}"
            raise ValueError(string)
        resolved.append(tag)

    return resolved

def assert_forum_thread(interaction : discord.Interaction) -> tuple[discord.Thread, discord.ForumChannel]:
    if not isinstance(interaction.channel, discord.Thread):
        string = "This command must be used inside a staff proposal thread."
        raise TypeError(string)

    thread: discord.Thread = interaction.channel

    if thread.parent_id != STAFF_PROPOSALS_CHANNEL_ID:
        string = "This command must be used inside #staff-proposals."
        raise ValueError(string)

    if not isinstance(thread.parent, discord.ForumChannel):
        string = "This thread is not attached to a forum."
        raise TypeError(string)

    return thread, thread.parent

def resolve_single_tag(
    forum  : discord.ForumChannel,
    tag_id : int,
    label  : str,
) -> discord.ForumTag:
    try:
        return resolve_forum_tags(forum, [tag_id])[0]
    except ValueError:
        raise ValueError(label) from None

def format_body(reason: str, notes: str | None) -> str:
    body = f"-# {reason}"
    if notes:
        body += f"\n-# **Notes:** {notes}"
    return body
