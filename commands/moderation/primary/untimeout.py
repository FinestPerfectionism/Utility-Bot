from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from ._base import ModerationBase

from commands.moderation.cases import CaseType
from constants import (
    COLOR_GREEN,
)
from core.utils import send_major_error, send_minor_error

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
        await send_major_error(
            interaction,
            title    = "Unauthorized!",
            texts    = "You lack the necessary permissions to remove timeouts.",
            subtitle = "Invalid permissions.",
        )
        return

    if not member.is_timed_out():
        await send_minor_error(interaction, f"{member.mention} is not currently timed out.")
        return

    _ = await interaction.response.defer(ephemeral = True)

    guild = interaction.guild
    if not guild:
        return

    try:
        await member.timeout(None, reason=f"Timeout removed by {actor}: {reason}")

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
            timestamp = datetime.now(),
        )
        _ = embed.add_field(name = "Member", value = member.mention, inline = True)
        _ = embed.add_field(name = "Senior Moderator", value = actor.mention, inline = True)
        _ = embed.add_field(name = "Reason", value = reason, inline = False)
        await interaction.followup.send(embed=embed, ephemeral = True)

    except discord.Forbidden:
        await send_major_error(
            interaction,
            texts    = "I lack the necessary permissions to un-timeout this member.",
            subtitle = "Invalid configuration. Contact the owner.",
        )
