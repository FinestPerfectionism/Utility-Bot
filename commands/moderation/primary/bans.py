import discord
from discord.ext import commands
from discord import app_commands

from datetime import datetime
from typing import Optional, Dict, cast

from commands.moderation.cases import CaseType

from bot import UtilityBot

from core.utils import (
    send_major_error,
    send_minor_error
)
from core.permissions import is_director

from constants import (
    COLOR_GREEN,
    COLOR_RED,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,
)

from ._base import (
    ModerationBase,
    BanFlags,
    KickFlags,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Ban Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class BanCommands(ModerationBase):
    def __init__(self, bot: "UtilityBot"):
        super().__init__(bot)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /ban Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.describe(
        member="The member to ban.",
        reason="Reason for the ban.",
        delete_messages="Delete messages from the last 1-7 days.",
        proof="Optional proof attachment."
    )
    async def ban_slash(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
        delete_messages: Optional[int] = 0,
        proof: Optional[discord.Attachment] = None
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

        if not is_director(actor):
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

            metadata: Dict = {"delete_message_days": delete_messages}
            if proof:
                metadata["proof_url"] = proof.url

            await self.cases_manager.log_case(
                guild=guild,
                case_type=CaseType.BAN,
                moderator=actor,
                reason=reason,
                target_user=member,
                metadata=metadata
            )

            embed = discord.Embed(
                title="Member Banned",
                color=COLOR_RED,
                timestamp=datetime.now()
            )
            embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=True)
            embed.add_field(name="Moderator", value=actor.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            if proof:
                embed.set_image(url=proof.url)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await send_major_error(
                interaction,
                "I lack the necessary permissions to ban this member.",
                subtitle="Invalid configuration. Contact the owner."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .ban Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="ban", aliases=["b"])
    async def ban_prefix(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        flags: BanFlags
    ):
        actor = ctx.author
        if not isinstance(actor, discord.Member):
            return

        if not self.can_moderate(actor):
            return

        if not flags.r:
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to ban member!**\n"
                f"Please provide a reason for the ban."
            )
            return

        reason = flags.r
        delete_messages = max(0, min(7, flags.d))

        if member.id == actor.id:
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to ban member!**\n"
                f"You cannot ban yourself."
            )
            return

        can_moderate, error_msg = self.check_can_moderate_target(actor, member)
        if not can_moderate:
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to ban member!**\n"
                f"{error_msg}"
            )
            return

        guild = ctx.guild
        if not guild:
            return

        if not is_director(actor):
            can_proceed, error_msg = self.check_rate_limit(str(actor.id), "ban")
            if not can_proceed:
                await ctx.send(
                    f"{CONTESTED_EMOJI_ID} **Failed to ban member!**\n"
                    f"Rate limit exceeded. {error_msg}."
                )
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

            if flags.s:
                await ctx.message.delete()
                return

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
            await ctx.send(
                f"{DENIED_EMOJI_ID} **Failed to ban member!**\n"
                f"I lack the necessary permissions to ban members.\n"
                f"-# Contact the owner."
            )

    @ban_prefix.error
    async def ban_prefix_error(self, ctx: commands.Context, error: Exception):
        actor = ctx.author
        if not isinstance(actor, discord.Member) or not self.can_moderate(actor):
            return

        if isinstance(error, commands.MemberNotFound):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to ban member!**\n"
                f"Please provide a valid user to ban."
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to ban member!**\n"
                f"Please provide a member to ban."
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to ban member!**\n"
                f"Please provide a valid user to ban."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /un-ban Command
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
                    if (
                        str(ban_entry.user.id) == user or
                        str(ban_entry.user) == user or
                        ban_entry.user.name == user
                    ):
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
    # .un-ban Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="un-ban", aliases=["unban", "ub"])
    async def unban_prefix(
        self,
        ctx: commands.Context,
        user: str,
        *,
        flags: KickFlags
    ):
        actor = ctx.author
        if not isinstance(actor, discord.Member):
            return

        if not self.can_unban_untimeout(actor):
            return

        if not flags.r:
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to unban user!**\n"
                f"Please provide a reason for the unban."
            )
            return

        reason = flags.r

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
                    if (
                        str(ban_entry.user.id) == user or
                        str(ban_entry.user) == user or
                        ban_entry.user.name == user
                    ):
                        user_to_unban = ban_entry.user
                        break
            except discord.Forbidden:
                await ctx.send(
                    f"{DENIED_EMOJI_ID} **Failed to unban user!**\n"
                    f"I lack the necessary permissions to view bans.\n"
                    f"-# Contact the owner."
                )
                return

        if not user_to_unban:
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to unban user!**\n"
                f"Could not find a banned user matching `{user}`."
            )
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

            if flags.s:
                await ctx.message.delete()
                return

            embed = discord.Embed(
                title="User Unbanned",
                color=COLOR_GREEN,
                timestamp=datetime.now()
            )
            embed.add_field(name="User", value=f"{user_to_unban.mention} ({user_to_unban.id})", inline=True)
            embed.add_field(name="Director", value=actor.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)

            await ctx.send(embed=embed)

        except discord.NotFound:
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to unban user!**\n"
                f"{user_to_unban.mention} is not currently banned."
            )
        except discord.Forbidden:
            await ctx.send(
                f"{DENIED_EMOJI_ID} **Failed to unban user!**\n"
                f"I lack the necessary permissions to unban members.\n"
                f"-# Contact the owner."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /bans Command
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

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .bans Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

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
            await ctx.send(
                f"{DENIED_EMOJI_ID} **Failed to retrieve ban list!**\n"
                f"I lack the necessary permissions to view bans.\n"
                f"-# Contact the owner."
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(BanCommands(cast(UtilityBot, bot)))
