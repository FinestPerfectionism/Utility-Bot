from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import discord

if TYPE_CHECKING:
    from ._group_cog import CasesCommands

from core.permissions import is_director
from core.responses import multi_custom_message, send_custom_message

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /cases add-note Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_add_note(
    self        : CasesCommands,
    interaction : discord.Interaction,
    content     : str,
    user        : discord.User | None,
    case_id     : int          | None,
    visibility  : Literal["moderators", "senior_moderators", "directors"],
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not self.can_view(actor):
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

    errors = multi_custom_message(interaction)

    if user is None and case_id is None:
        _ = errors.add_field(
            title     = "add note",
            msg_type  = "warning",
            subfields = [
                errors.add_subfield(
                    subtitle = "You must provide either a user or a case ID.",
                    footer   = "Bad argument",
                ),
            ],
        )

    if visibility == "directors" and not is_director(actor):
        _ = errors.add_field(
            title     = "add note",
            msg_type  = "warning",
            subfields = [
                errors.add_subfield(
                    subtitle = "Only Directors can create director-level notes.",
                    footer   = "No permissions",
                ),
            ],
        )

    if errors.has_errors():
        await errors.send()
        return

    new_case_id = await self.cases_manager.add_note(
        guild            = guild,
        moderator        = actor,
        content          = content,
        target_user      = user,
        related_case_id  = case_id,
        visibility_level = visibility,
    )

    description = (
        f"added #{new_case_id} note for {user.mention}."
        if user else
        f"added #{new_case_id} note to Case **#{case_id}**."
    )

    await send_custom_message(
        interaction,
        msg_type = "success",
        title    = description,
    )
