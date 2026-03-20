from __future__ import annotations

import discord
from discord.ext import commands

from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any
)

if TYPE_CHECKING:
    from ._base import ModerationBase, KickFlags

from commands.moderation.cases import CaseType

from core.utils import (
    send_major_error,
    send_minor_error
)
from core.permissions import is_director

from constants import (
    COLOR_ORANGE,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation kick Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_kick(
    base:        "ModerationBase",
    interaction: discord.Interaction,
    member:      discord.Member,
    reason:      str,
    proof:       discord.Attachment | None = None,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_apply_standard_actions(actor):
        await send_major_error(
            interaction,
            title="Unauthorized!",
            texts="You lack the necessary permissions to kick members.",
            subtitle="Invalid permissions."
        )
        return

    if member.id == actor.id:
        await send_minor_error(interaction, "You cannot kick yourself.")
        return

    can_moderate, error_msg = base.check_can_moderate_target(actor, member)
    if not can_moderate:
        await send_minor_error(interaction, error_msg)
        return

    guild = interaction.guild
    if not guild:
        return

    if not is_director(actor):
        can_proceed, error_msg = base.check_rate_limit(str(actor.id), "kick")
        if not can_proceed:
            await send_major_error(
                interaction,
                f"Rate limit exceeded. {error_msg}.\n"
                f"Continuing to exceed rate limits will result in your own quarantine.",
                subtitle="Rate limit exceeded."
            )
            await base.auto_quarantine_moderator(actor, guild)
            return

        base.add_rate_limit_entry(str(actor.id), "kick")

    await interaction.response.defer(ephemeral=True)

    try:
        await member.kick(reason=f"Kicked by {actor}: {reason}")

        kicks = base.ensure_data_section("kicks")
        kicks[str(member.id)] = {
            "kicked_at": datetime.now().isoformat(),
            "kicked_by": actor.id,
            "reason":    reason
        }
        base.save_data()

        metadata: dict[str, Any] = {}

        if proof:
            metadata["proof_url"] = proof.url

        await base.cases_manager.log_case(
            guild=guild,
            case_type=CaseType.KICK,
            moderator=actor,
            reason=reason,
            target_user=member,
            metadata=metadata if metadata else None
        )

        embed = discord.Embed(
            title="Member Kicked",
            color=COLOR_ORANGE,
            timestamp=datetime.now()
        )
        embed.add_field(name="Member",    value=f"{member.mention} ({member.id})", inline=True)
        embed.add_field(name="Moderator", value=actor.mention,                     inline=True)
        embed.add_field(name="Reason",    value=reason,                            inline=False)
        if proof:
            embed.set_image(url=proof.url)

        await interaction.followup.send(embed=embed, ephemeral=True)

    except discord.Forbidden:
        await send_major_error(
            interaction,
            "I lack the necessary permissions to kick this member.",
            subtitle="Invalid configuration. Contact the owner."
        )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .kick Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_kick_prefix(
    base:   "ModerationBase",
    ctx:    commands.Context[commands.Bot],
    member: discord.Member,
    flags:  "KickFlags",
) -> None:
    actor = ctx.author
    if not isinstance(actor, discord.Member):
        return

    if not base.can_apply_standard_actions(actor):
        await base.send_prefix_denied(
            ctx,
            "Failed to kick member",
            "You lack the necessary permissions to kick members."
        )
        return

    if not flags.r:
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to kick member!**\n"
            f"Please provide a reason for the kick."
        )
        return

    reason = flags.r

    if member.id == actor.id:
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to kick member!**\n"
            f"You cannot kick yourself."
        )
        return

    can_moderate, error_msg = base.check_can_moderate_target(actor, member)
    if not can_moderate:
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to kick member!**\n"
            f"{error_msg}"
        )
        return

    guild = ctx.guild
    if not guild:
        return

    if not is_director(actor):
        can_proceed, error_msg = base.check_rate_limit(str(actor.id), "kick")
        if not can_proceed:
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to kick member!**\n"
                f"Rate limit exceeded. {error_msg}.\n"
                f"-# Continuing to exceed rate limits will result in your own quarantine."
            )
            await base.auto_quarantine_moderator(actor, guild)
            return

        base.add_rate_limit_entry(str(actor.id), "kick")

    try:
        await member.kick(reason=f"Kicked by {actor}: {reason}")

        kicks = base.ensure_data_section("kicks")
        kicks[str(member.id)] = {
            "kicked_at": datetime.now().isoformat(),
            "kicked_by": actor.id,
            "reason":    reason
        }
        base.save_data()

        await base.cases_manager.log_case(
            guild=guild,
            case_type=CaseType.KICK,
            moderator=actor,
            reason=reason,
            target_user=member
        )

        if flags.s:
            await ctx.message.delete()
            return

        embed = discord.Embed(
            title="Member Kicked",
            color=COLOR_ORANGE,
            timestamp=datetime.now()
        )
        embed.add_field(name="Member",    value=f"{member.mention} ({member.id})", inline=True)
        embed.add_field(name="Moderator", value=actor.mention,                     inline=True)
        embed.add_field(name="Reason",    value=reason,                            inline=False)

        await base.send_prefix_temp_embed(ctx, embed)

    except discord.Forbidden:
        await ctx.send(
            f"{DENIED_EMOJI_ID} **Failed to kick member!**\n"
            f"I lack the necessary permissions to kick members.\n"
            f"-# Contact the owner."
        )
