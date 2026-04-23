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
from ._base import MemberPickerView

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation kick Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_kick(
    base        : ModerationBase,
    interaction : discord.Interaction,
    member      : discord.Member | None,
    reason      : str | None,
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

    if member is None:
        picker = MemberPickerView(
            base,
            "Kick",
            "kick",
            execute_callback = lambda i, m, data: _execute_kick(
                base, i, actor, m, str(data["reason"]), data.get("proof"),
            ),
        )
        await interaction.response.send_message(view = picker, ephemeral = True)
        return

    if not reason:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "kick member",
            subtitle = "You must provide a reason.",
            footer   = "Bad argument",
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
    ok, msg = await _execute_kick(base, interaction, actor, member, reason, proof)
    if not ok:
        await send_custom_message(
            interaction,
            msg_type          = "error",
            title             = "kick members",
            subtitle          = msg,
            footer            = "Bad configuration",
            contact_bot_owner = True,
        )

async def _execute_kick(
    base        : ModerationBase,
    interaction : discord.Interaction,
    actor       : discord.Member,
    member      : discord.Member,
    reason      : str,
    proof       : discord.Attachment | None,
) -> tuple[bool, str]:
    guild = interaction.guild
    if not guild:
        return False, "No guild context."

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

        if interaction.response.is_done():
            await interaction.followup.send(embed = embed, ephemeral = True)
        else:
            await interaction.response.send_message(embed = embed, ephemeral = True)
        return True, "ok"

    except discord.Forbidden:
        return False, "I lack permissions to kick members: `Kick Members`"
