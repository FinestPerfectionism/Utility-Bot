from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from ._group_cog import CasesCommands

from core.permissions import is_director
from core.responses import send_custom_message

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /cases delete-entry Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_delete_entry(
    self        : CasesCommands,
    interaction : discord.Interaction,
    case_id     : int,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not is_director(actor):
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

    case = self.cases_manager.get_case_by_id(case_id)

    if not case or case["guild_id"] != guild.id:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "delete case entry",
            subtitle = f"Case **#{case_id}** was not found.",
            footer   = "Bad argument",
        )
        return

    _ = self.cases_manager.delete_case(case_id)

    await send_custom_message(
        interaction,
        msg_type = "success",
        title    = f"deleted #{case_id}",
    )
