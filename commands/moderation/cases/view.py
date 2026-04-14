from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from ._group_cog import CasesCommands

from core.responses import send_custom_message

from ._base import CaseViewPaginator

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /cases view Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_view(
    self        : CasesCommands,
    interaction : discord.Interaction,
    case_id     : int,
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

    _ = await interaction.response.defer(ephemeral=True)

    case = self.cases_manager.get_case_by_id(case_id)

    if not case or case["guild_id"] != guild.id:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "view case",
            subtitle = f"Case **#{case_id}** was not found.",
            footer   = "Bad argument",
        )
        return

    if not self.can_see_case(actor, case):
        await send_custom_message(
            interaction,
            msg_type = "error",
            title    = "run command",
            subtitle = "You are not authorized to run this command.",
            footer   = "No permissions",
        )
        return

    embed = await self.build_case_embed(self.bot, guild, case)

    notes         = self.cases_manager.get_related_notes(case_id, guild.id)
    visible_notes = [n for n in notes if self.can_see_case(actor, n)]

    if not visible_notes:
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    view = CaseViewPaginator(interaction, embed, visible_notes)
    await interaction.followup.send(embed=view.get_embed(), view=view, ephemeral=True)
