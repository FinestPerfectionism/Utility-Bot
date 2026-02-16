import discord
from discord.ext import commands
from discord import app_commands

from core.bot import UtilityBot

import json
import os
from datetime import datetime, timedelta
from typing import Dict, cast

from constants import(
    BOT_OWNER_ID,

    COLOR_GREEN,
    COLOR_ORANGE,
    COLOR_RED,

    CONTESTED_EMOJI_ID,

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
from core.utils import send_major_error, send_minor_error

from commands.moderation.cases import CaseType

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Quarantine Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class QuarantineCommands(commands.Cog):
    def __init__(self, bot: "UtilityBot"):
        self.bot = bot
        self.data_file = "quarantine_data.json"
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

        self.HOURLY_LIMIT = 5
        self.DAILY_LIMIT = 20

    @property
    def cases_manager(self):
        return cast(UtilityBot, self.bot).cases_manager

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
            "quarantined": {},
            "rate_limits": {}
        }

    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=4)

    def clean_old_rate_limits(self, user_id: str):
        now = datetime.now()
        if user_id not in self.data["rate_limits"]:
            self.data["rate_limits"][user_id] = {"hourly": [], "daily": []}

        self.data["rate_limits"][user_id]["hourly"] = [
            ts for ts in self.data["rate_limits"][user_id]["hourly"]
            if datetime.fromisoformat(ts) > now - timedelta(hours=1)
        ]

        self.data["rate_limits"][user_id]["daily"] = [
            ts for ts in self.data["rate_limits"][user_id]["daily"]
            if datetime.fromisoformat(ts) > now - timedelta(days=1)
        ]

    def check_rate_limit(self, user_id: str) -> tuple[bool, str]:
        self.clean_old_rate_limits(user_id)

        hourly_count = len(self.data["rate_limits"][user_id]["hourly"])
        daily_count = len(self.data["rate_limits"][user_id]["daily"])

        if hourly_count >= self.HOURLY_LIMIT:
            return False, f"Hourly limit exceeded ({self.HOURLY_LIMIT} quarantines per hour)"

        if daily_count >= self.DAILY_LIMIT:
            return False, f"Daily limit exceeded ({self.DAILY_LIMIT} quarantines per day)"

        return True, ""

    def add_rate_limit_entry(self, user_id: str):
        now = datetime.now().isoformat()
        if user_id not in self.data["rate_limits"]:
            self.data["rate_limits"][user_id] = {"hourly": [], "daily": []}

        self.data["rate_limits"][user_id]["hourly"].append(now)
        self.data["rate_limits"][user_id]["daily"].append(now)
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

    def can_add(self, member: discord.Member) -> bool:
        return self.is_senior_moderator(member)

    def can_remove(self, member: discord.Member) -> bool:
        return self.is_director(member)

    def check_hierarchy(self, moderator: discord.Member, target: discord.Member) -> bool:
        if target.id == moderator.guild.owner_id:
            return False

        if moderator.id == moderator.guild.owner_id:
            return True

        target_roles = [
            role for role in target.roles
            if role.id != self.QUARANTINE_ROLE_ID
        ]

        if not target_roles:
            return True

        highest_target_role = max(target_roles, key=lambda r: r.position)

        return moderator.top_role.position > highest_target_role.position

    quarantine_group = app_commands.Group(
        name="quarantine",
        description="Staff only —— Quarantine management."
    )

    @quarantine_group.command(
        name="view",
        description="View the members in quarantine."
    )
    async def quarantine_view(self, interaction: discord.Interaction):
        member = interaction.user
        if not isinstance(member, discord.Member):
            return
        if not self.can_view(member):

            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to view quarantined members.",
                subtitle="No permisisons."
            )
            return

        if not self.data["quarantined"]:
            await interaction.response.send_message(
                "No members are currently quarantined.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Quarantined Members",
            color=COLOR_ORANGE,
            timestamp=datetime.now()
        )

        for user_id, data in self.data["quarantined"].items():
            guild = interaction.guild
            if guild is None:
                return
            member = guild.get_member(int(user_id))
            member_name = member.mention if member else f"Unknown User ({user_id})"
            quarantined_at = datetime.fromisoformat(data["quarantined_at"])

            embed.add_field(
                name=member_name,
                value=f"Quarantined: {discord.utils.format_dt(quarantined_at, 'R')}\n"
                      f"Saved roles: {len(data['roles'])}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @quarantine_group.command(name="add", description="Add a member to quarantine.")
    @app_commands.describe(member="The member to quarantine.", reason="Reason for quarantine.")
    async def quarantine_add(
        self, 
        interaction: discord.Interaction, 
        member: discord.Member,
        reason: str | None = None
    ):
        reason = reason or f"No reason specified by {interaction.user}."

        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return
        if not self.can_add(actor):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to add members to quarantine.",
                subtitle="No permisisons."
            )
            return

        if member.id == interaction.user.id:
            await send_minor_error(
                interaction,
                "You cannot quarantine yourself.",
            )
            return

        if not self.check_hierarchy(actor, member):
            await send_minor_error(
                interaction,
                "You cannot quarantine members with a role ≥ to yours.",
            )
            return

        if str(member.id) in self.data["quarantined"]:
            await send_minor_error(
                interaction,
                f"{member.mention} is already quarantined.",
            )
            return

        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not self.is_director(interaction.user):
            can_proceed, error_msg = self.check_rate_limit(str(actor.id))
            if not can_proceed:
                await send_major_error(
                    interaction,
                    f"Rate limit exceeded. {error_msg}.\n"
                    f"Continuing to exceed rate limits will result in your own quarantine.",
                    subtitle="Rate limit exceeded."
                )

                guild = interaction.guild
                if guild is None:
                    return
                await self.auto_quarantine_moderator(actor, guild)
                return

            self.add_rate_limit_entry(str(actor.id))

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if guild is None:
            return
        quarantine_role = guild.get_role(self.QUARANTINE_ROLE_ID)
        if not quarantine_role:
            await send_major_error(
                interaction,
                "Quarantine role not found.",
                subtitle=f"Invalid IDs. Contact <@{BOT_OWNER_ID}>."
            )
            return

        saved_roles = [
            role.id for role in member.roles
            if role.id not in (guild.default_role.id, self.QUARANTINE_ROLE_ID)
        ]

        self.data["quarantined"][str(member.id)] = {
            "roles": saved_roles,
            "quarantined_at": datetime.now().isoformat(),
            "quarantined_by": interaction.user.id,
            "reason": reason
        }
        self.save_data()

        try:
            roles_to_remove = [role for role in member.roles if role.id != guild.default_role.id]
            await member.remove_roles(*roles_to_remove, reason=f"Quarantined by {interaction.user}")
            await member.add_roles(quarantine_role, reason=f"Quarantined by {interaction.user}: {reason}")

            await self.cases_manager.log_case(
                guild=guild,
                case_type=CaseType.QUARANTINE_ADD,
                moderator=actor,
                reason=reason,
                target_user=member,
                metadata={"roles_saved": len(saved_roles)}
            )

            embed = discord.Embed(
                title="Member Quarantined",
                color=COLOR_RED,
                timestamp=datetime.now()
            )
            embed.add_field(name="Member", value=member.mention, inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Roles Saved", value=str(len(saved_roles)), inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await send_major_error(
                interaction,
                "I lack the necessary permissions to run this command.",
                subtitle="Invalid configuration. Contact the owner."
            )
            if str(member.id) in self.data["quarantined"]:
                del self.data["quarantined"][str(member.id)]
                self.save_data()

    async def auto_quarantine_moderator(self, moderator: discord.Member, guild: discord.Guild):
        if not guild or not self.bot.user:
            return

        quarantine_role = guild.get_role(self.QUARANTINE_ROLE_ID)
        if not quarantine_role:
            return

        saved_roles = [
            role.id for role in moderator.roles
            if role.id not in (guild.default_role.id, self.QUARANTINE_ROLE_ID)
        ]

        self.data["quarantined"][str(moderator.id)] = {
            "roles": saved_roles,
            "quarantined_at": datetime.now().isoformat(),
            "quarantined_by": self.bot.user.id,
            "reason": "Exceeded quarantine rate limits"
        }
        self.save_data()

        try:
            roles_to_remove = [role for role in moderator.roles if role.id != guild.default_role.id]
            await moderator.remove_roles(*roles_to_remove, reason="Auto-quarantined: Exceeded rate limits")
            await moderator.add_roles(quarantine_role, reason="Auto-quarantined: Exceeded rate limits")

            bot_member = guild.get_member(self.bot.user.id)
            if bot_member:
                await self.cases_manager.log_case(
                    guild=guild,
                    case_type=CaseType.QUARANTINE_ADD,
                    moderator=bot_member,
                    reason="Exceeded quarantine rate limits (auto-quarantine)",
                    target_user=moderator,
                    metadata={"roles_saved": len(saved_roles), "auto_quarantine": True}
                )
        except discord.Forbidden:
            pass

    @quarantine_group.command(name="remove", description="Remove a member from quarantine.")
    @app_commands.describe(member="The member to remove from quarantine.")
    async def quarantine_remove(
        self, 
        interaction: discord.Interaction, 
        member: discord.Member
    ):

        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return
        if not self.can_remove(actor):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to remove members from quarantine.",
                subtitle="No permisisons."
            )
            return

        guild = interaction.guild
        if not guild:
            await send_minor_error(
                interaction,
                "This command can only be used in a server.",
                subtitle="Bad command environment."
            )
            return

        quarantine_role = guild.get_role(self.QUARANTINE_ROLE_ID)
        in_json = str(member.id) in self.data["quarantined"]
        has_role = quarantine_role in member.roles if quarantine_role else False

        if not in_json and not has_role:
            await send_minor_error(
                interaction,
                f"{member.mention} is already not quarantined.",
            )
            return

        await interaction.response.defer(ephemeral=True)

        quarantine_data = self.data["quarantined"].get(str(member.id))
        saved_role_ids = quarantine_data["roles"] if quarantine_data else []

        guild = interaction.guild
        if guild is None:
            return
        quarantine_role = await guild.fetch_role(self.QUARANTINE_ROLE_ID)

        try:
            if quarantine_role and quarantine_role in member.roles:
                await member.remove_roles(quarantine_role, reason=f"Unquarantined by {interaction.user}")

            roles_to_add = []
            roles_not_found = []

            for role_id in saved_role_ids:
                if role_id == self.QUARANTINE_ROLE_ID:
                    continue

                role = guild.get_role(role_id)
                if role:
                    roles_to_add.append(role)
                else:
                    roles_not_found.append(role_id)

            if roles_to_add:
                await member.add_roles(*roles_to_add, reason=f"Unquarantined by {interaction.user}")

            if str(member.id) in self.data["quarantined"]:
                del self.data["quarantined"][str(member.id)]
                self.save_data()

            await self.cases_manager.log_case(
                guild=guild,
                case_type=CaseType.QUARANTINE_REMOVE,
                moderator=actor,
                reason="Removed from quarantine",
                target_user=member,
                metadata={"roles_restored": len(roles_to_add)}
            )

            embed = discord.Embed(
                title="Member Unquarantined",
                color=COLOR_GREEN,
                timestamp=datetime.now()
            )
            embed.add_field(name="Member", value=member.mention, inline=True)
            embed.add_field(name="Director", value=interaction.user.mention, inline=True)
            embed.add_field(name="Roles Restored", value=str(len(roles_to_add)), inline=True)

            if roles_not_found:
                embed.add_field(
                    name=f"{CONTESTED_EMOJI_ID} Roles Not Found",
                    value=f"{len(roles_not_found)} role(s) no longer exist and could not be restored.",
                    inline=False
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await send_major_error(
                interaction,
                "I lack the necessary permissions to run this command.",
                subtitle="Invalid configuration. Contact the owner."
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(QuarantineCommands(cast(UtilityBot, bot)))