from __future__ import annotations

import discord
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any
)

if TYPE_CHECKING:
    from ._base import ModerationBase

from commands.moderation.cases import CaseType

from core.utils import (
    send_major_error,
    send_minor_error,
)

from constants import (
    COLOR_GREEN,
    CONTESTED_EMOJI_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation unquarantine Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_unquarantine(
    base        : "ModerationBase",
    interaction : discord.Interaction,
    member      : discord.Member,
    reason      : str,
    proof       : discord.Attachment | None = None,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_reverse_actions(actor):
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
    in_json         = str(member.id) in base.data.get("quarantined", {})
    has_quarantine  = quarantine_role in member.roles if quarantine_role else False

    if not in_json and not has_quarantine:
        await send_minor_error(interaction, f"{member.mention} is already not quarantined.")
        return

    _ = await interaction.response.defer(ephemeral = True)

    quarantine_data           = base.data.get("quarantined", {}).get(str(member.id))
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

        quarantined = base.ensure_data_section("quarantined")
        if str(member.id) in quarantined:
            del quarantined[str(member.id)]
            base.save_data()

        metadata: dict[str, Any] = {"roles_restored": len(roles_to_add)}
        if proof:
            metadata["proof_url"] = proof.url

        _ = await base.cases_manager.log_case(
            guild       = guild,
            case_type   = CaseType.QUARANTINE_REMOVE,
            moderator   = actor,
            reason      = reason,
            target_user = member,
            metadata    = metadata
        )

        embed = discord.Embed(
            title = "Member Unquarantined",
            color = COLOR_GREEN,
            timestamp = datetime.now()
        )
        _ = embed.add_field(name = "Member",        value = member.mention,         inline = True)
        _ = embed.add_field(name = "Director",      value = actor.mention,          inline = True)
        _ = embed.add_field(name = "Roles Restored", value = str(len(roles_to_add)), inline = True)
        _ = embed.add_field(name = "Reason",        value = reason,                 inline = False)

        if roles_not_found:
            _ = embed.add_field(
                name   = f"{CONTESTED_EMOJI_ID} Roles Not Found",
                value  = f"{len(roles_not_found)} role(s) no longer exist and could not be restored.",
                inline = False
            )

        if proof:
            _ = embed.set_image(url=proof.url)

        await interaction.followup.send(embed=embed, ephemeral = True)

    except discord.Forbidden:
        await send_major_error(
            interaction,
            texts    = "I lack the necessary permissions to unquarantine this member.",
            subtitle = "Invalid configuration. Contact the owner."
        )