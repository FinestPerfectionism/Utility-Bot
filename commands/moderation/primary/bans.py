import discord
from discord.ext import commands

import asyncio
import contextlib
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any
)

if TYPE_CHECKING:
    from ._base import ModerationBase, BanFlags

from commands.moderation.cases import CaseType

from core.utils import (
    send_major_error,
    send_minor_error
)
from core.permissions import is_director

from constants import (
    COLOR_GREEN,
    COLOR_RED,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation ban Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_ban(
    base:            "ModerationBase",
    interaction:     discord.Interaction,
    member:          discord.Member,
    reason:          str,
    delete_messages: int | None = 0,
    proof:           discord.Attachment | None = None,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_moderate(actor):
        await send_major_error(
            interaction,
            title="Unauthorized!",
            texts="You lack the necessary permissions to ban members.",
            subtitle="Invalid permissions."
        )
        return

    if member.id == actor.id:
        await send_minor_error(interaction, "You cannot ban yourself.")
        return

    can_moderate, error_msg = base.check_can_moderate_target(actor, member)
    if not can_moderate:
        await send_minor_error(interaction, error_msg)
        return

    guild = interaction.guild
    if not guild:
        return

    if not is_director(actor):
        can_proceed, error_msg = base.check_rate_limit(str(actor.id), "ban")
        if not can_proceed:
            await send_major_error(
                interaction,
                f"Rate limit exceeded. {error_msg}.\n"
                f"Continuing to exceed rate limits will result in your own quarantine.",
                subtitle="Rate limit exceeded."
            )
            await base.auto_quarantine_moderator(actor, guild)
            return

        base.add_rate_limit_entry(str(actor.id), "ban")

    await interaction.response.defer(ephemeral=True)

    dm_value        = delete_messages if delete_messages is not None else 0
    delete_messages = max(0, min(7, dm_value))

    try:
        await member.ban(
            reason=f"Banned by {actor}: {reason}",
            delete_message_seconds=delete_messages * 86400
        )

        base.data["bans"][str(member.id)] = {
            "banned_at": datetime.now().isoformat(),
            "banned_by": actor.id,
            "reason":    reason
        }
        base.save_data()

        metadata: dict[str, Any] = {"delete_message_days": delete_messages}

        if proof:
            metadata["proof_url"] = proof.url

        await base.cases_manager.log_case(
            guild=guild,
            case_type=CaseType.BAN,
            moderator=actor,
            reason=reason,
            target_user=member,
            metadata=metadata
        )

        embed = discord.Embed(
            title="Member Banned",
            color=COLOR_RED,
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
            "I lack the necessary permissions to ban this member.",
            subtitle="Invalid configuration. Contact the owner."
        )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .ban Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_ban_prefix(
    base:   "ModerationBase",
    ctx:    commands.Context[commands.Bot],
    member: discord.Member,
    flags:  "BanFlags",
) -> None:
    actor = ctx.author
    if not isinstance(actor, discord.Member):
        return

    if not base.can_moderate(actor):
        return

    if not flags.r:
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to ban member!**\n"
            f"Please provide a reason for the ban."
        )
        return

    reason          = flags.r
    delete_messages = max(0, min(7, flags.d))

    if member.id == actor.id:
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to ban member!**\n"
            f"You cannot ban yourself."
        )
        return

    can_moderate, error_msg = base.check_can_moderate_target(actor, member)
    if not can_moderate:
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to ban member!**\n"
            f"{error_msg}"
        )
        return

    guild = ctx.guild
    if not guild:
        return

    if not is_director(actor):
        can_proceed, error_msg = base.check_rate_limit(str(actor.id), "ban")
        if not can_proceed:
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to ban member!**\n"
                f"Rate limit exceeded. {error_msg}."
            )
            await base.auto_quarantine_moderator(actor, guild)
            return

        base.add_rate_limit_entry(str(actor.id), "ban")

    try:
        await member.ban(
            reason=f"Banned by {actor}: {reason}",
            delete_message_seconds=delete_messages * 86400
        )

        base.data["bans"][str(member.id)] = {
            "banned_at": datetime.now().isoformat(),
            "banned_by": actor.id,
            "reason":    reason
        }
        base.save_data()

        await base.cases_manager.log_case(
            guild=guild,
            case_type=CaseType.BAN,
            moderator=actor,
            reason=reason,
            target_user=member,
            metadata={"delete_message_days": delete_messages}
        )

        if flags.s:
            await ctx.message.delete()
            return

        embed = discord.Embed(
            title="Member Banned",
            color=COLOR_RED,
            timestamp=datetime.now()
        )
        embed.add_field(name="Member",    value=f"{member.mention} ({member.id})", inline=True)
        embed.add_field(name="Moderator", value=actor.mention,                     inline=True)
        embed.add_field(name="Reason",    value=reason,                            inline=False)

        msg = await ctx.send(embed=embed)
        await asyncio.sleep(10)
        with contextlib.suppress(discord.NotFound):
            await msg.delete()

    except discord.Forbidden:
        await ctx.send(
            f"{DENIED_EMOJI_ID} **Failed to ban member!**\n"
            f"I lack the necessary permissions to ban members.\n"
            f"-# Contact the owner."
        )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation bans Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_bans(
    base:        "ModerationBase",
    interaction: discord.Interaction,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_view(actor):
        await send_major_error(
            interaction,
            title="Unauthorized!",
            texts="You lack the necessary permissions to view bans.",
            subtitle="Invalid permissions."
        )
        return

    guild = interaction.guild
    if not guild:
        return

    await interaction.response.defer(ephemeral=True)

    try:
        bans = [entry async for entry in guild.bans(limit=None)]

        if not bans:
            embed = discord.Embed(
                description="No members are currently banned.",
                color=COLOR_GREEN
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="Banned Members",
            color=COLOR_RED,
            timestamp=datetime.now()
        )

        for ban_entry in bans[:25]:
            user     = ban_entry.user
            ban_data = base.data["bans"].get(str(user.id))

            if ban_data:
                banned_at = datetime.fromisoformat(ban_data["banned_at"])
                reason    = ban_data["reason"]
                value     = f"Banned: {discord.utils.format_dt(banned_at, 'R')}\nReason: {reason}"
            else:
                value = f"Reason: {ban_entry.reason or 'No reason provided'}"

            embed.add_field(
                name=f"{user} ({user.id})",
                value=value,
                inline=False
            )

        if len(bans) > 25:
            embed.set_footer(text=f"Showing 25 of {len(bans)} bans")

        await interaction.followup.send(embed=embed, ephemeral=True)

    except discord.Forbidden:
        await send_major_error(
            interaction,
            "I lack the necessary permissions to view bans.",
            subtitle="Invalid configuration. Contact the owner."
        )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .bans Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_bans_prefix(
    base: "ModerationBase",
    ctx:  commands.Context[commands.Bot],
) -> None:
    actor = ctx.author
    if not isinstance(actor, discord.Member):
        return

    if not base.can_view(actor):
        return

    guild = ctx.guild
    if not guild:
        return

    try:
        bans = [entry async for entry in guild.bans(limit=None)]

        if not bans:
            embed = discord.Embed(
                description="No members are currently banned.",
                color=COLOR_GREEN
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="Banned Members",
            color=COLOR_RED,
            timestamp=datetime.now()
        )

        for ban_entry in bans[:25]:
            user     = ban_entry.user
            ban_data = base.data["bans"].get(str(user.id))

            if ban_data:
                banned_at = datetime.fromisoformat(ban_data["banned_at"])
                reason    = ban_data["reason"]
                value     = f"Banned: {discord.utils.format_dt(banned_at, 'R')}\nReason: {reason}"
            else:
                value = f"Reason: {ban_entry.reason or 'No reason provided'}"

            embed.add_field(
                name=f"{user} ({user.id})",
                value=value,
                inline=False
            )

        if len(bans) > 25:
            embed.set_footer(text=f"Showing 25 of {len(bans)} bans")

        msg = await ctx.send(embed=embed)
        await asyncio.sleep(10)
        with contextlib.suppress(discord.NotFound):
            await msg.delete()

    except discord.Forbidden:
        await ctx.send(
            f"{DENIED_EMOJI_ID} **Failed to retrieve ban list!**\n"
            f"I lack the necessary permissions to view bans.\n"
            f"-# Contact the owner."
        )
