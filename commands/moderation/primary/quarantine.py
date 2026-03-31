from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import discord

if TYPE_CHECKING:
    from ._base import ModerationBase

from commands.moderation.cases import CaseType
from constants import (
    BOT_OWNER_ID,
    COLOR_RED,
)
from core.permissions import is_director
from core.utils import (
    send_major_error,
    send_minor_error,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation quarantine Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_quarantine(
    base:        ModerationBase,
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
            title = "Unauthorized!",
            texts="You lack the necessary permissions to add members to quarantine.",
            subtitle = "No permissions.",
        )
        return

    if member.id == actor.id:
        await send_minor_error(interaction, "You cannot quarantine yourself.")
        return

    if not base.check_hierarchy(actor, member):
        await send_minor_error(interaction, "You cannot quarantine members with a role ≥ to yours.")
        return

    quarantined = base.ensure_data_section("quarantined")

    if str(member.id) in quarantined:
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
                            "Continuing to exceed rate limits will result in your own quarantine.",
                subtitle =  "Rate limit exceeded.",
            )
            await base.auto_quarantine_moderator(actor, guild)
            return

        base.add_rate_limit_entry(str(actor.id), "quarantine")

    _ = await interaction.response.defer(ephemeral = True)

    quarantine_role = guild.get_role(base.QUARANTINE_ROLE_ID)
    if not quarantine_role:
        await send_major_error(
            interaction,
            texts    =  "Quarantine role not found.",
            subtitle = f"Invalid IDs. Contact <@{BOT_OWNER_ID}>.",
        )
        return

    saved_roles = [
        role.id for role in member.roles
        if role.id not in (guild.default_role.id, base.QUARANTINE_ROLE_ID)
    ]

    quarantined[str(member.id)] = {
        "roles":          saved_roles,
        "quarantined_at": datetime.now().isoformat(),
        "quarantined_by": actor.id,
        "reason":         reason,
    }
    base.save_data()

    try:
        roles_to_remove = [role for role in member.roles if role.id != guild.default_role.id]
        await member.remove_roles(*roles_to_remove, reason=f"Quarantined by {actor}")
        await member.add_roles(quarantine_role, reason=f"Quarantined by {actor}: {reason}")

        metadata: dict[str, Any] = {"roles_saved": len(saved_roles)}
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
            color     = COLOR_RED,
            timestamp = datetime.now(),
        )
        _ = embed.add_field(name = "Member",      value = member.mention,        inline = True)
        _ = embed.add_field(name = "Moderator",   value = actor.mention,         inline = True)
        _ = embed.add_field(name = "Roles Saved", value = str(len(saved_roles)), inline = True)
        _ = embed.add_field(name = "Reason",      value = reason,                inline = False)
        if proof:
            _ = embed.set_image(url=proof.url)

        await interaction.followup.send(embed=embed, ephemeral = True)

    except discord.Forbidden:
        await send_major_error(
            interaction,
            texts    = "I lack the necessary permissions to quarantine this member.",
            subtitle = "Invalid configuration. Contact the owner.",
        )
        if str(member.id) in quarantined:
            del quarantined[str(member.id)]
            base.save_data()
