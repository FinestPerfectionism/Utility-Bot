import discord
from discord.ext import commands

from typing import Any
import contextlib
import json
import os
from datetime import datetime
from enum import Enum

from constants import (
    COLOR_GREEN,
    COLOR_YELLOW,
    COLOR_ORANGE,
    COLOR_RED,
    COLOR_BLURPLE,
    COLOR_GREY,
    COLOR_BLACK,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Cases Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class CaseType(str, Enum):
    BAN               = "ban"
    UNBAN             = "unban"
    KICK              = "kick"
    TIMEOUT           = "timeout"
    UNTIMEOUT         = "untimeout"
    QUARANTINE_ADD    = "quarantine_add"
    QUARANTINE_REMOVE = "quarantine_remove"
    LOCKDOWN_ADD      = "lockdown_add"
    LOCKDOWN_REMOVE   = "lockdown_remove"
    PURGE             = "purge"
    NOTE              = "note"

class CasesManager:
    def __init__(self, bot: commands.Bot) -> None:
        self.bot         = bot
        self.data_file   = "cases_data.json"
        self.config_file = "cases_config.json"
        self.data        = self.load_data()
        self.config      = self.load_config()
        self._auto_migrate_notes()

    def load_data(self) -> dict[str, Any]:
        if os.path.exists(self.data_file):
            with contextlib.suppress(json.JSONDecodeError), open(self.data_file) as f:
                data: dict[str, Any] = json.load(f)
                self._normalize_cases(data)
                return data
        return {"cases": [], "next_case_id": 1}

    def _normalize_cases(self, data: dict[str, Any]) -> None:
        for case in data.get("cases", []):
            if "timestamp" in case and "created_at" not in case:
                case["created_at"] = case.pop("timestamp")
            case.setdefault("content", None)
            case.setdefault("related_case_id", None)
            case.setdefault("visibility_level", "moderators")
            case.setdefault("pending_visibility", None)
            case.setdefault("edited_at", None)
            case.setdefault("metadata", {})

    def _auto_migrate_notes(self) -> None:
        notes_file = "notes_data.json"
        if not os.path.exists(notes_file):
            return

        notes_data: dict[str, Any] = {}
        with contextlib.suppress(json.JSONDecodeError), open(notes_file) as f:
            notes_data = json.load(f)

        if not notes_data:
            with contextlib.suppress(OSError):
                os.remove(notes_file)
            return

        existing_ids: set[int] = {c["case_id"] for c in self.data["cases"]}

        def _next_id() -> int:
            nid = self.data["next_case_id"]
            while nid in existing_ids:
                nid += 1
            existing_ids.add(nid)
            self.data["next_case_id"] = nid + 1
            return nid

        now_iso = datetime.now().isoformat()

        for user_id_str, notes in notes_data.get("user_notes", {}).items():
            for note in notes:
                self.data["cases"].append({
                    "case_id"            : _next_id(),
                    "type"               : CaseType.NOTE.value,
                    "guild_id"           : note.get("guild_id", 0),
                    "moderator_id"       : note.get("author_id", 0),
                    "moderator_name"     : note.get("author_name", "Unknown"),
                    "target_user_id"     : int(user_id_str),
                    "target_user_name"   : None,
                    "reason"             : None,
                    "content"            : note.get("content"),
                    "duration"           : None,
                    "related_case_id"    : None,
                    "visibility_level"   : note.get("classification") or "moderators",
                    "pending_visibility" : note.get("classification_pending"),
                    "created_at"         : note.get("created_at", now_iso),
                    "edited_at"          : note.get("edited_at"),
                    "metadata"           : {},
                })

        for case_id_str, notes in notes_data.get("case_notes", {}).items():
            for note in notes:
                self.data["cases"].append({
                    "case_id"            : _next_id(),
                    "type"               : CaseType.NOTE.value,
                    "guild_id"           : note.get("guild_id", 0),
                    "moderator_id"       : note.get("author_id", 0),
                    "moderator_name"     : note.get("author_name", "Unknown"),
                    "target_user_id"     : None,
                    "target_user_name"   : None,
                    "reason"             : None,
                    "content"            : note.get("content"),
                    "duration"           : None,
                    "related_case_id"    : int(case_id_str),
                    "visibility_level"   : note.get("classification") or "moderators",
                    "pending_visibility" : note.get("classification_pending"),
                    "created_at"         : note.get("created_at", now_iso),
                    "edited_at"          : note.get("edited_at"),
                    "metadata"           : {},
                })

        self.save_data()
        with contextlib.suppress(OSError):
            os.remove(notes_file)

    def load_config(self) -> dict[str, Any]:
        if os.path.exists(self.config_file):
            with contextlib.suppress(json.JSONDecodeError), open(self.config_file) as f:
                return json.load(f)
        return {"log_channel_id": None}

    def save_data(self) -> None:
        with open(self.data_file, "w") as f:
            json.dump(self.data, f, indent=4)

    def save_config(self) -> None:
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=4)

    def get_next_case_id(self) -> int:
        case_id                    = self.data["next_case_id"]
        self.data["next_case_id"] += 1
        self.save_data()
        return case_id

    async def log_case(
        self,
        guild            : discord.Guild,
        case_type        : CaseType,
        moderator        : discord.Member,
        reason           : str                             | None = None,
        target_user      : discord.User   | discord.Member | None = None,
        duration         : str                             | None = None,
        content          : str                             | None = None,
        related_case_id  : int                             | None = None,
        visibility_level : str                                    = "moderators",
        metadata         : dict[str, Any] | None                  = None,
    ) -> int:
        case_id = self.get_next_case_id()

        case_data: dict[str, Any] = {
            "case_id"            : case_id,
            "type"               : case_type.value,
            "guild_id"           : guild.id,
            "moderator_id"       : moderator.id,
            "moderator_name"     : str(moderator),
            "target_user_id"     : target_user.id   if target_user else None,
            "target_user_name"   : str(target_user) if target_user else None,
            "reason"             : reason,
            "content"            : content,
            "duration"           : duration,
            "related_case_id"    : related_case_id,
            "visibility_level"   : visibility_level,
            "pending_visibility" : None,
            "created_at"         : datetime.now().isoformat(),
            "edited_at"          : None,
            "metadata"           : metadata or {},
        }

        self.data["cases"].append(case_data)
        self.save_data()

        if self.config.get("log_channel_id"):
            await self._send_to_log_channel(guild, case_data)

        return case_id

    async def add_note(
        self,
        guild            : discord.Guild,
        moderator        : discord.Member,
        content          : str,
        target_user      : discord.User | discord.Member | None = None,
        related_case_id  : int                           | None = None,
        visibility_level : str                                  = "moderators",
    ) -> int:
        return await self.log_case(
            guild            = guild,
            case_type        = CaseType.NOTE,
            moderator        = moderator,
            content          = content,
            target_user      = target_user,
            related_case_id  = related_case_id,
            visibility_level = visibility_level,
        )

    async def _send_to_log_channel(self, guild: discord.Guild, case_data: dict[str, Any]) -> None:
        channel_id = self.config.get("log_channel_id")
        if not channel_id:
            return

        log_channel = guild.get_channel(channel_id)
        if not isinstance(log_channel, (discord.TextChannel, discord.Thread)):
            return

        case_type = case_data["type"]

        color_map: dict[str, discord.Color] = {
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

        title_map: dict[str, str] = {
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

        embed = discord.Embed(
            title     = f"Case #{case_data['case_id']} — {title_map.get(case_type, 'Moderation Action')}",
            color     = color_map.get(case_type, COLOR_BLURPLE),
            timestamp = datetime.fromisoformat(case_data["created_at"])
        )

        mod_added = False
        moderator = guild.get_member(case_data["moderator_id"])
        if moderator:
            embed.add_field(name="Moderator", value=moderator.mention, inline=True)
            mod_added = True
        if not mod_added:
            embed.add_field(name="Moderator", value=case_data["moderator_name"], inline=True)

        if case_data["target_user_id"]:
            user_added = False
            with contextlib.suppress(discord.NotFound, discord.HTTPException):
                user = await self.bot.fetch_user(case_data["target_user_id"])
                embed.add_field(name="User", value=f"{user.mention} ({user.id})", inline=True)
                user_added = True
            if not user_added:
                embed.add_field(
                    name   = "User",
                    value  = f"{case_data['target_user_name']} ({case_data['target_user_id']})",
                    inline = True
                )

        if case_data.get("duration"):
            embed.add_field(name="Duration", value=case_data["duration"], inline=True)

        if case_data.get("reason"):
            embed.add_field(name="Reason", value=case_data["reason"], inline=False)

        if case_data.get("content"):
            embed.add_field(name="Content", value=case_data["content"], inline=False)

        if case_data.get("related_case_id"):
            embed.add_field(name="Related Case", value=f"#{case_data['related_case_id']}", inline=True)

        metadata: dict[str, Any] = case_data.get("metadata") or {}

        if "deleted_messages" in metadata:
            embed.add_field(name="Messages Deleted", value=str(metadata["deleted_messages"]), inline=True)

        if "channel_id" in metadata:
            action_channel = guild.get_channel(metadata["channel_id"])
            if action_channel:
                embed.add_field(name="Channel", value=action_channel.mention, inline=True)

        if "roles_saved" in metadata:
            embed.add_field(name="Roles Saved", value=str(metadata["roles_saved"]), inline=True)

        if "roles_restored" in metadata:
            embed.add_field(name="Roles Restored", value=str(metadata["roles_restored"]), inline=True)

        if "channels_locked" in metadata:
            embed.add_field(name="Channels Locked", value=str(metadata["channels_locked"]), inline=True)

        if "channels_restored" in metadata:
            embed.add_field(name="Channels Restored", value=str(metadata["channels_restored"]), inline=True)

        if "proof_url" in metadata:
            embed.add_field(name="Proof", value=metadata["proof_url"], inline=False)
            embed.set_image(url=metadata["proof_url"])

        with contextlib.suppress(discord.Forbidden):
            await log_channel.send(embed=embed)

    def get_case_by_id(self, case_id: int) -> dict[str, Any] | None:
        self.data = self.load_data()
        for case in self.data["cases"]:
            if case["case_id"] == case_id:
                return case
        return None

    def get_all_pending_classifications(self) -> list[dict[str, Any]]:
        self.data = self.load_data()
        return [
            c for c in self.data["cases"]
            if c.get("pending_visibility") is not None
        ]

    def edit_case(self, case_id: int, content: str) -> bool:
        case = self.get_case_by_id(case_id)
        if not case:
            return False
        case["content"]   = content
        case["edited_at"] = datetime.now().isoformat()
        self.save_data()
        return True

    def delete_case(self, case_id: int) -> bool:
        cases: list[dict[str, Any]] = self.data["cases"]
        for i, case in enumerate(cases):
            if case["case_id"] == case_id:
                cases.pop(i)
                self.save_data()
                return True
        return False

    def set_visibility(self, case_id: int, visibility: str) -> bool:
        case = self.get_case_by_id(case_id)
        if not case:
            return False
        case["visibility_level"]   = visibility
        case["pending_visibility"] = None
        self.save_data()
        return True

    def request_visibility(self, case_id: int, visibility: str) -> bool:
        case = self.get_case_by_id(case_id)
        if not case:
            return False
        case["pending_visibility"] = visibility
        self.save_data()
        return True

    def approve_visibility(self, case_id: int) -> bool:
        case = self.get_case_by_id(case_id)
        if not case or not case.get("pending_visibility"):
            return False
        case["visibility_level"]   = case["pending_visibility"]
        case["pending_visibility"] = None
        self.save_data()
        return True

    def deny_visibility(self, case_id: int) -> bool:
        case = self.get_case_by_id(case_id)
        if not case or not case.get("pending_visibility"):
            return False
        case["pending_visibility"] = None
        self.save_data()
        return True

    def get_related_notes(self, case_id: int, guild_id: int) -> list[dict[str, Any]]:
        self.data = self.load_data()
        return [
            c for c in self.data["cases"]
            if c.get("related_case_id") == case_id
            and c["guild_id"]           == guild_id
            and c["type"]               == CaseType.NOTE.value
        ]

    def get_cases(
        self,
        guild_id      : int,
        user_id       : int      | None = None,
        moderator_id  : int      | None = None,
        case_type     : str      | None = None,
        contains      : str      | None = None,
        after         : datetime | None = None,
        before        : datetime | None = None,
        include_notes : bool            = True,
    ) -> list[dict[str, Any]]:
        self.data = self.load_data()

        cases = [c for c in self.data["cases"] if c["guild_id"] == guild_id]

        if not include_notes:
            cases = [c for c in cases if c["type"] != CaseType.NOTE.value]

        if user_id is not None:
            cases = [c for c in cases if c.get("target_user_id") == user_id]

        if moderator_id is not None:
            cases = [c for c in cases if c["moderator_id"] == moderator_id]

        if case_type is not None:
            cases = [c for c in cases if c["type"] == case_type]

        if contains is not None:
            query = contains.lower()
            cases = [
                c for c in cases
                if query in (c.get("reason")  or "").lower()
                or query in (c.get("content") or "").lower()
            ]

        if after is not None:
            cases = [c for c in cases if datetime.fromisoformat(c["created_at"]) > after]

        if before is not None:
            cases = [c for c in cases if datetime.fromisoformat(c["created_at"]) < before]

        cases.sort(key=lambda x: x["case_id"], reverse=True)
        return cases