from __future__ import annotations

import discord
from discord.ext import commands

import contextlib
import json
import os
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
)

if TYPE_CHECKING:
    from ._base import ModerationBase

from core.utils import (
    send_major_error,
    send_minor_error,
)
from constants import (
    COLOR_GREEN,
    COLOR_BLURPLE,
    COLOR_YELLOW,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Notes Manager
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class NotesManager:
    def __init__(self, bot: commands.Bot) -> None:
        self.bot       = bot
        self.data_file = "notes_data.json"
        self.data      = self.load_data()

    def load_data(self) -> dict[str, Any]:
        defaults = self._default_data()
        if os.path.exists(self.data_file):
            with contextlib.suppress(json.JSONDecodeError), open(self.data_file) as f:
                loaded: dict[str, Any] = json.load(f)
                return {**defaults, **loaded}
        return defaults

    def _default_data(self) -> dict[str, Any]:
        return {
            "user_notes"   : {},
            "case_notes"   : {},
            "next_note_id" : 1,
        }

    def save_data(self) -> None:
        with open(self.data_file, "w") as f:
            json.dump(self.data, f, indent=4)

    def get_next_note_id(self) -> int:
        note_id                    = self.data["next_note_id"]
        self.data["next_note_id"] += 1
        self.save_data()
        return note_id

    def _make_note(
        self,
        guild_id : int,
        author   : discord.Member,
        content  : str,
    ) -> dict[str, Any]:
        return {
            "note_id"                : self.get_next_note_id(),
            "guild_id"               : guild_id,
            "content"                : content,
            "author_id"              : author.id,
            "author_name"            : str(author),
            "created_at"             : datetime.now().isoformat(),
            "edited_at"              : None,
            "classification"         : None,
            "classification_pending" : None,
        }

    def add_user_note(
        self,
        guild_id : int,
        user_id  : int,
        author   : discord.Member,
        content  : str,
    ) -> dict[str, Any]:
        note = self._make_note(guild_id, author, content)
        key  = str(user_id)
        if key not in self.data["user_notes"]:
            self.data["user_notes"][key] = []
        self.data["user_notes"][key].append(note)
        self.save_data()
        return note

    def add_case_note(
        self,
        guild_id : int,
        case_id  : int,
        author   : discord.Member,
        content  : str,
    ) -> dict[str, Any]:
        note = self._make_note(guild_id, author, content)
        key  = str(case_id)
        if key not in self.data["case_notes"]:
            self.data["case_notes"][key] = []
        self.data["case_notes"][key].append(note)
        self.save_data()
        return note

    def get_note_by_id(self, note_id: int) -> tuple[dict[str, Any], str, str] | None:
        for key, notes in self.data["user_notes"].items():
            for note in notes:
                if note["note_id"] == note_id:
                    return note, "user_notes", key
        for key, notes in self.data["case_notes"].items():
            for note in notes:
                if note["note_id"] == note_id:
                    return note, "case_notes", key
        return None

    def edit_note(self, note_id: int, content: str) -> bool:
        result = self.get_note_by_id(note_id)
        if not result:
            return False
        note, _, _        = result
        note["content"]   = content
        note["edited_at"] = datetime.now().isoformat()
        self.save_data()
        return True

    def delete_note(self, note_id: int) -> bool:
        for notes_list in self.data["user_notes"].values():
            for i, note in enumerate(notes_list):
                if note["note_id"] == note_id:
                    notes_list.pop(i)
                    self.save_data()
                    return True
        for notes_list in self.data["case_notes"].values():
            for i, note in enumerate(notes_list):
                if note["note_id"] == note_id:
                    notes_list.pop(i)
                    self.save_data()
                    return True
        return False

    def set_classification(self, note_id: int, classification: str | None) -> bool:
        result = self.get_note_by_id(note_id)
        if not result:
            return False
        note, _, _                     = result
        note["classification"]         = classification
        note["classification_pending"] = None
        self.save_data()
        return True

    def request_classification(self, note_id: int, classification: str) -> bool:
        result = self.get_note_by_id(note_id)
        if not result:
            return False
        note, _, _                     = result
        note["classification_pending"] = classification
        self.save_data()
        return True

    def approve_classification(self, note_id: int) -> bool:
        result = self.get_note_by_id(note_id)
        if not result:
            return False
        note, _, _ = result
        if not note.get("classification_pending"):
            return False
        note["classification"]         = note["classification_pending"]
        note["classification_pending"] = None
        self.save_data()
        return True

    def deny_classification(self, note_id: int) -> bool:
        result = self.get_note_by_id(note_id)
        if not result:
            return False
        note, _, _ = result
        if not note.get("classification_pending"):
            return False
        note["classification_pending"] = None
        self.save_data()
        return True

    def get_user_notes(self, guild_id: int, user_id: int) -> list[dict[str, Any]]:
        self.data = self.load_data()
        return [
            n for n in self.data["user_notes"].get(str(user_id), [])
            if n["guild_id"] == guild_id
        ]

    def get_case_notes(self, guild_id: int, case_id: int) -> list[dict[str, Any]]:
        self.data = self.load_data()
        return [
            n for n in self.data["case_notes"].get(str(case_id), [])
            if n["guild_id"] == guild_id
        ]


def _build_note_field(
    base  : "ModerationBase",
    actor : discord.Member,
    note  : dict[str, Any],
) -> tuple[str, str]:
    visibility = base.note_visibility_for(actor, note)
    created    = datetime.fromisoformat(note["created_at"])

    if visibility == "full":
        parts: list[str] = [
            f"**Author:** {note['author_name']}",
            f"**Created:** {discord.utils.format_dt(created, 'R')}",
        ]
        if note.get("edited_at"):
            edited = datetime.fromisoformat(note["edited_at"])
            parts.append(f"**Edited:** {discord.utils.format_dt(edited, 'R')}")
        if cls := note.get("classification"):
            parts.append(f"**Classification:** {str(cls).replace('_', ' ').title()}")
        if pending := note.get("classification_pending"):
            if base.can_classify_note(actor):
                parts.append(f"**Pending Classification:** {str(pending).replace('_', ' ').title()}")
        parts.append(f"\n{note['content']}")
        return f"Note #{note['note_id']}", "\n".join(parts)

    if visibility == "group_only":
        cls_label = str(note.get("classification") or "Unknown").replace("_", " ").title()
        return (
            f"Note #{note['note_id']} [Classified]",
            f"**Restricted to:** {cls_label}\n**Created:** {discord.utils.format_dt(created, 'R')}",
        )

    return (
        f"Note #{note['note_id']} [Classified]",
        f"This note is restricted.\n**Created:** {discord.utils.format_dt(created, 'R')}",
    )


# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation note add-user Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_note_add_user(
    base:        "ModerationBase",
    interaction: discord.Interaction,
    user:        discord.User,
    content:     str,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_create_user_note(actor):
        await send_major_error(
            interaction,
            title    = "Unauthorized!",
            texts    = "You lack the necessary permissions to add notes to users.",
            subtitle = "Invalid permissions."
        )
        return

    guild = interaction.guild
    if not guild:
        return

    note = base.notes_manager.add_user_note(guild.id, user.id, actor, content)

    embed = discord.Embed(
        description = f"Note **#{note['note_id']}** added for {user.mention}.",
        color       = COLOR_GREEN,
        timestamp   = datetime.now()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation note add-case Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_note_add_case(
    base:        "ModerationBase",
    interaction: discord.Interaction,
    case_id:     int,
    content:     str,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_create_case_note(actor):
        await send_major_error(
            interaction,
            title    = "Unauthorized!",
            texts    = "You lack the necessary permissions to add notes to cases.",
            subtitle = "Invalid permissions."
        )
        return

    guild = interaction.guild
    if not guild:
        return

    note = base.notes_manager.add_case_note(guild.id, case_id, actor, content)

    embed = discord.Embed(
        description = f"Note **#{note['note_id']}** added to Case **#{case_id}**.",
        color       = COLOR_GREEN,
        timestamp   = datetime.now()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation note view-user Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_note_view_user(
    base:        "ModerationBase",
    interaction: discord.Interaction,
    user:        discord.User,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_view_user_notes(actor):
        await send_major_error(
            interaction,
            title    = "Unauthorized!",
            texts    = "You lack the necessary permissions to view user notes.",
            subtitle = "Invalid permissions."
        )
        return

    guild = interaction.guild
    if not guild:
        return

    await interaction.response.defer(ephemeral=True)

    notes = base.notes_manager.get_user_notes(guild.id, user.id)

    if not notes:
        embed = discord.Embed(
            description = f"No notes found for {user.mention}.",
            color       = COLOR_GREEN,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    embed = discord.Embed(
        title     = f"Notes — {user.name}",
        color     = COLOR_BLURPLE,
        timestamp = datetime.now()
    )

    for note in notes[:25]:
        name, value = _build_note_field(base, actor, note)
        embed.add_field(name=name, value=value, inline=False)

    if len(notes) > 25:
        embed.set_footer(text=f"Showing 25 of {len(notes)} notes")

    await interaction.followup.send(embed=embed, ephemeral=True)


# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation note view-case Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_note_view_case(
    base:        "ModerationBase",
    interaction: discord.Interaction,
    case_id:     int,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_view_case_notes(actor):
        await send_major_error(
            interaction,
            title    = "Unauthorized!",
            texts    = "You lack the necessary permissions to view case notes.",
            subtitle = "Invalid permissions."
        )
        return

    guild = interaction.guild
    if not guild:
        return

    await interaction.response.defer(ephemeral=True)

    notes = base.notes_manager.get_case_notes(guild.id, case_id)

    if not notes:
        embed = discord.Embed(
            description = f"No notes found for Case **#{case_id}**.",
            color       = COLOR_GREEN,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    embed = discord.Embed(
        title     = f"Notes — Case #{case_id}",
        color     = COLOR_BLURPLE,
        timestamp = datetime.now()
    )

    for note in notes[:25]:
        name, value = _build_note_field(base, actor, note)
        embed.add_field(name=name, value=value, inline=False)

    if len(notes) > 25:
        embed.set_footer(text=f"Showing 25 of {len(notes)} notes")

    await interaction.followup.send(embed=embed, ephemeral=True)


# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation note edit Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_note_edit(
    base:        "ModerationBase",
    interaction: discord.Interaction,
    note_id:     int,
    content:     str,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    guild = interaction.guild
    if not guild:
        return

    base.notes_manager.data = base.notes_manager.load_data()
    result = base.notes_manager.get_note_by_id(note_id)

    if not result or result[0]["guild_id"] != guild.id:
        await send_minor_error(interaction, texts=f"Note **#{note_id}** was not found.")
        return

    note, category, _ = result
    is_user_note      = category == "user_notes"

    can_edit = (
        (is_user_note     and base.can_edit_user_note(actor)) or
        (not is_user_note and base.can_edit_case_note(actor))
    )

    if not can_edit:
        await send_major_error(
            interaction,
            title    = "Unauthorized!",
            texts    = "You lack the necessary permissions to edit this note.",
            subtitle = "Invalid permissions."
        )
        return

    if note["author_id"] != actor.id:
        await send_major_error(
            interaction,
            title    = "Unauthorized!",
            texts    = "You may only edit notes that you authored.",
            subtitle = "Not your note."
        )
        return

    base.notes_manager.edit_note(note_id, content)

    embed = discord.Embed(
        description = f"Note **#{note_id}** has been updated.",
        color       = COLOR_GREEN,
        timestamp   = datetime.now()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation note delete Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_note_delete(
    base:        "ModerationBase",
    interaction: discord.Interaction,
    note_id:     int,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_delete_note(actor):
        await send_major_error(
            interaction,
            title    = "Unauthorized!",
            texts    = "Only Directors can delete notes.",
            subtitle = "Invalid permissions."
        )
        return

    guild = interaction.guild
    if not guild:
        return

    base.notes_manager.data = base.notes_manager.load_data()
    result = base.notes_manager.get_note_by_id(note_id)

    if not result or result[0]["guild_id"] != guild.id:
        await send_minor_error(interaction, texts=f"Note **#{note_id}** was not found.")
        return

    base.notes_manager.delete_note(note_id)

    embed = discord.Embed(
        description = f"Note **#{note_id}** has been deleted.",
        color       = COLOR_GREEN,
        timestamp   = datetime.now()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation note classify Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_note_classify(
    base:           "ModerationBase",
    interaction:    discord.Interaction,
    note_id:        int,
    classification: Literal["moderators", "senior_moderators", "directors"],
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_classify_note(actor):
        await send_major_error(
            interaction,
            title    = "Unauthorized!",
            texts    = "You lack the necessary permissions to classify notes.",
            subtitle = "Invalid permissions."
        )
        return

    guild = interaction.guild
    if not guild:
        return

    if not base.can_approve_classification(actor) and classification == "directors":
        await send_minor_error(
            interaction,
            texts = "Only Directors can apply or request director-level classification."
        )
        return

    base.notes_manager.data = base.notes_manager.load_data()
    result = base.notes_manager.get_note_by_id(note_id)

    if not result or result[0]["guild_id"] != guild.id:
        await send_minor_error(interaction, texts=f"Note **#{note_id}** was not found.")
        return

    label = classification.replace("_", " ").title()

    if base.can_approve_classification(actor):
        base.notes_manager.set_classification(note_id, classification)
        embed = discord.Embed(
            description = f"Note **#{note_id}** classified as **{label}**.",
            color       = COLOR_GREEN,
            timestamp   = datetime.now()
        )
    else:
        base.notes_manager.request_classification(note_id, classification)
        embed = discord.Embed(
            description = (
                f"Classification request submitted for Note **#{note_id}**.\n"
                f"A Director must approve the **{label}** restriction."
            ),
            color     = COLOR_YELLOW,
            timestamp = datetime.now()
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)


# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation note approve Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_note_approve(
    base:        "ModerationBase",
    interaction: discord.Interaction,
    note_id:     int,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_approve_classification(actor):
        await send_major_error(
            interaction,
            title    = "Unauthorized!",
            texts    = "Only Directors can approve classification requests.",
            subtitle = "Invalid permissions."
        )
        return

    guild = interaction.guild
    if not guild:
        return

    base.notes_manager.data = base.notes_manager.load_data()
    result = base.notes_manager.get_note_by_id(note_id)

    if not result or result[0]["guild_id"] != guild.id:
        await send_minor_error(interaction, texts=f"Note **#{note_id}** was not found.")
        return

    note    = result[0]
    pending = note.get("classification_pending")

    if not pending:
        await send_minor_error(
            interaction,
            texts = f"Note **#{note_id}** has no pending classification request."
        )
        return

    base.notes_manager.approve_classification(note_id)

    label = str(pending).replace("_", " ").title()
    embed = discord.Embed(
        description = f"Note **#{note_id}** classification approved as **{label}**.",
        color       = COLOR_GREEN,
        timestamp   = datetime.now()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation note deny Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_note_deny(
    base:        "ModerationBase",
    interaction: discord.Interaction,
    note_id:     int,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_approve_classification(actor):
        await send_major_error(
            interaction,
            title    = "Unauthorized!",
            texts    = "Only Directors can deny classification requests.",
            subtitle = "Invalid permissions."
        )
        return

    guild = interaction.guild
    if not guild:
        return

    base.notes_manager.data = base.notes_manager.load_data()
    result = base.notes_manager.get_note_by_id(note_id)

    if not result or result[0]["guild_id"] != guild.id:
        await send_minor_error(interaction, texts=f"Note **#{note_id}** was not found.")
        return

    if not result[0].get("classification_pending"):
        await send_minor_error(
            interaction,
            texts = f"Note **#{note_id}** has no pending classification request."
        )
        return

    base.notes_manager.deny_classification(note_id)

    embed = discord.Embed(
        description = f"Classification request for Note **#{note_id}** has been denied.",
        color       = COLOR_GREEN,
        timestamp   = datetime.now()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)