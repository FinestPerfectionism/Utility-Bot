from asyncio import Queue

import discord
from discord import ForumChannel, TextChannel, Thread
from discord.ui import LayoutView, Separator

from constants import STAFF_PROPOSALS_CHANNEL_ID

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Helpers Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

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