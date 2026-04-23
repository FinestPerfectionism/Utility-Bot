import asyncio
import contextlib
import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import discord
from discord import ButtonStyle
from discord.ext import commands
from discord.ui import (
    ActionRow,
    Button,
    FileUpload,
    Label,
    LayoutView,
    Modal,
    Section,
    Separator,
    TextDisplay,
    TextInput,
    View,
)
from typing_extensions import override

from core.cases import CasesManager, CaseType
from core.responses import multi_custom_message, send_custom_message

if TYPE_CHECKING:
    from bot import UtilityBot

from constants import (
    ADMINISTRATORS_ROLE_ID,
    DIRECTORS_ROLE_ID,
    JUNIOR_ADMINISTRATORS_ROLE_ID,
    JUNIOR_MODERATORS_ROLE_ID,
    MODERATORS_AND_ADMINISTRATORS_ROLE_ID,
    MODERATORS_ROLE_ID,
    QUARANTINE_ROLE_ID,
    SENIOR_ADMINISTRATORS_ROLE_ID,
    SENIOR_MODERATORS_ROLE_ID,
    STAFF_ROLE_ID,
)
from core.permissions import (
    has_role,
    is_administrator,
    is_director,
    is_moderator,
    is_senior_moderator,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Moderation List Paginator
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

_Context = discord.Interaction

class ModerationListPaginator(View):
    def __init__(
        self,
        context         : _Context,
        title           : str,
        color           : discord.Color,
        fields          : list[tuple[str, str]],
        delete_delay    : float                         | None = None,
        delete_callback : Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        super().__init__(timeout = 120)
        self.context         = context
        self.title           = title
        self.color           = color
        self.fields          = fields
        self.per_page        = 5
        self.page            = 0
        self.max_page        = (len(fields) - 1) // self.per_page
        self.delete_delay    = delete_delay
        self.delete_callback = delete_callback
        self._delete_task : asyncio.Task[None] | None = None

        self.update_buttons()

        if delete_delay is not None:
            self._schedule_delete()

    def _schedule_delete(self) -> None:
        if self._delete_task is not None:
            _ = self._delete_task.cancel()
        loop = asyncio.get_event_loop()
        self._delete_task = loop.create_task(self._delete_after())

    async def _delete_after(self) -> None:
        await asyncio.sleep(self.delete_delay or 0)
        if self.delete_callback:
            with contextlib.suppress(discord.NotFound, discord.HTTPException):
                await self.delete_callback()
        self.stop()

    def update_buttons(self) -> None:
        no_pagination_needed = len(self.fields) <= self.per_page

        self.first_page.disabled    = no_pagination_needed or self.page == 0
        self.previous_page.disabled = no_pagination_needed or self.page == 0
        self.next_page.disabled     = no_pagination_needed or self.page >= self.max_page
        self.last_page.disabled     = no_pagination_needed or self.page >= self.max_page

    def get_embed(self) -> discord.Embed:
        start       = self.page * self.per_page
        end         = start + self.per_page
        page_fields = self.fields[start:end]

        embed = discord.Embed(
            title     = self.title,
            color     = self.color,
            timestamp = datetime.now(UTC),
        )

        for name, value in page_fields:
            _ = embed.add_field(name = name, value = value, inline = False)

        _ = embed.set_footer(
            text=f"Page {self.page + 1}/{self.max_page + 1} · {len(self.fields)} total",
        )

        return embed

    @override
    async def interaction_check(self, interaction : discord.Interaction) -> bool:
        return interaction.user == self.context.user

    @discord.ui.button(label = "<<", style = ButtonStyle.secondary)
    async def first_page(
        self,
        interaction : discord.Interaction,
        _button     : Button["ModerationListPaginator"],
    ) -> None:
        self.page = 0
        self.update_buttons()
        if self.delete_delay is not None:
            self._schedule_delete()
        _ = await interaction.response.edit_message(embed = self.get_embed(), view = self)

    @discord.ui.button(label = "<", style = ButtonStyle.secondary)
    async def previous_page(
        self,
        interaction : discord.Interaction,
        _button     : Button["ModerationListPaginator"],
    ) -> None:
        if self.page > 0:
            self.page -= 1
        self.update_buttons()
        if self.delete_delay is not None:
            self._schedule_delete()
        _ = await interaction.response.edit_message(embed = self.get_embed(), view = self)

    @discord.ui.button(label = ">", style = ButtonStyle.secondary)
    async def next_page(
        self,
        interaction : discord.Interaction,
        _button     : Button["ModerationListPaginator"],
    ) -> None:
        if self.page < self.max_page:
            self.page += 1
        self.update_buttons()
        if self.delete_delay is not None:
            self._schedule_delete()
        _ = await interaction.response.edit_message(embed = self.get_embed(), view = self)

    @discord.ui.button(label = ">>", style = ButtonStyle.secondary)
    async def last_page(
        self,
        interaction : discord.Interaction,
        _button     : Button["ModerationListPaginator"],
    ) -> None:
        self.page = self.max_page
        self.update_buttons()
        if self.delete_delay is not None:
            self._schedule_delete()
        _ = await interaction.response.edit_message(embed = self.get_embed(), view = self)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Moderation Base
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ModerationBase(commands.Cog):
    def __init__(self, bot : "UtilityBot") -> None:
        self.bot = bot

        if not hasattr(bot, "mod_data"):
            bot.mod_data = self._load_data()

        self.QUARANTINE_ROLE_ID        = QUARANTINE_ROLE_ID
        self.DIRECTORS_ROLE_ID         = DIRECTORS_ROLE_ID
        self.SENIOR_MODERATORS_ROLE_ID = SENIOR_MODERATORS_ROLE_ID
        self.MODERATORS_ROLE_ID        = MODERATORS_ROLE_ID
        self.ADMINISTRATORS_ROLE_ID    = ADMINISTRATORS_ROLE_ID

        self.PROTECTED_ROLE_IDS = [
            STAFF_ROLE_ID,
            ADMINISTRATORS_ROLE_ID,
            JUNIOR_ADMINISTRATORS_ROLE_ID,
            SENIOR_ADMINISTRATORS_ROLE_ID,
            MODERATORS_AND_ADMINISTRATORS_ROLE_ID,
            MODERATORS_ROLE_ID,
            JUNIOR_MODERATORS_ROLE_ID,
            SENIOR_MODERATORS_ROLE_ID,
            DIRECTORS_ROLE_ID,
        ]

        self.BAN_HOURLY_LIMIT        = 2
        self.BAN_DAILY_LIMIT         = 4
        self.KICK_HOURLY_LIMIT       = 3
        self.KICK_DAILY_LIMIT        = 6
        self.TIMEOUT_HOURLY_LIMIT    = 5
        self.TIMEOUT_DAILY_LIMIT     = 10
        self.QUARANTINE_HOURLY_LIMIT = 5
        self.QUARANTINE_DAILY_LIMIT  = 20
        self.SEVERE_HOURLY_LIMIT     = 4
        self.SEVERE_DAILY_LIMIT      = 8

    @property
    def data(self) -> dict[str, Any]:
        return self.bot.mod_data

    @property
    def cases_manager(self) -> CasesManager:
        return self.bot.cases_manager

    def _load_data(self) -> dict[str, Any]:
        if Path("moderation_data.json").exists():
            with contextlib.suppress(json.JSONDecodeError), Path("moderation_data.json").open() as f:
                return json.load(f)
        return self._get_default_data()

    def _get_default_data(self) -> dict[str, Any]:
        return {
            "bans"        : {},
            "timeouts"    : {},
            "kicks"       : {},
            "rate_limits" : {},
            "quarantined" : {},
        }

    def save_data(self) -> None:
        with Path("moderation_data.json").open("w") as f:
            json.dump(self.data, f, indent=4)

    def ensure_data_section(self, section: str) -> dict[str, Any]:
        if section not in self.data:
            self.data[section] = {}
        return self.data[section]

    def parse_duration(self, duration_str: str) -> int | None:
        duration_str = duration_str.lower().strip()
        try:
            if duration_str.endswith("s"):
                return int(duration_str[:-1])
            if duration_str.endswith("m"):
                return int(duration_str[:-1]) * 60
            if duration_str.endswith("h"):
                return int(duration_str[:-1]) * 3600
            if duration_str.endswith("d"):
                return int(duration_str[:-1]) * 86400
            if duration_str.endswith("w"):
                return int(duration_str[:-1]) * 604800
            return int(duration_str) * 60
        except ValueError:
            return None

    def _ensure_rate_limit_entry(self, user_id: str) -> None:
        if "rate_limits" not in self.data:
            self.data["rate_limits"] = {}

        rate_limits: dict[str, dict[str, list[str]]] = self.data["rate_limits"]

        if user_id not in rate_limits:
            rate_limits[user_id] = {}

        rl: dict[str, list[str]] = rate_limits[user_id]
        for key in (
            "ban_hourly"       , "ban_daily",
            "kick_hourly"      , "kick_daily",
            "timeout_hourly"   , "timeout_daily",
            "quarantine_hourly", "quarantine_daily",
            "severe_hourly"    , "severe_daily",
        ):
            if key not in rl:
                rl[key] = []

    def clean_old_rate_limits(self, user_id: str) -> None:
        now = datetime.now(UTC)
        self._ensure_rate_limit_entry(user_id)

        rate_limits: dict[str, dict[str, list[str]]] = self.data["rate_limits"]
        rl: dict[str, list[str]] = rate_limits[user_id]

        for key in ("ban_hourly", "kick_hourly", "timeout_hourly", "quarantine_hourly", "severe_hourly"):
            rl[key] = [ts for ts in rl[key] if datetime.fromisoformat(ts) > now - timedelta(hours=1)]
        for key in ("ban_daily", "kick_daily", "timeout_daily", "quarantine_daily", "severe_daily"):
            rl[key] = [ts for ts in rl[key] if datetime.fromisoformat(ts) > now - timedelta(days=1)]

    def check_rate_limit(self, user_id: str, action: str) -> tuple[bool, str]:
        self.clean_old_rate_limits(user_id)

        rate_limits: dict[str, dict[str, list[str]]] = self.data["rate_limits"]
        rl: dict[str, list[str]] = rate_limits[user_id]

        if len(rl["severe_hourly"]) >= self.SEVERE_HOURLY_LIMIT:
            return False, f"Severe action hourly limit exceeded ({self.SEVERE_HOURLY_LIMIT} bans/kicks/quarantines per hour)"
        if len(rl["severe_daily"]) >= self.SEVERE_DAILY_LIMIT:
            return False, f"Severe action daily limit exceeded ({self.SEVERE_DAILY_LIMIT} bans/kicks/quarantines per day)"

        if action == "ban":
            if len(rl["ban_hourly"]) >= self.BAN_HOURLY_LIMIT:
                return False, f"Ban hourly limit exceeded ({self.BAN_HOURLY_LIMIT} bans per hour)"
            if len(rl["ban_daily"]) >= self.BAN_DAILY_LIMIT:
                return False, f"Ban daily limit exceeded ({self.BAN_DAILY_LIMIT} bans per day)"
        elif action == "kick":
            if len(rl["kick_hourly"]) >= self.KICK_HOURLY_LIMIT:
                return False, f"Kick hourly limit exceeded ({self.KICK_HOURLY_LIMIT} kicks per hour)"
            if len(rl["kick_daily"]) >= self.KICK_DAILY_LIMIT:
                return False, f"Kick daily limit exceeded ({self.KICK_DAILY_LIMIT} kicks per day)"
        elif action == "timeout":
            if len(rl["timeout_hourly"]) >= self.TIMEOUT_HOURLY_LIMIT:
                return False, f"Timeout hourly limit exceeded ({self.TIMEOUT_HOURLY_LIMIT} timeouts per hour)"
            if len(rl["timeout_daily"]) >= self.TIMEOUT_DAILY_LIMIT:
                return False, f"Timeout daily limit exceeded ({self.TIMEOUT_DAILY_LIMIT} timeouts per day)"
        elif action == "quarantine":
            if len(rl["quarantine_hourly"]) >= self.QUARANTINE_HOURLY_LIMIT:
                return False, f"Quarantine hourly limit exceeded ({self.QUARANTINE_HOURLY_LIMIT} quarantines per hour)"
            if len(rl["quarantine_daily"]) >= self.QUARANTINE_DAILY_LIMIT:
                return False, f"Quarantine daily limit exceeded ({self.QUARANTINE_DAILY_LIMIT} quarantines per day)"

        return True, ""

    def add_rate_limit_entry(self, user_id: str, action: str) -> None:
        now = datetime.now(UTC).isoformat()
        self._ensure_rate_limit_entry(user_id)

        rate_limits: dict[str, dict[str, list[str]]] = self.data["rate_limits"]
        rl: dict[str, list[str]] = rate_limits[user_id]

        if action in ("ban", "kick", "quarantine"):
            rl["severe_hourly"].append(now)
            rl["severe_daily"].append(now)

        if action == "ban":
            rl["ban_hourly"].append(now)
            rl["ban_daily"].append(now)
        elif action == "kick":
            rl["kick_hourly"].append(now)
            rl["kick_daily"].append(now)
        elif action == "timeout":
            rl["timeout_hourly"].append(now)
            rl["timeout_daily"].append(now)
        elif action == "quarantine":
            rl["quarantine_hourly"].append(now)
            rl["quarantine_daily"].append(now)

        self.save_data()

    def has_protected_role(self, member: discord.Member) -> bool:
        return any(has_role(member, role_id) for role_id in self.PROTECTED_ROLE_IDS)

    def can_view_moderation(self, member: discord.Member) -> bool:
        return (
            is_director(member) or
            is_senior_moderator(member) or
            is_administrator(member) or
            is_moderator(member)
        )

    def can_apply_standard_actions(self, member: discord.Member) -> bool:
        return is_moderator(member)

    def can_untimeout(self, member: discord.Member) -> bool:
        return is_director(member) or is_senior_moderator(member)

    def can_reverse_actions(self, member: discord.Member) -> bool:
        return is_director(member)

    def can_quarantine(self, member: discord.Member) -> bool:
        return self.can_apply_standard_actions(member)

    def can_view(self, member: discord.Member) -> bool:
        return self.can_view_moderation(member)

    def can_moderate(self, member: discord.Member) -> bool:
        return self.can_apply_standard_actions(member)

    def can_unban_untimeout(self, member: discord.Member) -> bool:
        return self.can_reverse_actions(member)

    def check_hierarchy(self, moderator: discord.Member, target: discord.Member) -> bool:
        if target.id == moderator.guild.owner_id:
            return False
        if moderator.id == moderator.guild.owner_id:
            return True
        if is_director(moderator) and has_role(target, self.QUARANTINE_ROLE_ID):
            return True

        target_roles = [role for role in target.roles if role.id != self.QUARANTINE_ROLE_ID]
        if not target_roles:
            return True

        highest_target_role = max(target_roles, key=lambda r: r.position)
        return moderator.top_role.position > highest_target_role.position

    def check_can_moderate_target(self, moderator: discord.Member, target: discord.Member) -> tuple[bool, str]:
        if self.has_protected_role(target):
            if self.can_quarantine(moderator):
                return False, "You cannot ban/kick/timeout staff members. Use `/moderation quarantine` instead."
            return False, "You cannot ban/kick/timeout staff members."

        if not self.check_hierarchy(moderator, target):
            if self.can_quarantine(moderator):
                return False, "Target user is greater than or equal to your highest role."
            return False, "Target user is greater than or equal to your highest role."

        return True, ""
    async def auto_quarantine_moderator(self, moderator: discord.Member, guild: discord.Guild) -> None:
        if not guild or not self.bot.user:
            return

        quarantine_role = guild.get_role(self.QUARANTINE_ROLE_ID)
        if not quarantine_role:
            return

        saved_roles = [role.id for role in moderator.roles if role.id != guild.id]

        if "quarantined" not in self.data:
            self.data["quarantined"] = {}

        self.data["quarantined"][str(moderator.id)] = {
            "roles"          : saved_roles,
            "quarantined_at" : datetime.now(UTC).isoformat(),
            "quarantined_by" : self.bot.user.id,
            "reason"         : "UB Anti-Nuke: exceeded moderation rate limits",
        }
        self.save_data()

        try:
            roles_to_remove = [role for role in moderator.roles if role.id != guild.default_role.id]
            await moderator.remove_roles(*roles_to_remove, reason = "UB Anti-Nuke: Exceeded rate limits")
            await moderator.add_roles(quarantine_role, reason = "UB Anti-Nuke: Exceeded rate limits")

            bot_member = guild.get_member(self.bot.user.id)
            if bot_member:
                _ = await self.cases_manager.log_case(
                    guild       = guild,
                    case_type   = CaseType.QUARANTINE_ADD,
                    moderator   = bot_member,
                    reason      = "Exceeded moderation rate limits (auto-quarantine)",
                    target_user = moderator,
                    metadata    = {"roles_saved": len(saved_roles), "auto_quarantine": True},
                )
        except discord.Forbidden:
            pass


class MassConfigModal(Modal):
    def __init__(
        self,
        member      : discord.Member | None,
        parent      : "MassModerationView",
        *,
        is_global   : bool = False,
        with_duration : bool = False,
    ) -> None:
        super().__init__(title = "Configure")
        self.member         = member
        self.parent         = parent
        self.is_global      = is_global
        self.with_duration  = with_duration

        if with_duration:
            self.duration_input = TextInput(label = "Duration", required = True)
            self.add_item(self.duration_input)

        self.reason_input = TextInput(
            label    = "Reason",
            required = True,
            style    = discord.TextStyle.paragraph,
        )
        self.file_upload = FileUpload(required = False)

        self.add_item(self.reason_input)
        self.add_item(Label(text = "Proof", component = self.file_upload))

    async def on_submit(self, interaction : discord.Interaction) -> None:
        payload: dict[str, Any] = {
            "reason"   : self.reason_input.value,
            "proof"    : self.file_upload.values[0] if self.file_upload.values else None,
            "duration" : self.duration_input.value if self.with_duration else None,
        }

        if self.is_global:
            for member in self.parent.members:
                self.parent.values[member.id] = payload
        elif self.member:
            self.parent.values[self.member.id] = payload

        await self.parent.update(interaction)


class MassModerationView(LayoutView):
    def __init__(
        self,
        base              : ModerationBase,
        interaction       : discord.Interaction,
        members           : list[discord.Member],
        action_label      : str,
        action_key        : str,
        *,
        with_duration     : bool = False,
        precheck_callback : Callable[[discord.Member, discord.Member], tuple[bool, str]] | None = None,
        execute_callback  : Callable[
            [discord.Interaction, discord.Member, dict[str, Any]],
            Awaitable[tuple[bool, str]],
        ],
    ) -> None:
        super().__init__(timeout = 300)
        self.base             = base
        self.oi               = interaction
        self.members          = members
        self.action_label     = action_label
        self.action_key       = action_key
        self.with_duration    = with_duration
        self.precheck_callback = precheck_callback
        self.execute_callback = execute_callback
        self.page             = 0
        self.locked           = False
        self.values           = {
            member.id : {"reason" : None, "duration" : None, "proof" : None}
            for member in members
        }
        self.build()

    def _is_ready(self, member_id : int) -> bool:
        data = self.values[member_id]
        has_reason = bool(data.get("reason"))
        if self.with_duration:
            return has_reason and bool(data.get("duration"))
        return has_reason

    def build(self) -> None:
        self.clear_items()

        start   = self.page * 5
        end     = (self.page + 1) * 5
        sublist = self.members[start:end]

        for member in sublist:
            data       = self.values[member.id]
            display    = data["duration"] if self.with_duration else data["reason"]
            label_text = f"Edit: {display}"[:80] if display else "Set"
            style      = ButtonStyle.success if self._is_ready(member.id) else ButtonStyle.secondary
            button     = Button(label = label_text, style = style, disabled = self.locked)

            async def on_click(interaction : discord.Interaction, selected : discord.Member = member) -> None:
                await interaction.response.send_modal(
                    MassConfigModal(
                        selected,
                        self,
                        with_duration = self.with_duration,
                    ),
                )

            button.callback = on_click
            self.add_item(Section(TextDisplay(member.mention), accessory = button))

        self.add_item(Separator(visible = True))

        global_button = Button(label = "Global", style = ButtonStyle.primary, disabled = self.locked)
        run_button    = Button(label = "Execute", style = ButtonStyle.danger, disabled = self.locked)

        async def global_cb(interaction : discord.Interaction) -> None:
            await interaction.response.send_modal(
                MassConfigModal(
                    None,
                    self,
                    is_global     = True,
                    with_duration = self.with_duration,
                ),
            )

        async def execute_cb(interaction : discord.Interaction) -> None:
            actor = interaction.user
            if not isinstance(actor, discord.Member):
                return

            missing = [m.mention for m in self.members if not self._is_ready(m.id)]
            if missing:
                await send_custom_message(
                    interaction,
                    msg_type = "warning",
                    title    = "run mass moderation",
                    subtitle = f"Missing configuration for: {', '.join(missing[:10])}",
                    footer   = "Bad argument",
                )
                return

            self.locked = True
            await self.update(interaction)

            results: list[tuple[discord.Member, bool, str]] = []

            for member in self.members:
                if self.precheck_callback:
                    can_run, precheck_msg = self.precheck_callback(actor, member)
                    if not can_run:
                        results.append((member, False, precheck_msg))
                        continue

                if self.action_key in {"ban", "kick", "timeout", "quarantine"}:
                    can_proceed, error_msg = self.base.check_rate_limit(str(actor.id), self.action_key)
                    if not can_proceed:
                        guild = interaction.guild
                        if guild:
                            await self.base.auto_quarantine_moderator(actor, guild)
                        results.append((member, False, f"Rate limited: {error_msg}"))
                        break
                    self.base.add_rate_limit_entry(str(actor.id), self.action_key)

                ok, message = await self.execute_callback(interaction, member, self.values[member.id])
                results.append((member, ok, message))
                await asyncio.sleep(1.2)

            succeeded = [r for r in results if r[1]]
            failed    = [r for r in results if not r[1]]
            summary = f"Succeeded: **{len(succeeded)}** | Failed: **{len(failed)}**"
            if failed:
                failed_lines = [f"- {m.mention}: {msg}" for m, _ok, msg in failed[:10]]
                summary = f"{summary}\n" + "\n".join(failed_lines)

            msg_type = "success" if not failed else "warning"
            await send_custom_message(
                interaction,
                msg_type = msg_type,
                title    = f"complete mass {self.action_label.lower()} run",
                subtitle = summary,
            )

        global_button.callback = global_cb
        run_button.callback    = execute_cb
        self.add_item(ActionRow(global_button, run_button))

        max_page = (len(self.members) - 1) // 5
        first    = Button(label = "<<", disabled = self.page == 0)
        previous = Button(label = "<", disabled = self.page == 0)
        next_b   = Button(label = ">", disabled = self.page >= max_page)
        last     = Button(label = ">>", disabled = self.page >= max_page)

        async def move(interaction : discord.Interaction, value : int) -> None:
            if value == -2:
                self.page = 0
            elif value == -1 and self.page > 0:
                self.page -= 1
            elif value == 1 and self.page < max_page:
                self.page += 1
            elif value == 2:
                self.page = max_page
            await self.update(interaction)

        first.callback    = lambda i: move(i, -2)
        previous.callback = lambda i: move(i, -1)
        next_b.callback   = lambda i: move(i, 1)
        last.callback     = lambda i: move(i, 2)
        self.add_item(ActionRow(first, previous, next_b, last))

    async def update(self, interaction : discord.Interaction) -> None:
        self.build()
        if interaction.response.is_done():
            await interaction.edit_original_response(view = self)
        else:
            await interaction.response.edit_message(view = self)


class MemberPickerView(View):
    def __init__(
        self,
        base             : ModerationBase,
        action_label     : str,
        action_key       : str,
        *,
        with_duration    : bool = False,
        precheck_callback: Callable[[discord.Member, discord.Member], tuple[bool, str]] | None = None,
        execute_callback : Callable[
            [discord.Interaction, discord.Member, dict[str, Any]],
            Awaitable[tuple[bool, str]],
        ],
    ) -> None:
        super().__init__(timeout = 180)
        self.base             = base
        self.action_label     = action_label
        self.action_key       = action_key
        self.with_duration    = with_duration
        self.precheck_callback = precheck_callback
        self.execute_callback = execute_callback
        self.active_view : MassModerationView | None = None

    @discord.ui.select(
        cls         = discord.ui.UserSelect,
        placeholder = "Select members for mass moderation.",
        min_values  = 1,
        max_values  = 10,
    )
    async def select_callback(
        self,
        interaction : discord.Interaction,
        selection   : discord.ui.UserSelect,
    ) -> None:
        guild = interaction.guild
        if not guild:
            return

        members: list[discord.Member] = []
        errors = multi_custom_message(interaction)

        for user in selection.values:
            member = guild.get_member(user.id)
            if not member:
                _ = errors.add_field(
                    title     = "mass moderation",
                    msg_type  = "warning",
                    subfields = [
                        errors.add_subfield(
                            subtitle = f"Could not resolve **{user}** as a guild member.",
                            footer   = "Bad argument",
                        ),
                    ],
                )
                continue
            members.append(member)

        if errors.has_errors():
            await errors.send()
            return

        self.active_view = MassModerationView(
            self.base,
            interaction,
            members,
            self.action_label,
            self.action_key,
            with_duration    = self.with_duration,
            precheck_callback = self.precheck_callback,
            execute_callback = self.execute_callback,
        )
        await interaction.response.send_message(view = self.active_view, ephemeral = True)
