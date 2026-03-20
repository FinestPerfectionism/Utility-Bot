from __future__ import annotations

import discord
from discord.ext import commands

from datetime import (
    datetime,
    timedelta
)
from typing import (
    TYPE_CHECKING,
    Any
)

if TYPE_CHECKING:
    from ._base import ModerationBase, TimeoutFlags

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
# /moderation timeout Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_timeout(
    base:        "ModerationBase",
    interaction: discord.Interaction,
    member:      discord.Member,
    duration:    str,
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
            texts="You lack the necessary permissions to timeout members.",
            subtitle="Invalid permissions."
        )
        return

    if member.id == actor.id:
        await send_minor_error(interaction, "You cannot timeout yourself.")
        return

    can_moderate, error_msg = base.check_can_moderate_target(actor, member)
    if not can_moderate:
        await send_minor_error(interaction, error_msg)
        return

    duration_seconds = base.parse_duration(duration)
    if not duration_seconds:
        await send_minor_error(interaction, "Invalid duration format. Use: 30s, 5m, 1h, 2d, 1w")
        return

    max_duration = 28 * 86400
    if duration_seconds > max_duration:
        await send_minor_error(interaction, f"Timeout duration cannot exceed 28 days. You provided: {duration}")
        return

    guild = interaction.guild
    if not guild:
        return

    if not is_director(actor):
        can_proceed, error_msg = base.check_rate_limit(str(actor.id), "timeout")
        if not can_proceed:
            await send_major_error(
                interaction,
                f"Rate limit exceeded. {error_msg}.\n"
                f"Continuing to exceed rate limits will result in your own quarantine.",
                subtitle="Rate limit exceeded."
            )
            await base.auto_quarantine_moderator(actor, guild)
            return

        base.add_rate_limit_entry(str(actor.id), "timeout")

    await interaction.response.defer(ephemeral=True)

    try:
        until = discord.utils.utcnow() + timedelta(seconds=duration_seconds)
        await member.timeout(until, reason=f"Timed out by {actor}: {reason}")

        timeouts = base.ensure_data_section("timeouts")
        timeouts[str(member.id)] = {
            "timed_out_at": datetime.now().isoformat(),
            "timed_out_by": actor.id,
            "reason":       reason,
            "duration":     duration_seconds,
            "until":        until.isoformat()
        }
        base.save_data()

        metadata: dict[str, Any] = {"until": until.isoformat()}

        if proof:
            metadata["proof_url"] = proof.url

        await base.cases_manager.log_case(
            guild=guild,
            case_type=CaseType.TIMEOUT,
            moderator=actor,
            reason=reason,
            target_user=member,
            duration=duration,
            metadata=metadata
        )

        embed = discord.Embed(
            title="Member Timed Out",
            color=COLOR_ORANGE,
            timestamp=datetime.now()
        )
        embed.add_field(name="Member",    value=member.mention,                      inline=True)
        embed.add_field(name="Moderator", value=actor.mention,                       inline=True)
        embed.add_field(name="Duration",  value=duration,                            inline=True)
        embed.add_field(name="Expires",   value=discord.utils.format_dt(until, "R"), inline=True)
        embed.add_field(name="Reason",    value=reason,                              inline=False)
        if proof:
            embed.set_image(url=proof.url)

        await interaction.followup.send(embed=embed, ephemeral=True)

    except discord.Forbidden:
        await send_major_error(
            interaction,
            "I lack the necessary permissions to timeout this member.",
            subtitle="Invalid configuration. Contact the owner."
        )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .timeout Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_timeout_prefix(
    base:   "ModerationBase",
    ctx:    commands.Context[commands.Bot],
    member: discord.Member,
    flags:  "TimeoutFlags",
) -> None:
    actor = ctx.author
    if not isinstance(actor, discord.Member):
        return

    if not base.can_apply_standard_actions(actor):
        await base.send_prefix_denied(
            ctx,
            "Failed to timeout member",
            "You lack the necessary permissions to timeout members."
        )
        return

    if not flags.r:
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
            f"Please provide a reason for the timeout."
        )
        return

    if not flags.d:
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
            f"Please provide a duration. Use: 30s, 5m, 1h, 2d, 1w"
        )
        return

    reason   = flags.r
    duration = flags.d

    if member.id == actor.id:
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
            f"You cannot timeout yourself."
        )
        return

    can_moderate, error_msg = base.check_can_moderate_target(actor, member)
    if not can_moderate:
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
            f"{error_msg}"
        )
        return

    duration_seconds = base.parse_duration(duration)
    if not duration_seconds:
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
            f"Invalid duration format. Use: 30s, 5m, 1h, 2d, 1w"
        )
        return

    max_duration = 28 * 86400
    if duration_seconds > max_duration:
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
            f"Timeout duration cannot exceed 28 days. You provided: {duration}"
        )
        return

    guild = ctx.guild
    if not guild:
        return

    if not is_director(actor):
        can_proceed, error_msg = base.check_rate_limit(str(actor.id), "timeout")
        if not can_proceed:
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
                f"Rate limit exceeded. {error_msg}.\n"
                f"-# Continuing to exceed rate limits will result in your own quarantine."
            )
            await base.auto_quarantine_moderator(actor, guild)
            return

        base.add_rate_limit_entry(str(actor.id), "timeout")

    try:
        until = discord.utils.utcnow() + timedelta(seconds=duration_seconds)
        await member.timeout(until, reason=f"Timed out by {actor}: {reason}")

        timeouts = base.ensure_data_section("timeouts")
        timeouts[str(member.id)] = {
            "timed_out_at": datetime.now().isoformat(),
            "timed_out_by": actor.id,
            "reason":       reason,
            "duration":     duration_seconds,
            "until":        until.isoformat()
        }
        base.save_data()

        await base.cases_manager.log_case(
            guild=guild,
            case_type=CaseType.TIMEOUT,
            moderator=actor,
            reason=reason,
            target_user=member,
            duration=duration,
            metadata={"until": until.isoformat()}
        )

        if flags.s:
            await ctx.message.delete()
            return

        embed = discord.Embed(
            title="Member Timed Out",
            color=COLOR_ORANGE,
            timestamp=datetime.now()
        )
        embed.add_field(name="Member",    value=member.mention,                      inline=True)
        embed.add_field(name="Moderator", value=actor.mention,                       inline=True)
        embed.add_field(name="Duration",  value=duration,                            inline=True)
        embed.add_field(name="Expires",   value=discord.utils.format_dt(until, "R"), inline=True)
        embed.add_field(name="Reason",    value=reason,                              inline=False)

        await base.send_prefix_temp_embed(ctx, embed)

    except discord.Forbidden:
        await ctx.send(
            f"{DENIED_EMOJI_ID} **Failed to timeout member!**\n"
            f"I lack the necessary permissions to timeout members.\n"
            f"-# Contact the owner."
        )
