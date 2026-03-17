from __future__ import annotations

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
    from ._base import (
        ModerationBase,
        QuarantineFlags,
    )

from commands.moderation.cases import CaseType

from core.utils import (
    send_major_error,
    send_minor_error,
)
from core.permissions import is_director

from constants import (
    BOT_OWNER_ID,
    COLOR_RED,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation quarantine Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_quarantine(
    base:        "ModerationBase",
    interaction: discord.Interaction,
    member:      discord.Member,
    reason:      str,
    proof:       discord.Attachment | None = None,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_quarantine(actor):
        await send_major_error(
            interaction,
            title="Unauthorized!",
            texts="You lack the necessary permissions to add members to quarantine.",
            subtitle="No permissions."
        )
        return

    if member.id == actor.id:
        await send_minor_error(interaction, "You cannot quarantine yourself.")
        return

    if not base.check_hierarchy(actor, member):
        await send_minor_error(interaction, "You cannot quarantine members with a role ≥ to yours.")
        return

    if "quarantined" not in base.data:
        base.data["quarantined"] = {}

    if str(member.id) in base.data["quarantined"]:
        await send_minor_error(interaction, f"{member.mention} is already quarantined.")
        return

    guild = interaction.guild
    if not guild:
        return

    if not is_director(actor):
        can_proceed, error_msg = base.check_rate_limit(str(actor.id), "quarantine")
        if not can_proceed:
            await send_major_error(
                interaction,
                texts    = f"Rate limit exceeded. {error_msg}.\n"
                           f"Continuing to exceed rate limits will result in your own quarantine.",
                subtitle =  "Rate limit exceeded."
            )
            await base.auto_quarantine_moderator(actor, guild)
            return

        base.add_rate_limit_entry(str(actor.id), "quarantine")

    await interaction.response.defer(ephemeral=True)

    quarantine_role = guild.get_role(base.QUARANTINE_ROLE_ID)
    if not quarantine_role:
        await send_major_error(
            interaction,
            texts    =  "Quarantine role not found.",
            subtitle = f"Invalid IDs. Contact <@{BOT_OWNER_ID}>."
        )
        return

    saved_roles = [
        role.id for role in member.roles
        if role.id not in (guild.default_role.id, base.QUARANTINE_ROLE_ID)
    ]

    base.data["quarantined"][str(member.id)] = {
        "roles":          saved_roles,
        "quarantined_at": datetime.now().isoformat(),
        "quarantined_by": actor.id,
        "reason":         reason
    }
    base.save_data()

    try:
        roles_to_remove = [role for role in member.roles if role.id != guild.default_role.id]
        await member.remove_roles(*roles_to_remove, reason=f"Quarantined by {actor}")
        await member.add_roles(quarantine_role, reason=f"Quarantined by {actor}: {reason}")

        metadata: dict[str, Any] = {"roles_saved": len(saved_roles)}
        if proof:
            metadata["proof_url"] = proof.url

        await base.cases_manager.log_case(
            guild=guild,
            case_type=CaseType.QUARANTINE_ADD,
            moderator=actor,
            reason=reason,
            target_user=member,
            metadata=metadata
        )

        embed = discord.Embed(
            title="Member Quarantined",
            color=COLOR_RED,
            timestamp=datetime.now()
        )
        embed.add_field(name="Member",      value=member.mention,        inline=True)
        embed.add_field(name="Moderator",   value=actor.mention,         inline=True)
        embed.add_field(name="Roles Saved", value=str(len(saved_roles)), inline=True)
        embed.add_field(name="Reason",      value=reason,                inline=False)
        if proof:
            embed.set_image(url=proof.url)

        await interaction.followup.send(embed=embed, ephemeral=True)

    except discord.Forbidden:
        await send_major_error(
            interaction,
            texts    = "I lack the necessary permissions to run this command.",
            subtitle = "Invalid configuration. Contact the owner."
        )
        if str(member.id) in base.data["quarantined"]:
            del base.data["quarantined"][str(member.id)]
            base.save_data()

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .quarantine Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_quarantine_prefix(
    base:   "ModerationBase",
    ctx:    commands.Context[commands.Bot],
    member: discord.Member,
    flags:  QuarantineFlags,
) -> None:
    actor = ctx.author
    if not isinstance(actor, discord.Member):
        return

    if not base.can_quarantine(actor):
        return

    if not flags.r:
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to quarantine member!**\n"
            f"Please provide a reason for the quarantine."
        )
        return

    reason = flags.r

    if member.id == actor.id:
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to quarantine member!**\n"
            f"You cannot quarantine yourself."
        )
        return

    if not base.check_hierarchy(actor, member):
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to quarantine member!**\n"
            f"You cannot quarantine members with a role ≥ to yours."
        )
        return

    if "quarantined" not in base.data:
        base.data["quarantined"] = {}

    if str(member.id) in base.data["quarantined"]:
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to quarantine member!**\n"
            f"{member.mention} is already quarantined."
        )
        return

    guild = ctx.guild
    if not guild:
        return

    if not is_director(actor):
        can_proceed, error_msg = base.check_rate_limit(str(actor.id), "quarantine")
        if not can_proceed:
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to quarantine member!**\n"
                f"Rate limit exceeded. {error_msg}."
            )
            await base.auto_quarantine_moderator(actor, guild)
            return

        base.add_rate_limit_entry(str(actor.id), "quarantine")

    quarantine_role = guild.get_role(base.QUARANTINE_ROLE_ID)
    if not quarantine_role:
        return

    saved_roles = [
        role.id for role in member.roles
        if role.id not in (guild.default_role.id, base.QUARANTINE_ROLE_ID)
    ]

    base.data["quarantined"][str(member.id)] = {
        "roles":          saved_roles,
        "quarantined_at": datetime.now().isoformat(),
        "quarantined_by": actor.id,
        "reason":         reason
    }
    base.save_data()

    try:
        roles_to_remove = [role for role in member.roles if role.id != guild.default_role.id]
        await member.remove_roles(*roles_to_remove, reason=f"Quarantined by {actor}")
        await member.add_roles(quarantine_role, reason=f"Quarantined by {actor}: {reason}")

        await base.cases_manager.log_case(
            guild=guild,
            case_type=CaseType.QUARANTINE_ADD,
            moderator=actor,
            reason=reason,
            target_user=member,
            metadata={"roles_saved": len(saved_roles)}
        )

        if flags.s:
            await ctx.message.delete()
            return

        embed = discord.Embed(
            title="Member Quarantined",
            color=COLOR_RED,
            timestamp=datetime.now()
        )
        embed.add_field(name="Member",      value=member.mention,        inline=True)
        embed.add_field(name="Moderator",   value=actor.mention,         inline=True)
        embed.add_field(name="Roles Saved", value=str(len(saved_roles)), inline=True)
        embed.add_field(name="Reason",      value=reason,                inline=False)

        msg = await ctx.send(embed=embed)
        await asyncio.sleep(10)
        with contextlib.suppress(discord.NotFound):
            await msg.delete()

    except discord.Forbidden:
        await ctx.send(
            f"{DENIED_EMOJI_ID} **Failed to quarantine member!**\n"
            f"I lack the necessary permissions to run this command.\n"
            f"-# Contact the owner."
        )
        if str(member.id) in base.data["quarantined"]:
            del base.data["quarantined"][str(member.id)]
            base.save_data()