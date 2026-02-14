import discord
from discord.ext import commands
from discord import app_commands

import json
import os
from datetime import datetime
from typing import Optional, Dict, List, Literal
from enum import Enum

from constants import(
    COLOR_GREEN,
    COLOR_YELLOW,
    COLOR_ORANGE,
    COLOR_RED,
    COLOR_BLURPLE,
    COLOR_GREY,
    COLOR_BLACK,

    ACCEPTED_EMOJI_ID,
    DENIED_EMOJI_ID,

    DIRECTORS_ROLE_ID,
    SENIOR_MODERATORS_ROLE_ID,
    MODERATORS_ROLE_ID,
    ADMINISTRATORS_ROLE_ID,
)
from core.utils import send_minor_error, send_major_error

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Cases Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class CaseType(str, Enum):
    BAN = "ban"
    UNBAN = "unban"
    KICK = "kick"
    TIMEOUT = "timeout"
    UNTIMEOUT = "untimeout"
    QUARANTINE_ADD = "quarantine_add"
    QUARANTINE_REMOVE = "quarantine_remove"
    LOCKDOWN_ADD = "lockdown_add"
    LOCKDOWN_REMOVE = "lockdown_remove"
    PURGE = "purge"

class CasesManager:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data_file = "cases_data.json"
        self.config_file = "cases_config.json"
        self.data = self.load_data()
        self.config = self.load_config()

    def load_data(self) -> Dict:
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {"cases": [], "next_case_id": 1}
        return {"cases": [], "next_case_id": 1}

    def load_config(self) -> Dict:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {"log_channel_id": None}
        return {"log_channel_id": None}

    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=4)

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)

    def get_next_case_id(self) -> int:
        case_id = self.data["next_case_id"]
        self.data["next_case_id"] += 1
        self.save_data()
        return case_id

    async def log_case(
        self,
        guild: discord.Guild,
        case_type: CaseType,
        moderator: discord.Member,
        reason: str,
        target_user: Optional[discord.User | discord.Member] = None,
        duration: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> int:

        case_id = self.get_next_case_id()

        case_data = {
            "case_id": case_id,
            "type": case_type.value,
            "guild_id": guild.id,
            "moderator_id": moderator.id,
            "moderator_name": str(moderator),
            "target_user_id": target_user.id if target_user else None,
            "target_user_name": str(target_user) if target_user else None,
            "reason": reason,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        self.data["cases"].append(case_data)
        self.save_data()

        if self.config.get("log_channel_id"):
            await self._send_to_log_channel(guild, case_data)

        return case_id

    async def _send_to_log_channel(self, guild: discord.Guild, case_data: Dict):
        channel_id = self.config.get("log_channel_id")
        if not channel_id:
            return

        log_channel = guild.get_channel(channel_id)
        if not isinstance(log_channel, (discord.TextChannel, discord.Thread)):
            return

        case_type = case_data["type"]

        color_map = {
            CaseType.BAN.value: COLOR_BLACK,
            CaseType.UNBAN.value: COLOR_GREEN,
            CaseType.KICK.value: COLOR_ORANGE,
            CaseType.TIMEOUT.value: COLOR_YELLOW,
            CaseType.UNTIMEOUT.value: COLOR_GREEN,
            CaseType.QUARANTINE_ADD.value: COLOR_RED,
            CaseType.QUARANTINE_REMOVE.value: COLOR_GREEN,
            CaseType.LOCKDOWN_ADD.value: COLOR_GREY,
            CaseType.LOCKDOWN_REMOVE.value: COLOR_GREEN,
            CaseType.PURGE.value: COLOR_BLURPLE,
        }

        title_map = {
            CaseType.BAN.value: "Member Banned",
            CaseType.UNBAN.value: "User Un-banned",
            CaseType.KICK.value: "Member Kicked",
            CaseType.TIMEOUT.value: "Member Muted",
            CaseType.UNTIMEOUT.value: "Memebr Un-muted",
            CaseType.QUARANTINE_ADD.value: "Member Quarantined",
            CaseType.QUARANTINE_REMOVE.value: "Member Un-quarantined",
            CaseType.LOCKDOWN_ADD.value: "Lockdown Engaged",
            CaseType.LOCKDOWN_REMOVE.value: "Lockdown Lifted",
            CaseType.PURGE.value: "Messages Purged",
        }

        embed = discord.Embed(
            title=f"Case #{case_data['case_id']} — {title_map.get(case_type, 'Moderation Action')}",
            color=color_map.get(case_type, COLOR_BLURPLE),
            timestamp=datetime.fromisoformat(case_data["timestamp"])
        )

        moderator = guild.get_member(case_data["moderator_id"])
        if moderator:
            embed.add_field(name="Moderator", value=moderator.mention, inline=True)
        else:
            embed.add_field(name="Moderator", value=case_data["moderator_name"], inline=True)

        if case_data["target_user_id"]:
            try:
                user = await self.bot.fetch_user(case_data["target_user_id"])
                embed.add_field(name="User", value=f"{user.mention} ({user.id})", inline=True)
            except Exception:
                embed.add_field(name="User", value=f"{case_data['target_user_name']} ({case_data['target_user_id']})", inline=True)

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

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    def get_cases(
        self,
        guild_id: int,
        user_id: Optional[int] = None,
        moderator_id: Optional[int] = None,
        case_type: Optional[str] = None
    ) -> List[Dict]:

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

class CasesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cases_manager = CasesManager(bot)

        self.DIRECTORS_ROLE_ID = DIRECTORS_ROLE_ID
        self.SENIOR_MODERATORS_ROLE_ID = SENIOR_MODERATORS_ROLE_ID
        self.MODERATORS_ROLE_ID = MODERATORS_ROLE_ID
        self.ADMINISTRATORS_ROLE_ID = ADMINISTRATORS_ROLE_ID

    def has_role(self, member: discord.Member, role_id: int) -> bool:
        return any(role.id == role_id for role in member.roles)

    def is_director(self, member: discord.Member) -> bool:
        return self.has_role(member, self.DIRECTORS_ROLE_ID)

    def is_senior_moderator(self, member: discord.Member) -> bool:
        return self.has_role(member, self.SENIOR_MODERATORS_ROLE_ID)

    def is_administrator(self, member: discord.Member) -> bool:
        return self.has_role(member, self.ADMINISTRATORS_ROLE_ID)

    def is_moderator(self, member: discord.Member) -> bool:
        return self.has_role(member, self.MODERATORS_ROLE_ID)

    def can_view(self, member: discord.Member) -> bool:
        return (self.is_director(member) or 
                self.is_senior_moderator(member) or 
                self.is_administrator(member) or 
                self.is_moderator(member))

    def can_configure(self, member: discord.Member) -> bool:
        return self.is_director(member)

    cases_group = app_commands.Group(
        name="cases",
        description="Moderators only —— Cases management."
    )

    @cases_group.command(name="view", description="View moderation cases with filters.")
    @app_commands.describe(
        user="Filter by user.",
        moderator="Filter by moderator.",
        case_type="Filter by case type."
    )
    async def cases_view(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.User] = None,
        moderator: Optional[discord.User] = None,
        case_type: Optional[Literal["ban", "unban", "kick", "timeout", "untimeout", "quarantine", "unquarantine", "lockdown", "unlockdown", "purge"]] = None
    ):
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_view(actor):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to view cases.",
                subtitle="No permissions."
            )
            return

        guild = interaction.guild
        if not guild:
            return

        if case_type == "purge" and user is not None:
            await send_minor_error(
                interaction,
                "You cannot filter purge cases by user. Purge actions affect channels, not individual users."
            )
            return

        await interaction.response.defer(ephemeral=True)

        type_mapping = {
            "ban": CaseType.BAN.value,
            "unban": CaseType.UNBAN.value,
            "kick": CaseType.KICK.value,
            "timeout": CaseType.TIMEOUT.value,
            "untimeout": CaseType.UNTIMEOUT.value,
            "quarantine": CaseType.QUARANTINE_ADD.value,
            "unquarantine": CaseType.QUARANTINE_REMOVE.value,
            "lockdown": CaseType.LOCKDOWN_ADD.value,
            "unlockdown": CaseType.LOCKDOWN_REMOVE.value,
            "purge": CaseType.PURGE.value,
        }

        internal_case_type = type_mapping.get(case_type) if case_type else None

        cases = self.cases_manager.get_cases(
            guild_id=guild.id,
            user_id=user.id if user else None,
            moderator_id=moderator.id if moderator else None,
            case_type=internal_case_type
        )

        if not cases:
            filters = []
            if user:
                filters.append(f"user {user.mention}")
            if moderator:
                filters.append(f"moderator {moderator.mention}")
            if case_type:
                filters.append(f"type **{case_type}**")

            filter_text = " and ".join(filters) if filters else ""
            description = f"No cases found{' for ' + filter_text if filter_text else ''}."

            embed = discord.Embed(
                description=description,
                color=COLOR_GREEN
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        title_parts = []
        if user:
            title_parts.append(f"for {user.name}")
        if moderator:
            title_parts.append(f"by {moderator.name}")
        if case_type:
            title_parts.append(f"({case_type})")

        title = "Cases " + " ".join(title_parts) if title_parts else "All Cases"

        embed = discord.Embed(
            title=title,
            color=COLOR_BLURPLE,
            timestamp=datetime.now()
        )

        for case in cases[:25]:
            case_type_display = case["type"].replace("_", " ").title()
            timestamp = datetime.fromisoformat(case["timestamp"])

            value_parts = []
            value_parts.append(f"**Type:** {case_type_display}")

            if case.get("target_user_id"):
                try:
                    target = await self.bot.fetch_user(case["target_user_id"])
                    value_parts.append(f"**User:** {target.mention}")
                except Exception:
                    value_parts.append(f"**User:** {case['target_user_name']} ({case['target_user_id']})")

            try:
                mod = await self.bot.fetch_user(case["moderator_id"])
                value_parts.append(f"**Moderator:** {mod.mention}")
            except Exception:
                value_parts.append(f"**Moderator:** {case['moderator_name']}")

            if case.get("duration"):
                value_parts.append(f"**Duration:** {case['duration']}")

            value_parts.append(f"**Reason:** {case['reason']}")

            value_parts.append(f"**When:** {discord.utils.format_dt(timestamp, 'R')}")

            field_name = f"Case #{case['case_id']}"
            field_value = "\n".join(value_parts)

            embed.add_field(name=field_name, value=field_value, inline=False)

        if len(cases) > 25:
            embed.set_footer(text=f"Showing 25 of {len(cases)} cases")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @cases_group.command(name="config", description="Configure the cases log channel.")
    @app_commands.describe(
        channel="The channel where case logs will be sent."
    )
    async def cases_config(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_configure(actor):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to configure cases.",
                subtitle="No permissions."
            )
            return

        self.cases_manager.config["log_channel_id"] = channel.id
        self.cases_manager.save_config()

        embed = discord.Embed(
            title=f"{ACCEPTED_EMOJI_ID} Cases Log Channel Configured",
            description=f"Case logs will now be sent to {channel.mention}.",
            color=COLOR_GREEN,
            timestamp=datetime.now()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(CasesCog(bot))