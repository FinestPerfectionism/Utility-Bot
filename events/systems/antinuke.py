import discord
from discord.ext import commands

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, cast
from collections import defaultdict

from constants import(
    BOT_OWNER_ID,

    COLOR_ORANGE,
    COLOR_RED,

    DENIED_EMOJI_ID,

    QUARANTINE_ROLE_ID,
    DIRECTORS_ROLE_ID,
)

from bot import UtilityBot

from commands.moderation.cases import CaseType

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Anti-Nuke System
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ActionType:
    CHANNEL_DELETE = "channel_delete"
    CHANNEL_CREATE = "channel_create"
    CHANNEL_UPDATE = "channel_update"
    ROLE_DELETE = "role_delete"
    ROLE_CREATE = "role_create"
    ROLE_UPDATE = "role_update"

class AntiNukeSystem(commands.Cog):
    def __init__(self, bot: "UtilityBot"):
        self.bot = bot
        self.config_file = "antinuke_config.json"
        self.config = self.load_config()
        self.DIRECTORS_ROLE_ID = DIRECTORS_ROLE_ID
        self.QUARANTINE_ROLE_ID = QUARANTINE_ROLE_ID

        self.action_tracker: Dict[int, Dict[str, Dict[str, List[datetime]]]] = defaultdict(
            lambda: defaultdict(lambda: {"hourly": [], "daily": []})
        )

    @property
    def cases_manager(self):
        return cast(UtilityBot, self.bot).cases_manager

    def load_config(self) -> Dict:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self.get_default_config()
        return self.get_default_config()

    def get_default_config(self) -> Dict:
        return {
            "enabled": True,
            "limits": {
                ActionType.CHANNEL_DELETE: {"hourly": 3, "daily": 10},
                ActionType.CHANNEL_CREATE: {"hourly": 5, "daily": 15},
                ActionType.CHANNEL_UPDATE: {"hourly": 10, "daily": 30},
                ActionType.ROLE_DELETE: {"hourly": 3, "daily": 10},
                ActionType.ROLE_CREATE: {"hourly": 5, "daily": 15},
                ActionType.ROLE_UPDATE: {"hourly": 10, "daily": 30},
            },
            "log_channel_id": None
        }

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)

    def is_director(self, member: discord.Member) -> bool:
        return any(role.id == self.DIRECTORS_ROLE_ID for role in member.roles)

    def clean_old_actions(self, user_id: int, action_type: str):
        now = datetime.now()

        bucket = self.action_tracker[user_id][action_type]

        bucket["hourly"] = [
            timestamp
            for timestamp in bucket["hourly"]
            if timestamp > now - timedelta(hours=1)
        ]

        bucket["daily"] = [
            timestamp
            for timestamp in bucket["daily"]
            if timestamp > now - timedelta(days=1)
        ]

    async def track_action(
        self, 
        guild: discord.Guild, 
        user: discord.User | discord.Member,
        action_type: str,
        details: str = ""
    ) -> bool:
        if not self.config.get("enabled", True):
            return True

        if isinstance(user, discord.Member) and self.is_director(user):
            return True

        if user.id == BOT_OWNER_ID:
            return True

        limits = self.config["limits"].get(action_type)
        if not limits:
            return True

        hourly_limit = limits.get("hourly", 999)
        daily_limit = limits.get("daily", 999)

        if action_type not in self.action_tracker[user.id]:
            self.action_tracker[user.id][action_type] = {"hourly": [], "daily": []}

        self.clean_old_actions(user.id, action_type)
        now = datetime.now()
        self.action_tracker[user.id][action_type]["hourly"].append(now)
        self.action_tracker[user.id][action_type]["daily"].append(now)

        hourly_count = len(self.action_tracker[user.id][action_type]["hourly"])
        daily_count = len(self.action_tracker[user.id][action_type]["daily"])

        if hourly_count > hourly_limit:
            await self.quarantine_offender(guild, user, action_type, hourly_count, daily_count, "hourly", details)
            return False

        if daily_count > daily_limit:
            await self.quarantine_offender(guild, user, action_type, hourly_count, daily_count, "daily", details)
            return False

        if hourly_count >= hourly_limit - 1 or daily_count >= daily_limit - 1:
            await self.send_warning(guild, user, action_type, hourly_count, daily_count, hourly_limit, daily_limit)

        return True

    async def quarantine_offender(
        self,
        guild: discord.Guild,
        user: discord.User | discord.Member,
        action_type: str,
        hourly_count: int,
        daily_count: int,
        limit_type: str,
        details: str
    ):
        member = guild.get_member(user.id)
        if not member:
            return

        quarantine_role = guild.get_role(self.QUARANTINE_ROLE_ID)
        if not quarantine_role:
            return

        saved_roles = [role.id for role in member.roles if role.id != guild.default_role.id]

        try:
            roles_to_remove = [role for role in member.roles if role.id != guild.default_role.id]
            await member.remove_roles(*roles_to_remove, reason=f"UB Anti-Nuke: Exceeded {action_type} {limit_type} limits")
            await member.add_roles(quarantine_role, reason=f"UB Anti-Nuke: {action_type} {limit_type} limit exceeded")

            bot_member = guild.get_member(self.bot.user.id) if self.bot.user else None
            if bot_member:
                reason = (
                    f"Anti-nuke system triggered: Exceeded {action_type.replace('_', ' ')} {limit_type} limits "
                    f"({hourly_count} hourly, {daily_count} daily). {details}"
                )

                await self.cases_manager.log_case(
                    guild=guild,
                    case_type=CaseType.QUARANTINE_ADD,
                    moderator=bot_member,
                    reason=reason,
                    target_user=member,
                    metadata={
                        "roles_saved": len(saved_roles),
                        "auto_quarantine": True,
                        "antinuke_trigger": True,
                        "action_type": action_type,
                        "hourly_count": hourly_count,
                        "daily_count": daily_count,
                        "limit_type": limit_type
                    }
                )

            await self.send_quarantine_alert(guild, member, action_type, hourly_count, daily_count, limit_type, details)

        except discord.Forbidden:
            await self.send_quarantine_failure(guild, member, action_type)

    async def send_warning(
        self,
        guild: discord.Guild,
        user: discord.User | discord.Member,
        action_type: str,
        hourly_count: int,
        daily_count: int,
        hourly_limit: int,
        daily_limit: int
    ):
        log_channel_id = self.config.get("log_channel_id")
        if not log_channel_id:
            return

        log_channel = guild.get_channel(log_channel_id)
        if not isinstance(log_channel, (discord.TextChannel, discord.Thread)):
            return

        embed = discord.Embed(
            title="Anti-Nuke Warning",
            description=f"{user.mention} is approaching rate limits",
            color=COLOR_ORANGE,
            timestamp=datetime.now()
        )
        embed.add_field(name="User", value=f"{user.mention} ({user.id})", inline=True)
        embed.add_field(name="Action Type", value=action_type.replace("_", " ").title(), inline=True)
        embed.add_field(name="Hourly", value=f"{hourly_count}/{hourly_limit}", inline=True)
        embed.add_field(name="Daily", value=f"{daily_count}/{daily_limit}", inline=True)

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    async def send_quarantine_alert(
        self,
        guild: discord.Guild,
        member: discord.Member,
        action_type: str,
        hourly_count: int,
        daily_count: int,
        limit_type: str,
        details: str
    ):
        log_channel_id = self.config.get("log_channel_id")
        if not log_channel_id:
            return

        log_channel = guild.get_channel(log_channel_id)
        if not isinstance(log_channel, (discord.TextChannel, discord.Thread)):
            return

        embed = discord.Embed(
            title="Anti-Nuke: User Quarantined",
            description=f"{member.mention} has been automatically quarantined for exceeding action limits.",
            color=COLOR_RED,
            timestamp=datetime.now()
        )
        embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=True)
        embed.add_field(name="Action Type", value=action_type.replace("_", " ").title(), inline=True)
        embed.add_field(name="Limit Exceeded", value=limit_type.title(), inline=True)
        embed.add_field(name="Hourly Count", value=str(hourly_count), inline=True)
        embed.add_field(name="Daily Count", value=str(daily_count), inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)

        if details:
            embed.add_field(name="Details", value=details, inline=False)

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    async def send_quarantine_failure(
        self,
        guild: discord.Guild,
        member: discord.Member,
        action_type: str
    ):
        log_channel_id = self.config.get("log_channel_id")
        if not log_channel_id:
            return

        log_channel = guild.get_channel(log_channel_id)
        if not isinstance(log_channel, (discord.TextChannel, discord.Thread)):
            return

        try:
            await log_channel.send(
                f"{DENIED_EMOJI_ID} **Failed to quarantine {member.mention}!**\n"
                "I lack the necessary permissions to quarantine members. Please contact the owner."
            )
        except discord.Forbidden:
            pass

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Event Listeners
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        guild = channel.guild

        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            if (
                entry.target
                and entry.target.id == channel.id
                and entry.user
            ):
                await self.track_action(
                    guild,
                    entry.user,
                    ActionType.CHANNEL_DELETE,
                    f"Deleted channel: {channel.name}"
                )
                break

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        guild = channel.guild

        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
            if (
                entry.target
                and entry.target.id == channel.id
                and entry.user
            ):
                await self.track_action(
                    guild,
                    entry.user,
                    ActionType.CHANNEL_CREATE,
                    f"Created channel: {channel.name}"
                )
                break

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        if before.name == after.name:
            return

        guild = after.guild

        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_update):
            if (
                entry.target
                and entry.target.id == after.id
                and entry.user
            ):
                await self.track_action(
                    guild,
                    entry.user,
                    ActionType.CHANNEL_UPDATE,
                    f"Renamed channel: {before.name} → {after.name}"
                )
                break

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        guild = role.guild

        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            if (
                entry.target
                and entry.target.id == role.id
                and entry.user
            ):
                await self.track_action(
                    guild,
                    entry.user,
                    ActionType.ROLE_DELETE,
                    f"Deleted role: {role.name}"
                )
                break

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        guild = role.guild

        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
            if (
                entry.target
                and entry.target.id == role.id
                and entry.user
            ):
                await self.track_action(
                    guild,
                    entry.user,
                    ActionType.ROLE_CREATE,
                    f"Created role: {role.name}"
                )
                break

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if before.name == after.name:
            return

        guild = after.guild

        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_update):
            if (
                entry.target
                and entry.target.id == after.id
                and entry.user
            ):
                await self.track_action(
                    guild,
                    entry.user,
                    ActionType.ROLE_UPDATE,
                    f"Renamed role: {before.name} → {after.name}"
                )
                break

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiNukeSystem(cast(UtilityBot, bot)))