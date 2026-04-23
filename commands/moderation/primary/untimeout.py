from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from ._base import ModerationBase

from constants import COLOR_GREEN
from core.cases import CaseType
from core.responses import send_custom_message

from ._base import MemberPickerView

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation un-timeout Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_untimeout(
    base        : ModerationBase,
    interaction : discord.Interaction,
    member      : discord.Member | None,
    reason      : str | None,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_untimeout(actor):
        await send_custom_message(
            interaction,
            msg_type = "error",
            title    = "run command",
            subtitle = "You are not authorized to run this command.",
            footer   = "No permissions",
        )
        return

    if member is None:
        picker = MemberPickerView(
            base,
            "Un-timeout",
            "none",
            precheck_callback = lambda _moderator, target: (
                (False, "Member is not currently timed out.")
                if not target.is_timed_out()
                else (True, "")
            ),
            execute_callback = lambda i, m, data: _execute_untimeout(
                base, i, actor, m, str(data["reason"]),
            ),
        )
        _ = await interaction.response.send_message(view = picker, ephemeral = True)
        return

    if not reason:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "remove member timeout",
            subtitle = "You must provide a reason.",
            footer   = "Bad argument",
        )
        return

    if not member.is_timed_out():
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "remove member timeout",
            subtitle = f"{member.mention} is not currently timed out.",
            footer   = "Bad argument",
        )
        return

    _ = await interaction.response.defer(ephemeral = True)

    guild = interaction.guild
    if not guild:
        return

    ok, msg = await _execute_untimeout(base, interaction, actor, member, reason)
    if not ok:
        await send_custom_message(
            interaction,
            msg_type          = "error",
            title             = "remove member timeout",
            subtitle          = msg,
            footer            = "Bad configuration",
            contact_bot_owner = True,
        )

async def _execute_untimeout(
    base        : ModerationBase,
    interaction : discord.Interaction,
    actor       : discord.Member,
    member      : discord.Member,
    reason      : str,
) -> tuple[bool, str]:
    guild = interaction.guild
    if not guild:
        return False, "No guild context."
    bot_member = guild.me
    if not bot_member or not bot_member.guild_permissions.moderate_members:
        return False, "I lack permissions to timeout members: `Moderate Members`"

    try:
        await member.timeout(None, reason = f"Timeout removed by {actor}: {reason}")

        if "timeouts" in base.data and str(member.id) in base.data["timeouts"]:
            del base.data["timeouts"][str(member.id)]
            base.save_data()

        _ = await base.cases_manager.log_case(
            guild       = guild,
            case_type   = CaseType.UNTIMEOUT,
            moderator   = actor,
            reason      = reason,
            target_user = member,
        )

        embed = discord.Embed(
            title     = "Timeout Removed",
            color     = COLOR_GREEN,
            timestamp = datetime.now(UTC),
        )
        _ = embed.add_field(name = "Member",           value = member.mention, inline = True)
        _ = embed.add_field(name = "Senior Moderator", value = actor.mention,  inline = True)
        _ = embed.add_field(name = "Reason",           value = reason,         inline = False)
    except discord.Forbidden:
        return False, "I lack permissions to timeout members: `Moderate Members`"
    else:
        if interaction.response.is_done():
            await interaction.followup.send(embed = embed, ephemeral = True)
        else:
            _ = await interaction.response.send_message(embed = embed, ephemeral = True)
        return True, "ok"
