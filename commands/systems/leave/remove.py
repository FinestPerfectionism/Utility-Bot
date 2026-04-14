from __future__ import annotations

from typing import Any

import discord

from constants import DENIED_EMOJI_ID, PERSONAL_LEAVE_ROLE_ID
from core.permissions import is_staff
from core.responses import send_custom_message

from ._base import (
    InterferenceConfirmView,
    LeaveType,
    can_manage_leave,
    describe_automation,
    entry_has_automation,
    extract_name,
    normalize_entry,
    save_data,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /leave remove Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_leave_remove(
    data        : dict[str, Any],
    interaction : discord.Interaction,
    target      : discord.Member | None,
) -> None:
    if not interaction.guild:
        await send_custom_message(
            interaction,
            msg_type = "error",
            title    = "use this command in a server",
            subtitle = "This command can only be used in a server.",
            footer   = "Bad environment",
        )
        return

    _ = await interaction.response.defer(ephemeral = True)

    invocator = interaction.user
    if not isinstance(invocator, discord.Member):
        return

    target_member = target or invocator

    if target_member.bot:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "remove personal leave from a bot",
            footer   = "Bad argument",
        )
        return

    is_self_removal  = target_member.id == invocator.id
    is_self_on_leave = str(invocator.id) in data

    if not (is_self_removal and is_self_on_leave):
        if not is_staff(invocator):
            await send_custom_message(
                interaction,
                msg_type = "error",
                title    = "run command",
                subtitle = "You are not authorized to run this command.",
                footer   = "No permissions",
            )
            return

        if not is_staff(target_member):
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "remove personal leave from this member",
                subtitle = "Target must exist within the Goobers Staff Team.",
                footer   = "Bad argument",
            )
            return

        if not can_manage_leave(invocator, target_member):
            await send_custom_message(
                interaction,
                msg_type = "error",
                title    = "run command",
                subtitle = "You are not authorized to run this command.",
                footer   = "No permissions",
            )
            return

    raw_entry = data.get(str(target_member.id))
    if not raw_entry:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "remove personal leave from this member",
            subtitle = "User is not on personal leave.",
            footer   = "Bad argument",
        )
        return

    entry = normalize_entry(raw_entry)

    personal_leave_role = interaction.guild.get_role(PERSONAL_LEAVE_ROLE_ID)
    if personal_leave_role is None:
        await send_custom_message(
            interaction,
            msg_type          = "error",
            title             = "fetch the Personal Leave role",
            subtitle          = "I lack permissions to fetch the Personal Leave role: `PERSONAL_LEAVE_ROLE_ID`",
            footer            = "Invalid IDs",
            contact_bot_owner = True,
        )
        return

    is_scheduled = entry.get("begin_date") is not None
    is_active    = personal_leave_role in target_member.roles

    if is_scheduled and not is_active:
        automation_desc = describe_automation(entry)
        warning_text = (
            f"### {DENIED_EMOJI_ID} Scheduled Leave,\n"
            f"{target_member.mention} has a pending scheduled leave entry ({automation_desc}).\n\n"
            "Confirming will cancel this scheduled leave before it applies."
        )
        view         = InterferenceConfirmView(invocator_id = invocator.id, warning_text = warning_text)
        msg          = await interaction.followup.send(view = view, ephemeral = True)
        view.message = msg
        _ = await view.wait()

        if not view.confirmed:
            return

        data.pop(str(target_member.id), None)
        save_data(data)

        who = "Your" if target_member.id == interaction.user.id else f"{target_member.mention}'s"
        await send_custom_message(
            interaction,
            msg_type = "success",
            title    = f"canceled {who} scheduled leave",
        )
        return

    if not is_active:
        data.pop(str(target_member.id), None)
        save_data(data)
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "remove personal leave from this member",
            subtitle = "User does not have the Personal Leave role.",
            footer   = "Bad argument",
        )
        return

    if entry_has_automation(entry):
        automation_desc = describe_automation(entry)
        warning_text = (
            f"### {DENIED_EMOJI_ID} Warning,\n"
            f"{target_member.mention} currently has an active automation entry ({automation_desc}).\n\n"
            "Running `/leave remove` now will override and clear that automation. Proceed?"
        )
        view         = InterferenceConfirmView(invocator_id = invocator.id, warning_text = warning_text)
        msg          = await interaction.followup.send(view = view, ephemeral = True)
        view.message = msg
        _ = await view.wait()

        if not view.confirmed:
            return

    stored_name     : str       = entry.get("original_nick") or target_member.display_name
    leave_type_str  : str       = entry.get("leave_type", LeaveType.none.value)
    stored_role_ids : list[int] = entry.get("removed_roles", [])

    roles_to_restore : list[discord.Role] = []
    if leave_type_str in (LeaveType.soft_clean.value, "soft_clean"):
        for role_id in stored_role_ids:
            restored_role = interaction.guild.get_role(role_id)
            if restored_role is not None:
                roles_to_restore.append(restored_role)

    nickname_error      : str | None = None
    roles_restore_error : str | None = None

    try:
        await target_member.remove_roles(personal_leave_role)

        current_nick   = target_member.nick or target_member.name
        base_name      = extract_name(stored_name)
        expected_long  = f"P. Leave | {base_name}"
        expected_short = f"PL | {base_name}"

        if current_nick in (expected_long, expected_short):
            try:
                _ = await target_member.edit(nick = stored_name)
            except discord.Forbidden:
                nickname_error = "forbidden"
            except discord.HTTPException:
                nickname_error = "http"

        if roles_to_restore:
            try:
                await target_member.add_roles(*roles_to_restore)
            except discord.Forbidden:
                roles_restore_error = "forbidden"
            except discord.HTTPException:
                roles_restore_error = "http"

        data.pop(str(target_member.id), None)
        save_data(data)

    except discord.Forbidden:
        await send_custom_message(
            interaction,
            msg_type          = "error",
            title             = "remove the Personal Leave role",
            subtitle          = "I lack permissions to remove roles: `Manage Roles`",
            footer            = "Bad configuration",
            contact_bot_owner = True,
        )
        return

    except discord.HTTPException:
        await send_custom_message(
            interaction,
            msg_type          = "error",
            title             = "remove the Personal Leave role",
            subtitle          = "A Discord API error occurred while removing the role. Please try again later.",
            footer            = "Bad operation",
            contact_bot_owner = True,
        )
        return

    if nickname_error == "forbidden":
        if target_member.id == interaction.guild.owner_id:
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "restore the server owner's nickname",
                subtitle = "The role was removed, but I cannot change the server owner's nickname. Please change it back manually.",
                footer   = "Bad argument",
            )
        else:
            await send_custom_message(
                interaction,
                msg_type          = "error",
                title             = "restore the member's nickname",
                subtitle          = "I lack permissions to edit members: `Manage Nicknames`",
                footer            = "Bad configuration",
                contact_bot_owner = True,
            )
    elif nickname_error == "http":
        await send_custom_message(
            interaction,
            msg_type          = "error",
            title             = "restore the member's nickname",
            subtitle          = "The role was removed, but a Discord API error prevented the nickname from being restored.",
            footer            = "Bad operation",
            contact_bot_owner = True,
        )
    elif roles_restore_error == "forbidden":
        await send_custom_message(
            interaction,
            msg_type          = "error",
            title             = "restore the member's staff roles",
            subtitle          = "I lack permissions to add roles: `Manage Roles`",
            footer            = "Bad configuration",
            contact_bot_owner = True,
        )
    elif roles_restore_error == "http":
        await send_custom_message(
            interaction,
            msg_type          = "error",
            title             = "restore the member's staff roles",
            subtitle          = "Personal leave was removed and the nickname restored, but a Discord API error prevented the original staff roles from being re-added.",
            footer            = "Bad operation",
            contact_bot_owner = True,
        )
    elif target_member.id == interaction.user.id:
        await send_custom_message(
            interaction,
            msg_type = "success",
            title    = "removed you from personal leave",
        )
    else:
        await send_custom_message(
            interaction,
            msg_type = "success",
            title    = f"removed {target_member.mention} from personal leave",
        )
