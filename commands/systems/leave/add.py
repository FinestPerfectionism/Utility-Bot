from __future__ import annotations

import contextlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from datetime import date as date_type
from typing import Any

import discord

from constants import (
    DENIED_EMOJI_ID,
    LEADING_DIRECTOR_ROLE_ID,
    PERSONAL_LEAVE_ROLE_ID,
)
from core.permissions import is_director, is_staff
from core.responses import send_custom_message

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

@dataclass
class _ParsedArgs:
    resolved_type : LeaveType
    parsed_begin  : date_type | None
    parsed_end    : date_type | None
    timer_seconds : int       | None

async def _validate_scheduling(
    interaction   : discord.Interaction,
    resolved_type : LeaveType,
    begin_date    : str | None,
    end_date      : str | None,
    timer         : str | None,
) -> bool:
    has_scheduling = begin_date is not None or end_date is not None or timer is not None

    if resolved_type == LeaveType.hard_clean and has_scheduling:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "add leave",
            subtitle = "Scheduling arguments (`begin_date`, `end_date`, `timer`) are incompatible with Hard Clean.",
            footer   = "Bad argument",
        )
        return False

    if end_date is not None and timer is not None:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "add leave",
            subtitle = "`end_date` and `timer` are mutually exclusive. Please use one or the other.",
            footer   = "Bad argument",
        )
        return False

    return True

async def _parse_begin(
    interaction : discord.Interaction,
    begin_date  : str,
) -> date_type | None:
    parsed = parse_date(begin_date)
    if parsed is None:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "add leave",
            subtitle = "Invalid `begin_date` format. Use `YYYY-MM-DD` (e.g. `2025-06-01`).",
            footer   = "Bad argument",
        )
        return None
    today = datetime.now(tz = UTC).date()
    if parsed <= today:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "add leave",
            subtitle = "`begin_date` must be a future date.",
            footer   = "Bad argument",
        )
        return None
    return parsed

async def _parse_end(
    interaction  : discord.Interaction,
    end_date     : str,
    parsed_begin : date_type | None,
) -> date_type | None:
    parsed = parse_date(end_date)
    if parsed is None:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "add leave",
            subtitle = "Invalid `end_date` format. Use `YYYY-MM-DD` (e.g. `2025-06-15`).",
            footer   = "Bad argument",
        )
        return None
    today = datetime.now(tz = UTC).date()
    if parsed <= today:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "add leave",
            subtitle = "`end_date` must be a future date.",
            footer   = "Bad argument",
        )
        return None
    if parsed_begin is not None and parsed <= parsed_begin:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "add leave",
            subtitle = "`end_date` must be after `begin_date`.",
            footer   = "Bad argument",
        )
        return None
    return parsed

async def _parse_args(
    interaction   : discord.Interaction,
    leave_type    : str,
    begin_date    : str | None,
    end_date      : str | None,
    timer         : str | None,
) -> _ParsedArgs | None:
    resolved_type = LeaveType(leave_type)

    if not await _validate_scheduling(interaction, resolved_type, begin_date, end_date, timer):
        return None

    parsed_begin : date_type | None = None
    if begin_date is not None:
        parsed_begin = await _parse_begin(interaction, begin_date)
        if parsed_begin is None:
            return None

    parsed_end : date_type | None = None
    if end_date is not None:
        parsed_end = await _parse_end(interaction, end_date, parsed_begin)
        if parsed_end is None:
            return None

    timer_seconds : int | None = None
    if timer is not None:
        timer_seconds = parse_timer(timer)
        if timer_seconds is None:
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "add leave",
                subtitle = "Invalid `timer` format. Use combinations like `1w`, `2d`, `3h`, `4m`, or `1w2d3h4m`.",
                footer   = "Bad argument",
            )
            return None

    return _ParsedArgs(
        resolved_type = resolved_type,
        parsed_begin  = parsed_begin,
        parsed_end    = parsed_end,
        timer_seconds = timer_seconds,
    )

