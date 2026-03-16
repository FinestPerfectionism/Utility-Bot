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

    def load_data(self) -> dict[str, Any]:
        if os.path.exists(self.data_file):
            with contextlib.suppress(json.JSONDecodeError), open(self.data_file) as f:
                return json.load(f)
        return {"cases": [], "next_case_id": 1}

    def load_config(self) -> dict[str, Any]:
        if os.path.exists(self.config_file):
            with contextlib.suppress(json.JSONDecodeError), open(self.config_file) as f:
                return json.load(f)
        return {"log_channel_id": None}

    def save_data(self) -> None:
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=4)

    def save_config(self) -> None:
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)

    def get_next_case_id(self) -> int:
        case_id                    = self.data["next_case_id"]
        self.data["next_case_id"] += 1
        self.save_data()
        return case_id

    async def log_case(
        self,
        guild       : discord.Guild,
        case_type   : CaseType,
        moderator   : discord.Member,
        reason      : str,
        target_user : discord.User   | discord.Member | None = None,
        duration    : str            |                  None = None,
        metadata    : dict[str, Any] |                  None = None
    ) -> int:
        case_id   = self.get_next_case_id()

        case_data = {
            "case_id"          : case_id,
            "type"             : case_type.value,
            "guild_id"         : guild.id,
            "moderator_id"     : moderator.id,
            "moderator_name"   : str(moderator),
            "target_user_id"   : target_user.id   if target_user else None,
            "target_user_name" : str(target_user) if target_user else None,
            "reason"           : reason,
            "duration"         : duration,
            "timestamp"        : datetime.now().isoformat(),
            "metadata"         : metadata or {}
        }

        self.data["cases"].append(case_data)
        self.save_data()

        if self.config.get("log_channel_id"):
            await self._send_to_log_channel(guild, case_data)

        return case_id

    async def _send_to_log_channel(self, guild: discord.Guild, case_data: dict[str, Any]) -> None:
        channel_id = self.config.get("log_channel_id")
        if not channel_id:
            return

        log_channel = guild.get_channel(channel_id)
        if not isinstance(log_channel, (discord.TextChannel, discord.Thread)):
            return

        case_type = case_data["type"]

        color_map = {
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

        title_map = {
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
            timestamp = datetime.fromisoformat(case_data["timestamp"])
        )

        moderator = guild.get_member(case_data["moderator_id"])
        if moderator:
            embed.add_field(name="Moderator", value=moderator.mention, inline=True)
        else:
            embed.add_field(name="Moderator", value=case_data["moderator_name"], inline=True)

        if case_data["target_user_id"]:
            with contextlib.suppress(discord.NotFound, discord.HTTPException):
                user = await self.bot.fetch_user(case_data["target_user_id"])
                embed.add_field(name="User", value=f"{user.mention} ({user.id})", inline=True)

            if not embed.fields or embed.fields[-1].name != "User":
                embed.add_field(
                    name   = "User",
                    value  = f"{case_data['target_user_name']} ({case_data['target_user_id']})",
                    inline = True
                )

        if case_data.get("duration"):
            embed.add_field(name="Duration", value=case_data["duration"], inline=True)

        embed.add_field(name="Reason", value=case_data["reason"], inline=False)

        if case_data.get("metadata"):
            metadata = case_data["metadata"]

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

    def get_cases(
        self,
        guild_id     : int,
        user_id      : int | None = None,
        moderator_id : int | None = None,
        case_type    : str | None = None
    ) -> list[dict[str, Any]]:
        self.data = self.load_data()

        cases = [c for c in self.data["cases"] if c["guild_id"] == guild_id]

        if user_id is not None:
            cases = [c for c in cases if c.get("target_user_id") == user_id]

        if moderator_id is not None:
            cases = [c for c in cases if c["moderator_id"] == moderator_id]

        if case_type is not None:
            cases = [c for c in cases if c["type"] == case_type]

        cases.sort(key=lambda x: x["case_id"], reverse=True)

        return cases