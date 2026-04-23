from __future__ import annotations

import contextlib
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
    users       : str          | None,
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

    targets: list[discord.User] = []

    if user is not None:
        targets.append(user)

    unresolved_ids: list[str] = []
    if users:
        raw_ids = [chunk.strip().strip("<@!>").strip() for chunk in users.split(",")]
        for raw_id in raw_ids:
            if not raw_id.isdigit():
                unresolved_ids.append(raw_id)
                continue
            resolved = self.bot.get_user(int(raw_id))
            if not resolved:
                with contextlib.suppress(discord.NotFound, discord.HTTPException):
                    resolved = await self.bot.fetch_user(int(raw_id))
            if resolved:
                targets.append(resolved)
            else:
                unresolved_ids.append(raw_id)

    if not targets and case_id is None:
        _ = errors.add_field(
            title     = "add note",
            msg_type  = "warning",
            subfields = [
                errors.add_subfield(
                    subtitle = "You must provide either user/users or a case ID.",
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

    if case_id is not None:
        existing_case = self.cases_manager.get_case_by_id(case_id)
        if existing_case is None or existing_case.get("guild_id") != guild.id:
            _ = errors.add_field(
                title     = "add note",
                msg_type  = "warning",
                subfields = [
                    errors.add_subfield(
                        subtitle = f"Case **#{case_id}** was not found in this server.",
                        footer   = "Bad argument",
                    ),
                ],
            )

    if unresolved_ids:
        _ = errors.add_field(
            title     = "add note",
            msg_type  = "warning",
            subfields = [
                errors.add_subfield(
                    subtitle = f"Could not resolve: {', '.join(f'`{rid}`' for rid in unresolved_ids[:10])}",
                    footer   = "Bad argument",
                ),
            ],
        )

    if errors.has_errors():
        await errors.send()
        return

    if targets:
        unique_targets = list({u.id: u for u in targets}.values())
        case_ids = await self.cases_manager.add_notes_for_users(
            guild            = guild,
            moderator        = actor,
            content          = content,
            users            = unique_targets,
            visibility_level = visibility,
        )
        description = f"added {len(case_ids)} note case(s) for {len(unique_targets)} user(s)."
    else:
        new_case_id = await self.cases_manager.add_note(
            guild            = guild,
            moderator        = actor,
            content          = content,
            related_case_id  = case_id,
            visibility_level = visibility,
        )
        description = f"added #{new_case_id} note to Case **#{case_id}**."

    await send_custom_message(
        interaction,
        msg_type = "success",
        title    = description,
    )
