import discord
from discord.ext import commands
from discord import app_commands

import contextlib
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    cast,
)

if TYPE_CHECKING:
    from bot import UtilityBot

from core.cases import (
    CaseType,
    CasesManager,
)
from core.permissions import (
    is_administrator,
    is_director,
    is_moderator,
    is_senior_moderator,
)
from core.utils import (
    send_major_error,
    send_minor_error,
)
from constants import (
    COLOR_GREEN,
    COLOR_YELLOW,
    COLOR_ORANGE,
    COLOR_RED,
    COLOR_BLURPLE,
    COLOR_GREY,
    COLOR_BLACK,
    DIRECTORS_ROLE_ID,
    SENIOR_MODERATORS_ROLE_ID,
    MODERATORS_ROLE_ID,
    ADMINISTRATORS_ROLE_ID,
    DIRECTOR_TASKS_CHANNEL_ID,
    ACCEPTED_EMOJI_ID,
    DENIED_EMOJI_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Classification Request View
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ClassificationView(discord.ui.View):
    def __init__(self, case_id: int, cases_manager: "CasesManager") -> None:
        super().__init__(timeout=None)
        self.case_id       = case_id
        self.cases_manager = cases_manager

        self.accept_button.custom_id = f"classify:accept:{case_id}"
        self.deny_button.custom_id   = f"classify:deny:{case_id}"

    @discord.ui.button(
        label     = "Accept",
        style     = discord.ButtonStyle.success,
        emoji     = "✅",
        custom_id = "classify:accept:0",
    )
    async def accept_button(
        self,
        interaction: discord.Interaction,
        button:      discord.ui.Button["ClassificationView"],
    ) -> None:
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not is_director(actor):
            await send_major_error(
                interaction,
                title    = "Unauthorized!",
                texts    = "Only Directors can accept classification requests.",
                subtitle = "Invalid permissions.",
            )
            return

        case = self.cases_manager.get_case_by_id(self.case_id)
        if not case or not case.get("pending_visibility"):
            await send_minor_error(
                interaction,
                texts = f"Case **#{self.case_id}** has no pending visibility request.",
            )
            return

        self.cases_manager.approve_visibility(self.case_id)

        thread = interaction.channel
        if isinstance(thread, discord.Thread):
            await interaction.response.send_message(
                f"{ACCEPTED_EMOJI_ID} **Classification request accepted by {actor.mention}.**"
            )
            with contextlib.suppress(discord.HTTPException):
                await thread.edit(locked=True, archived=True)
        else:
            await interaction.response.send_message(
                f"{ACCEPTED_EMOJI_ID} **Classification request accepted by {actor.mention}.**",
                ephemeral=True,
            )

        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        with contextlib.suppress(discord.HTTPException):
            await interaction.message.edit(view=self) if interaction.message else None

    @discord.ui.button(
        label     = "Deny",
        style     = discord.ButtonStyle.danger,
        emoji     = "❌",
        custom_id = "classify:deny:0",
    )
    async def deny_button(
        self,
        interaction: discord.Interaction,
        button:      discord.ui.Button["ClassificationView"],
    ) -> None:
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not is_director(actor):
            await send_major_error(
                interaction,
                title    = "Unauthorized!",
                texts    = "Only Directors can deny classification requests.",
                subtitle = "Invalid permissions.",
            )
            return

        case = self.cases_manager.get_case_by_id(self.case_id)
        if not case or not case.get("pending_visibility"):
            await send_minor_error(
                interaction,
                texts = f"Case **#{self.case_id}** has no pending visibility request.",
            )
            return

        self.cases_manager.deny_visibility(self.case_id)

        thread = interaction.channel
        if isinstance(thread, discord.Thread):
            await interaction.response.send_message(
                f"{DENIED_EMOJI_ID} **Classification request denied by {actor.mention}.**"
            )
            with contextlib.suppress(discord.HTTPException):
                await thread.edit(locked=True, archived=True)
        else:
            await interaction.response.send_message(
                f"{DENIED_EMOJI_ID} **Classification request denied by {actor.mention}.**",
                ephemeral=True,
            )

        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        with contextlib.suppress(discord.HTTPException):
            await interaction.message.edit(view=self) if interaction.message else None

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Cases Paginators
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class CaseQueryPaginator(discord.ui.View):
    def __init__(
        self,
        interaction: discord.Interaction,
        cases:       list[dict[str, Any]],
        title:       str,
        color_map:   dict[str, discord.Color],
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

        parts.append(f"**Moderator:** {case['moderator_name']}")

        if case.get("duration"):
            parts.append(f"**Duration:** {case['duration']}")

        if case.get("reason"):
            reason = str(case["reason"])
            if len(reason) > 200:
                reason = reason[:197] + "..."
            parts.append(f"**Reason:** {reason}")

        if case.get("content"):
            content = str(case["content"])
            if len(content) > 200:
                content = content[:197] + "..."
            parts.append(f"**Content:** {content}")

        vis = case.get("visibility_level", "moderators")
        if vis != "moderators":
            parts.append(f"**Visibility:** {str(vis).replace('_', ' ').title()}")

        parts.append(f"**Created:** {discord.utils.format_dt(created, 'R')}")

        return f"Case #{case['case_id']}", "\n".join(parts)

    def get_embed(self) -> discord.Embed:
        start = self.page * self.per_page
        end   = start + self.per_page
        page_cases = self.cases[start:end]

        embed = discord.Embed(
            title     = self.title,
            color     = COLOR_BLURPLE,
            timestamp = datetime.now(),
        )

        for case in page_cases:
            name, value = self._format_case_field(case)
            embed.add_field(name=name, value=value, inline=False)

        embed.set_footer(
            text=f"Page {self.page + 1}/{self.max_page + 1} · {len(self.cases)} cases total"
        )

        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.interaction.user

    @discord.ui.button(label="<<", style=discord.ButtonStyle.secondary)
    async def first_page(
        self,
        interaction: discord.Interaction,
        button:      discord.ui.Button["CaseQueryPaginator"],
    ) -> None:
        self.page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="<", style=discord.ButtonStyle.secondary)
    async def previous_page(
        self,
        interaction: discord.Interaction,
        button:      discord.ui.Button["CaseQueryPaginator"],
    ) -> None:
        if self.page > 0:
            self.page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label=">", style=discord.ButtonStyle.secondary)
    async def next_page(
        self,
        interaction: discord.Interaction,
        button:      discord.ui.Button["CaseQueryPaginator"],
    ) -> None:
        if self.page < self.max_page:
            self.page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label=">>", style=discord.ButtonStyle.secondary)
    async def last_page(
        self,
        interaction: discord.Interaction,
        button:      discord.ui.Button["CaseQueryPaginator"],
    ) -> None:
        self.page = self.max_page
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)


