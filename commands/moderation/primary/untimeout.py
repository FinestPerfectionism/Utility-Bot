from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from ._base import ModerationBase

from constants import COLOR_GREEN
from core.cases import CaseType
from core.responses import send_custom_message

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation un-timeout Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_untimeout(
    base        : ModerationBase,
    interaction : discord.Interaction,
    member      : discord.Member,
    reason      : str,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_untimeout(actor):
        await send_custom_message(
            interaction,
            msg_type = "error",
            title    = "run command",
            subtitle = "You are not authorized to run this command.",
            footer   = "No permissions",
        )
        return

    if not member.is_timed_out():
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "un-timeout member",
            subtitle = f"{member.mention} is not currently timed out.",
            footer   = "Bad argument",
        )
        return

    _ = await interaction.response.defer(ephemeral = True)

    guild = interaction.guild
    if not guild:
        return

    try:
        await member.timeout(None, reason = f"Timeout removed by {actor}: {reason}")

        if "timeouts" in base.data and str(member.id) in base.data["timeouts"]:
            del base.data["timeouts"][str(member.id)]
            base.save_data()

        _ = await base.cases_manager.log_case(
            guild       = guild,
            case_type   = CaseType.UNTIMEOUT,
            moderator   = actor,
            reason      = reason,
            target_user = member,
        )

        embed = discord.Embed(
            title     = "Timeout Removed",
            color     = COLOR_GREEN,
            timestamp = datetime.now(UTC),
        )
        _ = embed.add_field(name = "Member",           value = member.mention, inline = True)
        _ = embed.add_field(name = "Senior Moderator", value = actor.mention,  inline = True)
        _ = embed.add_field(name = "Reason",           value = reason,         inline = False)
        await interaction.followup.send(embed = embed, ephemeral = True)

    except discord.Forbidden:
        await send_custom_message(
            interaction,
            msg_type          = "error",
            title             = "un-timeout members",
            subtitle          = "I lack permissions to timeout members: `Moderate Members`",
            footer            = "Bad configuration",
            contact_bot_owner = True,
        )
