from discord.ext import commands

from ._base import AuditQueue
from .channels.channel_create import ChannelCreateCog
from .channels.channel_delete import ChannelDeleteCog
from .channels.channel_edit import ChannelEditCog
from .emojis.emoji_create import EmojiAddCog
from .emojis.emoji_delete import EmojiDeleteCog
from .emojis.emoji_edit import EmojiEditCog
from .invites.invite_create import InviteCreateCog
from .invites.invite_delete import InviteDeleteCog
from .members.member_ban import MemberBanCog
from .members.member_edit import MemberEditCog
from .members.member_join import MemberJoinCog
from .members.member_remove import MemberRemoveCog
from .members.member_unban import MemberUnbanCog
from .roles.role_create import RoleCreateCog
from .roles.role_delete import RoleDeleteCog
from .roles.role_edit import RoleEditCog
from .server.integrations import IntegrationsCog
from .server.server_edit import ServerEditCog
from .stickers.sticker_create import StickerAddCog
from .stickers.sticker_delete import StickerDeleteCog
from .stickers.sticker_edit import StickerEditCog
from .threads.thread_create import ThreadCreateCog
from .threads.thread_delete import ThreadDeleteCog
from .threads.thread_edit import ThreadEditCog

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Setup
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

_COGS = [
    ChannelCreateCog,
    ChannelDeleteCog,
    ChannelEditCog,
    RoleCreateCog,
    RoleDeleteCog,
    RoleEditCog,
    MemberJoinCog,
    MemberRemoveCog,
    MemberBanCog,
    MemberUnbanCog,
    MemberEditCog,
    ServerEditCog,
    IntegrationsCog,
    EmojiAddCog,
    EmojiDeleteCog,
    EmojiEditCog,
    StickerAddCog,
    StickerDeleteCog,
    StickerEditCog,
    InviteCreateCog,
    InviteDeleteCog,
    ThreadCreateCog,
    ThreadDeleteCog,
    ThreadEditCog,
]

async def setup(bot: commands.Bot) -> None:
    queue = AuditQueue(bot)
    await bot.add_cog(queue)

    for cog_cls in _COGS:
        await bot.add_cog(cog_cls(bot, queue))
