from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import (
    TYPE_CHECKING,
    Any,
)

import discord

if TYPE_CHECKING:
    from ._base import ModerationBase

from constants import COLOR_YELLOW
from core.cases import CaseType
from core.permissions import is_director
from core.responses import send_custom_message

from ._base import MemberPickerView

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation timeout Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_timeout(
    base        : ModerationBase,
    interaction : discord.Interaction,
    member      : discord.Member | None,
    duration    : str,
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
            "Timeout",
            "timeout",
            with_duration = True,
            precheck_callback = lambda moderator, target: base.check_can_moderate_target(moderator, target, "timeout"),
            execute_callback = lambda i, m, data: _execute_timeout(
                base,
                i,
                actor,
                m,
                str(data["duration"]),
                str(data["reason"]),
                data.get("proof"),
            ),
        )
        _ = await interaction.response.send_message(view = picker, ephemeral = True)
        return

    if not reason:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "timeout member",
            subtitle = "You must provide a reason.",
            footer   = "Bad argument",
        )
        return

    if member.id == actor.id:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "timeout member",
            subtitle = "You cannot timeout yourself.",
            footer   = "Bad argument",
        )
        return

    can_moderate, error_msg = base.check_can_moderate_target(actor, member, "timeout")
    if not can_moderate:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "timeout member",
            subtitle = error_msg,
            footer   = "Bad argument",
        )
        return

    duration_seconds = base.parse_duration(duration)
    if not duration_seconds:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "timeout member",
            subtitle = "Invalid duration format. Use: 30s, 5m, 1h, 2d, 1w",
            footer   = "Bad argument",
        )
        return

    if duration_seconds > 28 * 86400:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "timeout member",
            subtitle = "Timeout duration cannot exceed 28 days.",
            footer   = "Bad argument",
        )
        return

    guild = interaction.guild
    if not guild:
        return

    if not is_director(actor):
        can_proceed, error_msg = base.check_rate_limit(str(actor.id), "timeout")
        if not can_proceed:
            await send_custom_message(
                interaction,
                msg_type          = "error",
                title             = "timeout member",
                subtitle          = (
                    f"Rate limit exceeded. {error_msg}.\n"
                    "Continuing to exceed rate limits will result in your own quarantine."
                ),
                footer            = "Bad operation",
                contact_bot_owner = True,
            )
            await base.auto_quarantine_moderator(actor, guild)
            return

        base.add_rate_limit_entry(str(actor.id), "timeout")

    _ = await interaction.response.defer(ephemeral = True)
    ok, msg = await _execute_timeout(base, interaction, actor, member, duration, reason, proof)
    if not ok:
        await send_custom_message(
            interaction,
            msg_type          = "error",
            title             = "timeout member",
            subtitle          = msg,
            footer            = "Bad configuration",
            contact_bot_owner = True,
        )

async def _execute_timeout(
    base        : ModerationBase,
    interaction : discord.Interaction,
    actor       : discord.Member,
    member      : discord.Member,
    duration    : str,
    reason      : str,
    proof       : discord.Attachment | None,
) -> tuple[bool, str]:
    guild = interaction.guild
    if not guild:
        return False, "No guild context."
    bot_member = guild.me
    if not bot_member or not bot_member.guild_permissions.moderate_members:
        return False, "I lack permissions to timeout members: `Moderate Members`"
    if member.top_role >= bot_member.top_role:
        return False, "Target user is above or equal to my highest role."

    duration_seconds = base.parse_duration(duration)
    if not duration_seconds:
        return False, "Invalid duration format."
    if duration_seconds > 28 * 86400:
        return False, "Timeout duration cannot exceed 28 days."

    try:
        until = discord.utils.utcnow() + timedelta(seconds = duration_seconds)
        await member.timeout(until, reason = f"Timed out by {actor}: {reason}")

        timeouts = base.ensure_data_section("timeouts")
        timeouts[str(member.id)] = {
            "timed_out_at" : datetime.now(UTC).isoformat(),
            "timed_out_by" : actor.id,
            "reason"       : reason,
            "duration"     : duration_seconds,
            "until"        : until.isoformat(),
        }
        base.save_data()

        metadata: dict[str, Any] = {"until": until.isoformat()}
        if proof:
            metadata["proof_url"] = proof.url

        _ = await base.cases_manager.log_case(
            guild       = guild,
            case_type   = CaseType.TIMEOUT,
            moderator   = actor,
            reason      = reason,
            target_user = member,
            duration    = duration,
            metadata    = metadata,
        )

        embed = discord.Embed(
            title     = "Member Timed Out",
            color     = COLOR_YELLOW,
            timestamp = datetime.now(UTC),
        )
        _ = embed.add_field(name = "Member",    value = member.mention,                      inline = True)
        _ = embed.add_field(name = "Moderator", value = actor.mention,                       inline = True)
        _ = embed.add_field(name = "Duration",  value = duration,                            inline = True)
        _ = embed.add_field(name = "Expires",   value = discord.utils.format_dt(until, "R"), inline = True)
        _ = embed.add_field(name = "Reason",    value = reason,                              inline = False)
        if proof:
            _ = embed.set_image(url = proof.url)

    except discord.Forbidden:
        return False, "I lack permissions to timeout members: `Moderate Members`"
    else:
        if interaction.response.is_done():
            await interaction.followup.send(embed = embed, ephemeral = True)
        else:
            _ = await interaction.response.send_message(embed = embed, ephemeral = True)
        return True, "ok"
