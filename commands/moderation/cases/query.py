from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import discord

if TYPE_CHECKING:
    from datetime import datetime

    from ._group_cog import CasesCommands

from constants import COLOR_GREEN
from core.responses import multi_custom_message, send_custom_message

from ._base import CaseQueryPaginator

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /cases query Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_query(
    self          : CasesCommands,
    interaction   : discord.Interaction,
    user          : discord.User | None,
    moderator     : discord.User | None,
    case_type     : Literal[
        "ban", "unban", "kick",
        "timeout", "untimeout",
        "quarantine_add", "quarantine_remove",
        "lockdown_add", "lockdown_remove",
        "purge", "note",
    ]                    | None,
    contains      : str  | None,
    after         : str  | None,
    before        : str  | None,
    *,
    include_notes : bool,
    mass_only     : bool,
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

    after_dt  : datetime | None = None
    before_dt : datetime | None = None

    if after:
        after_dt = self.parse_dt(after)
        if after_dt is None:
            _ = errors.add_field(
                title     = "query cases",
                msg_type  = "warning",
                subfields = [
                    errors.add_subfield(
                        subtitle = "Invalid `after` date. Use ISO format: `YYYY-MM-DD`.",
                        footer   = "Bad argument",
                    ),
                ],
            )

    if before:
        before_dt = self.parse_dt(before)
        if before_dt is None:
            _ = errors.add_field(
                title     = "query cases",
                msg_type  = "warning",
                subfields = [
                    errors.add_subfield(
                        subtitle = "Invalid `before` date. Use ISO format: `YYYY-MM-DD`.",
                        footer   = "Bad argument",
                    ),
                ],
            )

    if errors.has_errors():
        await errors.send()
        return

    _ = await interaction.response.defer(ephemeral=True)

    cases = self.cases_manager.get_cases(
        guild_id      = guild.id,
        user_id       = user.id if user else None,
        moderator_id  = moderator.id if moderator else None,
        case_type     = case_type,
        contains      = contains,
        after         = after_dt,
        before        = before_dt,
        include_notes = include_notes,
    )

    if mass_only:
        cases = [
            c for c in cases
            if isinstance(c.get("metadata"), dict) and c["metadata"].get("mass_action")
        ]

    cases = [c for c in cases if self.can_see_case(actor, c)]

    if not cases:
        filters: list[str] = []
        if user:
            filters.append(f"user {user.mention}")
        if moderator:
            filters.append(f"moderator {moderator.mention}")
        if case_type:
            filters.append(f"type **{case_type.replace('_', ' ')}**")
        if contains:
            filters.append(f"containing **{contains}**")

        filter_text = " and ".join(filters)
        description = f"No cases found{' for ' + filter_text if filter_text else ''}."

        embed = discord.Embed(description = description, color = COLOR_GREEN)
        await interaction.followup.send(embed = embed, ephemeral = True)
        return

    title_parts: list[str] = []
    if user:
        title_parts.append(f"for {user.name}")
    if moderator:
        title_parts.append(f"by {moderator.name}")
    if case_type:
        title_parts.append(f"({case_type.replace('_', ' ').title()})")

    title = "Cases " + " ".join(title_parts) if title_parts else "All Cases"

    view = CaseQueryPaginator(interaction, cases, title, self.COLOR_MAP)
    await interaction.followup.send(embed = view.get_embed(), view = view, ephemeral = True)
