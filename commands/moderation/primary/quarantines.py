from __future__ import annotations

import discord
from discord.ext import commands

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._base import ModerationBase

from core.utils import send_major_error

from constants import COLOR_ORANGE

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation quarantines Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_quarantines(
    base:        "ModerationBase",
    interaction: discord.Interaction,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_view(actor):
        await send_major_error(
            interaction,
            title="Unauthorized!",
            texts="You lack the necessary permissions to view quarantined members.",
            subtitle="No permissions."
        )
        return

    if not base.data.get("quarantined"):
        await interaction.response.send_message(
            "No members are currently quarantined.",
            ephemeral=True
        )
        return

    guild = interaction.guild
    if guild is None:
        return

    embed = discord.Embed(
        title="Quarantined Members",
        color=COLOR_ORANGE,
        timestamp=datetime.now()
    )

    for user_id, entry in base.data["quarantined"].items():
        target         = guild.get_member(int(user_id))
        member_name    = target.mention if target else f"Unknown User ({user_id})"
        quarantined_at = datetime.fromisoformat(entry["quarantined_at"])

        embed.add_field(
            name=member_name,
            value=(
                f"Quarantined: {discord.utils.format_dt(quarantined_at, 'R')}\n"
                f"Saved roles: {len(entry['roles'])}"
            ),
            inline=False
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .quarantines Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_quarantines_prefix(
    base: "ModerationBase",
    ctx:  commands.Context[commands.Bot],
) -> None:
    actor = ctx.author
    if not isinstance(actor, discord.Member):
        return

    if not base.can_view(actor):
        return

    if not base.data.get("quarantined"):
        await ctx.send("No members are currently quarantined.")
        return

    guild = ctx.guild
    if not guild:
        return

    embed = discord.Embed(
        title="Quarantined Members",
        color=COLOR_ORANGE,
        timestamp=datetime.now()
    )

    for user_id, entry in base.data["quarantined"].items():
        target         = guild.get_member(int(user_id))
        member_name    = target.mention if target else f"Unknown User ({user_id})"
        quarantined_at = datetime.fromisoformat(entry["quarantined_at"])

        embed.add_field(
            name=member_name,
            value=(
                f"Quarantined: {discord.utils.format_dt(quarantined_at, 'R')}\n"
                f"Saved roles: {len(entry['roles'])}"
            ),
            inline=False
        )

    await ctx.send(embed=embed)