async def _validate_hard_clean(
    interaction   : discord.Interaction,
    invocator     : discord.Member,
    target_member : discord.Member,
    resolved_type : LeaveType,
) -> bool:
    if resolved_type != LeaveType.hard_clean:
        return True

    if target_member.id == invocator.id:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "add leave",
            subtitle = "You cannot hard clean yourself.",
            footer   = "Bad request",
        )
        return False

    is_target_director   = is_director(target_member)
    has_leading_director = any(r.id == LEADING_DIRECTOR_ROLE_ID for r in invocator.roles)

    if is_target_director and not has_leading_director:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "add leave",
            subtitle = "You cannot hard clean a Director.",
            footer   = "No permissions",
        )
        return False

    return True

async def _validate_permissions(
    interaction   : discord.Interaction,
    invocator     : discord.Member,
    target_member : discord.Member,
    resolved_type : LeaveType,
    data          : dict[str, Any],
) -> bool:
    if not is_staff(invocator):
        await send_custom_message(
            interaction,
            msg_type = "error",
            title    = "run command",
            subtitle = "You are not authorized to run this command.",
            footer   = "No permissions",
        )
        return False

    if resolved_type != LeaveType.hard_clean and not is_staff(target_member):
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "add leave",
            subtitle = "Target must exist within the Goobers Staff Team.",
            footer   = "Bad argument",
        )
        return False

    if not can_manage_leave(invocator, target_member):
        await send_custom_message(
            interaction,
            msg_type = "error",
            title    = "run command",
            subtitle = "You are not authorized to run this command.",
            footer   = "No permissions",
        )
        return False

    existing_raw = data.get(str(target_member.id))
    if existing_raw is not None:
        existing_entry = normalize_entry(existing_raw)

        if entry_has_automation(existing_entry):
            automation_desc = describe_automation(existing_entry)
            warning_text    = (
                f"### {DENIED_EMOJI_ID} Warning,\n"
                f"{target_member.mention} currently has an active automation entry ({automation_desc}).\n\n"
                "Running `/leave add` now will override and clear that automation. Proceed?"
            )
            view         = InterferenceConfirmView(invocator_id=invocator.id, warning_text=warning_text)
            msg          = await interaction.followup.send(view = view, ephemeral = True)
            view.message = msg
            _            = await view.wait()

            if not view.confirmed:
                return False

        elif resolved_type != LeaveType.hard_clean:
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "add leave",
                subtitle = "User is already on personal leave.",
                footer   = "Bad argument",
            )
            return False

    return True

def _build_end_note_scheduled(
    parsed_begin  : date_type,
    parsed_end    : date_type | None,
    timer_seconds : int       | None,
) -> str:
    if parsed_end is not None:
        end_stamp = discord.utils.format_dt(
            datetime(parsed_end.year, parsed_end.month, parsed_end.day, tzinfo=UTC),
            style = "D",
        )
        return f" and scheduled to end on {end_stamp}"

    if timer_seconds is not None:
        approx_end_dt = (
            datetime(parsed_begin.year, parsed_begin.month, parsed_begin.day, tzinfo=UTC)
            + timedelta(seconds=timer_seconds)
        )
        return f" with a timer ending approximately {discord.utils.format_dt(approx_end_dt, style='f')}"

    return ""

