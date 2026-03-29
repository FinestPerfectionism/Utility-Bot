from __future__ import annotations

import discord
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._base import ModerationBase

from ._base import ModerationListPaginator
from core.utils import send_major_error

from constants import (
    COLOR_GREEN,
    COLOR_ORANGE
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation quarantines Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_quarantines(
    base        : "ModerationBase",
    interaction : discord.Interaction,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_view_moderation(actor):
        await send_major_error(
            interaction,
            title    = "Unauthorized!",
            texts    = "You lack the necessary permissions to view quarantined members.",
            subtitle = "No permissions."
        )
        return

    if not base.data.get("quarantined"):
        embed = discord.Embed(
            description = "No members are currently quarantined.",
            color       = COLOR_GREEN
        )
        _ = await interaction.response.send_message(embed=embed, ephemeral = True)
        return

    guild = interaction.guild
    if guild is None:
        return

    _ = await interaction.response.defer(ephemeral = True)

    fields: list[tuple[str, str]] = []
    for user_id, entry in base.data["quarantined"].items():
        target         = guild.get_member(int(user_id))
        member_name    = target.mention if target else f"Unknown User ({user_id})"
        quarantined_at = datetime.fromisoformat(entry["quarantined_at"])
        fields.append((
            member_name,
            f"Quarantined: {discord.utils.format_dt(quarantined_at, 'R')}\n"
            f"Saved roles: {len(entry['roles'])}"
        ))

    view = ModerationListPaginator(interaction, "Quarantined Members", COLOR_ORANGE, fields)
    await interaction.followup.send(embed=view.get_embed(), view = view, ephemeral = True)