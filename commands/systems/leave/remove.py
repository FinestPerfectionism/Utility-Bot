from typing import Any

import discord

from constants import (
    BOT_OWNER_ID,
    DENIED_EMOJI_ID,
    PERSONAL_LEAVE_ROLE_ID,
)
from core.permissions import is_staff
from core.utils import (
    send_major_error,
    send_minor_error,
)

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
    data:        dict[str, Any],
    interaction: discord.Interaction,
    target:      discord.Member | None,
) -> None:
    if not interaction.guild:
        await send_minor_error(
            interaction,
            texts    = "This command can only be used in a server.",
            subtitle = "Bad command environment.",
        )
        return

    _ = await interaction.response.defer(ephemeral = True)

    invocator = interaction.user
    if not isinstance(invocator, discord.Member):
        return

    target_member = target or invocator

    if target_member.bot:
        await send_minor_error(interaction, "Bots cannot go on personal leave.")
        return

    is_self_removal  = target_member.id == invocator.id
    is_self_on_leave = str(invocator.id) in data

    if not (is_self_removal and is_self_on_leave):
        if not is_staff(invocator):
            await send_major_error(
                interaction,
                title    = "Unauthorized!",
                texts    = "You lack the necessary permissions to run this command.",
                subtitle = "Invalid permissions.",
            )
            return

        if not is_staff(target_member):
            await send_minor_error(interaction, "Target must exist within the Goobers Staff Team.")
            return

        if not can_manage_leave(invocator, target_member):
            await send_major_error(
                interaction,
                title    = "Unauthorized!",
                texts    = "You lack the necessary permissions to remove personal leave from other Staff Members.",
                subtitle = "Invalid permissions.",
            )
            return

    raw_entry = data.get(str(target_member.id))
    if not raw_entry:
        await send_minor_error(interaction, "User is not on personal leave.")
        return

    entry = normalize_entry(raw_entry)

    personal_leave_role = interaction.guild.get_role(PERSONAL_LEAVE_ROLE_ID)
    if personal_leave_role is None:
        await send_major_error(
            interaction,
            title = "Error!",
            texts="I could not fetch the Personal Leave role.",
            subtitle = f"Invalid configuration. Contact an administrator and <@{BOT_OWNER_ID}>.",
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
        view         = InterferenceConfirmView(invocator_id=invocator.id, warning_text=warning_text)
        msg          = await interaction.followup.send(view = view, ephemeral = True)
        view.message = msg
        _ = await view.wait()

        if not view.confirmed:
            return

        data.pop(str(target_member.id), None)
        save_data(data)
        who = "Your" if target_member.id == interaction.user.id else f"{target_member.mention}'s"
        await interaction.followup.send(f"{who} scheduled leave has been cancelled.", ephemeral = True)
        return

    if not is_active:
        data.pop(str(target_member.id), None)
        save_data(data)
        await send_minor_error(interaction, "User does not have the Personal Leave role.")
        return

    if entry_has_automation(entry):
        automation_desc = describe_automation(entry)
        warning_text = (
            f"### {DENIED_EMOJI_ID} Warning,\n"
            f"{target_member.mention} currently has an active automation entry ({automation_desc}).\n\n"
            "Running `/leave remove` now will override and clear that automation. Proceed?"
        )
        view         = InterferenceConfirmView(invocator_id=invocator.id, warning_text=warning_text)
        msg          = await interaction.followup.send(view = view, ephemeral = True)
        view.message = msg
        _ = await view.wait()

        if not view.confirmed:
            return

    stored_name:     str       = entry.get("original_nick") or target_member.display_name
    leave_type_str:  str       = entry.get("leave_type", LeaveType.none.value)
    stored_role_ids: list[int] = entry.get("removed_roles", [])

    roles_to_restore: list[discord.Role] = []
    if leave_type_str in (LeaveType.soft_clean.value, "soft_clean"):
        for role_id in stored_role_ids:
            restored_role = interaction.guild.get_role(role_id)
            if restored_role is not None:
                roles_to_restore.append(restored_role)

    nickname_error:      str | None = None
    roles_restore_error: str | None = None

    try:
        await target_member.remove_roles(personal_leave_role)

        current_nick   = target_member.nick or target_member.name
        base_name      = extract_name(stored_name)
        expected_long  = f"P. Leave | {base_name}"
        expected_short = f"PL | {base_name}"

        if current_nick in (expected_long, expected_short):
            try:
                _ = await target_member.edit(nick=stored_name)
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
        await send_major_error(
            interaction,
            title = "Error!",
            texts="I lack the necessary permissions to remove the Personal Leave role.",
            subtitle = "Invalid configuration. Contact the owner.",
        )
        return

    except discord.HTTPException:
        await send_major_error(
            interaction,
            title = "Error!",
            texts="A Discord API error occurred while removing the role. Please try again later.",
            subtitle = f"Invalid operation. Contact <@{BOT_OWNER_ID}>.",
        )
        return

    if nickname_error == "forbidden":
        if target_member.id == interaction.guild.owner_id:
            await send_minor_error(
                interaction,
                "The role was removed, but I cannot change the server owner's nickname. Please change it back manually.",
            )
        else:
            await send_major_error(
                interaction,
                title = "Error!",
                texts="The role was removed, but I lack the necessary permissions to restore the nickname. Please change it back manually.",
                subtitle = "Invalid configuration. Contact the owner.",
            )
    elif nickname_error == "http":
        await send_minor_error(
            interaction,
            "The role was removed, but a Discord API error prevented the nickname from being restored.",
            subtitle = f"Invalid operation. Contact <@{BOT_OWNER_ID}>.",
        )
    elif roles_restore_error == "forbidden":
        await send_major_error(
            interaction,
            title = "Error!",
            texts="Personal leave was removed and the nickname restored, but I lack the permissions to re-add the original staff roles. Please restore them manually.",
            subtitle = "Invalid configuration. Contact the owner.",
        )
    elif roles_restore_error == "http":
        await send_minor_error(
            interaction,
            "Personal leave was removed and the nickname restored, but a Discord API error prevented the original staff roles from being re-added.",
            subtitle = f"Invalid operation. Contact <@{BOT_OWNER_ID}>.",
        )
    elif target_member.id == interaction.user.id:
        await interaction.followup.send("You have been removed from personal leave.", ephemeral = True)
    else:
        await interaction.followup.send(
            f"{target_member.mention} has been removed from personal leave.",
            ephemeral = True,
        )
