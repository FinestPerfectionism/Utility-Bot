from __future__ import annotations

import discord
from discord.ext import commands

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._base import (
        ModerationBase,
    
        UntimeoutFlags
    )

from commands.moderation.cases import CaseType

from core.utils import (
    send_major_error,
    send_minor_error
)

from constants import (
    COLOR_GREEN,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation un-timeout Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_untimeout(
    base        : "ModerationBase",
    interaction : discord.Interaction,
    member      : discord.Member,
    reason      : str,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_untimeout(actor):
        await send_major_error(
            interaction,
            title    = "Unauthorized!",
            texts    = "You lack the necessary permissions to remove timeouts.",
            subtitle = "Invalid permissions."
        )
        return

    if not member.is_timed_out():
        await send_minor_error(interaction, f"{member.mention} is not currently timed out.")
        return

    _ = await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    if not guild:
        return

    try:
        await member.timeout(None, reason=f"Timeout removed by {actor}: {reason}")

        if "timeouts" in base.data and str(member.id) in base.data["timeouts"]:
            del base.data["timeouts"][str(member.id)]
            base.save_data()

        _ = await base.cases_manager.log_case(
            guild       = guild,
            case_type   = CaseType.UNTIMEOUT,
            moderator   = actor,
            reason      = reason,
            target_user = member
        )

        embed = discord.Embed(
            title     = "Timeout Removed",
            color     = COLOR_GREEN,
            timestamp = datetime.now()
        )
        _ = embed.add_field(name="Member", value=member.mention, inline=True)
        _ = embed.add_field(name="Senior Moderator", value=actor.mention, inline=True)
        _ = embed.add_field(name="Reason", value=reason, inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    except discord.Forbidden:
        await send_major_error(
            interaction,
            texts    = "I lack the necessary permissions to remove timeout from this member.",
            subtitle = "Invalid configuration. Contact the owner."
        )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .un-timeout Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_untimeout_prefix(
    base:   "ModerationBase",
    ctx:    commands.Context[commands.Bot],
    member: discord.Member,
    flags:  UntimeoutFlags,
) -> None:
    actor = ctx.author
    if not isinstance(actor, discord.Member):
        return

    if not base.can_untimeout(actor):
        await base.send_prefix_denied(
            ctx,
            "Failed to remove timeout",
            "You lack the necessary permissions to remove timeouts."
        )
        return

    if not flags.r:
        _ = await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to remove timeout!**\n"
            f"Please provide a reason."
        )
        return

    reason = flags.r

    if not member.is_timed_out():
        _ = await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to remove timeout!**\n"
            f"{member.mention} is not currently timed out."
        )
        return

    guild = ctx.guild
    if not guild:
        return

    try:
        await member.timeout(None, reason=f"Timeout removed by {actor}: {reason}")

        if "timeouts" in base.data and str(member.id) in base.data["timeouts"]:
            del base.data["timeouts"][str(member.id)]
            base.save_data()

        _ = await base.cases_manager.log_case(
            guild       = guild,
            case_type   = CaseType.UNTIMEOUT,
            moderator   = actor,
            reason      = reason,
            target_user = member
        )

        if flags.s:
            _ = await ctx.message.delete()
            return

        embed = discord.Embed(
            title     = "Timeout Removed",
            color     = COLOR_GREEN,
            timestamp = datetime.now()
        )
        _ = embed.add_field(name="Member",   value=member.mention, inline=True)
        _ = embed.add_field(name="Senior Moderator", value=actor.mention,  inline=True)
        _ = embed.add_field(name="Reason",   value=reason,         inline=False)
        await base.send_prefix_temp_embed(ctx, embed)

    except discord.Forbidden:
        _ = await ctx.send(
            f"{DENIED_EMOJI_ID} **Failed to remove timeout!**\n"
            f"I lack the necessary permissions to remove timeouts.\n"
            f"-# Contact the owner."
        )
