from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from ._base import ModerationBase

from core.cases import CaseType
from core.responses import send_custom_message

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation un-ban Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_unban(
    base        : ModerationBase,
    interaction : discord.Interaction,
    user        : str | None,
    users       : str | None,
    reason      : str | None,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_reverse_actions(actor):
        await send_custom_message(
            interaction,
            msg_type = "error",
            title    = "run command",
            subtitle = "You are not authorized to run this command.",
            footer   = "No permissions",
        )
        return

    if not reason:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "remove member ban",
            subtitle = "You must provide a reason.",
            footer   = "Bad argument",
        )
        return

    guild = interaction.guild
    if not guild:
        return

    identifiers: list[str] = []
    if user:
        identifiers.append(user)
    if users:
        identifiers.extend(chunk.strip() for chunk in users.split(",") if chunk.strip())

    if not identifiers:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "remove member ban",
            subtitle = "You must provide at least one user identifier.",
            footer   = "Bad argument",
        )
        return

    _ = await interaction.response.defer(ephemeral = True)

    results: list[tuple[str, bool, str]] = []
    for identifier in identifiers:
        ok, msg = await _execute_unban(base, guild, actor, identifier, reason)
        results.append((identifier, ok, msg))

    success_count = len([r for r in results if r[1]])
    fail = [r for r in results if not r[1]]
    subtitle = f"Succeeded: **{success_count}** | Failed: **{len(fail)}**"
    if fail:
        subtitle += "\n" + "\n".join(f"- `{ident}`: {msg}" for ident, _ok, msg in fail[:10])

    await send_custom_message(
        interaction,
        msg_type = "success" if not fail else "warning",
        title    = "complete mass un-ban run" if len(identifiers) > 1 else "remove member ban",
        subtitle = subtitle,
    )

async def _execute_unban(
    base        : ModerationBase,
    guild       : discord.Guild,
    actor       : discord.Member,
    identifier  : str,
    reason      : str,
) -> tuple[bool, str]:
    user_to_unban: discord.User | None = None
    cleaned = identifier.strip().strip("<@!>").strip()

    if cleaned.isdigit():
        with contextlib.suppress(discord.NotFound):
            user_to_unban = await base.bot.fetch_user(int(cleaned))

    if not user_to_unban:
        try:
            bans = [entry async for entry in guild.bans(limit=None)]
            for ban_entry in bans:
                if (
                    str(ban_entry.user.id) == cleaned or
                    str(ban_entry.user) == cleaned or
                    ban_entry.user.name == cleaned
                ):
                    user_to_unban = ban_entry.user
                    break
        except discord.Forbidden:
            return False, "I lack permissions to view banned members: `Ban Members`"

    if not user_to_unban:
        return False, "Could not find banned user"

    try:
        await guild.unban(user_to_unban, reason = f"Unbanned by {actor}: {reason}")
        if "bans" in base.data and str(user_to_unban.id) in base.data["bans"]:
            del base.data["bans"][str(user_to_unban.id)]
            base.save_data()

        _ = await base.cases_manager.log_case(
            guild       = guild,
            case_type   = CaseType.UNBAN,
            moderator   = actor,
            reason      = reason,
            target_user = user_to_unban,
        )
        return True, "ok"
    except discord.NotFound:
        return False, "User is not banned"
    except discord.Forbidden:
        return False, "I lack permissions to unban members: `Ban Members`"