class CaseViewPaginator(discord.ui.View):
    def __init__(
        self,
        interaction: discord.Interaction,
        case_embed:  discord.Embed,
        notes:       list[dict[str, Any]],
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

        embed.add_field(name="—— Notes ——", value="\u200b", inline=False)

        for note in page_notes:
            note_created = datetime.fromisoformat(note["created_at"])
            note_parts   = [
                f"**Moderator:** {note['moderator_name']}",
                f"**Created:** {discord.utils.format_dt(note_created, 'R')}",
            ]
            if note.get("content"):
                note_parts.append(f"\n{note['content']}")
            embed.add_field(
                name   = f"Note #{note['case_id']}",
                value  = "\n".join(note_parts),
                inline = False,
            )

        embed.set_footer(
            text=f"Notes page {self.page + 1}/{self.max_page + 1} · {len(self.notes)} notes total"
        )

        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.interaction.user

    @discord.ui.button(label="<<", style=discord.ButtonStyle.secondary)
    async def first_page(
        self,
        interaction: discord.Interaction,
        button:      discord.ui.Button["CaseViewPaginator"],
    ) -> None:
        self.page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="<", style=discord.ButtonStyle.secondary)
    async def previous_page(
        self,
        interaction: discord.Interaction,
        button:      discord.ui.Button["CaseViewPaginator"],
    ) -> None:
        if self.page > 0:
            self.page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label=">", style=discord.ButtonStyle.secondary)
    async def next_page(
        self,
        interaction: discord.Interaction,
        button:      discord.ui.Button["CaseViewPaginator"],
    ) -> None:
        if self.page < self.max_page:
            self.page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label=">>", style=discord.ButtonStyle.secondary)
    async def last_page(
        self,
        interaction: discord.Interaction,
        button:      discord.ui.Button["CaseViewPaginator"],
    ) -> None:
        self.page = self.max_page
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Cases Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class CasesCommands(commands.Cog):
    def __init__(self, bot: "UtilityBot") -> None:
        self.bot = bot

        if not hasattr(bot, "cases_manager"):
            bot.cases_manager = CasesManager(bot)

        self.cases_manager: CasesManager = bot.cases_manager

        self.DIRECTORS_ROLE_ID         = DIRECTORS_ROLE_ID
        self.SENIOR_MODERATORS_ROLE_ID = SENIOR_MODERATORS_ROLE_ID
        self.MODERATORS_ROLE_ID        = MODERATORS_ROLE_ID
        self.ADMINISTRATORS_ROLE_ID    = ADMINISTRATORS_ROLE_ID

        self._register_classification_views()

    def _register_classification_views(self) -> None:
        pending: list[dict[str, Any]] = self.cases_manager.get_all_pending_classifications()
        for case in pending:
            case_id = cast("int", case["case_id"])
            view    = ClassificationView(case_id, self.cases_manager)
            self.bot.add_view(view)

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

    def _can_see_case(self, member: discord.Member, case: dict[str, Any]) -> bool:
        vis   = case.get("visibility_level", "moderators")
        level = self._visibility_level(member)
        if vis == "directors":
            return level >= 3
        if vis == "senior_moderators":
            return level >= 2
        return level >= 1

    def _can_edit_entry(self, member: discord.Member, case: dict[str, Any]) -> bool:
        return (
            member.id == case["moderator_id"]
            or is_senior_moderator(member)
            or is_director(member)
        )

    def _parse_dt(self, value: str) -> datetime | None:
        with contextlib.suppress(ValueError):
            return datetime.fromisoformat(value)
        return None

    COLOR_MAP: dict[str, discord.Color] = {
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

    TITLE_MAP: dict[str, str] = {
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

    async def _build_case_embed(
        self,
        guild : discord.Guild,
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
            mod = await self.bot.fetch_user(case["moderator_id"])
            embed.add_field(name="Moderator", value=mod.mention, inline=True)
            mod_added = True
        if not mod_added:
            embed.add_field(name="Moderator", value=case["moderator_name"], inline=True)

        if case.get("target_user_id"):
            user_added = False
            with contextlib.suppress(discord.NotFound, discord.HTTPException):
                user = await self.bot.fetch_user(case["target_user_id"])
                embed.add_field(name="User", value=f"{user.mention} ({user.id})", inline=True)
                user_added = True
            if not user_added:
                embed.add_field(
                    name   = "User",
                    value  = f"{case['target_user_name']} ({case['target_user_id']})",
                    inline = True,
                )

        if case.get("duration"):
            embed.add_field(name="Duration", value=case["duration"], inline=True)

        if case.get("reason"):
            embed.add_field(name="Reason", value=case["reason"], inline=False)

        if case.get("content"):
            embed.add_field(name="Content", value=case["content"], inline=False)

        if case.get("related_case_id"):
            embed.add_field(name="Related Case", value=f"#{case['related_case_id']}", inline=True)

        vis = case.get("visibility_level", "moderators")
        embed.add_field(
            name   = "Visibility",
            value  = str(vis).replace("_", " ").title(),
            inline = True,
        )

        embed.add_field(
            name   = "Created",
            value  = discord.utils.format_dt(created, "R"),
            inline = True,
        )

        if case.get("edited_at"):
            edited = datetime.fromisoformat(case["edited_at"])
            embed.add_field(
                name   = "Edited",
                value  = discord.utils.format_dt(edited, "R"),
                inline = True,
            )

        if case.get("pending_visibility"):
            pending = str(case["pending_visibility"]).replace("_", " ").title()
            embed.add_field(name="Pending Visibility", value=pending, inline=True)

        return embed

    cases_group = app_commands.Group(
        name        = "cases",
        description = "Moderators only —— Cases management."
    )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /cases query Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @cases_group.command(name="query", description="Query the moderation case history.")
    @app_commands.describe(
        user          = "Filter by user.",
        moderator     = "Filter by moderator.",
        case_type     = "Filter by case type.",
        contains      = "Search reason or content.",
        after         = "Only cases after this date (ISO format: YYYY-MM-DD).",
        before        = "Only cases before this date (ISO format: YYYY-MM-DD).",
        include_notes = "Include note entries. Default: true.",
    )
    @app_commands.rename(
        case_type     = "type",
        include_notes = "include-notes",
    )
    async def cases_query(
        self,
        interaction:   discord.Interaction,
        user:          discord.User | None = None,
        moderator:     discord.User | None = None,
        case_type:     Literal[
            "ban", "unban", "kick",
            "timeout", "untimeout",
            "quarantine_add", "quarantine_remove",
            "lockdown_add", "lockdown_remove",
            "purge", "note",
        ] | None = None,
        contains:      str | None = None,
        after:         str | None = None,
        before:        str | None = None,
        include_notes: bool       = True,
    ) -> None:
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_view(actor):
            await send_major_error(
                interaction,
                title    = "Unauthorized!",
                texts    = "You lack the necessary permissions to query cases.",
                subtitle = "Invalid permissions.",
            )
            return

        guild = interaction.guild
        if not guild:
            return

        after_dt:  datetime | None = None
        before_dt: datetime | None = None

        if after:
            after_dt = self._parse_dt(after)
            if after_dt is None:
                await send_minor_error(
                    interaction,
                    texts = "Invalid `after` date. Use ISO format: `YYYY-MM-DD`.",
                )
                return

        if before:
            before_dt = self._parse_dt(before)
            if before_dt is None:
                await send_minor_error(
                    interaction,
                    texts = "Invalid `before` date. Use ISO format: `YYYY-MM-DD`.",
                )
                return

        await interaction.response.defer(ephemeral=True)

        cases = self.cases_manager.get_cases(
            guild_id      = guild.id,
            user_id       = user.id if user else None,
            moderator_id  = moderator.id if moderator else None,
            case_type     = case_type,
            contains      = contains,
            after         = after_dt,
            before        = before_dt,
            include_notes = include_notes,
        )

        cases = [c for c in cases if self._can_see_case(actor, c)]

        if not cases:
            filters: list[str] = []
            if user:
                filters.append(f"user {user.mention}")
            if moderator:
                filters.append(f"moderator {moderator.mention}")
            if case_type:
                filters.append(f"type **{case_type.replace('_', ' ')}**")
            if contains:
                filters.append(f"containing **{contains}**")

            filter_text = " and ".join(filters)
            description = f"No cases found{' for ' + filter_text if filter_text else ''}."

            embed = discord.Embed(description=description, color=COLOR_GREEN)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        title_parts: list[str] = []
        if user:
            title_parts.append(f"for {user.name}")
        if moderator:
            title_parts.append(f"by {moderator.name}")
        if case_type:
            title_parts.append(f"({case_type.replace('_', ' ').title()})")

        title = "Cases " + " ".join(title_parts) if title_parts else "All Cases"

        view = CaseQueryPaginator(interaction, cases, title, self.COLOR_MAP)
        await interaction.followup.send(embed=view.get_embed(), view=view, ephemeral=True)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /cases view Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @cases_group.command(name="view", description="View a single case with its related notes.")
    @app_commands.describe(case_id="The case ID to view.")
    @app_commands.rename(case_id="case-id")
    async def cases_view(
        self,
        interaction: discord.Interaction,
        case_id:     int,
    ) -> None:
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_view(actor):
            await send_major_error(
                interaction,
                title    = "Unauthorized!",
                texts    = "You lack the necessary permissions to view cases.",
                subtitle = "Invalid permissions.",
            )
            return

        guild = interaction.guild
        if not guild:
            return

        await interaction.response.defer(ephemeral=True)

        case = self.cases_manager.get_case_by_id(case_id)

        if not case or case["guild_id"] != guild.id:
            await send_minor_error(
                interaction,
                texts = f"Case **#{case_id}** was not found."
            )
            return

        if not self._can_see_case(actor, case):
            await send_major_error(
                interaction,
                title    =  "Unauthorized!",
                texts    = f"You lack the necessary permissions to view Case **#{case_id}**.",
                subtitle =  "Invalid permissions."
            )
            return

        embed = await self._build_case_embed(guild, case)

        notes         = self.cases_manager.get_related_notes(case_id, guild.id)
        visible_notes = [n for n in notes if self._can_see_case(actor, n)]

        if not visible_notes:
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        view = CaseViewPaginator(interaction, embed, visible_notes)
        await interaction.followup.send(embed=view.get_embed(), view=view, ephemeral=True)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /cases add-note Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @cases_group.command(name="add-note", description="Add a note to a user or case.")
    @app_commands.describe(
        content    = "The note content.",
        user       = "The user to attach the note to.",
        case_id    = "The case ID to attach the note to.",
        visibility = "Visibility restriction level.",
    )
    @app_commands.rename(case_id="case-id")
    async def cases_add_note(
        self,
        interaction: discord.Interaction,
        content:     str,
        user:        discord.User | None = None,
        case_id:     int          | None = None,
        visibility:  Literal[
            "moderators", "senior_moderators", "directors"
        ] = "moderators",
    ) -> None:
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_view(actor):
            await send_major_error(
                interaction,
                title    = "Unauthorized!",
                texts    = "You lack the necessary permissions to add notes.",
                subtitle = "Invalid permissions.",
            )
            return

        if user is None and case_id is None:
            await send_minor_error(
                interaction,
                texts = "You must provide either a user or a case ID.",
            )
            return

        guild = interaction.guild
        if not guild:
            return

        if visibility == "directors" and not is_director(actor):
            await send_minor_error(
                interaction,
                texts = "Only Directors can create director-level notes.",
            )
            return

        new_case_id = await self.cases_manager.add_note(
            guild            = guild,
            moderator        = actor,
            content          = content,
            target_user      = user,
            related_case_id  = case_id,
            visibility_level = visibility,
        )

        description = (
            f"Note **#{new_case_id}** added for {user.mention}."
            if user else
            f"Note **#{new_case_id}** added to Case **#{case_id}**."
        )

        embed = discord.Embed(
            description = description,
            color       = COLOR_GREEN,
            timestamp   = datetime.now(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /cases edit-entry Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @cases_group.command(name="edit-entry", description="Edit a note entry.")
    @app_commands.describe(
        case_id = "The case ID of the note to edit.",
        content = "The updated note content.",
    )
    @app_commands.rename(case_id="case-id")
    async def cases_edit_entry(
        self,
        interaction: discord.Interaction,
        case_id:     int,
        content:     str,
    ) -> None:
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        guild = interaction.guild
        if not guild:
            return

        case = self.cases_manager.get_case_by_id(case_id)

        if not case or case["guild_id"] != guild.id:
            await send_minor_error(interaction, texts=f"Case **#{case_id}** was not found.")
            return

        if case["type"] != CaseType.NOTE.value:
            await send_minor_error(
                interaction,
                texts = f"Case **#{case_id}** is not a note entry and cannot be edited here.",
            )
            return

        if not self._can_edit_entry(actor, case):
            await send_major_error(
                interaction,
                title    = "Unauthorized!",
                texts    = "You lack the necessary permissions to edit this note.",
                subtitle = "Invalid permissions.",
            )
            return

        self.cases_manager.edit_case(case_id, content)

        embed = discord.Embed(
            description = f"Note **#{case_id}** has been updated.",
            color       = COLOR_GREEN,
            timestamp   = datetime.now(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /cases delete-entry Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @cases_group.command(name="delete-entry", description="Delete a case entry.")
    @app_commands.describe(case_id="The case ID to delete.")
    @app_commands.rename(case_id="case-id")
    async def cases_delete_entry(
        self,
        interaction: discord.Interaction,
        case_id:     int,
    ) -> None:
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not is_director(actor):
            await send_major_error(
                interaction,
                title    = "Unauthorized!",
                texts    = "Only Directors can delete case entries.",
                subtitle = "Invalid permissions.",
            )
            return

        guild = interaction.guild
        if not guild:
            return

        case = self.cases_manager.get_case_by_id(case_id)

        if not case or case["guild_id"] != guild.id:
            await send_minor_error(interaction, texts=f"Case **#{case_id}** was not found.")
            return

        self.cases_manager.delete_case(case_id)

        embed = discord.Embed(
            description = f"Case **#{case_id}** has been deleted.",
            color       = COLOR_GREEN,
            timestamp   = datetime.now(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /cases classify Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @cases_group.command(name="classify", description="Classify a case entry's visibility.")
    @app_commands.describe(
        case_id    = "The case ID to classify.",
        visibility = "The visibility restriction to apply or request.",
    )
    @app_commands.rename(
        case_id    = "case-id",
        visibility = "level",
    )
    async def cases_classify(
        self,
        interaction: discord.Interaction,
        case_id:     int,
        visibility:  Literal["moderators", "senior_moderators", "directors"],
    ) -> None:
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_view(actor):
            await send_major_error(
                interaction,
                title    = "Unauthorized!",
                texts    = "You lack the necessary permissions to classify cases.",
                subtitle = "Invalid permissions.",
            )
            return

        guild = interaction.guild
        if not guild:
            return

        case = self.cases_manager.get_case_by_id(case_id)

        if not case or case["guild_id"] != guild.id:
            await send_minor_error(interaction, texts=f"Case **#{case_id}** was not found.")
            return

        if is_director(actor):
            label = visibility.replace("_", " ").title()
            self.cases_manager.set_visibility(case_id, visibility)
            embed = discord.Embed(
                description = f"Case **#{case_id}** visibility set to **{label}**.",
                color       = COLOR_GREEN,
                timestamp   = datetime.now(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if visibility == "directors" and not is_director(actor):
            await send_minor_error(
                interaction,
                texts = "Only Directors can apply or request director-level classification.",
            )
            return

        if case.get("pending_visibility"):
            await send_minor_error(
                interaction,
                texts = (
                    f"Case **#{case_id}** already has a pending classification request. "
                    f"It must be resolved before a new one can be submitted."
                ),
            )
            return

        forum_channel = self.bot.get_channel(DIRECTOR_TASKS_CHANNEL_ID)
        if not isinstance(forum_channel, discord.ForumChannel):
            await send_minor_error(
                interaction,
                texts = "The Director tasks channel could not be found or is not a forum.",
            )
            return

        label = visibility.replace("_", " ").title()

        self.cases_manager.request_visibility(case_id, visibility)

        view           = ClassificationView(case_id, self.cases_manager)
        thread_name    = f"DR: Classification Request by {actor.display_name}"
        thread_content = (
            f"{ACCEPTED_EMOJI_ID} **A new classification to {label} request has been made affecting case #{case_id}.**\n"
            f"<@&{DIRECTORS_ROLE_ID}>"
        )

        thread_with_message = await forum_channel.create_thread(
            name    = thread_name,
            content = thread_content,
            view    = view,
        )

        self.bot.add_view(view, message_id=thread_with_message.message.id)

        embed = discord.Embed(
            description = (
                f"Visibility request submitted for Case **#{case_id}**.\n"
                f"A Director must approve the **{label}** restriction."
            ),
            color     = COLOR_YELLOW,
            timestamp = datetime.now(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /cases config Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @cases_group.command(name="config", description="Configure the cases log channel.")
    @app_commands.describe(channel="The channel where case logs will be sent.")
    async def cases_config(
        self,
        interaction: discord.Interaction,
        channel:     discord.TextChannel,
    ) -> None:
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_configure(actor):
            await send_major_error(
                interaction,
                title    = "Unauthorized!",
                texts    = "You lack the necessary permissions to configure cases.",
                subtitle = "Invalid permissions.",
            )
            return

        self.cases_manager.config["log_channel_id"] = channel.id
        self.cases_manager.save_config()

        await interaction.response.send_message(
            f"Case logs will now be sent to {channel.mention}.",
            ephemeral = True,
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CasesCommands(cast("UtilityBot", bot)))