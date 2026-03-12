import discord
from discord.ext import (
    commands,
    tasks
)
from discord import app_commands

import contextlib
from typing import Any
from datetime import (
    datetime,
    UTC,
    date as date_type,
)

from ._base import (
    LeaveType,
    ALL_STAFF_ROLE_IDS,
    DATE_FMT,
    leave_group,
    load_data,
    save_data,
    extract_name,
    can_manage_leave,
    normalize_entry,
    parse_timer,
    parse_date,
    entry_has_automation,
    describe_automation,
    HardCleanConfirmView,
    InterferenceConfirmView,
)
from core.utils import (
    send_minor_error,
    send_major_error,
)
from core.permissions import (
    is_director,
    is_staff,
)
from constants import (
    BOT_OWNER_ID,
    DENIED_EMOJI_ID,
    PERSONAL_LEAVE_ROLE_ID,
    LEADING_DIRECTOR_ROLE_ID,
    GUILD_ID
)


# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Leave Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class Leave(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot  = bot
        self.data = load_data()
        self._automation_loop.start()

    async def cog_unload(self) -> None:
        self._automation_loop.cancel()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Automation Loop
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @tasks.loop(minutes=1)
    async def _automation_loop(self) -> None:
        now_ts = datetime.now(tz=UTC).timestamp()
        today  = datetime.now(tz=UTC).date()

        to_begin: list[tuple[str, dict[str, Any]]] = []
        to_end:   list[tuple[str, dict[str, Any]]] = []

        for user_id_str, raw in list(self.data.items()):
            entry = normalize_entry(raw)

            begin_str:   str | None = entry.get("begin_date")
            end_str:     str | None = entry.get("end_date")
            timer_end: float | None = entry.get("timer_end")

            if begin_str:
                begin_date = parse_date(begin_str)
                if begin_date is not None and today >= begin_date:
                    to_begin.append((user_id_str, entry))
                    continue

            if timer_end is not None and now_ts >= timer_end:
                to_end.append((user_id_str, entry))
            elif end_str:
                end_date = parse_date(end_str)
                if end_date is not None and today >= end_date:
                    to_end.append((user_id_str, entry))

        for user_id_str, entry in to_begin:
            await self._automation_apply_leave(user_id_str, entry)

        for user_id_str, entry in to_end:
            await self._automation_remove_leave(user_id_str, entry)

    @_automation_loop.before_loop
    async def _before_automation_loop(self) -> None:
        await self.bot.wait_until_ready()

    async def _automation_apply_leave(self, user_id_str: str, entry: dict[str, Any]) -> None:
        guild = discord.utils.get(self.bot.guilds)
        if guild is None:
            return

        member = guild.get_member(int(user_id_str))
        if member is None:
            entry["begin_date"]    = None
            self.data[user_id_str] = entry
            save_data(self.data)
            return

        resolved_leave_type = LeaveType(entry.get("leave_type", LeaveType.none.value))
        personal_leave_role = guild.get_role(PERSONAL_LEAVE_ROLE_ID)
        if personal_leave_role is None:
            return

        if personal_leave_role in member.roles:
            entry["begin_date"]    = None
            self.data[user_id_str] = entry
            save_data(self.data)
            return

        roles_to_remove: list[discord.Role] = []
        if resolved_leave_type == LeaveType.soft_clean:
            roles_to_remove = [r for r in member.roles if r.id in ALL_STAFF_ROLE_IDS]

        original_full_nick = member.nick or member.name
        actual_name        = extract_name(original_full_nick)
        new_nick           = f"P. Leave | {actual_name}"

        if len(new_nick) > 32:
            entry["begin_date"]    = None
            self.data[user_id_str] = entry
            save_data(self.data)
            return

        with contextlib.suppress(discord.HTTPException):
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="Scheduled leave automation")
            await member.add_roles(personal_leave_role, reason="Scheduled leave automation")
            await member.edit(nick=new_nick)

        entry["begin_date"]    = None
        entry["original_nick"] = original_full_nick
        entry["removed_roles"] = [r.id for r in roles_to_remove]
        self.data[user_id_str] = entry
        save_data(self.data)

    async def _automation_remove_leave(self, user_id_str: str, entry: dict[str, Any]) -> None:
        guild = discord.utils.get(self.bot.guilds)
        if guild is None:
            return

        member = guild.get_member(int(user_id_str))
        if member is None:
            self.data.pop(user_id_str, None)
            save_data(self.data)
            return

        personal_leave_role = guild.get_role(PERSONAL_LEAVE_ROLE_ID)
        if personal_leave_role is None:
            return

        stored_name:     str       = entry.get("original_nick", member.display_name)
        leave_type_str:  str       = entry.get("leave_type", LeaveType.none.value)
        stored_role_ids: list[int] = entry.get("removed_roles", [])

        roles_to_restore: list[discord.Role] = []
        if leave_type_str in (LeaveType.soft_clean.value, "soft_clean"):
            for role_id in stored_role_ids:
                restored_role = guild.get_role(role_id)
                if restored_role is not None:
                    roles_to_restore.append(restored_role)

        with contextlib.suppress(discord.HTTPException):
            if personal_leave_role in member.roles:
                await member.remove_roles(personal_leave_role, reason="Scheduled leave automation")

            current_nick  = member.nick or member.name
            expected_nick = f"P. Leave | {extract_name(stored_name)}"
            if current_nick == expected_nick:
                await member.edit(nick=stored_name)

            if roles_to_restore:
                await member.add_roles(*roles_to_restore, reason="Scheduled leave automation")

        self.data.pop(user_id_str, None)
        save_data(self.data)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /leave add Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @leave_group.command(name="add", description="Add personal leave to yourself or another user.")
    @app_commands.rename(leave_type="type")
    @app_commands.describe(
        leave_type = "The type of leave to apply.",
        target     = "The user to add personal leave to. Defaults to yourself.",
        begin_date = "Date to begin leave (YYYY-MM-DD). Incompatible with Hard Clean.",
        end_date   = "Date to end leave (YYYY-MM-DD). Incompatible with Hard Clean and timer.",
        timer      = "Duration until leave ends (e.g. 1w2d3h4m). Incompatible with Hard Clean and end_date.",
    )
    @app_commands.choices(
        leave_type=[
            app_commands.Choice(name="None",       value="none"),
            app_commands.Choice(name="Soft Clean", value="soft_clean"),
            app_commands.Choice(name="Hard Clean", value="hard_clean"),
        ]
    )
    async def leave_add(
        self,
        interaction: discord.Interaction,
        leave_type:  app_commands.Choice[str],
        target:      discord.Member | None = None,
        begin_date:             str | None = None,
        end_date:               str | None = None,
        timer:                  str | None = None,
    ) -> None:
        resolved_type = LeaveType(leave_type.value)

        if not interaction.guild:
            await send_minor_error(
                interaction,
                "This command can only be used in a server.",
                subtitle="Bad command environment."
            )
            return

        await interaction.response.defer(ephemeral=True)

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
                title="Unauthorized!",
                texts="You lack the necessary permissions to run this command.",
                subtitle="Invalid permissions."
            )
            return

        if resolved_type != LeaveType.hard_clean and not is_staff(target_member):
            await send_minor_error(interaction, "Target must exist within the Goobers Staff Team.")
            return

        if not can_manage_leave(invocator, target_member):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to add personal leave to other Staff Members.",
                subtitle="Invalid permissions."
            )
            return

        existing_raw = self.data.get(str(target_member.id))
        if existing_raw is not None:
            existing_entry = normalize_entry(existing_raw)

            if entry_has_automation(existing_entry):
                automation_desc = describe_automation(existing_entry)
                warning_text = (
                    f"### {DENIED_EMOJI_ID} Automation Conflict,\n"
                    f"{target_member.mention} currently has an active automation entry ({automation_desc}).\n\n"
                    "Running `/leave add` now will override and clear that automation. Proceed?"
                )
                view         = InterferenceConfirmView(invocator_id=invocator.id, warning_text=warning_text)
                msg          = await interaction.followup.send(view=view, ephemeral=True)
                view.message = msg
                await view.wait()

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
                "This action is a **demotional action** and will require manual intervention to restore. Please confirm below."
            )
            view         = HardCleanConfirmView(
                invocator_id    = invocator.id,
                target          = target_member,
                roles_to_remove = roles_to_remove,
                warning_text    = warning_text,
            )
            msg          = await interaction.followup.send(view=view, ephemeral=True)
            view.message = msg
            return

        if parsed_begin is not None:
            personal_leave_role = interaction.guild.get_role(PERSONAL_LEAVE_ROLE_ID)
            if personal_leave_role is None:
                await send_major_error(
                    interaction,
                    title="Error!",
                    texts="I could not fetch the Personal Leave role.",
                    subtitle=f"Invalid Configuration. Contact an administrator and <@{BOT_OWNER_ID}>."
                )
                return

            original_full_nick = target_member.nick or target_member.name
            actual_name        = extract_name(original_full_nick)
            new_nick           = f"P. Leave | {actual_name}"

            if len(new_nick) > 32:
                await send_minor_error(
                    interaction,
                    "The resulting nickname exceeds Discord's 32 character limit.",
                    subtitle="Invalid operation."
                )
                return

            timer_end_ts: float | None = None
            if timer_seconds is not None:
                now_ts       = datetime.now(tz=UTC).timestamp()
                timer_end_ts = now_ts + timer_seconds

            soft_role_ids = (
                [r.id for r in target_member.roles if r.id in ALL_STAFF_ROLE_IDS]
                if resolved_type == LeaveType.soft_clean else []
            )

            self.data[str(target_member.id)] = {
                "original_nick": original_full_nick,
                "leave_type":    resolved_type.value,
                "removed_roles": soft_role_ids,
                "begin_date":    parsed_begin.strftime(DATE_FMT),
                "end_date":      parsed_end.strftime(DATE_FMT) if parsed_end is not None else None,
                "timer_end":     timer_end_ts,
            }
            save_data(self.data)

            begin_stamp = discord.utils.format_dt(
                datetime(parsed_begin.year, parsed_begin.month, parsed_begin.day, tzinfo=UTC),
                style="D"
            )

            end_note = ""
            if parsed_end is not None:
                end_stamp = discord.utils.format_dt(
                    datetime(parsed_end.year, parsed_end.month, parsed_end.day, tzinfo=UTC),
                    style="D"
                )
                end_note = f" and scheduled to end on {end_stamp}"
            elif timer_seconds is not None and timer_end_ts is not None:
                end_stamp = discord.utils.format_dt(
                    datetime.fromtimestamp(timer_end_ts, tz=UTC),
                    style="f"
                )
                end_note = f" with a timer ending at {end_stamp}"

            who = "You have" if target_member.id == interaction.user.id else f"{target_member.mention} has"
            await interaction.followup.send(
                f"{who} been scheduled for personal leave starting {begin_stamp}{end_note}.",
                ephemeral=True
            )
            return

        personal_leave_role = interaction.guild.get_role(PERSONAL_LEAVE_ROLE_ID)
        if personal_leave_role is None:
            await send_major_error(
                interaction,
                title="Error!",
                texts="I could not fetch the Personal Leave role.",
                subtitle=f"Invalid Configuration. Contact an administrator and <@{BOT_OWNER_ID}>."
            )
            return

        if personal_leave_role in target_member.roles:
            await send_minor_error(interaction, "User already has the Personal Leave role.")
            return

        original_full_nick = target_member.nick or target_member.name
        actual_name        = extract_name(original_full_nick)
        new_nick           = f"P. Leave | {actual_name}"

        if len(new_nick) > 32:
            await send_minor_error(
                interaction,
                "The resulting nickname exceeds Discord's 32 character limit.",
                subtitle="Invalid operation."
            )
            return

        timer_end_ts = None
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

            await target_member.edit(nick=new_nick)
            nick_changed = True

            self.data[str(target_member.id)] = {
                "original_nick": original_full_nick,
                "leave_type":    resolved_type.value,
                "removed_roles": [r.id for r in roles_to_remove],
                "begin_date":    None,
                "end_date":      parsed_end.strftime(DATE_FMT) if parsed_end is not None else None,
                "timer_end":     timer_end_ts,
            }
            save_data(self.data)

            end_note = ""
            if parsed_end is not None:
                end_stamp = discord.utils.format_dt(
                    datetime(parsed_end.year, parsed_end.month, parsed_end.day, tzinfo=UTC),
                    style="D"
                )
                end_note = f" Leave is scheduled to end on {end_stamp}."
            elif timer_end_ts is not None:
                end_stamp = discord.utils.format_dt(
                    datetime.fromtimestamp(timer_end_ts, tz=UTC),
                    style="f"
                )
                end_note = f" Leave will automatically end at {end_stamp}."

            who = "You have" if target_member.id == interaction.user.id else f"{target_member.mention} has"
            await interaction.followup.send(
                f"{who} been placed on personal leave.{end_note}",
                ephemeral=True
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
                    title="Error!",
                    texts="I lack the necessary permissions to modify this user's roles.",
                    subtitle="Invalid configuration. Contact the owner."
                )
            elif not role_added:
                await send_major_error(
                    interaction,
                    title="Error!",
                    texts="I lack the necessary permissions to assign the Personal Leave role.",
                    subtitle="Invalid configuration. Contact the owner."
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
                        title="Error!",
                        texts="I lack the necessary permissions to change this user's nickname.",
                        subtitle="Invalid configuration. Contact the owner."
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
                title="Error!",
                texts="A Discord API error occurred. Please try again later.",
                subtitle=f"Invalid operation. Contact <@{BOT_OWNER_ID}> if this persists."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /leave remove Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @leave_group.command(name="remove", description="Remove personal leave from yourself or another user.")
    @app_commands.describe(target="The user to remove personal leave from.")
    async def leave_remove(
        self,
        interaction: discord.Interaction,
        target:      discord.Member | None = None,
    ) -> None:
        if not interaction.guild:
            await send_minor_error(
                interaction,
                "This command can only be used in a server.",
                subtitle="Bad command environment."
            )
            return

        await interaction.response.defer(ephemeral=True)

        invocator = interaction.user
        if not isinstance(invocator, discord.Member):
            return

        target_member = target or invocator

        if target_member.bot:
            await send_minor_error(interaction, "Bots cannot go on personal leave.")
            return

        is_self_removal  = target_member.id == invocator.id
        is_self_on_leave = str(invocator.id) in self.data

        if not (is_self_removal and is_self_on_leave):
            if not is_staff(invocator):
                await send_major_error(
                    interaction,
                    title="Unauthorized!",
                    texts="You lack the necessary permissions to run this command.",
                    subtitle="Invalid permissions."
                )
                return

            if not is_staff(target_member):
                await send_minor_error(interaction, "Target must exist within the Goobers Staff Team.")
                return

            if not can_manage_leave(invocator, target_member):
                await send_major_error(
                    interaction,
                    title="Unauthorized!",
                    texts="You lack the necessary permissions to remove personal leave from other Staff Members.",
                    subtitle="Invalid permissions."
                )
                return

        raw_entry = self.data.get(str(target_member.id))
        if not raw_entry:
            await send_minor_error(interaction, "User is not on personal leave.")
            return

        entry = normalize_entry(raw_entry)

        if entry_has_automation(entry):
            automation_desc = describe_automation(entry)
            warning_text = (
                f"### {DENIED_EMOJI_ID} Automation Conflict,\n"
                f"{target_member.mention} currently has an active automation entry ({automation_desc}).\n\n"
                "Running `/leave remove` now will override and clear that automation. Proceed?"
            )
            view         = InterferenceConfirmView(invocator_id=invocator.id, warning_text=warning_text)
            msg          = await interaction.followup.send(view=view, ephemeral=True)
            view.message = msg
            await view.wait()

            if not view.confirmed:
                return

        stored_name:     str       = entry["original_nick"]
        leave_type_str:  str       = entry.get("leave_type", LeaveType.none.value)
        stored_role_ids: list[int] = entry.get("removed_roles", [])

        personal_leave_role = interaction.guild.get_role(PERSONAL_LEAVE_ROLE_ID)
        if personal_leave_role is None:
            await send_major_error(
                interaction,
                title="Error!",
                texts="I could not fetch the Personal Leave role.",
                subtitle=f"Invalid configuration. Contact an administrator and <@{BOT_OWNER_ID}>."
            )
            return

        if personal_leave_role not in target_member.roles:
            self.data.pop(str(target_member.id), None)
            save_data(self.data)
            await send_minor_error(interaction, "User does not have the Personal Leave role.")
            return

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

            current_nick  = target_member.nick or target_member.name
            expected_nick = f"P. Leave | {extract_name(stored_name)}"

            if current_nick == expected_nick:
                try:
                    await target_member.edit(nick=stored_name)
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

            self.data.pop(str(target_member.id), None)
            save_data(self.data)

        except discord.Forbidden:
            await send_major_error(
                interaction,
                title="Error!",
                texts="I lack the necessary permissions to remove the Personal Leave role.",
                subtitle="Invalid configuration. Contact the owner."
            )
            return

        except discord.HTTPException:
            await send_major_error(
                interaction,
                title="Error!",
                texts="A Discord API error occurred while removing the role. Please try again later.",
                subtitle=f"Invalid operation. Contact <@{BOT_OWNER_ID}>."
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
                    title="Error!",
                    texts="The role was removed, but I lack the necessary permissions to restore the nickname. Please change it back manually.",
                    subtitle="Invalid configuration. Contact the owner."
                )
        elif nickname_error == "http":
            await send_minor_error(
                interaction,
                "The role was removed, but a Discord API error prevented the nickname from being restored.",
                subtitle=f"Invalid operation. Contact <@{BOT_OWNER_ID}>."
            )
        elif roles_restore_error == "forbidden":
            await send_major_error(
                interaction,
                title="Error!",
                texts="Personal leave was removed and the nickname restored, but I lack the permissions to re-add the original staff roles. Please restore them manually.",
                subtitle="Invalid configuration. Contact the owner."
            )
        elif roles_restore_error == "http":
            await send_minor_error(
                interaction,
                "Personal leave was removed and the nickname restored, but a Discord API error prevented the original staff roles from being re-added.",
                subtitle=f"Invalid operation. Contact <@{BOT_OWNER_ID}>."
            )
        else:
            if target_member.id == interaction.user.id:
                await interaction.followup.send("You have been removed from personal leave.", ephemeral=True)
            else:
                await interaction.followup.send(
                    f"{target_member.mention} has been removed from personal leave.",
                    ephemeral=True
                )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Leave(bot))
    bot.tree.add_command(leave_group, guild=discord.Object(id=GUILD_ID))