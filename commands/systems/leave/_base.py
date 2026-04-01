import contextlib
import enum
import json
import re
from datetime import UTC, datetime
from datetime import date as date_type
from pathlib import Path
from typing import Any, cast

import discord
from typing_extensions import override

from constants import (
    ADMINISTRATORS_ROLE_ID,
    BOT_OWNER_ID,
    COLOR_RED,
    DIRECTORS_ROLE_ID,
    JUNIOR_ADMINISTRATORS_ROLE_ID,
    JUNIOR_MODERATORS_ROLE_ID,
    MODERATORS_AND_ADMINISTRATORS_ROLE_ID,
    MODERATORS_ROLE_ID,
    SENIOR_ADMINISTRATORS_ROLE_ID,
    SENIOR_MODERATORS_ROLE_ID,
    STAFF_COMMITTEE_ROLE_ID,
    STAFF_ROLE_ID,
    SUPPORTING_DIRECTORS_ROLE_ID,
)
from core.permissions import is_director, is_staff
from core.utils import send_major_error, send_minor_error

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Leave Base
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

DATA_FILE = "leave_data.json"

ALL_STAFF_ROLE_IDS: list[int] = [
    STAFF_ROLE_ID,
    SENIOR_MODERATORS_ROLE_ID,
    JUNIOR_MODERATORS_ROLE_ID,
    MODERATORS_ROLE_ID,
    STAFF_COMMITTEE_ROLE_ID,
    MODERATORS_AND_ADMINISTRATORS_ROLE_ID,
    SENIOR_ADMINISTRATORS_ROLE_ID,
    JUNIOR_ADMINISTRATORS_ROLE_ID,
    ADMINISTRATORS_ROLE_ID,
    DIRECTORS_ROLE_ID,
    SUPPORTING_DIRECTORS_ROLE_ID,
]

_TIMER_RE = re.compile(r"^(?:(\d+)w)?(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?$", re.IGNORECASE)
DATE_FMT  = "%Y-%m-%d"

class LeaveType(enum.Enum):
    none       = "none"
    soft_clean = "soft_clean"
    hard_clean = "hard_clean"

def load_data() -> dict[str, Any]:
    if not Path(DATA_FILE).exists():
        return {}
    with Path(DATA_FILE).open() as f:
        return json.load(f)

def save_data(data: dict[str, Any]) -> None:
    with Path(DATA_FILE).open("w") as f:
        json.dump(data, f, indent=2)

def extract_name(nickname: str) -> str:
    if "|" in nickname:
        return nickname.split("|")[-1].strip()
    return nickname

def can_manage_leave(invocator: discord.Member, target: discord.Member) -> bool:
    if not is_staff(invocator):
        return False
    if target.id != invocator.id:
        return is_director(invocator)
    return True

def normalize_entry(raw: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, str):
        return {
            "original_nick": raw,
            "leave_type":    LeaveType.none.value,
            "removed_roles": [],
            "begin_date":    None,
            "end_date":      None,
            "timer_end":     None,
            "timer_seconds": None,
        }
    entry = dict(raw)
    _ = entry.setdefault("original_nick", None)
    entry.setdefault("leave_type",    LeaveType.none.value)
    entry.setdefault("removed_roles", [])
    _ = entry.setdefault("begin_date",    None)
    _ = entry.setdefault("end_date",      None)
    _ = entry.setdefault("timer_end",     None)
    _ = entry.setdefault("timer_seconds", None)
    return entry

def parse_timer(value: str) -> int | None:
    m = _TIMER_RE.match(value.strip())
    if not m or not any(m.groups()):
        return None
    weeks, days, hours, minutes = (int(x) if x else 0 for x in m.groups())
    total = minutes * 60 + hours * 3600 + days * 86400 + weeks * 604800
    return total if total > 0 else None

def parse_date(value: str) -> date_type | None:
    with contextlib.suppress(ValueError):
        return datetime.strptime(value.strip(), DATE_FMT).replace(tzinfo=UTC).date()
    return None

def entry_has_automation(entry: dict[str, Any]) -> bool:
    return bool(entry.get("begin_date") or entry.get("end_date") or entry.get("timer_end"))

def describe_automation(entry: dict[str, Any]) -> str:
    parts: list[str] = []
    if entry.get("begin_date"):
        parts.append(f"scheduled to **begin** on `{entry['begin_date']}`")
    if entry.get("end_date"):
        parts.append(f"scheduled to **end** on `{entry['end_date']}`")
    if entry.get("timer_end"):
        ts    = cast("float", entry["timer_end"])
        dt    = datetime.fromtimestamp(ts, tz=UTC)
        stamp = discord.utils.format_dt(dt, style="f")
        parts.append(f"on a **timer** expiring {stamp}")
    return ", ".join(parts) if parts else "unknown automation"

def build_leave_nick(name: str) -> str | None:
    long_nick = f"P. Leave | {name}"
    n_32 = 32
    if len(long_nick) <= n_32:
        return long_nick
    short_nick = f"PL | {name}"
    if len(short_nick) <= n_32:
        return short_nick
    return None

