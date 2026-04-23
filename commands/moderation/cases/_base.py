from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar

import discord
from discord import ButtonStyle
from discord.ui import Button, View
from typing_extensions import override

if TYPE_CHECKING:
    from bot import UtilityBot

from constants import (
    ACCEPTED_EMOJI_ID,
    COLOR_BLACK,
    COLOR_BLURPLE,
    COLOR_GREEN,
    COLOR_GREY,
    COLOR_ORANGE,
    COLOR_RED,
    COLOR_YELLOW,
    DENIED_EMOJI_ID,
)
from core.cases import CasesManager, CaseType
from core.permissions import (
    is_administrator,
    is_director,
    is_moderator,
    is_senior_moderator,
)
from core.responses import send_custom_message

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Classification Request View
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ClassificationView(View):
    def __init__(self, case_id: int, cases_manager: CasesManager) -> None:
        super().__init__(timeout=None)
        self.case_id       = case_id
        self.cases_manager = cases_manager

        self.accept_button.custom_id = f"classify:accept:{case_id}"
        self.deny_button.custom_id   = f"classify:deny:{case_id}"

    @discord.ui.button(
        label     =  "Accept",
        style     = ButtonStyle.success,
        emoji     = f"{ACCEPTED_EMOJI_ID}",
        custom_id =  "classify:accept:0",
    )
    async def accept_button(
        self,
        interaction : discord.Interaction,
        _button     : Button[ClassificationView],
    ) -> None:
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not is_director(actor):
            await send_custom_message(
                interaction,
                msg_type = "error",
                title    = "run command",
                subtitle = "You are not authorized to run this command.",
                footer   = "No permissions",
            )
            return

        case = self.cases_manager.get_case_by_id(self.case_id)
        if not case or not case.get("pending_visibility"):
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "accept classification request",
                subtitle = f"Case **#{self.case_id}** has no pending visibility request.",
                footer   = "Bad argument",
            )
            return

        _ = self.cases_manager.approve_visibility(self.case_id)

        thread = interaction.channel
        if isinstance(thread, discord.Thread):
            _ = await interaction.response.send_message(
                f"{ACCEPTED_EMOJI_ID} **Classification request accepted by {actor.mention}.**",
            )
            with contextlib.suppress(discord.HTTPException):
                _ = await thread.edit(locked=True, archived=True)
        else:
            _ = await interaction.response.send_message(
                f"{ACCEPTED_EMOJI_ID} **Classification request accepted by {actor.mention}.**",
                ephemeral=True,
            )

        for child in self.children:
            if isinstance(child, Button):
                child.disabled = True
        with contextlib.suppress(discord.HTTPException):
            await interaction.message.edit(view=self) if interaction.message else None

    @discord.ui.button(
        label     = "Deny",
        style     = ButtonStyle.danger,
        emoji     = f"{DENIED_EMOJI_ID}",
        custom_id = "classify:deny:0",
    )
    async def deny_button(
        self,
        interaction : discord.Interaction,
        _button     : Button[ClassificationView],
    ) -> None:
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not is_director(actor):
            await send_custom_message(
                interaction,
                msg_type = "error",
                title    = "run command",
                subtitle = "You are not authorized to run this command.",
                footer   = "No permissions",
            )
            return

        case = self.cases_manager.get_case_by_id(self.case_id)
        if not case or not case.get("pending_visibility"):
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "deny classification request",
                subtitle = f"Case **#{self.case_id}** has no pending visibility request.",
                footer   = "Bad argument",
            )
            return

        _ = self.cases_manager.deny_visibility(self.case_id)

        thread = interaction.channel
        if isinstance(thread, discord.Thread):
            _ = await interaction.response.send_message(
                f"{DENIED_EMOJI_ID} **Classification request denied by {actor.mention}.**",
            )
            with contextlib.suppress(discord.HTTPException):
                _ = await thread.edit(locked=True, archived=True)
        else:
            _ = await interaction.response.send_message(
                f"{DENIED_EMOJI_ID} **Classification request denied by {actor.mention}.**",
                ephemeral=True,
            )

        for child in self.children:
            if isinstance(child, Button):
                child.disabled = True
        with contextlib.suppress(discord.HTTPException):
            await interaction.message.edit(view=self) if interaction.message else None

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Cases Paginators
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class CaseQueryPaginator(View):
    def __init__(
        self,
        interaction : discord.Interaction,
        cases       : list[dict[str, Any]],
        title       : str,
        color_map   : dict[str, discord.Color],
    ) -> None:
        super().__init__(timeout=120)
        self.interaction = interaction
        self.cases       = cases
        self.title       = title
        self.color_map   = color_map
        self.per_page    = 5
        self.page        = 0
        self.max_page    = (len(cases) - 1) // self.per_page

        self.update_buttons()

    def update_buttons(self) -> None:
        no_pagination_needed = len(self.cases) <= self.per_page

        self.first_page.disabled    = no_pagination_needed or self.page == 0
        self.previous_page.disabled = no_pagination_needed or self.page == 0
        self.next_page.disabled     = no_pagination_needed or self.page >= self.max_page
        self.last_page.disabled     = no_pagination_needed or self.page >= self.max_page

    def _format_case_field(self, case: dict[str, Any]) -> tuple[str, str]:
        case_type  = case["type"]
        type_label = case_type.replace("_", " ").title()
        created    = datetime.fromisoformat(case["created_at"])

        parts: list[str] = [f"**Type:** {type_label}"]

        if case.get("target_user_name"):
            parts.append(f"**User:** {case['target_user_name']} ({case['target_user_id']})")
        elif case.get("metadata", {}).get("target_user_ids"):
            user_ids = case["metadata"]["target_user_ids"]
            parts.append(f"**Users:** {len(user_ids)} targeted")

        parts.append(f"**Moderator:** {case['moderator_name']}")

        if case.get("duration"):
            parts.append(f"**Duration:** {case['duration']}")

        if case.get("reason"):
            reason = str(case["reason"])
            n_20 = 20
            if len(reason) > n_20:
                reason = reason[:197] + "..."
            parts.append(f"**Reason:** {reason}")

        if case.get("content"):
            content = str(case["content"])
            n_20 = 20
            if len(content) > n_20:
                content = content[:197] + "..."
            parts.append(f"**Content:** {content}")

        vis = case.get("visibility_level", "moderators")
        if vis != "moderators":
            parts.append(f"**Visibility:** {str(vis).replace('_', ' ').title()}")

        metadata : dict[str, Any] = case.get("metadata") or {}
        if metadata.get("mass_action"):
            parts.append("**Mass Action:** Yes")

        parts.append(f"**Created:** {discord.utils.format_dt(created, 'R')}")

        return f"Case #{case['case_id']}", "\n".join(parts)

    def get_embed(self) -> discord.Embed:
        start      = self.page * self.per_page
        end        = start + self.per_page
        page_cases = self.cases[start:end]

        embed = discord.Embed(
            title     = self.title,
            color     = COLOR_BLURPLE,
            timestamp = datetime.now(UTC),
        )

        for case in page_cases:
            name, value = self._format_case_field(case)
            _ = embed.add_field(name=name, value=value, inline=False)

        _ = embed.set_footer(
            text=f"Page {self.page + 1}/{self.max_page + 1} · {len(self.cases)} cases total",
        )

        return embed

    @override
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.interaction.user

    @discord.ui.button(label="<<", style=ButtonStyle.secondary)
    async def first_page(
        self,
        interaction : discord.Interaction,
        _button     : Button[CaseQueryPaginator],
    ) -> None:
        self.page = 0
        self.update_buttons()
        _ = await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="<", style=ButtonStyle.secondary)
    async def previous_page(
        self,
        interaction : discord.Interaction,
        _button     : Button[CaseQueryPaginator],
    ) -> None:
        if self.page > 0:
            self.page -= 1
        self.update_buttons()
        _ = await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label=">", style=ButtonStyle.secondary)
    async def next_page(
        self,
        interaction : discord.Interaction,
        _button     : Button[CaseQueryPaginator],
    ) -> None:
        if self.page < self.max_page:
            self.page += 1
        self.update_buttons()
        _ = await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label=">>", style=ButtonStyle.secondary)
    async def last_page(
        self,
        interaction : discord.Interaction,
        _button     : Button[CaseQueryPaginator],
    ) -> None:
        self.page = self.max_page
        self.update_buttons()
        _ = await interaction.response.edit_message(embed=self.get_embed(), view=self)


