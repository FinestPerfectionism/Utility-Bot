from __future__ import annotations

from datetime import UTC, datetime
from typing import (
    TYPE_CHECKING,
    Any,
)

import discord

if TYPE_CHECKING:
    from ._base import ModerationBase

from constants import COLOR_ORANGE
from core.cases import CaseType
from core.permissions import is_director
from core.responses import send_custom_message

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation quarantine Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_quarantine(
    base        : ModerationBase,
    interaction : discord.Interaction,
    member      : discord.Member,
    reason      : str,
    proof       : discord.Attachment | None = None,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_quarantine(actor):
        await send_custom_message(
            interaction,
            msg_type = "error",
            title    = "run command",
            subtitle = "You are not authorized to run this command.",
            footer   = "No permissions",
        )
        return

    if member.id == actor.id:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "quarantine member",
            subtitle = "You cannot quarantine yourself.",
            footer   = "Bad argument",
        )
        return

    if not base.check_hierarchy(actor, member):
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "quarantine member",
            subtitle = "Target user is greater than or equal to your highest role.",
            footer   = "Bad argument",
        )
        return

    quarantined = base.ensure_data_section("quarantined")

    if str(member.id) in quarantined:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "quarantine member",
            subtitle = f"{member.mention} is already quarantined.",
            footer   = "Bad argument",
        )
        return

    guild = interaction.guild
    if not guild:
        return

    if not is_director(actor):
        can_proceed, error_msg = base.check_rate_limit(str(actor.id), "quarantine")
        if not can_proceed:
            await send_custom_message(
                interaction,
                msg_type          = "error",
                title             = "quarantine member",
                subtitle          = (
                    f"Rate limit exceeded. {error_msg}.\n"
                    "Continuing to exceed rate limits will result in your own quarantine."
                ),
                footer            = "Bad operation",
                contact_bot_owner = True,
            )
            await base.auto_quarantine_moderator(actor, guild)
            return

        base.add_rate_limit_entry(str(actor.id), "quarantine")

    _ = await interaction.response.defer(ephemeral = True)

    quarantine_role = guild.get_role(base.QUARANTINE_ROLE_ID)
    if not quarantine_role:
        await send_custom_message(
            interaction,
            msg_type          = "error",
            title             = "quarantine member",
            subtitle          = "The quarantine role could not be found.",
            footer            = "Invalid IDs",
            contact_bot_owner = True,
        )
        return

    saved_roles = [
        role.id for role in member.roles
        if role.id not in (guild.default_role.id, base.QUARANTINE_ROLE_ID)
    ]

    quarantined[str(member.id)] = {
        "roles"          : saved_roles,
        "quarantined_at" : datetime.now(UTC).isoformat(),
        "quarantined_by" : actor.id,
        "reason"         : reason,
    }
    base.save_data()

    try:
        roles_to_remove = [role for role in member.roles if role.id != guild.default_role.id]
        await member.remove_roles(*roles_to_remove, reason = f"Quarantined by {actor}")
        await member.add_roles(quarantine_role, reason = f"Quarantined by {actor}: {reason}")

        metadata: dict[str, Any] = {"roles_saved" : len(saved_roles)}
        if proof:
            metadata["proof_url"] = proof.url

        _ = await base.cases_manager.log_case(
            guild       = guild,
            case_type   = CaseType.QUARANTINE_ADD,
            moderator   = actor,
            reason      = reason,
            target_user = member,
            metadata    = metadata,
        )

        embed = discord.Embed(
            title     = "Member Quarantined",
            color     = COLOR_ORANGE,
            timestamp = datetime.now(UTC),
        )
        _ = embed.add_field(name = "Member",      value = member.mention,        inline = True)
        _ = embed.add_field(name = "Moderator",   value = actor.mention,         inline = True)
        _ = embed.add_field(name = "Roles Saved", value = str(len(saved_roles)), inline = True)
        _ = embed.add_field(name = "Reason",      value = reason,                inline = False)
        if proof:
            _ = embed.set_image(url = proof.url)

        await interaction.followup.send(embed = embed, ephemeral = True)

    except discord.Forbidden:
        await send_custom_message(
            interaction,
            msg_type          = "error",
            title             = "quarantine members",
            subtitle          = "I lack permissions to manage member roles: `Manage Roles`",
            footer            = "Bad configuration",
            contact_bot_owner = True,
        )
        if str(member.id) in quarantined:
            del quarantined[str(member.id)]
            base.save_data()
