from __future__ import annotations

from datetime import UTC, datetime
from typing import (
    TYPE_CHECKING,
    Any,
)

import discord

if TYPE_CHECKING:
    from ._base import ModerationBase

from constants import COLOR_RED
from core.cases import CaseType
from core.permissions import is_director
from core.responses import send_custom_message

from ._base import MemberPickerView

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation ban Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_ban(
    base            : ModerationBase,
    interaction     : discord.Interaction,
    member          : discord.Member | None,
    reason          : str | None,
    delete_messages : int                | None = 0,
    proof           : discord.Attachment | None = None,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_apply_standard_actions(actor):
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
            "Ban",
            "ban",
            precheck_callback = base.check_can_moderate_target,
            execute_callback = lambda i, m, data: _execute_ban(
                base, i, actor, m, data["reason"], delete_messages or 0, data.get("proof"),
            ),
        )
        _ = await interaction.response.send_message(view = picker, ephemeral = True)
        return

    if not reason:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "ban member",
            subtitle = "You must provide a reason.",
            footer   = "Bad argument",
        )
        return

    if member.id == actor.id:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "ban member",
            subtitle = "You cannot ban yourself.",
            footer   = "Bad argument",
        )
        return

    can_moderate, error_msg = base.check_can_moderate_target(actor, member)
    if not can_moderate:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "ban member",
            subtitle = error_msg,
            footer   = "Bad request",
        )
        return

    guild = interaction.guild
    if not guild:
        return

    if not is_director(actor):
        can_proceed, error_msg = base.check_rate_limit(str(actor.id), "ban")
        if not can_proceed:
            await send_custom_message(
                interaction,
                msg_type          = "error",
                title             = "ban member",
                subtitle          = (
                    f"Rate limit exceeded. {error_msg}.\n"
                    "Continuing to exceed rate limits will result in your own quarantine."
                ),
                footer            = "Bad operation",
                contact_bot_owner = True,
            )
            await base.auto_quarantine_moderator(actor, guild)
            return
        base.add_rate_limit_entry(str(actor.id), "ban")

    _ = await interaction.response.defer(ephemeral = True)
    ok, msg = await _execute_ban(base, interaction, actor, member, reason, delete_messages or 0, proof)
    if not ok:
        await send_custom_message(
            interaction,
            msg_type          = "error",
            title             = "ban member",
            subtitle          = msg,
            footer            = "Bad operation",
            contact_bot_owner = True,
        )

async def _execute_ban(
    base            : ModerationBase,
    interaction     : discord.Interaction,
    actor           : discord.Member,
    member          : discord.Member,
    reason          : str,
    delete_messages : int,
    proof           : discord.Attachment | None,
) -> tuple[bool, str]:
    guild = interaction.guild
    if not guild:
        return False, "No guild context."
    bot_member = guild.me
    if not bot_member or not guild.me.guild_permissions.ban_members:
        return False, "I lack permissions to ban members: `Ban Members`"
    if member.top_role >= bot_member.top_role:
        return False, "Target user is above or equal to my highest role."

    dm_value        = delete_messages
    delete_messages = max(0, min(7, dm_value))

    try:
        await member.ban(
            reason                 = f"Banned by {actor}: {reason}",
            delete_message_seconds = delete_messages * 86400,
        )

        if "bans" not in base.data:
            base.data["bans"] = {}

        base.data["bans"][str(member.id)] = {
            "banned_at" : datetime.now(UTC).isoformat(),
            "banned_by" : actor.id,
            "reason"    : reason,
        }
        base.save_data()

        metadata: dict[str, Any] = {"delete_message_days": delete_messages}
        if proof:
            metadata["proof_url"] = proof.url

        _ = await base.cases_manager.log_case(
            guild       = guild,
            case_type   = CaseType.BAN,
            moderator   = actor,
            reason      = reason,
            target_user = member,
            metadata    = metadata,
        )

        embed = discord.Embed(
            title     = "Member Banned",
            color     = COLOR_RED,
            timestamp = datetime.now(UTC),
        )
        _ = embed.add_field(name = "Member",    value = f"{member.mention} ({member.id})", inline = True)
        _ = embed.add_field(name = "Moderator", value = actor.mention,                     inline = True)
        _ = embed.add_field(name = "Reason",    value = reason,                            inline = False)
        if proof:
            _ = embed.set_image(url = proof.url)

    except discord.Forbidden:
        return False, "I lack permissions to ban members: `Ban Members`"
    else:
        if interaction.response.is_done():
            await interaction.followup.send(embed = embed, ephemeral = True)
        else:
            _ = await interaction.response.send_message(embed = embed, ephemeral = True)
        return True, "ok"