class CaseViewPaginator(View):
    def __init__(
        self,
        interaction : discord.Interaction,
        case_embed  : discord.Embed,
        notes       : list[dict[str, Any]],
    ) -> None:
        super().__init__(timeout=120)
        self.interaction = interaction
        self.case_embed  = case_embed
        self.notes       = notes
        self.per_page    = 5
        self.page        = 0
        self.max_page    = max(0, (len(notes) - 1) // self.per_page) if notes else 0

        self.update_buttons()

    def update_buttons(self) -> None:
        no_pagination_needed = len(self.notes) <= self.per_page

        self.first_page.disabled    = no_pagination_needed or self.page == 0
        self.previous_page.disabled = no_pagination_needed or self.page == 0
        self.next_page.disabled     = no_pagination_needed or self.page >= self.max_page
        self.last_page.disabled     = no_pagination_needed or self.page >= self.max_page

    def get_embed(self) -> discord.Embed:
        embed = self.case_embed.copy()

        if not self.notes:
            return embed

        start      = self.page * self.per_page
        end        = start + self.per_page
        page_notes = self.notes[start:end]

        _ = embed.add_field(name="—— Notes ——", value="\u200b", inline=False)

        for note in page_notes:
            note_created = datetime.fromisoformat(note["created_at"])
            note_parts   = [
                f"**Moderator:** {note['moderator_name']}",
                f"**Created:** {discord.utils.format_dt(note_created, 'R')}",
            ]
            if note.get("content"):
                note_parts.append(f"\n{note['content']}")
            _ = embed.add_field(
                name   = f"Note #{note['case_id']}",
                value  = "\n".join(note_parts),
                inline = False,
            )

        _ = embed.set_footer(
            text=f"Notes page {self.page + 1}/{self.max_page + 1} · {len(self.notes)} notes total",
        )

        return embed

    @override
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.interaction.user

    @discord.ui.button(label="<<", style=ButtonStyle.secondary)
    async def first_page(
        self,
        interaction : discord.Interaction,
        _button     : Button[CaseViewPaginator],
    ) -> None:
        self.page = 0
        self.update_buttons()
        _ = await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="<", style=ButtonStyle.secondary)
    async def previous_page(
        self,
        interaction : discord.Interaction,
        _button     : Button[CaseViewPaginator],
    ) -> None:
        if self.page > 0:
            self.page -= 1
        self.update_buttons()
        _ = await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label=">", style=ButtonStyle.secondary)
    async def next_page(
        self,
        interaction : discord.Interaction,
        _button     : Button[CaseViewPaginator],
    ) -> None:
        if self.page < self.max_page:
            self.page += 1
        self.update_buttons()
        _ = await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label=">>", style=ButtonStyle.secondary)
    async def last_page(
        self,
        interaction : discord.Interaction,
        _button     : Button[CaseViewPaginator],
    ) -> None:
        self.page = self.max_page
        self.update_buttons()
        _ = await interaction.response.edit_message(embed=self.get_embed(), view=self)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Cases Mixin
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class CasesMixin:
    COLOR_MAP: ClassVar[dict[str, discord.Color]] = {
        CaseType.BAN.value               : COLOR_BLACK,
        CaseType.UNBAN.value             : COLOR_GREEN,
        CaseType.KICK.value              : COLOR_RED,
        CaseType.TIMEOUT.value           : COLOR_YELLOW,
        CaseType.UNTIMEOUT.value         : COLOR_GREEN,
        CaseType.QUARANTINE_ADD.value    : COLOR_ORANGE,
        CaseType.QUARANTINE_REMOVE.value : COLOR_GREEN,
        CaseType.LOCKDOWN_ADD.value      : COLOR_GREY,
        CaseType.LOCKDOWN_REMOVE.value   : COLOR_GREEN,
        CaseType.PURGE.value             : COLOR_BLURPLE,
        CaseType.NOTE.value              : COLOR_BLURPLE,
    }

    TITLE_MAP: ClassVar[dict[str, str]] = {
        CaseType.BAN.value               : "Member Banned",
        CaseType.UNBAN.value             : "User Un-banned",
        CaseType.KICK.value              : "Member Kicked",
        CaseType.TIMEOUT.value           : "Member Muted",
        CaseType.UNTIMEOUT.value         : "Member Un-muted",
        CaseType.QUARANTINE_ADD.value    : "Member Quarantined",
        CaseType.QUARANTINE_REMOVE.value : "Member Un-quarantined",
        CaseType.LOCKDOWN_ADD.value      : "Lockdown Engaged",
        CaseType.LOCKDOWN_REMOVE.value   : "Lockdown Lifted",
        CaseType.PURGE.value             : "Messages Purged",
        CaseType.NOTE.value              : "Note Added",
    }

    def can_view(self, member: discord.Member) -> bool:
        return (
            is_director(member)
            or is_administrator(member)
            or is_moderator(member)
        )

    def can_configure(self, member: discord.Member) -> bool:
        return is_director(member)

    def _visibility_level(self, member: discord.Member) -> int:
        if is_director(member):
            return 3
        if is_senior_moderator(member):
            return 2
        if is_moderator(member):
            return 1
        return 0

    def can_see_case(self, member: discord.Member, case: dict[str, Any]) -> bool:
        vis   = case.get("visibility_level", "moderators")
        level = self._visibility_level(member)
        if vis == "directors":
            n_3 = 3
            return level >= n_3
        if vis == "senior_moderators":
            n_2 = 2
            return level >= n_2
        return level >= 1

    def can_edit_entry(self, member: discord.Member, case: dict[str, Any]) -> bool:
        return (
            member.id == case["moderator_id"]
            or is_senior_moderator(member)
            or is_director(member)
        )

    def parse_dt(self, value: str) -> datetime | None:
        with contextlib.suppress(ValueError):
            return datetime.fromisoformat(value)
        return None

    async def build_case_embed(
        self,
        bot   : UtilityBot,
        _guild : discord.Guild,
        case  : dict[str, Any],
    ) -> discord.Embed:
        case_type  = case["type"]
        type_label = case_type.replace("_", " ").title()
        created    = datetime.fromisoformat(case["created_at"])

        embed = discord.Embed(
            title     = f"Case #{case['case_id']} — {type_label}",
            color     = self.COLOR_MAP.get(case_type, COLOR_BLURPLE),
            timestamp = created,
        )

        mod_added = False
        with contextlib.suppress(discord.NotFound, discord.HTTPException):
            mod = await bot.fetch_user(case["moderator_id"])
            _ = embed.add_field(name="Moderator", value=mod.mention, inline=True)
            mod_added = True
        if not mod_added:
            _ = embed.add_field(name="Moderator", value=case["moderator_name"], inline=True)

        if case.get("target_user_id"):
            user_added = False
            with contextlib.suppress(discord.NotFound, discord.HTTPException):
                user = await bot.fetch_user(case["target_user_id"])
                _ = embed.add_field(
                    name   = "User",
                    value  = f"{user.mention} ({user.id})",
                    inline = True,
                )
                user_added = True
            if not user_added:
                _ = embed.add_field(
                    name   = "User",
                    value  = f"{case['target_user_name']} ({case['target_user_id']})",
                    inline = True,
                )

        if case.get("duration"):
            _ = embed.add_field(name="Duration", value=case["duration"], inline=True)

        if case.get("reason"):
            _ = embed.add_field(name="Reason", value=case["reason"], inline=False)

        if case.get("content"):
            _ = embed.add_field(name="Content", value=case["content"], inline=False)

        if case.get("related_case_id"):
            _ = embed.add_field(name="Related Case", value=f"#{case['related_case_id']}", inline=True)

        metadata : dict[str, Any] = case.get("metadata") or {}
        if metadata.get("mass_action"):
            _ = embed.add_field(name="Mass Action", value="Yes", inline=True)

        vis = case.get("visibility_level", "moderators")
        _ = embed.add_field(
            name   = "Visibility",
            value  = str(vis).replace("_", " ").title(),
            inline = True,
        )

        _ = embed.add_field(
            name   = "Created",
            value  = discord.utils.format_dt(created, "R"),
            inline = True,
        )

        if case.get("edited_at"):
            edited = datetime.fromisoformat(case["edited_at"])
            _ = embed.add_field(
                name   = "Edited",
                value  = discord.utils.format_dt(edited, "R"),
                inline = True,
            )

        if case.get("pending_visibility"):
            pending = str(case["pending_visibility"]).replace("_", " ").title()
            _ = embed.add_field(name="Pending Visibility", value=pending, inline=True)

        return embed


__all__ = [
    "CaseQueryPaginator",
    "CaseViewPaginator",
    "CasesMixin",
    "ClassificationView",
]
