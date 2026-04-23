from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, cast

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from bot import UtilityBot

from constants import (
    ADMINISTRATORS_ROLE_ID,
    DIRECTORS_ROLE_ID,
    MODERATORS_ROLE_ID,
    SENIOR_MODERATORS_ROLE_ID,
)
from core.cases import CasesManager
from core.help import ArgumentInfo, RoleConfig, help_description

from ._base import CasesMixin, ClassificationView
from .add_note import run_add_note
from .classify import run_classify
from .configure import run_configure
from .delete_entry import run_delete_entry
from .edit_entry import run_edit_entry
from .query import run_query
from .view import run_view

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Cases Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class CasesCommands(CasesMixin, commands.GroupCog, name = "cases", description = "Moderators only —— Cases management."):
    def __init__(self, bot: UtilityBot) -> None:
        self.bot = bot

        if not hasattr(bot, "cases_manager"):
            bot.cases_manager = CasesManager(bot)

        self.cases_manager : CasesManager = bot.cases_manager

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

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /cases query Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "query", description = "Query the moderation case history.")
    @app_commands.describe(
        user          = "Filter by user.",
        moderator     = "Filter by moderator.",
        case_type     = "Filter by case type.",
        contains      = "Search reason or content.",
        after         = "Only cases after this date (ISO format: YYYY-MM-DD).",
        before        = "Only cases before this date (ISO format: YYYY-MM-DD).",
        include_notes = "Include note entries. Default: true.",
        mass_only     = "Only show cases produced by mass moderation actions.",
    )
    @app_commands.rename(
        case_type     = "type",
        include_notes = "include-notes",
        mass_only     = "mass-only",
    )
    @help_description(
        desc      = "Staff* only —— Queries moderation cases visible to you.",
        prefix    = False,
        slash     = True,
        run_roles = [
            RoleConfig(role_id = MODERATORS_ROLE_ID),
            RoleConfig(role_id = ADMINISTRATORS_ROLE_ID),
        ],
        arguments = {
            "user"          : ArgumentInfo(required = False, description = "Optional target user filter."),
            "moderator"     : ArgumentInfo(required = False, description = "Optional moderator filter."),
            "type"          : ArgumentInfo(required = False, description = "Optional case type filter."),
            "contains"      : ArgumentInfo(required = False, description = "Optional text search over reason or content."),
            "after"         : ArgumentInfo(required = False, description = "Optional lower date bound in YYYY-MM-DD format."),
            "before"        : ArgumentInfo(required = False, description = "Optional upper date bound in YYYY-MM-DD format."),
            "include-notes" : ArgumentInfo(required = False, description = "Whether note entries should be included."),
            "mass-only"     : ArgumentInfo(required = False, description = "Only include entries produced by mass moderation."),
        },
    )
    async def cases_query(
        self          : CasesCommands,
        interaction   : discord.Interaction,
        user          : discord.User | None = None,
        moderator     : discord.User | None = None,
        case_type     : Literal[
            "ban", "unban", "kick",
            "timeout", "untimeout",
            "quarantine_add", "quarantine_remove",
            "lockdown_add", "lockdown_remove",
            "purge", "note",
        ]                            | None = None,
        contains      : str          | None = None,
        after         : str          | None = None,
        before        : str          | None = None,
        *,
        include_notes : bool                = True,
        mass_only     : bool                = False,
    ) -> None:
        await run_query(
            self,
            interaction,
            user,
            moderator,
            case_type,
            contains,
            after,
            before,
            include_notes = include_notes,
            mass_only     = mass_only,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /cases view Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "view", description = "View a single case with its related notes.")
    @app_commands.describe(case_id = "The case ID to view.")
    @app_commands.rename(case_id = "case-id")
    @help_description(
        desc      = "Staff* only —— Views a single case and any visible related notes.",
        prefix    = False,
        slash     = True,
        run_roles = [
            RoleConfig(role_id = MODERATORS_ROLE_ID),
            RoleConfig(role_id = ADMINISTRATORS_ROLE_ID),
        ],
        arguments = {"case-id" : ArgumentInfo(description = "Case ID to view.")},
    )
    async def cases_view(
        self        : CasesCommands,
        interaction : discord.Interaction,
        case_id     : int,
    ) -> None:
        await run_view(self, interaction, case_id)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /cases add-note Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "add-note", description = "Add a note to a user or case.")
    @app_commands.describe(
        content    = "The note content.",
        user       = "A single user to attach the note to.",
        users      = "Comma-separated user IDs or mentions for mass user notes.",
        case_id    = "The case ID to attach the note to.",
        visibility = "Visibility restriction level.",
    )
    @app_commands.rename(case_id = "case-id")
    @help_description(
        desc      = "Staff* only —— Adds a note to a user or an existing case.",
        prefix    = False,
        slash     = True,
        run_roles = [
            RoleConfig(role_id = MODERATORS_ROLE_ID),
            RoleConfig(role_id = ADMINISTRATORS_ROLE_ID),
        ],
        arguments = {
            "content"    : ArgumentInfo(description = "Note content."),
            "user"       : ArgumentInfo(required = False, description = "Optional user to attach the note to."),
            "users"      : ArgumentInfo(required = False, description = "Optional comma-separated users for mass user notes."),
            "case-id"    : ArgumentInfo(required = False, description = "Optional case ID to attach the note to."),
            "visibility" : ArgumentInfo(
                required = False,
                description = "Visibility restriction level.",
                choices=["moderators", "senior_moderators", "directors"],
            ),
        },
    )
    async def cases_add_note(
        self        : CasesCommands,
        interaction : discord.Interaction,
        content     : str,
        user        : discord.User | None = None,
        users       : str          | None = None,
        case_id     : int          | None = None,
        visibility  : Literal[
            "moderators", "senior_moderators", "directors",
        ] = "moderators",
    ) -> None:
        await run_add_note(self, interaction, content, user, users, case_id, visibility)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /cases edit-entry Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "edit-entry", description = "Edit a note entry.")
    @app_commands.describe(
        case_id = "The case ID of the note to edit.",
        content = "The updated note content.",
    )
    @app_commands.rename(case_id = "case-id")
    @help_description(
        desc      = "Staff* only —— Edits a note entry.",
        prefix    = False,
        slash     = True,
        run_roles = [
            RoleConfig(role_id = MODERATORS_ROLE_ID),
            RoleConfig(role_id = ADMINISTRATORS_ROLE_ID),
        ],
        arguments = {
            "case-id" : ArgumentInfo(description = "Note case ID to edit."),
            "content" : ArgumentInfo(description = "Replacement note content."),
        },
    )
    async def cases_edit_entry(
        self        : CasesCommands,
        interaction : discord.Interaction,
        case_id     : int,
        content     : str,
    ) -> None:
        await run_edit_entry(self, interaction, case_id, content)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /cases delete-entry Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "delete-entry", description = "Delete a case entry.")
    @app_commands.describe(case_id = "The case ID to delete.")
    @app_commands.rename(case_id = "case-id")
    @help_description(
        desc      = "Directors only —— Delete a case entry. Use strictly for deleting test cases.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id = DIRECTORS_ROLE_ID)],
        arguments = {"case-id" : ArgumentInfo(description = "Case ID to delete.")},
    )
    async def cases_delete_entry(
        self        : CasesCommands,
        interaction : discord.Interaction,
        case_id     : int,
    ) -> None:
        await run_delete_entry(self, interaction, case_id)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /cases classify Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "classify", description = "Classify a case entry's visibility.")
    @app_commands.describe(
        case_id    = "The case ID to classify.",
        visibility = "The visibility restriction to apply or request.",
    )
    @app_commands.rename(
        case_id    = "case-id",
        visibility = "level",
    )
    @help_description(
        desc      = "Staff* only —— Changes or requests a change to a case's visibility classification.",
        prefix    = False,
        slash     = True,
        run_roles = [
            RoleConfig(role_id = MODERATORS_ROLE_ID),
            RoleConfig(role_id = ADMINISTRATORS_ROLE_ID),
        ],
        arguments = {
            "case-id" : ArgumentInfo(description = "Case ID to classify."),
            "level"   : ArgumentInfo(
                description = "Requested visibility level.",
                choices=["moderators", "senior_moderators", "directors"],
            ),
        },
    )
    async def cases_classify(
        self        : CasesCommands,
        interaction : discord.Interaction,
        case_id     : int,
        visibility  : Literal["moderators", "senior_moderators", "directors"],
    ) -> None:
        await run_classify(self, interaction, case_id, visibility)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /cases configure Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "configure", description = "Configure the cases log channel.")
    @app_commands.describe(channel="The channel where case logs will be sent.")
    @help_description(
        desc      = "Directors only —— Configures the channel used for case logs",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id = DIRECTORS_ROLE_ID)],
        arguments = {"channel" : ArgumentInfo(description = "Text channel that should receive case logs.")},
    )
    async def cases_configure(
        self        : CasesCommands,
        interaction : discord.Interaction,
        channel     : discord.TextChannel,
    ) -> None:
        await run_configure(self, interaction, channel)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CasesCommands(cast("UtilityBot", bot)))
