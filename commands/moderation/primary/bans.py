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
    COLOR_BLACK,
    DENIED_EMOJI_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation bans Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_bans(
    base:        "ModerationBase",
    interaction: discord.Interaction,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_view(actor):
        await send_major_error(
            interaction,
            title    = "Unauthorized!",
            texts    = "You lack the necessary permissions to view bans.",
            subtitle = "Invalid permissions."
        )
        return

    guild = interaction.guild
    if not guild:
        return

    await interaction.response.defer(ephemeral=True)

    try:
        bans = [entry async for entry in guild.bans(limit=None)]

        if not bans:
            embed = discord.Embed(
                description = "No members are currently banned.",
                color       = COLOR_GREEN
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        fields: list[tuple[str, str]] = []
        for ban_entry in bans:
            user     = ban_entry.user
            ban_data = base.data.get("bans", {}).get(str(user.id))

            if ban_data:
                banned_at = datetime.fromisoformat(ban_data["banned_at"])
                reason    = ban_data["reason"]
                value     = f"Banned: {discord.utils.format_dt(banned_at, 'R')}\nReason: {reason}"
            else:
                value = f"Reason: {ban_entry.reason}"

            fields.append((f"{user} ({user.id})", value))

        view = ModerationListPaginator(interaction, "Banned Members", COLOR_BLACK, fields)
        await interaction.followup.send(embed=view.get_embed(), view=view, ephemeral=True)

    except discord.Forbidden:
        await send_major_error(
            interaction,
            "I lack the necessary permissions to view bans.",
            subtitle="Invalid configuration. Contact the owner."
        )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .bans Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_bans_prefix(
    base: "ModerationBase",
    ctx:  commands.Context[commands.Bot],
) -> None:
    actor = ctx.author
    if not isinstance(actor, discord.Member):
        return

    if not base.can_view(actor):
        return

    guild = ctx.guild
    if not guild:
        return

    try:
        bans = [entry async for entry in guild.bans(limit=None)]

        if not bans:
            embed = discord.Embed(
                description = "No members are currently banned.",
                color       = COLOR_GREEN
            )
            await ctx.send(embed=embed)
            return

        fields: list[tuple[str, str]] = []
        for ban_entry in bans:
            user     = ban_entry.user
            ban_data = base.data.get("bans", {}).get(str(user.id))

            if ban_data:
                banned_at = datetime.fromisoformat(ban_data["banned_at"])
                reason    = ban_data["reason"]
                value     = f"Banned: {discord.utils.format_dt(banned_at, 'R')}\nReason: {reason}"
            else:
                value = f"Reason: {ban_entry.reason}"

            fields.append((f"{user} ({user.id})", value))

        msg = await ctx.send(embed=discord.Embed(description="Loading...", color=COLOR_BLACK))
        view = ModerationListPaginator(
            ctx,
            "Banned Members",
            COLOR_BLACK,
            fields,
            delete_delay    = 10,
            delete_callback = msg.delete,
        )
        await msg.edit(embed=view.get_embed(), view=view)

    except discord.Forbidden:
        await ctx.send(
            f"{DENIED_EMOJI_ID} **Failed to retrieve ban list!**\n"
            f"I lack the necessary permissions to view bans.\n"
            f"-# Contact the owner."
        )