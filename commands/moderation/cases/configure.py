from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from ._group_cog import CasesCommands

from core.responses import send_custom_message

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /cases configure Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_configure(
    self        : CasesCommands,
    interaction : discord.Interaction,
    channel     : discord.TextChannel,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not self.can_configure(actor):
        await send_custom_message(
            interaction,
            msg_type = "error",
            title    = "run command",
            subtitle = "You are not authorized to run this command.",
            footer   = "No permissions",
        )
        return

    self.cases_manager.config["log_channel_id"] = channel.id
    self.cases_manager.save_config()

    await send_custom_message(
        interaction,
        msg_type = "success",
        title    = f"set case log channel to {channel.mention}",
    )
