from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from ._group_cog import CasesCommands

from core.cases import CaseType
from core.responses import multi_custom_message, send_custom_message

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /cases edit-entry Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_edit_entry(
    self        : CasesCommands,
    interaction : discord.Interaction,
    case_id     : int,
    content     : str,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    guild = interaction.guild
    if not guild:
        return

    case   = self.cases_manager.get_case_by_id(case_id)
    errors = multi_custom_message(interaction)

    if not case or case["guild_id"] != guild.id:
        _ = errors.add_field(
            title     = "edit note entry",
            msg_type  = "warning",
            subfields = [
                errors.add_subfield(
                    subtitle = f"Case **#{case_id}** was not found.",
                    footer   = "Bad argument",
                ),
            ],
        )
    elif case["type"] != CaseType.NOTE.value:
        _ = errors.add_field(
            title     = "edit note entry",
            msg_type  = "warning",
            subfields = [
                errors.add_subfield(
                    subtitle = f"Case **#{case_id}** is not a note entry and cannot be edited here.",
                    footer   = "Bad argument",
                ),
            ],
        )
    elif not self.can_edit_entry(actor, case):
        _ = errors.add_field(
            title     = "run command",
            msg_type  = "error",
            subfields = [
                errors.add_subfield(
                    subtitle = "You are not authorized to run this command.",
                    footer   = "No permissions",
                ),
            ],
        )

    if errors.has_errors():
        await errors.send()
        return

    _ = self.cases_manager.edit_case(case_id, content)

    await send_custom_message(
        interaction,
        msg_type = "success",
        title    = f"updated #{case_id}",
    )
