from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from ._base import ModerationBase

from constants import COLOR_BLACK, COLOR_GREEN
from core.responses import send_custom_message

from ._base import ModerationListPaginator

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation bans Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_bans(
    base        : ModerationBase,
    interaction : discord.Interaction,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_view_moderation(actor):
        await send_custom_message(
            interaction,
            msg_type = "error",
            title    = "run command",
            subtitle = "You are not authorized to run this command.",
            footer   = "No permissions",
        )
        return

    guild = interaction.guild
    if not guild:
        return

    _ = await interaction.response.defer(ephemeral = True)

    try:
        bans = [entry async for entry in guild.bans(limit=None)]

        if not bans:
            embed = discord.Embed(
                description = "No members are currently banned.",
                color       = COLOR_GREEN,
            )
            await interaction.followup.send(embed = embed, ephemeral = True)
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
        await interaction.followup.send(embed = view.get_embed(), view = view, ephemeral = True)

    except discord.Forbidden:
        await send_custom_message(
            interaction,
            msg_type          = "error",
            title             = "view banned members",
            subtitle          = "I lack permissions to view banned members: `Ban Members`",
            footer            = "Bad configuration",
            contact_bot_owner = True,
        )
