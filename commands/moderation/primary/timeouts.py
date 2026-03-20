from __future__ import annotations

import discord
from discord.ext import commands

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._base import ModerationBase

from ._base import ModerationListPaginator
from core.utils import send_major_error

from constants import (
    COLOR_GREEN,
    COLOR_YELLOW
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation timeouts Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_timeouts(
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
            texts    = "You lack the necessary permissions to view timeouts.",
            subtitle = "Invalid permissions."
        )
        return

    guild = interaction.guild
    if not guild:
        return

    _ = await interaction.response.defer(ephemeral=True)

    timed_out_members = [m for m in guild.members if m.is_timed_out()]

    if not timed_out_members:
        embed = discord.Embed(
            description = "No members are currently timed out.",
            color       = COLOR_GREEN
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    fields: list[tuple[str, str]] = []
    for member in timed_out_members:
        timeout_data = base.data.get("timeouts", {}).get(str(member.id))

        if timeout_data and member.timed_out_until:
            timed_out_at = datetime.fromisoformat(timeout_data["timed_out_at"])
            reason       = timeout_data["reason"]
            value        = (
                f"Timed out: {discord.utils.format_dt(timed_out_at, 'R')}\n"
                f"Expires: {discord.utils.format_dt(member.timed_out_until, 'R')}\n"
                f"Reason: {reason}"
            )
        elif member.timed_out_until:
            value = f"Expires: {discord.utils.format_dt(member.timed_out_until, 'R')}"
        else:
            value = "No data available"

        fields.append((f"{member} ({member.id})", value))

    view = ModerationListPaginator(interaction, "Timed Out Members", COLOR_YELLOW, fields)
    await interaction.followup.send(embed=view.get_embed(), view=view, ephemeral=True)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .timeouts Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_timeouts_prefix(
    base : "ModerationBase",
    ctx  : commands.Context[commands.Bot],
) -> None:
    actor = ctx.author
    if not isinstance(actor, discord.Member):
        return

    if not base.can_view_moderation(actor):
        await base.send_prefix_denied(
            ctx,
            "Failed to retrieve timeout list",
            "You lack the necessary permissions to view timeouts."
        )
        return

    guild = ctx.guild
    if not guild:
        return

    timed_out_members = [m for m in guild.members if m.is_timed_out()]

    if not timed_out_members:
        embed = discord.Embed(
            description = "No members are currently timed out.",
            color       = COLOR_GREEN
        )
        _ = await ctx.send(embed=embed)
        return

    fields: list[tuple[str, str]] = []
    for member in timed_out_members:
        timeout_data = base.data.get("timeouts", {}).get(str(member.id))

        if timeout_data and member.timed_out_until:
            timed_out_at = datetime.fromisoformat(timeout_data["timed_out_at"])
            reason       = timeout_data["reason"]
            value        = (
                f"Timed out: {discord.utils.format_dt(timed_out_at, 'R')}\n"
                f"Expires: {discord.utils.format_dt(member.timed_out_until, 'R')}\n"
                f"Reason: {reason}"
            )
        elif member.timed_out_until:
            value = f"Expires: {discord.utils.format_dt(member.timed_out_until, 'R')}"
        else:
            value = "No data available"

        fields.append((f"{member} ({member.id})", value))

    msg = await ctx.send(embed=discord.Embed(description="Loading...", color=COLOR_YELLOW))
    view = ModerationListPaginator(
        ctx,
        "Timed Out Members",
        COLOR_YELLOW,
        fields,
        delete_delay    = 10,
        delete_callback = msg.delete,
    )
    _ = await msg.edit(embed=view.get_embed(), view=view)