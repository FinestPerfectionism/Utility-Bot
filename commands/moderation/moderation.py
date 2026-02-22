import discord
from discord.ext import commands
from discord import app_commands

import json
import os
from datetime import (
    datetime,
    timedelta
)
from typing import (
    Optional,
    Dict, 
    cast
)

from commands.moderation.cases import CaseType

from bot import UtilityBot
from core.utils import (
    send_major_error,
    send_minor_error
)

from constants import(
    COLOR_GREEN,
    COLOR_ORANGE,
    COLOR_RED,
    COLOR_BLURPLE,

    QUARANTINE_ROLE_ID,
    DIRECTORS_ROLE_ID,
    MODERATORS_ROLE_ID,
    ADMINISTRATORS_ROLE_ID,
    STAFF_ROLE_ID,
    JUNIOR_ADMINISTRATORS_ROLE_ID,
    SENIOR_ADMINISTRATORS_ROLE_ID,
    MODERATORS_AND_ADMINISTRATORS_ROLE_ID,
    JUNIOR_MODERATORS_ROLE_ID,
    SENIOR_MODERATORS_ROLE_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Flag Converters
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class BanFlags(commands.FlagConverter, prefix="/", delimiter=" "):
    r: str = commands.flag(name="r", aliases=["reason"], default=None)
    d: int = commands.flag(name="d", aliases=["delete"], default=7)

class KickFlags(commands.FlagConverter, prefix="/", delimiter=" "):
    r: str = commands.flag(name="r", aliases=["reason"], default=None)

class TimeoutFlags(commands.FlagConverter, prefix="/", delimiter=" "):
    r: str = commands.flag(name="r", aliases=["reason"], default=None)
    d: str = commands.flag(name="d", aliases=["duration"], default=None)

class PurgeFlags(commands.FlagConverter, prefix="/", delimiter=" "):
    u: Optional[discord.Member] = commands.flag(name="u", aliases=["user"], default=None)
    r: str = commands.flag(name="r", aliases=["reason"])

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Moderation Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ModerationCommands(
    commands.GroupCog,
    name="moderation",
    description="Moderators only —— Moderation commands."
):
    def __init__(self, bot: "UtilityBot"):
        self.bot = bot
        self.data_file = "moderation_data.json"
        self.data = self.load_data()

        self.QUARANTINE_ROLE_ID = QUARANTINE_ROLE_ID
        self.DIRECTORS_ROLE_ID = DIRECTORS_ROLE_ID
        self.SENIOR_MODERATORS_ROLE_ID = SENIOR_MODERATORS_ROLE_ID
        self.MODERATORS_ROLE_ID = MODERATORS_ROLE_ID
        self.ADMINISTRATORS_ROLE_ID = ADMINISTRATORS_ROLE_ID

        self.PROTECTED_ROLE_IDS = [
            STAFF_ROLE_ID,
            ADMINISTRATORS_ROLE_ID,
            JUNIOR_ADMINISTRATORS_ROLE_ID,
            SENIOR_ADMINISTRATORS_ROLE_ID,
            MODERATORS_AND_ADMINISTRATORS_ROLE_ID,
            MODERATORS_ROLE_ID,
            JUNIOR_MODERATORS_ROLE_ID,
            SENIOR_MODERATORS_ROLE_ID,
            DIRECTORS_ROLE_ID,
        ]

        self.BAN_HOURLY_LIMIT = 2
        self.BAN_DAILY_LIMIT = 4
        self.KICK_HOURLY_LIMIT = 3
        self.KICK_DAILY_LIMIT = 6
        self.SEVERE_HOURLY_LIMIT = 4
        self.SEVERE_DAILY_LIMIT = 8

    @property
    def cases_manager(self):
        return cast(UtilityBot, self.bot).cases_manager

    def parse_duration(self, duration_str: str) -> Optional[int]:
        duration_str = duration_str.lower().strip()

        try:
            if duration_str.endswith('s'):
                return int(duration_str[:-1])
            elif duration_str.endswith('m'):
                return int(duration_str[:-1]) * 60
            elif duration_str.endswith('h'):
                return int(duration_str[:-1]) * 3600
            elif duration_str.endswith('d'):
                return int(duration_str[:-1]) * 86400
            elif duration_str.endswith('w'):
                return int(duration_str[:-1]) * 604800
            else:
                return int(duration_str) * 60
        except ValueError:
            return None

    def load_data(self) -> Dict:
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self.get_default_data()
        return self.get_default_data()

    def get_default_data(self) -> Dict:
        return {
            "bans": {},
            "timeouts": {},
            "kicks": {},
            "rate_limits": {},
            "quarantined": {}
        }

    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=4)

    def _ensure_rate_limit_entry(self, user_id: str):
        if user_id not in self.data["rate_limits"]:
            self.data["rate_limits"][user_id] = {}
        rl = self.data["rate_limits"][user_id]
        for key in ("ban_hourly", "ban_daily", "kick_hourly", "kick_daily", "severe_hourly", "severe_daily"):
            if key not in rl:
                rl[key] = []

    def clean_old_rate_limits(self, user_id: str):
        now = datetime.now()
        self._ensure_rate_limit_entry(user_id)
        rl = self.data["rate_limits"][user_id]

        for key in ("ban_hourly", "kick_hourly", "severe_hourly"):
            rl[key] = [ts for ts in rl[key] if datetime.fromisoformat(ts) > now - timedelta(hours=1)]

        for key in ("ban_daily", "kick_daily", "severe_daily"):
            rl[key] = [ts for ts in rl[key] if datetime.fromisoformat(ts) > now - timedelta(days=1)]

    def check_rate_limit(self, user_id: str, action: str) -> tuple[bool, str]:
        self.clean_old_rate_limits(user_id)
        rl = self.data["rate_limits"][user_id]

        if len(rl["severe_hourly"]) >= self.SEVERE_HOURLY_LIMIT:
            return False, f"Severe action hourly limit exceeded ({self.SEVERE_HOURLY_LIMIT} bans/kicks/quarantines per hour)"
        if len(rl["severe_daily"]) >= self.SEVERE_DAILY_LIMIT:
            return False, f"Severe action daily limit exceeded ({self.SEVERE_DAILY_LIMIT} bans/kicks/quarantines per day)"

        if action == "ban":
            if len(rl["ban_hourly"]) >= self.BAN_HOURLY_LIMIT:
                return False, f"Ban hourly limit exceeded ({self.BAN_HOURLY_LIMIT} bans per hour)"
            if len(rl["ban_daily"]) >= self.BAN_DAILY_LIMIT:
                return False, f"Ban daily limit exceeded ({self.BAN_DAILY_LIMIT} bans per day)"

        elif action == "kick":
            if len(rl["kick_hourly"]) >= self.KICK_HOURLY_LIMIT:
                return False, f"Kick hourly limit exceeded ({self.KICK_HOURLY_LIMIT} kicks per hour)"
            if len(rl["kick_daily"]) >= self.KICK_DAILY_LIMIT:
                return False, f"Kick daily limit exceeded ({self.KICK_DAILY_LIMIT} kicks per day)"

        return True, ""

    def add_rate_limit_entry(self, user_id: str, action: str):
        now = datetime.now().isoformat()
        self._ensure_rate_limit_entry(user_id)
        rl = self.data["rate_limits"][user_id]

        if action in ("ban", "kick"):
            rl["severe_hourly"].append(now)
            rl["severe_daily"].append(now)

        if action == "ban":
            rl["ban_hourly"].append(now)
            rl["ban_daily"].append(now)
        elif action == "kick":
            rl["kick_hourly"].append(now)
            rl["kick_daily"].append(now)

        self.save_data()

    def has_role(self, member: discord.Member, role_id: int) -> bool:
        return any(role.id == role_id for role in member.roles)

    def has_protected_role(self, member: discord.Member) -> bool:
        return any(self.has_role(member, role_id) for role_id in self.PROTECTED_ROLE_IDS)

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

    def can_moderate(self, member: discord.Member) -> bool:
        return self.is_senior_moderator(member)

    def can_unban_untimeout(self, member: discord.Member) -> bool:
        return self.is_director(member)

    def can_quarantine(self, member: discord.Member) -> bool:
        return self.is_senior_moderator(member)

    def check_hierarchy(self, moderator: discord.Member, target: discord.Member) -> bool:
        if target.id == moderator.guild.owner_id:
            return False

        if moderator.id == moderator.guild.owner_id:
            return True

        if self.is_director(moderator) and self.has_role(target, self.QUARANTINE_ROLE_ID):
            return True

        target_roles = [
            role for role in target.roles
            if role.id != self.QUARANTINE_ROLE_ID
        ]

        if not target_roles:
            return True

        highest_target_role = max(target_roles, key=lambda r: r.position)

        return moderator.top_role.position > highest_target_role.position

    def check_can_moderate_target(self, moderator: discord.Member, target: discord.Member) -> tuple[bool, str]:
        if self.has_protected_role(target):
            if self.can_quarantine(moderator):
                return False, "You cannot ban/kick/mute staff members. Use `/quarantine add` instead."
            else:
                return False, "You cannot ban/kick/mute staff members."

        if not self.check_hierarchy(moderator, target):
            if self.can_quarantine(moderator):
                return False, "You cannot ban/kick/mute members with a role ≥ to yours. Use `/quarantine add` instead."
            else:
                return False, "You cannot ban/kick/mute members with a role ≥ to yours."

        return True, ""

    async def auto_quarantine_moderator(self, moderator: discord.Member, guild: discord.Guild):
        if not guild or not self.bot.user:
            return

        quarantine_role = guild.get_role(self.QUARANTINE_ROLE_ID)
        if not quarantine_role:
            return

        saved_roles = [role.id for role in moderator.roles if role.id != guild.id]

        self.data["quarantined"][str(moderator.id)] = {
            "roles": saved_roles,
            "quarantined_at": datetime.now().isoformat(),
            "quarantined_by": self.bot.user.id,
            "reason": "UB Anti-Nuke: exceeded moderation rate limits"
        }
        self.save_data()

        try:
            roles_to_remove = [role for role in moderator.roles if role.id != guild.default_role.id]
            await moderator.remove_roles(*roles_to_remove, reason="UB Anti-Nuke: Exceeded rate limits")
            await moderator.add_roles(quarantine_role, reason="UB Anti-Nuke: Exceeded rate limits")

            bot_member = guild.get_member(self.bot.user.id)
            if bot_member:
                await self.cases_manager.log_case(
                    guild=guild,
                    case_type=CaseType.QUARANTINE_ADD,
                    moderator=bot_member,
                    reason="Exceeded moderation rate limits (auto-quarantine)",
                    target_user=moderator,
                    metadata={"roles_saved": len(saved_roles), "auto_quarantine": True}
                )
        except discord.Forbidden:
            pass

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /ban Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.describe(
        member="The member to ban.",
        reason="Reason for the ban.",
        delete_messages="Delete messages from the last 1-7 days."
    )
    async def ban_slash(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
        delete_messages: Optional[int] = 0
    ):
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_moderate(actor):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to ban members.",
                subtitle="Invalid permissions."
            )
            return

        if member.id == actor.id:
            await send_minor_error(interaction, "You cannot ban yourself.")
            return

        can_moderate, error_msg = self.check_can_moderate_target(actor, member)
        if not can_moderate:
            await send_minor_error(interaction, error_msg)
            return

        guild = interaction.guild
        if not guild:
            return

        if not self.is_director(actor):
            can_proceed, error_msg = self.check_rate_limit(str(actor.id), "ban")
            if not can_proceed:
                await send_major_error(
                    interaction,
                    f"Rate limit exceeded. {error_msg}.\n"
                    f"Continuing to exceed rate limits will result in your own quarantine.",
                    subtitle="Rate limit exceeded."
                )
                await self.auto_quarantine_moderator(actor, guild)
                return

            self.add_rate_limit_entry(str(actor.id), "ban")

        await interaction.response.defer(ephemeral=True)

        dm_value = delete_messages if delete_messages is not None else 0
        delete_messages = max(0, min(7, dm_value))

        try:
            await member.ban(
                reason=f"Banned by {actor}: {reason}",
                delete_message_seconds=delete_messages * 86400
            )

            self.data["bans"][str(member.id)] = {
                "banned_at": datetime.now().isoformat(),
                "banned_by": actor.id,
                "reason": reason
            }
            self.save_data()

            await self.cases_manager.log_case(
                guild=guild,
                case_type=CaseType.BAN,
                moderator=actor,
                reason=reason,
                target_user=member,
                metadata={"delete_message_days": delete_messages}
            )

            embed = discord.Embed(
                title="Member Banned",
                color=COLOR_RED,
                timestamp=datetime.now()
            )
            embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=True)
            embed.add_field(name="Moderator", value=actor.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await send_major_error(
                interaction,
                "I lack the necessary permissions to ban this member.",
                subtitle="Invalid configuration. Contact the owner."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ~ban Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="ban", aliases=["b"])
    async def ban_prefix(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        flags: BanFlags
    ):
        if not flags.r:
            return

        reason = flags.r
        delete_messages = max(0, min(7, flags.d))

        actor = ctx.author
        if not isinstance(actor, discord.Member):
            return

        if not self.can_moderate(actor):
            return

        if member.id == actor.id:
            return

        can_moderate, _ = self.check_can_moderate_target(actor, member)
        if not can_moderate:
            return

        guild = ctx.guild
        if not guild:
            return

        if not self.is_director(actor):
            can_proceed, _ = self.check_rate_limit(str(actor.id), "ban")
            if not can_proceed:
                await self.auto_quarantine_moderator(actor, guild)
                return

            self.add_rate_limit_entry(str(actor.id), "ban")

        try:
            await member.ban(
                reason=f"Banned by {actor}: {reason}",
                delete_message_seconds=delete_messages * 86400
            )

            self.data["bans"][str(member.id)] = {
                "banned_at": datetime.now().isoformat(),
                "banned_by": actor.id,
                "reason": reason
            }
            self.save_data()

            await self.cases_manager.log_case(
                guild=guild,
                case_type=CaseType.BAN,
                moderator=actor,
                reason=reason,
                target_user=member,
                metadata={"delete_message_days": delete_messages}
            )

            embed = discord.Embed(
                title="Member Banned",
                color=COLOR_RED,
                timestamp=datetime.now()
            )
            embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=True)
            embed.add_field(name="Moderator", value=actor.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)

            await ctx.send(embed=embed)

        except discord.Forbidden:
            pass

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /unban Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="un-ban", description="Unban a user from the server.")
    @app_commands.describe(
        user="The user to unban.",
        reason="Reason for the unban."
    )
    async def unban_slash(
        self,
        interaction: discord.Interaction,
        user: str,
        reason: str
    ):
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_unban_untimeout(actor):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to unban members.",
                subtitle="Invalid permissions."
            )
            return

        guild = interaction.guild
        if not guild:
            return

        await interaction.response.defer(ephemeral=True)

        user_to_unban = None

        if user.isdigit():
            try:
                user_to_unban = await self.bot.fetch_user(int(user))
            except discord.NotFound:
                pass

        if not user_to_unban:
            try:
                bans = [entry async for entry in guild.bans(limit=None)]
                for ban_entry in bans:
                    if (str(ban_entry.user.id) == user or 
                        str(ban_entry.user) == user or
                        ban_entry.user.name == user):
                        user_to_unban = ban_entry.user
                        break
            except discord.Forbidden:
                await send_major_error(
                    interaction,
                    "I lack the necessary permissions to view bans.",
                    subtitle="Invalid configuration. Contact the owner."
                )
                return

        if not user_to_unban:
            await send_minor_error(interaction, f"Could not find banned user: {user}")
            return

        try:
            await guild.unban(user_to_unban, reason=f"Unbanned by {actor}: {reason}")

            if str(user_to_unban.id) in self.data["bans"]:
                del self.data["bans"][str(user_to_unban.id)]
                self.save_data()

            await self.cases_manager.log_case(
                guild=guild,
                case_type=CaseType.UNBAN,
                moderator=actor,
                reason=reason,
                target_user=user_to_unban
            )

            embed = discord.Embed(
                title="User Unbanned",
                color=COLOR_GREEN,
                timestamp=datetime.now()
            )
            embed.add_field(name="User", value=f"{user_to_unban.mention} ({user_to_unban.id})", inline=True)
            embed.add_field(name="Director", value=actor.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.NotFound:
            await send_minor_error(interaction, f"{user_to_unban.mention} is not banned.")
        except discord.Forbidden:
            await send_major_error(
                interaction,
                "I lack the necessary permissions to unban this user.",
                subtitle="Invalid configuration. Contact the owner."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ~unban Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="un-ban", aliases=["unban", "ub"])
    async def unban_prefix(
        self,
        ctx: commands.Context,
        user: str,
        *,
        flags: KickFlags
    ):
        if not flags.r:
            return

        reason = flags.r

        actor = ctx.author
        if not isinstance(actor, discord.Member):
            return

        if not self.can_unban_untimeout(actor):
            return

        guild = ctx.guild
        if not guild:
            return

        user_to_unban = None

        if user.isdigit():
            try:
                user_to_unban = await self.bot.fetch_user(int(user))
            except discord.NotFound:
                pass

        if not user_to_unban:
            try:
                bans = [entry async for entry in guild.bans(limit=None)]
                for ban_entry in bans:
                    if (str(ban_entry.user.id) == user or 
                        str(ban_entry.user) == user or
                        ban_entry.user.name == user):
                        user_to_unban = ban_entry.user
                        break
            except discord.Forbidden:
                return

        if not user_to_unban:
            return

        try:
            await guild.unban(user_to_unban, reason=f"Unbanned by {actor}: {reason}")

            if str(user_to_unban.id) in self.data["bans"]:
                del self.data["bans"][str(user_to_unban.id)]
                self.save_data()

            await self.cases_manager.log_case(
                guild=guild,
                case_type=CaseType.UNBAN,
                moderator=actor,
                reason=reason,
                target_user=user_to_unban
            )

            embed = discord.Embed(
                title="User Unbanned",
                color=COLOR_GREEN,
                timestamp=datetime.now()
            )
            embed.add_field(name="User", value=f"{user_to_unban.mention} ({user_to_unban.id})", inline=True)
            embed.add_field(name="Director", value=actor.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)

            await ctx.send(embed=embed)

        except (discord.NotFound, discord.Forbidden):
            pass

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /kick Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(
        member="The member to kick.",
        reason="Reason for the kick."
    )
    async def kick_slash(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str
    ):
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_moderate(actor):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to kick members.",
                subtitle="Invalid permissions."
            )
            return

        if member.id == actor.id:
            await send_minor_error(interaction, "You cannot kick yourself.")
            return

        can_moderate, error_msg = self.check_can_moderate_target(actor, member)
        if not can_moderate:
            await send_minor_error(interaction, error_msg)
            return

        guild = interaction.guild
        if not guild:
            return

        if not self.is_director(actor):
            can_proceed, error_msg = self.check_rate_limit(str(actor.id), "kick")
            if not can_proceed:
                await send_major_error(
                    interaction,
                    f"Rate limit exceeded. {error_msg}.\n"
                    f"Continuing to exceed rate limits will result in your own quarantine.",
                    subtitle="Rate limit exceeded."
                )
                await self.auto_quarantine_moderator(actor, guild)
                return

            self.add_rate_limit_entry(str(actor.id), "kick")

        await interaction.response.defer(ephemeral=True)

        try:
            await member.kick(reason=f"Kicked by {actor}: {reason}")

            self.data["kicks"][str(member.id)] = {
                "kicked_at": datetime.now().isoformat(),
                "kicked_by": actor.id,
                "reason": reason
            }
            self.save_data()

            await self.cases_manager.log_case(
                guild=guild,
                case_type=CaseType.KICK,
                moderator=actor,
                reason=reason,
                target_user=member
            )

            embed = discord.Embed(
                title="Member Kicked",
                color=COLOR_ORANGE,
                timestamp=datetime.now()
            )
            embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=True)
            embed.add_field(name="Moderator", value=actor.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await send_major_error(
                interaction,
                "I lack the necessary permissions to kick this member.",
                subtitle="Invalid configuration. Contact the owner."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ~kick Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="kick", aliases=["k"])
    async def kick_prefix(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        flags: KickFlags
    ):
        if not flags.r:
            return

        reason = flags.r

        actor = ctx.author
        if not isinstance(actor, discord.Member):
            return

        if not self.can_moderate(actor):
            return

        if member.id == actor.id:
            return

        can_moderate, _ = self.check_can_moderate_target(actor, member)
        if not can_moderate:
            return

        guild = ctx.guild
        if not guild:
            return

        if not self.is_director(actor):
            can_proceed, _ = self.check_rate_limit(str(actor.id), "kick")
            if not can_proceed:
                await self.auto_quarantine_moderator(actor, guild)
                return

            self.add_rate_limit_entry(str(actor.id), "kick")

        try:
            await member.kick(reason=f"Kicked by {actor}: {reason}")

            self.data["kicks"][str(member.id)] = {
                "kicked_at": datetime.now().isoformat(),
                "kicked_by": actor.id,
                "reason": reason
            }
            self.save_data()

            await self.cases_manager.log_case(
                guild=guild,
                case_type=CaseType.KICK,
                moderator=actor,
                reason=reason,
                target_user=member
            )

            embed = discord.Embed(
                title="Member Kicked",
                color=COLOR_ORANGE,
                timestamp=datetime.now()
            )
            embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=True)
            embed.add_field(name="Moderator", value=actor.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)

            await ctx.send(embed=embed)

        except discord.Forbidden:
            pass

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /timeout Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="timeout", description="Timeout a member.")
    @app_commands.describe(
        member="The member to timeout.",
        duration="Duration.",
        reason="Reason for the timeout."
    )
    async def timeout_slash(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: str
    ):
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_moderate(actor):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to timeout members.",
                subtitle="Invalid permissions."
            )
            return

        if member.id == actor.id:
            await send_minor_error(interaction, "You cannot timeout yourself.")
            return

        can_moderate, error_msg = self.check_can_moderate_target(actor, member)
        if not can_moderate:
            await send_minor_error(interaction, error_msg)
            return

        duration_seconds = self.parse_duration(duration)
        if not duration_seconds:
            await send_minor_error(interaction, "Invalid duration format. Use: 30s, 5m, 1h, 2d, 1w")
            return

        max_duration = 28 * 86400
        if duration_seconds > max_duration:
            await send_minor_error(interaction, f"Timeout duration cannot exceed 28 days. You provided: {duration}")
            return

        guild = interaction.guild
        if not guild:
            return

        if not self.is_director(actor):
            can_proceed, error_msg = self.check_rate_limit(str(actor.id), "timeout")
            if not can_proceed:
                await send_major_error(
                    interaction,
                    f"Rate limit exceeded. {error_msg}.\n"
                    f"Continuing to exceed rate limits will result in your own quarantine.",
                    subtitle="Rate limit exceeded."
                )
                await self.auto_quarantine_moderator(actor, guild)
                return

            self.add_rate_limit_entry(str(actor.id), "timeout")

        await interaction.response.defer(ephemeral=True)

        try:
            until = discord.utils.utcnow() + timedelta(seconds=duration_seconds)
            await member.timeout(until, reason=f"Timed out by {actor}: {reason}")

            self.data["timeouts"][str(member.id)] = {
                "timed_out_at": datetime.now().isoformat(),
                "timed_out_by": actor.id,
                "reason": reason,
                "duration": duration_seconds,
                "until": until.isoformat()
            }
            self.save_data()

            await self.cases_manager.log_case(
                guild=guild,
                case_type=CaseType.TIMEOUT,
                moderator=actor,
                reason=reason,
                target_user=member,
                duration=duration,
                metadata={"until": until.isoformat()}
            )

            embed = discord.Embed(
                title="Member Timed Out",
                color=COLOR_ORANGE,
                timestamp=datetime.now()
            )
            embed.add_field(name="Member", value=member.mention, inline=True)
            embed.add_field(name="Moderator", value=actor.mention, inline=True)
            embed.add_field(name="Duration", value=duration, inline=True)
            embed.add_field(name="Expires", value=discord.utils.format_dt(until, 'R'), inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await send_major_error(
                interaction,
                "I lack the necessary permissions to timeout this member.",
                subtitle="Invalid configuration. Contact the owner."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ~timeout Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="timeout", aliases=["tt", "mute", "m"])
    async def timeout_prefix(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        flags: TimeoutFlags
    ):
        if not flags.r or not flags.d:
            return

        reason = flags.r
        duration = flags.d

        actor = ctx.author
        if not isinstance(actor, discord.Member):
            return

        if not self.can_moderate(actor):
            return

        if member.id == actor.id:
            return

        can_moderate, _ = self.check_can_moderate_target(actor, member)
        if not can_moderate:
            return

        duration_seconds = self.parse_duration(duration)
        if not duration_seconds:
            return

        max_duration = 28 * 86400
        if duration_seconds > max_duration:
            return

        guild = ctx.guild
        if not guild:
            return

        if not self.is_director(actor):
            can_proceed, _ = self.check_rate_limit(str(actor.id), "timeout")
            if not can_proceed:
                await self.auto_quarantine_moderator(actor, guild)
                return

            self.add_rate_limit_entry(str(actor.id), "timeout")

        try:
            until = discord.utils.utcnow() + timedelta(seconds=duration_seconds)
            await member.timeout(until, reason=f"Timed out by {actor}: {reason}")

            self.data["timeouts"][str(member.id)] = {
                "timed_out_at": datetime.now().isoformat(),
                "timed_out_by": actor.id,
                "reason": reason,
                "duration": duration_seconds,
                "until": until.isoformat()
            }
            self.save_data()

            await self.cases_manager.log_case(
                guild=guild,
                case_type=CaseType.TIMEOUT,
                moderator=actor,
                reason=reason,
                target_user=member,
                duration=duration,
                metadata={"until": until.isoformat()}
            )

            embed = discord.Embed(
                title="Member Timed Out",
                color=COLOR_ORANGE,
                timestamp=datetime.now()
            )
            embed.add_field(name="Member", value=member.mention, inline=True)
            embed.add_field(name="Moderator", value=actor.mention, inline=True)
            embed.add_field(name="Duration", value=duration, inline=True)
            embed.add_field(name="Expires", value=discord.utils.format_dt(until, 'R'), inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)

            await ctx.send(embed=embed)

        except discord.Forbidden:
            pass

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /untimeout Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="un-timeout", description="Remove timeout from a member.")
    @app_commands.describe(
        member="The member to remove timeout from.",
        reason="Reason for removing timeout."
    )
    async def untimeout_slash(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str
    ):
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_unban_untimeout(actor):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to remove timeouts.",
                subtitle="Invalid permissions."
            )
            return

        if not member.is_timed_out():
            await send_minor_error(interaction, f"{member.mention} is not currently timed out.")
            return

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not guild:
            return

        try:
            await member.timeout(None, reason=f"Timeout removed by {actor}: {reason}")

            if str(member.id) in self.data["timeouts"]:
                del self.data["timeouts"][str(member.id)]
                self.save_data()

            await self.cases_manager.log_case(
                guild=guild,
                case_type=CaseType.UNTIMEOUT,
                moderator=actor,
                reason=reason,
                target_user=member
            )

            embed = discord.Embed(
                title="Timeout Removed",
                color=COLOR_GREEN,
                timestamp=datetime.now()
            )
            embed.add_field(name="Member", value=member.mention, inline=True)
            embed.add_field(name="Director", value=actor.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await send_major_error(
                interaction,
                "I lack the necessary permissions to remove timeout from this member.",
                subtitle="Invalid configuration. Contact the owner."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ~un-timeout Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="un-timeout", aliases=["untimeout", "utt", "unmute", "um"])
    async def untimeout_prefix(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        flags: KickFlags
    ):
        if not flags.r:
            return

        reason = flags.r

        actor = ctx.author
        if not isinstance(actor, discord.Member):
            return

        if not self.can_unban_untimeout(actor):
            return

        if not member.is_timed_out():
            return

        guild = ctx.guild
        if not guild:
            return

        try:
            await member.timeout(None, reason=f"Timeout removed by {actor}: {reason}")

            if str(member.id) in self.data["timeouts"]:
                del self.data["timeouts"][str(member.id)]
                self.save_data()

            await self.cases_manager.log_case(
                guild=guild,
                case_type=CaseType.UNTIMEOUT,
                moderator=actor,
                reason=reason,
                target_user=member
            )

            embed = discord.Embed(
                title="Timeout Removed",
                color=COLOR_GREEN,
                timestamp=datetime.now()
            )
            embed.add_field(name="Member", value=member.mention, inline=True)
            embed.add_field(name="Director", value=actor.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)

            await ctx.send(embed=embed)

        except discord.Forbidden:
            pass

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Purge Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="purge", description="Delete a specified number of messages.")
    @app_commands.describe(
        amount="Number of messages to delete.",
        member="Only delete messages from this member.",
        reason="Reason for purging messages."
    )
    async def purge_slash(
        self,
        interaction: discord.Interaction,
        amount: int,
        reason: str,
        member: Optional[discord.Member] = None
    ):
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_moderate(actor):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to purge messages.",
                subtitle="Invalid permissions."
            )
            return

        if amount < 1 or amount > 100:
            await send_minor_error(interaction, "Amount must be between 1 and 100.")
            return

        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            return

        guild = interaction.guild
        if not guild:
            return

        try:
            if member:
                deleted = await channel.purge(
                    limit=500,
                    check=lambda m: m.author.id == member.id and (datetime.now() - m.created_at).days < 14,
                    before=interaction.created_at,
                    bulk=True
                )
                deleted = deleted[:amount]
            else:
                deleted = await channel.purge(
                    limit=amount,
                    before=interaction.created_at,
                    bulk=True
                )

            await self.cases_manager.log_case(
                guild=guild,
                case_type=CaseType.PURGE,
                moderator=actor,
                reason=reason,
                target_user=member if member else None,
                metadata={
                    "deleted_messages": len(deleted),
                    "channel_id": channel.id
                }
            )

            embed = discord.Embed(
                title="Messages Purged",
                color=COLOR_BLURPLE,
                timestamp=datetime.now()
            )
            embed.add_field(name="Deleted", value=str(len(deleted)), inline=True)
            embed.add_field(name="Moderator", value=actor.mention, inline=True)
            if member:
                embed.add_field(name="From User", value=member.mention, inline=True)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await send_major_error(
                interaction,
                "I lack the necessary permissions to delete messages.",
                subtitle="Invalid configuration. Contact the owner."
            )

    @commands.command(name="purge", aliases=["p"])
    async def purge_prefix(
        self,
        ctx: commands.Context,
        amount: int,
        *,
        flags: PurgeFlags
    ):
        actor = ctx.author
        if not isinstance(actor, discord.Member):
            return

        if not self.can_moderate(actor):
            return

        if amount < 1 or amount > 100:
            return

        channel = ctx.channel
        if not isinstance(channel, discord.TextChannel):
            return

        guild = ctx.guild
        if not guild:
            return

        member = flags.u

        try:
            if member:
                deleted = await channel.purge(
                    limit=amount,
                    check=lambda m: m.author.id == member.id
                )
            else:
                deleted = await channel.purge(limit=amount)

            await self.cases_manager.log_case(
                guild=guild,
                case_type=CaseType.PURGE,
                moderator=actor,
                reason=flags.r,
                target_user=member if member else None,
                metadata={
                    "deleted_messages": len(deleted),
                    "channel_id": channel.id
                }
            )

            embed = discord.Embed(
                title="Messages Purged",
                color=COLOR_BLURPLE,
                timestamp=datetime.now()
            )
            embed.add_field(name="Deleted", value=str(len(deleted)), inline=True)
            embed.add_field(name="Moderator", value=actor.mention, inline=True)
            if member:
                embed.add_field(name="From User", value=member.mention, inline=True)

            msg = await ctx.send(embed=embed)
            await msg.delete(delay=5)

        except discord.Forbidden:
            pass

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # View Commands
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="bans", description="View all banned members.")
    async def bans_slash(self, interaction: discord.Interaction):
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_view(actor):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to view bans.",
                subtitle="Invalid permissions."
            )
            return

        guild = interaction.guild
        if not guild:
            return

        await interaction.response.defer(ephemeral=True)

        try:
            bans = [entry async for entry in guild.bans(limit=None)]

            if not bans:
                embed = discord.Embed(
                    description="No members are currently banned.",
                    color=COLOR_GREEN
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            embed = discord.Embed(
                title="Banned Members",
                color=COLOR_RED,
                timestamp=datetime.now()
            )

            for ban_entry in bans[:25]:
                user = ban_entry.user
                ban_data = self.data["bans"].get(str(user.id))

                if ban_data:
                    banned_at = datetime.fromisoformat(ban_data["banned_at"])
                    reason = ban_data["reason"]
                    value = f"Banned: {discord.utils.format_dt(banned_at, 'R')}\nReason: {reason}"
                else:
                    value = f"Reason: {ban_entry.reason or 'No reason provided'}"

                embed.add_field(
                    name=f"{user} ({user.id})",
                    value=value,
                    inline=False
                )

            if len(bans) > 25:
                embed.set_footer(text=f"Showing 25 of {len(bans)} bans")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await send_major_error(
                interaction,
                "I lack the necessary permissions to view bans.",
                subtitle="Invalid configuration. Contact the owner."
            )

    @commands.command(name="bans", aliases=["banlist", "bls"])
    async def bans_prefix(self, ctx: commands.Context):
        actor = ctx.author
        if not isinstance(actor, discord.Member):
            return

        if not self.can_view(actor):
            return

        guild = ctx.guild
        if not guild:
            return

        try:
            bans = [entry async for entry in guild.bans(limit=None)]

            if not bans:
                embed = discord.Embed(
                    description="No members are currently banned.",
                    color=COLOR_GREEN
                )
                await ctx.send(embed=embed)
                return

            embed = discord.Embed(
                title="Banned Members",
                color=COLOR_RED,
                timestamp=datetime.now()
            )

            for ban_entry in bans[:25]:
                user = ban_entry.user
                ban_data = self.data["bans"].get(str(user.id))

                if ban_data:
                    banned_at = datetime.fromisoformat(ban_data["banned_at"])
                    reason = ban_data["reason"]
                    value = f"Banned: {discord.utils.format_dt(banned_at, 'R')}\nReason: {reason}"
                else:
                    value = f"Reason: {ban_entry.reason or 'No reason provided'}"

                embed.add_field(
                    name=f"{user} ({user.id})",
                    value=value,
                    inline=False
                )

            if len(bans) > 25:
                embed.set_footer(text=f"Showing 25 of {len(bans)} bans")

            await ctx.send(embed=embed)

        except discord.Forbidden:
            pass

    @app_commands.command(name="timeouts", description="View all timed out members.")
    async def timeouts_slash(self, interaction: discord.Interaction):
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_view(actor):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to view timeouts.",
                subtitle="Invalid permissions."
            )
            return

        guild = interaction.guild
        if not guild:
            return

        await interaction.response.defer(ephemeral=True)

        timed_out_members = [m for m in guild.members if m.is_timed_out()]

        if not timed_out_members:
            embed = discord.Embed(
                description="No members are currently timed out.",
                color=COLOR_GREEN
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="Timed Out Members",
            color=COLOR_ORANGE,
            timestamp=datetime.now()
        )

        for member in timed_out_members[:25]:
            timeout_data = self.data["timeouts"].get(str(member.id))

            if timeout_data and member.timed_out_until:
                timed_out_at = datetime.fromisoformat(timeout_data["timed_out_at"])
                reason = timeout_data["reason"]
                value = (f"Timed out: {discord.utils.format_dt(timed_out_at, 'R')}\n"
                        f"Expires: {discord.utils.format_dt(member.timed_out_until, 'R')}\n"
                        f"Reason: {reason}")
            elif member.timed_out_until:
                value = f"Expires: {discord.utils.format_dt(member.timed_out_until, 'R')}"
            else:
                value = "No data available"

            embed.add_field(
                name=f"{member} ({member.id})",
                value=value,
                inline=False
            )

        if len(timed_out_members) > 25:
            embed.set_footer(text=f"Showing 25 of {len(timed_out_members)} timeouts")

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /mute-list Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="mute-list", aliases=["mutelist", "mutes", "mls", "time-outs", "timeouts", "tls"])
    async def timeouts_prefix(self, ctx: commands.Context):
        actor = ctx.author
        if not isinstance(actor, discord.Member):
            return

        if not self.can_view(actor):
            return

        guild = ctx.guild
        if not guild:
            return

        timed_out_members = [m for m in guild.members if m.is_timed_out()]

        if not timed_out_members:
            embed = discord.Embed(
                description="No members are currently timed out.",
                color=COLOR_GREEN
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="Timed Out Members",
            color=COLOR_ORANGE,
            timestamp=datetime.now()
        )

        for member in timed_out_members[:25]:
            timeout_data = self.data["timeouts"].get(str(member.id))

            if timeout_data and member.timed_out_until:
                timed_out_at = datetime.fromisoformat(timeout_data["timed_out_at"])
                reason = timeout_data["reason"]
                value = (f"Timed out: {discord.utils.format_dt(timed_out_at, 'R')}\n"
                        f"Expires: {discord.utils.format_dt(member.timed_out_until, 'R')}\n"
                        f"Reason: {reason}")
            elif member.timed_out_until:
                value = f"Expires: {discord.utils.format_dt(member.timed_out_until, 'R')}"
            else:
                value = "No data available"

            embed.add_field(
                name=f"{member} ({member.id})",
                value=value,
                inline=False
            )

        if len(timed_out_members) > 25:
            embed.set_footer(text=f"Showing 25 of {len(timed_out_members)} timeouts")

        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCommands(cast(UtilityBot, bot)))