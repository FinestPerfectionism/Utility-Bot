import discord
from discord.ext import (
    commands,
    tasks
)
from discord import app_commands

from typing_extensions import override
from typing import Any
from datetime import (
    datetime,
    UTC
)

from ._base import (
    LeaveType,
    ALL_STAFF_ROLE_IDS,
    load_data,
    save_data,
    extract_name,
    normalize_entry,
    parse_date,
    build_leave_nick,
)
from core.help import (
    help_description,
    ArgumentInfo,
    RoleConfig,
)
from .add import run_leave_add
from .remove import run_leave_remove
from constants import (
    PERSONAL_LEAVE_ROLE_ID,
    STAFF_ROLE_ID,
    DIRECTORS_ROLE_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Leave Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class LeaveCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot  = bot
        self.data = load_data()
        _ = self._automation_loop.start()

    leave_group = app_commands.Group(
        name = "leave",
        description="Staff only —— Leave commands."
    )

    @override
    async def cog_unload(self) -> None:
        self._automation_loop.cancel()

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
        guild = next(iter(self.bot.guilds), None)
        if guild is None:
            return

        member = guild.get_member(int(user_id_str))
        if member is None:
            entry["begin_date"]    = None
            entry["timer_seconds"] = None
            self.data[user_id_str] = entry
            save_data(self.data)
            return

        resolved_leave_type = LeaveType(entry.get("leave_type", LeaveType.none.value))
        personal_leave_role = guild.get_role(PERSONAL_LEAVE_ROLE_ID)
        if personal_leave_role is None:
            return

        if personal_leave_role in member.roles:
            entry["begin_date"]    = None
            entry["timer_seconds"] = None
            self.data[user_id_str] = entry
            save_data(self.data)
            return

        roles_to_remove: list[discord.Role] = []
        if resolved_leave_type == LeaveType.soft_clean:
            roles_to_remove = [r for r in member.roles if r.id in ALL_STAFF_ROLE_IDS]

        original_full_nick = member.nick or member.name
        actual_name        = extract_name(original_full_nick)
        new_nick           = build_leave_nick(actual_name)

        if new_nick is None:
            entry["begin_date"]    = None
            entry["timer_seconds"] = None
            self.data[user_id_str] = entry
            save_data(self.data)
            return

        stored_timer_secs: int | None = entry.get("timer_seconds")
        new_timer_end:   float | None = (
            datetime.now(tz=UTC).timestamp() + stored_timer_secs
            if stored_timer_secs is not None else None
        )

        try:
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="UB Leave: Scheduled leave automation")
            await member.add_roles(personal_leave_role, reason="UB Leave: Scheduled leave automation")
            _ = await member.edit(nick=new_nick)
        except discord.HTTPException:
            return

        entry["begin_date"]    = None
        entry["timer_seconds"] = None
        entry["timer_end"]     = new_timer_end
        entry["original_nick"] = original_full_nick
        entry["removed_roles"] = [r.id for r in roles_to_remove]
        self.data[user_id_str] = entry
        save_data(self.data)

    async def _automation_remove_leave(self, user_id_str: str, entry: dict[str, Any]) -> None:
        guild = next(iter(self.bot.guilds), None)
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

        stored_name:     str       = entry.get("original_nick") or member.display_name
        leave_type_str:  str       = entry.get("leave_type", LeaveType.none.value)
        stored_role_ids: list[int] = entry.get("removed_roles", [])

        roles_to_restore: list[discord.Role] = []
        if leave_type_str in (LeaveType.soft_clean.value, "soft_clean"):
            for role_id in stored_role_ids:
                restored_role = guild.get_role(role_id)
                if restored_role is not None:
                    roles_to_restore.append(restored_role)

        try:
            if personal_leave_role in member.roles:
                await member.remove_roles(personal_leave_role, reason="UB Leave: Scheduled leave automation")

            current_nick   = member.nick or member.name
            base_name      = extract_name(stored_name)
            expected_long  = f"P. Leave | {base_name}"
            expected_short = f"PL | {base_name}"

            if current_nick in (expected_long, expected_short):
                _ = await member.edit(nick=stored_name)

            if roles_to_restore:
                await member.add_roles(*roles_to_restore, reason="UB Leave: Scheduled leave automation")
        except discord.HTTPException:
            return

        self.data.pop(user_id_str, None)
        save_data(self.data)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /leave add Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @leave_group.command(name = "add", description="Add personal leave to yourself or another user.")
    @app_commands.describe(
        leave_type = "The type of leave to apply.",
        target     = "The user to add personal leave to. Defaults to yourself.",
        begin_date = "Date to begin leave (YYYY-MM-DD). Incompatible with Hard Clean.",
        end_date   = "Date to end leave (YYYY-MM-DD). Incompatible with Hard Clean and timer.",
        timer      = "Duration until leave ends (e.g. 1w2d3h4m). Incompatible with Hard Clean and end_date.",
    )
    @app_commands.choices(
        leave_type=[
            app_commands.Choice(name = "None",       value = "none"),
            app_commands.Choice(name = "Soft Clean", value = "soft_clean"),
            app_commands.Choice(name = "Hard Clean", value = "hard_clean"),
        ]
    )
    @app_commands.rename(leave_type="type", begin_date="begin-date", end_date="end-date")
    @help_description(
        desc="Directors only —— Adds personal leave to yourself or another staff member, with optional scheduling and leave types.",
        prefix=False,
        slash=True,
        run_roles=[RoleConfig(role_id=DIRECTORS_ROLE_ID)],
        arguments={
            "type": ArgumentInfo(description="Leave mode to apply.", choices=["none", "soft_clean", "hard_clean"]),
            "target": ArgumentInfo(required=False, description="Staff member to place on leave; defaults to yourself."),
            "begin-date": ArgumentInfo(required=False, description="Optional future start date in YYYY-MM-DD format."),
            "end-date": ArgumentInfo(required=False, description="Optional future end date in YYYY-MM-DD format."),
            "timer": ArgumentInfo(required=False, description="Optional duration such as 1w2d3h4m."),
        },
    )
    async def leave_add(
        self,
        interaction: discord.Interaction,
        leave_type:  str,
        target:      discord.Member | None = None,
        begin_date:             str | None = None,
        end_date:               str | None = None,
        timer:                  str | None = None,
    ) -> None:
        await run_leave_add(self.data, interaction, leave_type, target, begin_date, end_date, timer)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /leave remove Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @leave_group.command(name = "remove", description="Remove personal leave from yourself or another user.")
    @app_commands.describe(target="The user to remove personal leave from.")
    @help_description(
        desc="Staff only —— Removes personal leave from yourself or another staff member. Self-removal also works for your own scheduled leave entry.",
        prefix=False,
        slash=True,
        run_roles=[RoleConfig(role_id=STAFF_ROLE_ID)],
        arguments={"target": ArgumentInfo(
                required=False,
                description="Staff member whose leave should be removed; defaults to yourself.",
                roles=[DIRECTORS_ROLE_ID]
            )
        },
    )
    async def leave_remove(
        self,
        interaction: discord.Interaction,
        target:      discord.Member | None = None,
    ) -> None:
        await run_leave_remove(self.data, interaction, target)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LeaveCommands(bot))