class HardCleanConfirmView(discord.ui.LayoutView):
    def __init__(
        self,
        invocator_id:    int,
        target:          discord.Member,
        roles_to_remove: list[discord.Role],
        warning_text:    str,
    ) -> None:
        super().__init__(timeout = 60)
        self.invocator_id    = invocator_id
        self.target          = target
        self.roles_to_remove = roles_to_remove
        self.message: discord.WebhookMessage | None = None

        self._confirm_button: discord.ui.Button[HardCleanConfirmView] = discord.ui.Button(label="Confirm", style=discord.ButtonStyle.danger)
        self._confirm_button.callback = self._confirm_callback

        self._cancel_button: discord.ui.Button[HardCleanConfirmView] = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.primary)
        self._cancel_button.callback = self._cancel_callback

        self._action_row: discord.ui.ActionRow[HardCleanConfirmView] = discord.ui.ActionRow()
        _ = self._action_row.add_item(self._confirm_button)
        _ = self._action_row.add_item(self._cancel_button)

        self._text_display: discord.ui.TextDisplay[HardCleanConfirmView] = discord.ui.TextDisplay(content = warning_text)

        container: discord.ui.Container[HardCleanConfirmView] = discord.ui.Container(accent_color = COLOR_RED)
        _ = container.add_item(self._text_display)
        _ = container.add_item(discord.ui.Separator(visible = True, spacing = discord.SeparatorSpacing.large))
        _ = container.add_item(self._action_row)

        _ = self.add_item(container)

    def _disable_buttons(self) -> None:
        self._confirm_button.disabled = True
        self._cancel_button.disabled  = True

    async def _confirm_callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.invocator_id:
            await send_minor_error(interaction, "This confirmation is not for you.", subtitle = "Invalid operation.")
            return

        self.stop()

        try:
            await self.target.remove_roles(*self.roles_to_remove, reason=f"Hard Clean leave by {interaction.user.display_name}")
        except discord.Forbidden:
            await send_major_error(
                interaction,
                title = "Error!",
                texts=f"I lack the permissions to remove roles from {self.target.mention}.",
                subtitle = "Invalid configuration. Contact the owner.",
            )
            return
        except discord.HTTPException:
            await send_major_error(
                interaction,
                title = "Error!",
                texts="A Discord API error occurred.",
                subtitle = f"Invalid operation. Contact <@{BOT_OWNER_ID}>.",
            )
            return

        self._disable_buttons()
        self._text_display.content = f"{self.target.mention} has been hard cleaned —— {len(self.roles_to_remove)} staff role(s) removed."
        _ = await interaction.response.edit_message(view = self)

    async def _cancel_callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.invocator_id:
            await send_minor_error(interaction, "This confirmation is not for you.", subtitle = "Invalid operation.")
            return

        self._disable_buttons()
        self.stop()

        self._text_display.content = "Hard clean cancelled —— no changes were made."
        _ = await interaction.response.edit_message(view = self)

    @override
    async def on_timeout(self) -> None:
        self._disable_buttons()
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                self._text_display.content = "Hard clean timed out —— no changes were made."
                _ = await self.message.edit(view = self)

class InterferenceConfirmView(discord.ui.LayoutView):
    def __init__(
        self,
        invocator_id: int,
        warning_text: str,
    ) -> None:
        super().__init__(timeout = 60)
        self.invocator_id = invocator_id
        self.confirmed    = False
        self.message: discord.WebhookMessage | None = None

        self._confirm_button: discord.ui.Button[InterferenceConfirmView] = discord.ui.Button(label="Proceed Anyway", style=discord.ButtonStyle.danger)
        self._confirm_button.callback = self._confirm_callback

        self._cancel_button: discord.ui.Button[InterferenceConfirmView] = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.primary)
        self._cancel_button.callback = self._cancel_callback

        self._action_row: discord.ui.ActionRow[InterferenceConfirmView] = discord.ui.ActionRow()
        _ = self._action_row.add_item(self._confirm_button)
        _ = self._action_row.add_item(self._cancel_button)

        self._text_display: discord.ui.TextDisplay[InterferenceConfirmView] = discord.ui.TextDisplay(content = warning_text)

        container: discord.ui.Container[InterferenceConfirmView] = discord.ui.Container(accent_color = COLOR_RED)
        _ = container.add_item(self._text_display)
        _ = container.add_item(discord.ui.Separator(visible = True, spacing = discord.SeparatorSpacing.large))
        _ = container.add_item(self._action_row)

        _ = self.add_item(container)

    def _disable_buttons(self) -> None:
        self._confirm_button.disabled = True
        self._cancel_button.disabled  = True

    async def _confirm_callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.invocator_id:
            await send_minor_error(interaction, "This confirmation is not for you.", subtitle = "Invalid operation.")
            return

        self.confirmed = True
        self._disable_buttons()
        self._text_display.content = "Proceeding —— automation override confirmed."
        self.stop()
        _ = await interaction.response.edit_message(view = self)

    async def _cancel_callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.invocator_id:
            await send_minor_error(interaction, "This confirmation is not for you.", subtitle = "Invalid operation.")
            return

        self._disable_buttons()
        self._text_display.content = "Action cancelled —— no changes were made."
        self.stop()
        _ = await interaction.response.edit_message(view = self)

    @override
    async def on_timeout(self) -> None:
        self._disable_buttons()
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                self._text_display.content = "Action timed out —— no changes were made."
                _ = await self.message.edit(view = self)
