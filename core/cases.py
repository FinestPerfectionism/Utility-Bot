import contextlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import TypedDict, cast

import discord
from discord.ext import commands

from constants import (
    COLOR_BLACK,
    COLOR_BLURPLE,
    COLOR_GREEN,
    COLOR_GREY,
    COLOR_ORANGE,
    COLOR_RED,
    COLOR_YELLOW,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Cases Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class CaseData(TypedDict):
    case_id            : int
    type               : str
    guild_id           : int
    moderator_id       : int
    moderator_name     : str
    target_user_id     : int | None
    target_user_name   : str | None
    reason             : str | None
    content            : str | None
    duration           : str | None
    related_case_id    : int | None
    visibility_level   : str
    pending_visibility : str | None
    created_at         : str
    edited_at          : str | None
    metadata           : dict[str, object]

class CasesDataFile(TypedDict):
    cases        : list[CaseData]
    next_case_id : int

class CasesConfig(TypedDict):
    log_channel_id : int | None

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
    bot         : commands.Bot
    data_file   : str
    config_file : str
    data        : CasesDataFile
    config      : CasesConfig

    def __init__(self, bot : commands.Bot) -> None:
        self.bot         = bot
        self.data_file   = "cases_data.json"
        self.config_file = "cases_config.json"
        self.data         = self.load_data()
        self.config       = self.load_config()
        self._auto_migrate_notes()

    def load_data(self) -> CasesDataFile:
        if Path(self.data_file).exists():
            with contextlib.suppress(json.JSONDecodeError), Path(self.data_file).open() as f:
                data = cast(CasesDataFile, json.load(f))
                self._normalize_cases(data)
                return data
        return {"cases": [], "next_case_id": 1}

    def _normalize_cases(self, data : CasesDataFile) -> None:
        for case in data.get("cases", []):
            if "timestamp" in case and "created_at" not in case:
                legacy_case = cast(dict[str, object], case)
                case["created_at"] = cast(str, legacy_case.pop("timestamp"))

            _ = case.setdefault("content", None)
            _ = case.setdefault("related_case_id", None)
            _ = case.setdefault("visibility_level", "moderators")
            _ = case.setdefault("pending_visibility", None)
            _ = case.setdefault("edited_at", None)
            _ = case.setdefault("metadata", {})

    def _auto_migrate_notes(self) -> None:
        notes_file = Path("notes_data.json")
        if not notes_file.exists():
            return

        notes_data : dict[str, dict[str, list[dict[str, object]]]] = {}
        with contextlib.suppress(json.JSONDecodeError), Path(notes_file).open() as f:
            notes_data = cast(dict[str, dict[str, list[dict[str, object]]]], json.load(f))

        if not notes_data:
            with contextlib.suppress(OSError):
                Path(notes_file).unlink()
            return

        existing_ids: set[int] = {c["case_id"] for c in self.data["cases"]}

        def _next_id() -> int:
            nid = self.data["next_case_id"]
            while nid in existing_ids:
                nid += 1
            existing_ids.add(nid)
            self.data["next_case_id"] = nid + 1
            return nid

        now_iso = datetime.now(UTC).isoformat()

        user_notes : dict [str, list [dict [str, object]]] = notes_data.get("user_notes", {})
        for user_id_str, notes in user_notes.items():
            for note in notes:
                new_note_entry : CaseData = {
                    "case_id"            : _next_id(),
                    "type"               : CaseType.NOTE.value,
                    "guild_id"           : int(cast(int, note.get("guild_id", 0))),
                    "moderator_id"       : int(cast(int, note.get("author_id", 0))),
                    "moderator_name"     : str(note.get("author_name", "Unknown")),
                    "target_user_id"     : int(user_id_str),
                    "target_user_name"   : None,
                    "reason"             : None,
                    "content"            : cast(str | None, note.get("content")),
                    "duration"           : None,
                    "related_case_id"    : None,
                    "visibility_level"   : str(note.get("classification") or "moderators"),
                    "pending_visibility" : cast(str | None, note.get("classification_pending")),
                    "created_at"         : cast(str, note.get("created_at") or now_iso),
                    "edited_at"          : cast(str | None, note.get("edited_at")),
                    "metadata"           : {},
                }
                self.data["cases"].append(new_note_entry)

        case_notes : dict[str, list[dict[str, object]]] = notes_data.get("case_notes", {})
        for case_id_str, notes in case_notes.items():
            for note in notes:
                new_note : CaseData = {
                    "case_id"            : _next_id(),
                    "type"               : CaseType.NOTE.value,
                    "guild_id"           : int(cast(int, note.get("guild_id", 0))),
                    "moderator_id"       : int(cast(int, note.get("author_id", 0))),
                    "moderator_name"     : str(note.get("author_name", "Unknown")),
                    "target_user_id"     : None,
                    "target_user_name"   : None,
                    "reason"             : None,
                    "content"            : cast(str | None, note.get("content")),
                    "duration"           : None,
                    "related_case_id"    : int(case_id_str),
                    "visibility_level"   : str(note.get("classification") or "moderators"),
                    "pending_visibility" : cast(str | None, note.get("classification_pending")),
                    "created_at"         : cast(str, note.get("created_at") or now_iso),
                    "edited_at"          : cast(str | None, note.get("edited_at")),
                    "metadata"           : {},
                }
                self.data["cases"].append(new_note)

        self.save_data()
        with contextlib.suppress(OSError):
            Path(notes_file).unlink()

    def load_config(self) -> CasesConfig:
        if Path(self.config_file).exists():
            with contextlib.suppress(json.JSONDecodeError), Path(self.config_file).open() as f:
                return cast(CasesConfig, json.load(f))
        return {"log_channel_id" : None}

    def save_data(self) -> None:
        with Path(self.data_file).open("w") as f:
            json.dump(self.data, f, indent=4)

    def save_config(self) -> None:
        with Path(self.config_file).open("w") as f:
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
        reason           : str                           | None = None,
        target_user      : discord.User | discord.Member | None = None,
        duration         : str                           | None = None,
        content          : str                           | None = None,
        related_case_id  : int                           | None = None,
        visibility_level : str                                  = "moderators",
        metadata         : dict[str, object]             | None = None,
    ) -> int:
        case_id = self.get_next_case_id()

        case_data : CaseData = {
            "case_id"            : case_id,
            "type"               : case_type.value,
            "guild_id"           : guild.id,
            "moderator_id"       : moderator.id,
            "moderator_name"     : str(moderator),
            "target_user_id"     : target_user.id if target_user else None,
            "target_user_name"   : str(target_user) if target_user else None,
            "reason"             : reason,
            "content"            : content,
            "duration"           : duration,
            "related_case_id"    : related_case_id,
            "visibility_level"   : visibility_level,
            "pending_visibility" : None,
            "created_at"         : datetime.now(UTC).isoformat(),
            "edited_at"          : None,
            "metadata"           : metadata or {},
        }

        self.data["cases"].append(case_data)
        self.save_data()

        if self.config.get("log_channel_id"):
            await self._send_to_log_channel(guild, case_data)

        return case_id
        
    async def log_cases(
        self,
        guild            : discord.Guild,
        case_type        : CaseType,
        moderator        : discord.Member,
        entries          : Sequence[dict[str, object]],
        *,
        reason           : str               | None = None,
        duration         : str               | None = None,
        visibility_level : str                      = "moderators",
        metadata         : dict[str, object] | None = None,
    ) -> list[int]:
        total = len(entries)
        pending_cases: list[CaseData] = []
        case_ids: list[int] = []

        for index, entry in enumerate(entries, start = 1):
            entry_metadata: dict[str, object] = dict(metadata or {})
            entry_metadata["mass_total"]  = total
            entry_metadata["mass_index"]  = index
            entry_metadata["mass_action"] = True

            case_id = self.data["next_case_id"]
            self.data["next_case_id"] += 1

            target_user = cast(discord.User | discord.Member | None, entry.get("target_user"))

            case_data: CaseData = {
                "case_id"            : case_id,
                "type"               : case_type.value,
                "guild_id"           : guild.id,
                "moderator_id"       : moderator.id,
                "moderator_name"     : str(moderator),
                "target_user_id"     : target_user.id if target_user else None,
                "target_user_name"   : str(target_user) if target_user else None,
                "reason"             : cast(str | None, entry.get("reason")) or reason,
                "content"            : cast(str | None, entry.get("content")),
                "duration"           : cast(str | None, entry.get("duration")) or duration,
                "related_case_id"    : cast(int | None, entry.get("related_case_id")),
                "visibility_level"   : cast(str, entry.get("visibility_level") or visibility_level),
                "pending_visibility" : None,
                "created_at"         : datetime.now(UTC).isoformat(),
                "edited_at"          : None,
                "metadata"           : entry_metadata,
            }

            pending_cases.append(case_data)
            case_ids.append(case_id)

        self.data["cases"].extend(pending_cases)
        self.save_data()

        if self.config.get("log_channel_id"):
            for case_data in pending_cases:
                await self._send_to_log_channel(guild, case_data)

        return case_ids

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

    async def add_notes_for_users(
        self,
        guild            : discord.Guild,
        moderator        : discord.Member,
        content          : str,
        users            : Sequence[discord.User | discord.Member],
        visibility_level : str = "moderators",
    ) -> list[int]:
        entries: list[dict[str, object]] = [
            {"target_user": user, "content": content} 
            for user in users
        ]
        return await self.log_cases(
            guild            = guild,
            case_type        = CaseType.NOTE,
            moderator        = moderator,
            entries          = entries,
            visibility_level = visibility_level,
        )

    async def _send_to_log_channel(self, guild : discord.Guild, case_data : CaseData) -> None:# noqa: PLR0915
        channel_id = self.config.get("log_channel_id")
        if not channel_id:
            return

        log_channel = guild.get_channel(channel_id)
        if not isinstance(log_channel, discord.TextChannel | discord.Thread):
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
            timestamp = datetime.fromisoformat(case_data["created_at"]),
        )

        mod_added = False
        moderator = guild.get_member(case_data["moderator_id"])
        if moderator:
            _ = embed.add_field(name = "Moderator", value = moderator.mention, inline = True)
            mod_added = True
        if not mod_added:
            _ = embed.add_field(name = "Moderator", value = case_data["moderator_name"], inline = True)

        if case_data["target_user_id"]:
            user_added = False
            with contextlib.suppress(discord.NotFound, discord.HTTPException):
                user = await self.bot.fetch_user(case_data["target_user_id"])
                _ = embed.add_field(name = "User", value = f"{user.mention} ({user.id})", inline = True)
                user_added = True
            if not user_added:
                _ = embed.add_field(
                    name   = "User",
                    value  = f"{case_data['target_user_name']} ({case_data['target_user_id']})",
                    inline = True,
                )

        if case_data.get("duration"):
            _ = embed.add_field(name = "Duration", value = case_data["duration"], inline = True)

        if case_data.get("reason"):
            _ = embed.add_field(name = "Reason", value = case_data["reason"], inline = False)

        if case_data.get("content"):
            _ = embed.add_field(name = "Content", value = case_data["content"], inline = False)

        if case_data.get("related_case_id"):
            _ = embed.add_field(name = "Related Case", value = f"#{case_data['related_case_id']}", inline = True)

        metadata: dict[str, object] = case_data.get("metadata") or {}

        if "deleted_messages" in metadata:
            _ = embed.add_field(name = "Messages Deleted", value = str(metadata["deleted_messages"]), inline = True)

        if "channel_id" in metadata:
            action_channel = guild.get_channel(cast(int, metadata["channel_id"]))
            if action_channel:
                _ = embed.add_field(name = "Channel", value = action_channel.mention, inline = True)

        if "roles_saved" in metadata:
            _ = embed.add_field(name = "Roles Saved", value = str(metadata["roles_saved"]), inline = True)

        if "roles_restored" in metadata:
            _ = embed.add_field(name = "Roles Restored", value = str(metadata["roles_restored"]), inline = True)

        if "channels_locked" in metadata:
            _ = embed.add_field(name = "Channels Locked", value = str(metadata["channels_locked"]), inline = True)

        if "channels_restored" in metadata:
            _ = embed.add_field(name = "Channels Restored", value = str(metadata["channels_restored"]), inline = True)

        if "proof_url" in metadata:
            proof_url = cast(str, metadata["proof_url"])
            _ = embed.add_field(name = "Proof", value = proof_url, inline = False)
            _ = embed.set_image(url = proof_url)

        with contextlib.suppress(discord.Forbidden):
            _ = await log_channel.send(embed = embed)

    def get_case_by_id(self, case_id : int) -> CaseData | None:
        self.data = self.load_data()
        for case in self.data["cases"]:
            if case["case_id"] == case_id:
                return case
        return None

    def get_all_pending_classifications(self) -> list[CaseData]:
        self.data = self.load_data()
        return [
            c for c in self.data["cases"]
            if c.get("pending_visibility") is not None
        ]

    def edit_case(self, case_id : int, content: str) -> bool:
        case = self.get_case_by_id(case_id)
        if not case:
            return False
        case["content"]   = content
        case["edited_at"] = datetime.now(UTC).isoformat()
        self.save_data()
        return True

    def delete_case(self, case_id : int) -> bool:
        cases : list[CaseData] = self.data["cases"]
        for i, case in enumerate(cases):
            if case["case_id"] == case_id:
                _ = cases.pop(i)
                self.save_data()
                return True
        return False

    def set_visibility(self, case_id : int, visibility : str) -> bool:
        case = self.get_case_by_id(case_id)
        if not case:
            return False
        case["visibility_level"]   = visibility
        case["pending_visibility"] = None
        self.save_data()
        return True

    def request_visibility(self, case_id : int, visibility : str) -> bool:
        case = self.get_case_by_id(case_id)
        if not case:
            return False
        case["pending_visibility"] = visibility
        self.save_data()
        return True

    def approve_visibility(self, case_id : int) -> bool:
        case = self.get_case_by_id(case_id)
        pending = case.get("pending_visibility") if case else None
        if not case or pending is None:
            return False

        case["visibility_level"]   = pending
        case["pending_visibility"] = None
        self.save_data()
        return True

    def deny_visibility(self, case_id : int) -> bool:
        case = self.get_case_by_id(case_id)
        if not case or not case.get("pending_visibility"):
            return False
        case["pending_visibility"] = None
        self.save_data()
        return True

    def get_related_notes(self, case_id : int, guild_id : int) -> list[CaseData]:
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
        *,
        include_notes : bool            = True,
    ) -> list[CaseData]:
        self.data = self.load_data()

        cases : list[CaseData] = [c for c in self.data["cases"] if c["guild_id"] == guild_id]

        if not include_notes:
            cases = [c for c in cases if c["type"] != CaseType.NOTE.value]

        if user_id is not None:
            cases = [c for c in cases if c.get("target_user_id") == user_id]

        if moderator_id is not None:
            cases = [c for c in cases if c["moderator_id"] == moderator_id]

        if case_type is not None:
            cases = [c for c in cases if c["type"] == case_type]

        if contains is not None:
            query: str = contains.lower()
            cases = [
                c for c in cases
                if query in (c.get("reason") or "").lower()
                or query in (c.get("content") or "").lower()
            ]

        if after is not None:
            cases = [c for c in cases if datetime.fromisoformat(c["created_at"]) > after]

        if before is not None:
            cases = [c for c in cases if datetime.fromisoformat(c["created_at"]) < before]

        cases.sort(key=lambda x: int(x["case_id"]), reverse=True)
        return cases