async def _schedule_leave(
    interaction   : discord.Interaction,
    data          : dict[str, Any],
    target_member : discord.Member,
    resolved_type : LeaveType,
    parsed_begin  : date_type,
    parsed_end    : date_type | None,
    timer_seconds : int       | None,
    original_nick : str,
) -> None:
    soft_role_ids = (
        [r.id for r in target_member.roles if r.id in ALL_STAFF_ROLE_IDS]
        if resolved_type == LeaveType.soft_clean else []
    )

    data[str(target_member.id)] = {
        "original_nick" : original_nick,
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
    end_note = _build_end_note_scheduled(parsed_begin, parsed_end, timer_seconds)

    who = "You have" if target_member.id == interaction.user.id else f"{target_member.mention} has"
    await interaction.followup.send(
        f"{who} been scheduled for personal leave starting {begin_stamp}{end_note}.",
        ephemeral = True,
    )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Immediate-leave path
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def _rollback(
    *,
    roles_removed     : bool,
    role_added        : bool,
    roles_to_remove   : list[discord.Role],
    personal_leave    : discord.Role,
    target_member     : discord.Member,
) -> None:
    if roles_removed and not role_added:
        with contextlib.suppress(discord.HTTPException):
            await target_member.add_roles(*roles_to_remove)
    elif role_added:
        with contextlib.suppress(discord.HTTPException):
            await target_member.remove_roles(personal_leave)
        if roles_removed:
            with contextlib.suppress(discord.HTTPException):
                await target_member.add_roles(*roles_to_remove)

async def _handle_forbidden(
    interaction       : discord.Interaction,
    target_member     : discord.Member,
    *,
    roles_removed     : bool,
    role_added        : bool,
    nick_changed      : bool,
    roles_to_remove   : list[discord.Role],
    personal_leave    : discord.Role,
) -> None:
    await _rollback(
        roles_removed   = roles_removed,
        role_added      = role_added,
        roles_to_remove = roles_to_remove,
        personal_leave  = personal_leave,
        target_member   = target_member,
    )

    if not role_added and not roles_removed:
        await send_custom_message(
            interaction,
            msg_type          = "error",
            title             = "add leave",
            subtitle          = "I lack permissions to modify this user's roles: `Manage Roles`",
            footer            = "Bad configuration",
            contact_bot_owner = True,
        )
    elif not role_added:
        await send_custom_message(
            interaction,
            msg_type          = "error",
            title             = "add leave",
            subtitle          = "I lack permissions to assign the Personal Leave role: `Manage Roles`",
            footer            = "Bad configuration",
            contact_bot_owner = True,
        )
    elif not nick_changed:
        if target_member.id == interaction.guild.owner_id:  # type: ignore[union-attr]
            if interaction.user.id == interaction.guild.owner_id:  # type: ignore[union-attr]
                await send_custom_message(
                    interaction,
                    msg_type = "warning",
                    title    = "add leave",
                    subtitle = "The roles were updated, but I cannot change the server owner's nickname. Please change it manually.",
                )
            else:
                await send_custom_message(
                    interaction,
                    msg_type = "warning",
                    title    = "add leave",
                    subtitle = "The roles were updated, but I cannot change the server owner's nickname. Please have them change it manually.",
                )
        else:
            await send_custom_message(
                interaction,
                msg_type          = "error",
                title             = "add leave",
                subtitle          = "I lack permissions to change this user's nickname: `Manage Nicknames`",
                footer            = "Bad configuration",
                contact_bot_owner = True,
            )

def _build_end_note_immediate(
    parsed_end   : date_type | None,
    timer_end_ts : float     | None,
) -> str:
    if parsed_end is not None:
        end_stamp = discord.utils.format_dt(
            datetime(parsed_end.year, parsed_end.month, parsed_end.day, tzinfo=UTC),
            style = "D",
        )
        return f" Leave is scheduled to end on {end_stamp}."

    if timer_end_ts is not None:
        end_stamp = discord.utils.format_dt(
            datetime.fromtimestamp(timer_end_ts, tz = UTC),
            style = "f",
        )
        return f" Leave will automatically end at {end_stamp}."

    return ""

async def _apply_leave(
    interaction         : discord.Interaction,
    data                : dict[str, Any],
    target_member       : discord.Member,
    resolved_type       : LeaveType,
    parsed_end          : date_type | None,
    timer_seconds       : int       | None,
    personal_leave_role : discord.Role,
    roles_to_remove     : list[discord.Role],
    original_nick       : str,
    new_nick            : str,
) -> None:
    timer_end_ts : float | None = None
    if timer_seconds is not None:
        timer_end_ts = datetime.now(tz = UTC).timestamp() + timer_seconds

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
            "original_nick" : original_nick,
            "leave_type"    : resolved_type.value,
            "removed_roles" : [r.id for r in roles_to_remove],
            "begin_date"    : None,
            "end_date"      : parsed_end.strftime(DATE_FMT) if parsed_end is not None else None,
            "timer_end"     : timer_end_ts,
            "timer_seconds" : None,
        }
        save_data(data)

        end_note = _build_end_note_immediate(parsed_end, timer_end_ts)
        who      = "You have" if target_member.id == interaction.user.id else f"{target_member.mention} has"
        await interaction.followup.send(
            f"{who} been placed on personal leave.{end_note}",
            ephemeral = True,
        )

    except discord.Forbidden:
        await _handle_forbidden(
            interaction,
            target_member,
            roles_removed   = roles_removed,
            role_added      = role_added,
            nick_changed    = nick_changed,
            roles_to_remove = roles_to_remove,
            personal_leave  = personal_leave_role,
        )

    except discord.HTTPException:
        await _rollback(
            roles_removed   = roles_removed,
            role_added      = role_added,
            roles_to_remove = roles_to_remove,
            personal_leave  = personal_leave_role,
            target_member   = target_member,
        )
        await send_custom_message(
            interaction,
            msg_type          = "error",
            title             = "add leave",
            subtitle          = "A Discord API error occurred. Please try again later.",
            footer            = "Bad operation",
            contact_bot_owner = True,
        )

