from __future__ import annotations

import discord
from discord.ext import commands

import asyncio
import contextlib
from datetime import datetime, timezone
from typing import (
    TYPE_CHECKING,
    Any
)

if TYPE_CHECKING:
    from ._base import (
        ModerationBase,
        PurgeFlags
    )

from commands.moderation.cases import CaseType

from core.utils import (
    send_major_error,
    send_minor_error
)

from constants import (
    COLOR_BLURPLE,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Purge Helpers
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

PurgeableChannel = (
    discord.TextChannel
    | discord.VoiceChannel
    | discord.Thread
)

def _get_purgeable_channel(
    channel: Any 
) -> PurgeableChannel | None:
    if isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.Thread)):
        return channel
    return None

def _build_purge_embed(
    deleted_count: int,
    moderator:     discord.Member,
    member:        discord.Member | None = None,
    proof:         discord.Attachment | None = None,
) -> discord.Embed:
    embed = discord.Embed(
        title="Messages Purged",
        color=COLOR_BLURPLE,
        timestamp=datetime.now(tz=timezone.utc)
    )
    embed.add_field(name="Deleted",   value=str(deleted_count), inline=True)
    embed.add_field(name="Moderator", value=moderator.mention,  inline=True)
    if member:
        embed.add_field(name="From User", value=member.mention, inline=True)
    if proof:
        embed.set_image(url=proof.url)
    return embed

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation purge Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_purge(
    base:        "ModerationBase",
    interaction: discord.Interaction,
    amount:      int,
    reason:      str,
    member:      discord.Member     | None = None,
    proof:       discord.Attachment | None = None,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_moderate(actor):
        await send_major_error(
            interaction,
            title="Unauthorized!",
            texts="You lack the necessary permissions to purge messages.",
            subtitle="Invalid permissions."
        )
        return

    if amount < 1 or amount > 100:
        await send_minor_error(interaction, "Amount must be between 1 and 100.")
        return

    channel = _get_purgeable_channel(interaction.channel) 

    if channel is None:
        await send_minor_error(interaction, "This command cannot be used in this channel type.", subtitle="Bad command environment.")
        return

    guild = interaction.guild
    if not guild:
        return

    await interaction.response.defer(ephemeral=True)

    try:
        if member:
            target_id = member.id
            cutoff    = datetime.now(tz=timezone.utc)
            deleted   = await channel.purge(
                limit=amount,
                check=lambda m: (
                    m.author.id == target_id
                    and (cutoff - m.created_at).days < 14
                ),
                before=interaction.created_at,
                bulk=True
            )
        else:
            deleted = await channel.purge(
                limit=amount,
                before=interaction.created_at,
                bulk=True
            )

        metadata: dict[str, Any] = {
            "deleted_messages": len(deleted),
            "channel_id":       channel.id
        }
        if proof:
            metadata["proof_url"] = proof.url

        await base.cases_manager.log_case(
            guild       = guild,
            case_type   = CaseType.PURGE,
            moderator   = actor,
            reason      = reason,
            target_user = member if member else None,
            metadata    = metadata
        )

        embed = _build_purge_embed(len(deleted), actor, member, proof)
        await interaction.followup.send(embed=embed, ephemeral=True)

    except discord.Forbidden:
        await send_major_error(
            interaction,
            title="Missing Permissions",
            texts="I lack the necessary permissions to delete messages.",
            subtitle="Invalid configuration. Contact the owner."
        )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .purge Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_purge_prefix(
    base:   "ModerationBase",
    ctx:    commands.Context[commands.Bot],
    amount: int,
    flags:  PurgeFlags,
) -> None:
    actor = ctx.author
    if not isinstance(actor, discord.Member):
        return

    if not base.can_moderate(actor):
        return

    if amount < 1 or amount > 100:
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to purge messages!**\n"
            f"Amount must be between 1 and 100."
        )
        return

    channel = _get_purgeable_channel(ctx.channel)
    if channel is None:
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to purge messages!**\n"
            f"This command cannot be used in this channel type."
        )
        return

    guild = ctx.guild
    if not guild:
        return

    member = flags.u
    if not flags.r:
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to purge messages!**\n"
            f"Please provide a reason for the purge."
        )
        return

    member = flags.u
    reason = flags.r

    try:
        if member:
            target_id = member.id
            deleted   = await channel.purge(
                limit  = amount,
                check  = lambda m: m.author.id == target_id,
                before = ctx.message
            )
        else:
            deleted = await channel.purge(limit=amount, before=ctx.message)

        with contextlib.suppress(discord.NotFound):
            await ctx.message.delete()

        metadata: dict[str, Any] = {
            "deleted_messages": len(deleted),
            "channel_id":       channel.id
        }

        await base.cases_manager.log_case(
            guild       = guild,
            case_type   = CaseType.PURGE,
            moderator   = actor,
            reason      = reason,
            target_user = member if member else None,
            metadata    = metadata
        )

        if flags.s:
            return

        embed = _build_purge_embed(len(deleted), actor, member)
        msg   = await ctx.send(embed=embed)
        await asyncio.sleep(10)
        with contextlib.suppress(discord.NotFound):
            await msg.delete()

    except discord.Forbidden:
        await ctx.send(
            f"{DENIED_EMOJI_ID} **Failed to purge messages!**\n"
            f"I lack the necessary permissions to delete messages.\n"
            f"-# Contact the owner."
        )