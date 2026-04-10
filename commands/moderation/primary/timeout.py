from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import discord

if TYPE_CHECKING:
    from ._base import ModerationBase

from commands.moderation.cases import CaseType
from constants import COLOR_YELLOW
from core.permissions import is_director
from core.utils import send_major_error, send_minor_error

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation timeout Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_timeout(
    base        : ModerationBase,
    interaction : discord.Interaction,
    member      : discord.Member,
    duration    : str,
    reason      : str,
    proof       : discord.Attachment | None = None,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_apply_standard_actions(actor):
        await send_major_error(
            interaction,
            title    = "Unauthorized!",
            texts    = "You lack the necessary permissions to timeout members.",
            subtitle = "Invalid permissions.",
        )
        return

    if member.id == actor.id:
        await send_minor_error(interaction, "You cannot timeout yourself.")
        return

    can_moderate, error_msg = base.check_can_moderate_target(actor, member)
    if not can_moderate:
        await send_minor_error(interaction, error_msg)
        return

    duration_seconds = base.parse_duration(duration)
    if not duration_seconds:
        await send_minor_error(interaction, "Invalid duration format. Use: 30s, 5m, 1h, 2d, 1w")
        return

    max_duration = 28 * 86400
    if duration_seconds > max_duration:
        await send_minor_error(interaction, "Timeout duration cannot exceed 28 days.")
        return

    guild = interaction.guild
    if not guild:
        return

    if not is_director(actor):
        can_proceed, error_msg = base.check_rate_limit(str(actor.id), "timeout")
        if not can_proceed:
            await send_major_error(
                interaction,
                texts    = f"Rate limit exceeded. {error_msg}.\n"
                           f"Continuing to exceed rate limits will result in your own quarantine.",
                subtitle =  "Rate limit exceeded.",
            )
            await base.auto_quarantine_moderator(actor, guild)
            return

        base.add_rate_limit_entry(str(actor.id), "timeout")

    _ = await interaction.response.defer(ephemeral = True)

    try:
        until = discord.utils.utcnow() + timedelta(seconds=duration_seconds)
        await member.timeout(until, reason=f"Timed out by {actor}: {reason}")

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
            title = "Member Timed Out",
            color = COLOR_YELLOW,
            timestamp = datetime.now(UTC),
        )
        _ = embed.add_field(name = "Member",    value = member.mention,                      inline = True)
        _ = embed.add_field(name = "Moderator", value = actor.mention,                       inline = True)
        _ = embed.add_field(name = "Duration",  value = duration,                            inline = True)
        _ = embed.add_field(name = "Expires",   value = discord.utils.format_dt(until, "R"), inline = True)
        _ = embed.add_field(name = "Reason",    value = reason,                              inline = False)
        if proof:
            _ = embed.set_image(url=proof.url)

        await interaction.followup.send(embed=embed, ephemeral = True)

    except discord.Forbidden:
        await send_major_error(
            interaction,
            texts    = "I lack the necessary permissions to timeout this member.",
            subtitle = "Invalid configuration. Contact the owner.",
        )