async def run_leave_add(
    data        : dict[str, Any],
    interaction : discord.Interaction,
    leave_type  : str,
    target      : discord.Member | None,
    begin_date  : str            | None,
    end_date    : str            | None,
    timer       : str            | None,
) -> None:
    if not interaction.guild:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "add leave",
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
            title    = "add leave",
            subtitle = "Bots cannot go on personal leave.",
            footer   = "Bad argument",
        )
        return

    args = await _parse_args(interaction, leave_type, begin_date, end_date, timer)
    if args is None:
        return

    if not await _validate_hard_clean(interaction, invocator, target_member, args.resolved_type):
        return

    if not await _validate_permissions(interaction, invocator, target_member, args.resolved_type, data):
        return

    roles_to_remove : list[discord.Role] = []
    if args.resolved_type in (LeaveType.soft_clean, LeaveType.hard_clean):
        roles_to_remove = [r for r in target_member.roles if r.id in ALL_STAFF_ROLE_IDS]

    if args.resolved_type == LeaveType.hard_clean:
        if not roles_to_remove:
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "add leave",
                subtitle = "Target has no staff roles to remove.",
                footer   = "Bad argument",
            )
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
        await send_custom_message(
            interaction,
            msg_type          = "error",
            title             = "add leave",
            subtitle          = "The Personal Leave role could not be found.",
            footer            = "Invalid IDs",
            contact_bot_owner = True,
        )
        return

    original_full_nick = target_member.nick or target_member.name
    actual_name        = extract_name(original_full_nick)
    new_nick           = build_leave_nick(actual_name)

    if new_nick is None:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "add leave",
            subtitle = "The resulting nickname, as well as `PL | nickname`, exceed Discord's 32 character limit.",
            footer   = "Bad argument",
        )
        return

    if args.parsed_begin is not None:
        await _schedule_leave(
            interaction,
            data,
            target_member,
            args.resolved_type,
            args.parsed_begin,
            args.parsed_end,
            args.timer_seconds,
            original_full_nick,
        )
        return

    if personal_leave_role in target_member.roles:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "add leave",
            subtitle = "User already has the Personal Leave role.",
            footer   = "Bad argument",
        )
        return

    await _apply_leave(
        interaction,
        data,
        target_member,
        args.resolved_type,
        args.parsed_end,
        args.timer_seconds,
        personal_leave_role,
        roles_to_remove,
        original_full_nick,
        new_nick,
    )
