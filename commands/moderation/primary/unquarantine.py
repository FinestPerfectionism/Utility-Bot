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
        UnquarantineFlags,
    )

from commands.moderation.cases import CaseType

from core.utils import (
    send_major_error,
    send_minor_error,
)

from constants import (
    COLOR_GREEN,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation unquarantine Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_unquarantine(
    base:        "ModerationBase",
    interaction: discord.Interaction,
    member:      discord.Member,
    reason:      str,
    proof:       discord.Attachment | None = None,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_unban_untimeout(actor):
        await send_major_error(
            interaction,
            title    = "Unauthorized!",
            texts    = "You lack the necessary permissions to remove members from quarantine.",
            subtitle = "No permissions."
        )
        return

    guild = interaction.guild
    if not guild:
        await send_minor_error(
            interaction,
            texts    = "This command can only be used in a server.",
            subtitle = "Bad command environment."
        )
        return

    quarantine_role = guild.get_role(base.QUARANTINE_ROLE_ID)
    in_json         = str(member.id) in base.data["quarantined"]
    has_quarantine  = quarantine_role in member.roles if quarantine_role else False

    if not in_json and not has_quarantine:
        await send_minor_error(interaction, f"{member.mention} is already not quarantined.")
        return

    await interaction.response.defer(ephemeral=True)

    quarantine_data           = base.data["quarantined"].get(str(member.id))
    saved_role_ids: list[int] = list(quarantine_data["roles"]) if quarantine_data else []

    try:
        if quarantine_role and quarantine_role in member.roles:
            await member.remove_roles(quarantine_role, reason=f"Unquarantined by {actor}: {reason}")

        roles_to_add:    list[discord.Role] = []
        roles_not_found: list[int]          = []

        for role_id in saved_role_ids:
            if role_id == base.QUARANTINE_ROLE_ID:
                continue
            role = guild.get_role(role_id)
            if role:
                roles_to_add.append(role)
            else:
                roles_not_found.append(role_id)

        if roles_to_add:
            await member.add_roles(*roles_to_add, reason=f"Unquarantined by {actor}: {reason}")

        if str(member.id) in base.data["quarantined"]:
            del base.data["quarantined"][str(member.id)]
            base.save_data()

        metadata: dict[str, Any] = {"roles_restored": len(roles_to_add)}
        if proof:
            metadata["proof_url"] = proof.url

        await base.cases_manager.log_case(
            guild=guild,
            case_type=CaseType.QUARANTINE_REMOVE,
            moderator=actor,
            reason=reason,
            target_user=member,
            metadata=metadata
        )

        embed = discord.Embed(
            title="Member Unquarantined",
            color=COLOR_GREEN,
            timestamp=datetime.now()
        )
        embed.add_field(name="Member",        value=member.mention,         inline=True)
        embed.add_field(name="Director",      value=actor.mention,          inline=True)
        embed.add_field(name="Roles Restored", value=str(len(roles_to_add)), inline=True)
        embed.add_field(name="Reason",        value=reason,                 inline=False)

        if roles_not_found:
            embed.add_field(
                name=f"{CONTESTED_EMOJI_ID} Roles Not Found",
                value=f"{len(roles_not_found)} role(s) no longer exist and could not be restored.",
                inline=False
            )

        if proof:
            embed.set_image(url=proof.url)

        await interaction.followup.send(embed=embed, ephemeral=True)

    except discord.Forbidden:
        await send_major_error(
            interaction,
            "I lack the necessary permissions to run this command.",
            subtitle="Invalid configuration. Contact the owner."
        )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .unquarantine Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_unquarantine_prefix(
    base:   "ModerationBase",
    ctx:    commands.Context[commands.Bot],
    member: discord.Member,
    flags:  "UnquarantineFlags",
) -> None:
    actor = ctx.author
    if not isinstance(actor, discord.Member):
        return

    if not base.can_unban_untimeout(actor):
        return

    if not flags.r:
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to unquarantine member!**\n"
            f"Please provide a reason for the unquarantine."
        )
        return

    reason = flags.r

    guild = ctx.guild
    if not guild:
        return

    quarantine_role = guild.get_role(base.QUARANTINE_ROLE_ID)
    in_json         = str(member.id) in base.data["quarantined"]
    has_quarantine  = quarantine_role in member.roles if quarantine_role else False

    if not in_json and not has_quarantine:
        await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Failed to unquarantine member!**\n"
            f"{member.mention} is already not quarantined."
        )
        return

    quarantine_data         = base.data["quarantined"].get(str(member.id))
    saved_role_ids: list[int] = list(quarantine_data["roles"]) if quarantine_data else []

    try:
        if quarantine_role and quarantine_role in member.roles:
            await member.remove_roles(quarantine_role, reason=f"Unquarantined by {actor}: {reason}")

        roles_to_add:    list[discord.Role] = []
        roles_not_found: list[int]          = []

        for role_id in saved_role_ids:
            if role_id == base.QUARANTINE_ROLE_ID:
                continue
            role = guild.get_role(role_id)
            if role:
                roles_to_add.append(role)
            else:
                roles_not_found.append(role_id)

        if roles_to_add:
            await member.add_roles(*roles_to_add, reason=f"Unquarantined by {actor}: {reason}")

        if str(member.id) in base.data["quarantined"]:
            del base.data["quarantined"][str(member.id)]
            base.save_data()

        await base.cases_manager.log_case(
            guild=guild,
            case_type=CaseType.QUARANTINE_REMOVE,
            moderator=actor,
            reason=reason,
            target_user=member,
            metadata={"roles_restored": len(roles_to_add)}
        )

        if flags.s:
            await ctx.message.delete()
            return

        embed = discord.Embed(
            title     = "Member Unquarantined",
            color     = COLOR_GREEN,
            timestamp = datetime.now()
        )
        embed.add_field(name="Member",         value=member.mention,         inline=True)
        embed.add_field(name="Director",       value=actor.mention,          inline=True)
        embed.add_field(name="Roles Restored", value=str(len(roles_to_add)), inline=True)
        embed.add_field(name="Reason",         value=reason,                 inline=False)

        if roles_not_found:
            count = "role" if len(roles_not_found) == 1 else "roles"
            exist = "exists" if len(roles_not_found) == 1 else "exist"
            embed.add_field(
                name=f"{CONTESTED_EMOJI_ID} Roles Not Found",
                value=f"{len(roles_not_found)} {count} no longer {exist} and could not be restored.",
                inline=False
            )

        msg = await ctx.send(embed=embed)
        await asyncio.sleep(10)
        with contextlib.suppress(discord.NotFound):
            await msg.delete()

    except discord.Forbidden:
        await ctx.send(
            f"{DENIED_EMOJI_ID} **Failed to unquarantine member!**\n"
            f"I lack the necessary permissions to run this command.\n"
            f"-# Contact the owner."
        )