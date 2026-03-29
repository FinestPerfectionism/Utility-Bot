from __future__ import annotations

import discord
import contextlib
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._base import ModerationBase

from commands.moderation.cases import CaseType

from core.utils import (
    send_major_error,
    send_minor_error
)

from constants import (
    COLOR_GREEN,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation un-ban Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_unban(
    base        : "ModerationBase",
    interaction : discord.Interaction,
    user        : str,
    reason      : str,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_reverse_actions(actor):
        await send_major_error(
            interaction,
            title    = "Unauthorized!",
            texts    = "You lack the necessary permissions to unban members.",
            subtitle = "Invalid permissions."
        )
        return

    guild = interaction.guild
    if not guild:
        return

    _ = await interaction.response.defer(ephemeral = True)

    user_to_unban: discord.User | None = None

    if user.isdigit():
        with contextlib.suppress(discord.NotFound):
            user_to_unban = await base.bot.fetch_user(int(user))

    if not user_to_unban:
        try:
            bans = [entry async for entry in guild.bans(limit=None)]
            for ban_entry in bans:
                if (
                    str(ban_entry.user.id) == user or
                    str(ban_entry.user) == user or
                    ban_entry.user.name == user
                ):
                    user_to_unban = ban_entry.user
                    break
        except discord.Forbidden:
            await send_major_error(
                interaction,
                texts    = "I lack the necessary permissions to view bans.",
                subtitle = "Invalid configuration. Contact the owner."
            )
            return

    if not user_to_unban:
        await send_minor_error(interaction, f"Could not find banned user: {user}")
        return

    try:
        await guild.unban(user_to_unban, reason=f"Unbanned by {actor}: {reason}")

        if "bans" in base.data and str(user_to_unban.id) in base.data["bans"]:
            del base.data["bans"][str(user_to_unban.id)]
            base.save_data()

        _ = await base.cases_manager.log_case(
            guild       = guild,
            case_type   = CaseType.UNBAN,
            moderator   = actor,
            reason      = reason,
            target_user = user_to_unban
        )

        embed = discord.Embed(
            title="User Unbanned",
            color=COLOR_GREEN,
            timestamp = datetime.now()
        )
        _ = embed.add_field(name="User",     value = f"{user_to_unban.mention} ({user_to_unban.id})", inline = True)
        _ = embed.add_field(name="Director", value = actor.mention,                                   inline = True)
        _ = embed.add_field(name="Reason",   value = reason,                                          inline = False)

        await interaction.followup.send(embed=embed, ephemeral = True)

    except discord.NotFound:
        await send_minor_error(interaction, f"{user_to_unban.mention} is not banned.")
    except discord.Forbidden:
        await send_major_error(
            interaction,
            texts    = "I lack the necessary permissions to unban this member.",
            subtitle = "Invalid configuration. Contact the owner."
        )
