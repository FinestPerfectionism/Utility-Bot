from __future__ import annotations

from datetime import UTC, datetime
from typing import (
    TYPE_CHECKING,
    Any,
)

import discord

if TYPE_CHECKING:
    from ._base import ModerationBase

from constants import COLOR_RED
from core.cases import CaseType
from core.permissions import is_director
from core.responses import send_custom_message

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation ban Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_ban(
    base            : ModerationBase,
    interaction     : discord.Interaction,
    member          : discord.Member,
    reason          : str,
    delete_messages : int                | None = 0,
    proof           : discord.Attachment | None = None,
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
            title    = "ban member",
            subtitle = "You cannot ban yourself.",
            footer   = "Bad argument",
        )
        return

    can_moderate, error_msg = base.check_can_moderate_target(actor, member)
    if not can_moderate:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "ban member",
            subtitle = error_msg,
            footer   = "Bad request",
        )
        return

    guild = interaction.guild
    if not guild:
        return

    if not is_director(actor):
        can_proceed, error_msg = base.check_rate_limit(str(actor.id), "ban")
        if not can_proceed:
            await send_custom_message(
                interaction,
                msg_type          = "error",
                title             = "ban member",
                subtitle          = (
                    f"Rate limit exceeded. {error_msg}.\n"
                    "Continuing to exceed rate limits will result in your own quarantine."
                ),
                footer            = "Bad operation",
                contact_bot_owner = True,
            )
            await base.auto_quarantine_moderator(actor, guild)
            return
        base.add_rate_limit_entry(str(actor.id), "ban")

    _ = await interaction.response.defer(ephemeral = True)

    dm_value        = delete_messages if delete_messages is not None else 0
    delete_messages = max(0, min(7, dm_value))

    try:
        await member.ban(
            reason                 = f"Banned by {actor}: {reason}",
            delete_message_seconds = delete_messages * 86400,
        )

        if "bans" not in base.data:
            base.data["bans"] = {}

        base.data["bans"][str(member.id)] = {
            "banned_at" : datetime.now(UTC).isoformat(),
            "banned_by" : actor.id,
            "reason"    : reason,
        }
        base.save_data()

        metadata: dict[str, Any] = {"delete_message_days": delete_messages}
        if proof:
            metadata["proof_url"] = proof.url

        _ = await base.cases_manager.log_case(
            guild       = guild,
            case_type   = CaseType.BAN,
            moderator   = actor,
            reason      = reason,
            target_user = member,
            metadata    = metadata,
        )

        embed = discord.Embed(
            title     = "Member Banned",
            color     = COLOR_RED,
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
            title             = "ban members",
            subtitle          = "I lack permissions to ban members: `Ban Members`",
            footer            = "Bad configuration",
            contact_bot_owner = True,
        )
