import contextlib
from datetime import UTC, datetime, timedelta
from datetime import date as date_type
from typing import Any

import discord

from constants import (
    BOT_OWNER_ID,
    DENIED_EMOJI_ID,
    LEADING_DIRECTOR_ROLE_ID,
    PERSONAL_LEAVE_ROLE_ID,
)
from core.permissions import is_director, is_staff
from core.utils import send_major_error, send_minor_error

from ._base import (
    ALL_STAFF_ROLE_IDS,
    DATE_FMT,
    HardCleanConfirmView,
    InterferenceConfirmView,
    LeaveType,
    build_leave_nick,
    can_manage_leave,
    describe_automation,
    entry_has_automation,
    extract_name,
    normalize_entry,
    parse_date,
    parse_timer,
    save_data,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /leave add Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_leave_add(
    data        : dict[str, Any],
    interaction : discord.Interaction,
    leave_type  : str,
    target      : discord.Member | None,
    begin_date  : str            | None,
    end_date    : str            | None,
    timer       : str            | None,
) -> None:
    resolved_type = LeaveType(leave_type)

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

    has_scheduling = begin_date is not None or end_date is not None or timer is not None

    if resolved_type == LeaveType.hard_clean and has_scheduling:
        await send_minor_error(
            interaction,
            "Scheduling arguments (`begin_date`, `end_date`, `timer`) are incompatible with Hard Clean.",
        )
        return

    if end_date is not None and timer is not None:
        await send_minor_error(
            interaction,
            "`end_date` and `timer` are mutually exclusive. Please use one or the other.",
        )
        return

    parsed_begin: date_type | None = None
    if begin_date is not None:
        parsed_begin = parse_date(begin_date)
        if parsed_begin is None:
            await send_minor_error(
                interaction,
                "Invalid `begin_date` format. Use `YYYY-MM-DD` (e.g. `2025-06-01`).",
            )
            return
        today = datetime.now(tz=UTC).date()
        if parsed_begin <= today:
            await send_minor_error(
                interaction,
                "`begin_date` must be a future date.",
            )
            return

    parsed_end: date_type | None = None
    if end_date is not None:
        parsed_end = parse_date(end_date)
        if parsed_end is None:
            await send_minor_error(
                interaction,
                "Invalid `end_date` format. Use `YYYY-MM-DD` (e.g. `2025-06-15`).",
            )
            return
        today = datetime.now(tz=UTC).date()
        if parsed_end <= today:
            await send_minor_error(
                interaction,
                "`end_date` must be a future date.",
            )
            return
        if parsed_begin is not None and parsed_end <= parsed_begin:
            await send_minor_error(
                interaction,
                "`end_date` must be after `begin_date`.",
            )
            return

    timer_seconds: int | None = None
    if timer is not None:
        timer_seconds = parse_timer(timer)
        if timer_seconds is None:
            await send_minor_error(
                interaction,
                "Invalid `timer` format. Use combinations like `1w`, `2d`, `3h`, `4m`, or `1w2d3h4m`.",
            )
            return

    if resolved_type == LeaveType.hard_clean:
        if target_member.id == invocator.id:
            await send_minor_error(interaction, "You cannot hard clean yourself.")
            return

        is_target_director   = is_director(target_member)
        has_leading_director = any(r.id == LEADING_DIRECTOR_ROLE_ID for r in invocator.roles)

        if is_target_director and not has_leading_director:
            await send_minor_error(interaction, "You cannot hard clean a Director.")
            return

    if not is_staff(invocator):
        await send_major_error(
            interaction,
            title    = "Unauthorized!",
            texts    = "You lack the necessary permissions to run this command.",
            subtitle = "Invalid permissions.",
        )
        return

    if resolved_type != LeaveType.hard_clean and not is_staff(target_member):
        await send_minor_error(interaction, "Target must exist within the Goobers Staff Team.")
        return

    if not can_manage_leave(invocator, target_member):
        await send_major_error(
            interaction,
            title    = "Unauthorized!",
            texts    = "You lack the necessary permissions to add personal leave to other Staff Members.",
            subtitle = "Invalid permissions.",
        )
        return

    existing_raw = data.get(str(target_member.id))
    if existing_raw is not None:
        existing_entry = normalize_entry(existing_raw)

        if entry_has_automation(existing_entry):
            automation_desc = describe_automation(existing_entry)
            warning_text = (
                f"### {DENIED_EMOJI_ID} Warning,\n"
                f"{target_member.mention} currently has an active automation entry ({automation_desc}).\n\n"
                "Running `/leave add` now will override and clear that automation. Proceed?"
            )
            view         = InterferenceConfirmView(invocator_id=invocator.id, warning_text=warning_text)
            msg          = await interaction.followup.send(view = view, ephemeral = True)
            view.message = msg
            _ = await view.wait()

            if not view.confirmed:
                return

        elif resolved_type != LeaveType.hard_clean:
            await send_minor_error(interaction, "User is already on personal leave.")
            return

    roles_to_remove: list[discord.Role] = []
    if resolved_type in (LeaveType.soft_clean, LeaveType.hard_clean):
        roles_to_remove = [r for r in target_member.roles if r.id in ALL_STAFF_ROLE_IDS]

    if resolved_type == LeaveType.hard_clean:
        if not roles_to_remove:
            await send_minor_error(interaction, "Target has no staff roles to remove.")
            return

        role_list    = ", ".join(r.mention for r in roles_to_remove)
        warning_text = (
            f"### {DENIED_EMOJI_ID} Warning,\n"
            f"This will remove all {len(roles_to_remove)} staff role(s) from {target_member.mention} and **cannot be undone** via `/leave remove`.\n\n"
            f"**Roles to remove:**\n {role_list}\n\n"
            "This action is a **demotional action** and will require manual intervention to restore. Proceed?"
        )
        view = HardCleanConfirmView(
            invocator_id    = invocator.id,
            target          = target_member,
            roles_to_remove = roles_to_remove,
            warning_text    = warning_text,
        )
        msg          = await interaction.followup.send(view = view, ephemeral = True)
        view.message = msg
        return

    personal_leave_role = interaction.guild.get_role(PERSONAL_LEAVE_ROLE_ID)
    if personal_leave_role is None:
        await send_major_error(
            interaction,
            title    = "Error!",
            texts    = "I could not fetch the Personal Leave role.",
            subtitle = f"Invalid Configuration. Contact an administrator and <@{BOT_OWNER_ID}>.",
        )
        return

    original_full_nick = target_member.nick or target_member.name
    actual_name        = extract_name(original_full_nick)
    new_nick           = build_leave_nick(actual_name)

    if new_nick is None:
        await send_minor_error(
            interaction,
            texts    = "The resulting nickname, as well as `PL | nickname`, exceed Discord's 32 character limit.",
            subtitle = "Invalid operation.",
        )
        return

    if parsed_begin is not None:
        soft_role_ids = (
            [r.id for r in target_member.roles if r.id in ALL_STAFF_ROLE_IDS]
            if resolved_type == LeaveType.soft_clean else []
        )

        data[str(target_member.id)] = {
            "original_nick" : original_full_nick,
            "leave_type"    : resolved_type.value,
            "removed_roles" : soft_role_ids,
            "begin_date"    : parsed_begin.strftime(DATE_FMT),
            "end_date"      : parsed_end.strftime(DATE_FMT) if parsed_end is not None else None,
            "timer_end"     : None,
            "timer_seconds" : timer_seconds,
        }
        save_data(data)

        begin_stamp = discord.utils.format_dt(
            datetime(parsed_begin.year, parsed_begin.month, parsed_begin.day, tzinfo=UTC),
            style = "D",
        )

        end_note = ""
        if parsed_end is not None:
            end_stamp = discord.utils.format_dt(
                datetime(parsed_end.year, parsed_end.month, parsed_end.day, tzinfo=UTC),
                style = "D",
            )
            end_note = f" and scheduled to end on {end_stamp}"
        elif timer_seconds is not None:
            approx_end_dt = (
                datetime(parsed_begin.year, parsed_begin.month, parsed_begin.day, tzinfo=UTC)
                + timedelta(seconds=timer_seconds)
            )
            end_note = f" with a timer ending approximately {discord.utils.format_dt(approx_end_dt, style='f')}"

        who = "You have" if target_member.id == interaction.user.id else f"{target_member.mention} has"
        await interaction.followup.send(
            f"{who} been scheduled for personal leave starting {begin_stamp}{end_note}.",
            ephemeral = True,
        )
        return

    if personal_leave_role in target_member.roles:
        await send_minor_error(interaction, "User already has the Personal Leave role.")
        return

    timer_end_ts : float | None = None
    if timer_seconds is not None:
        now_ts       = datetime.now(tz=UTC).timestamp()
        timer_end_ts = now_ts + timer_seconds

    roles_removed = False
    role_added    = False
    nick_changed  = False

    try:
        if roles_to_remove:
            await target_member.remove_roles(*roles_to_remove)
            roles_removed = True

        await target_member.add_roles(personal_leave_role)
        role_added = True

        _ = await target_member.edit(nick=new_nick)
        nick_changed = True

        data[str(target_member.id)] = {
            "original_nick" : original_full_nick,
            "leave_type"    : resolved_type.value,
            "removed_roles" : [r.id for r in roles_to_remove],
            "begin_date"    : None,
            "end_date"      : parsed_end.strftime(DATE_FMT) if parsed_end is not None else None,
            "timer_end"     : timer_end_ts,
            "timer_seconds" : None,
        }
        save_data(data)

        end_note = ""
        if parsed_end is not None:
            end_stamp = discord.utils.format_dt(
                datetime(parsed_end.year, parsed_end.month, parsed_end.day, tzinfo=UTC),
                style = "D",
            )
            end_note = f" Leave is scheduled to end on {end_stamp}."
        elif timer_end_ts is not None:
            end_stamp = discord.utils.format_dt(
                datetime.fromtimestamp(timer_end_ts, tz=UTC),
                style = "f",
            )
            end_note = f" Leave will automatically end at {end_stamp}."

        who = "You have" if target_member.id == interaction.user.id else f"{target_member.mention} has"
        await interaction.followup.send(
            f"{who} been placed on personal leave.{end_note}",
            ephemeral = True,
        )

    except discord.Forbidden:
        if roles_removed and not role_added:
            with contextlib.suppress(discord.HTTPException):
                await target_member.add_roles(*roles_to_remove)
        elif role_added and not nick_changed:
            with contextlib.suppress(discord.HTTPException):
                await target_member.remove_roles(personal_leave_role)
            if roles_removed:
                with contextlib.suppress(discord.HTTPException):
                    await target_member.add_roles(*roles_to_remove)

        if not role_added and not roles_removed:
            await send_major_error(
                interaction,
                texts    = "I lack the necessary permissions to modify this user's roles.",
                subtitle = "Invalid configuration. Contact the owner.",
            )
        elif not role_added:
            await send_major_error(
                interaction,
                texts    = "I lack the necessary permissions to assign the Personal Leave role.",
                subtitle = "Invalid configuration. Contact the owner.",
            )
        elif not nick_changed:
            if target_member.id == interaction.guild.owner_id:
                if interaction.user.id == interaction.guild.owner_id:
                    await send_minor_error(
                        interaction,
                        "The roles were updated, but I cannot change the server owner's nickname. Please change it manually.",
                    )
                else:
                    await send_minor_error(
                        interaction,
                        "The roles were updated, but I cannot change the server owner's nickname. Please have them change it manually.",
                    )
            else:
                await send_major_error(
                    interaction,
                    texts    = "I lack the necessary permissions to change this user's nickname.",
                    subtitle = "Invalid configuration. Contact the owner.",
                )

    except discord.HTTPException:
        if roles_removed and not role_added:
            with contextlib.suppress(discord.HTTPException):
                await target_member.add_roles(*roles_to_remove)
        elif role_added and not nick_changed:
            with contextlib.suppress(discord.HTTPException):
                await target_member.remove_roles(personal_leave_role)
            if roles_removed:
                with contextlib.suppress(discord.HTTPException):
                    await target_member.add_roles(*roles_to_remove)

        await send_major_error(
            interaction,
            texts    =  "A Discord API error occurred. Please try again later.",
            subtitle = f"Invalid operation. Contact <@{BOT_OWNER_ID}>.",
        )
