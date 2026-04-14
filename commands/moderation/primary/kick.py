from __future__ import annotations

from datetime import UTC, datetime
from typing import (
    TYPE_CHECKING,
    Any,
)

import discord

if TYPE_CHECKING:
    from ._base import ModerationBase

from commands.moderation.cases import CaseType
from constants import COLOR_ORANGE
from core.permissions import is_director
from core.responses import send_custom_message

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation kick Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_kick(
    base        : ModerationBase,
    interaction : discord.Interaction,
    member      : discord.Member,
    reason      : str,
    proof       : discord.Attachment | None = None,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_apply_standard_actions(actor):
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
            title    = "kick member",
            subtitle = "You cannot kick yourself.",
            footer   = "Bad argument",
        )
        return

    can_moderate, error_msg = base.check_can_moderate_target(actor, member)
    if not can_moderate:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "kick member",
            subtitle = error_msg,
            footer   = "Bad argument",
        )
        return

    guild = interaction.guild
    if not guild:
        return

    if not is_director(actor):
        can_proceed, error_msg = base.check_rate_limit(str(actor.id), "kick")
        if not can_proceed:
            await send_custom_message(
                interaction,
                msg_type          = "error",
                title             = "kick member",
                subtitle          = (
                    f"Rate limit exceeded. {error_msg}.\n"
                    "Continuing to exceed rate limits will result in your own quarantine."
                ),
                footer            = "Bad operation",
                contact_bot_owner = True,
            )
            await base.auto_quarantine_moderator(actor, guild)
            return
        base.add_rate_limit_entry(str(actor.id), "kick")

    _ = await interaction.response.defer(ephemeral = True)

    try:
        await member.kick(reason = f"Kicked by {actor}: {reason}")

        kicks = base.ensure_data_section("kicks")
        kicks[str(member.id)] = {
            "kicked_at" : datetime.now(UTC).isoformat(),
            "kicked_by" : actor.id,
            "reason"    : reason,
        }
        base.save_data()

        metadata: dict[str, Any] = {}
        if proof:
            metadata["proof_url"] = proof.url

        _ = await base.cases_manager.log_case(
            guild       = guild,
            case_type   = CaseType.KICK,
            moderator   = actor,
            reason      = reason,
            target_user = member,
            metadata    = metadata if metadata else None,
        )

        embed = discord.Embed(
            title     = "Member Kicked",
            color     = COLOR_ORANGE,
            timestamp = datetime.now(UTC),
        )
        _ = embed.add_field(name = "Member",    value = f"{member.mention} ({member.id})", inline = True)
        _ = embed.add_field(name = "Moderator", value = actor.mention,                     inline = True)
        _ = embed.add_field(name = "Reason",    value = reason,                            inline = False)
        if proof:
            _ = embed.set_image(url = proof.url)

        await interaction.followup.send(embed = embed, ephemeral = True)

    except discord.Forbidden:
        await send_custom_message(
            interaction,
            msg_type          = "error",
            title             = "kick members",
            subtitle          = "I lack permissions to kick members: `Kick Members`",
            footer            = "Bad configuration",
            contact_bot_owner = True,
        )
