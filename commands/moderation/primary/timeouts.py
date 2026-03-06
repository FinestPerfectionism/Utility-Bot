import discord
from discord.ext import commands
from discord import app_commands

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
from core.permissions import is_director

from constants import (
    COLOR_GREEN,
    COLOR_ORANGE,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,
)

from ._base import (
    ModerationBase,
    KickFlags,
    TimeoutFlags,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Timeout Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class TimeoutCommands(ModerationBase):
    def __init__(self, bot: "UtilityBot"):
        super().__init__(bot)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /timeout Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="timeout", description="Timeout a member.")
    @app_commands.describe(
        member="The member to timeout.",
        duration="Duration.",
        reason="Reason for the timeout.",
        proof="Optional proof attachment."
    )
    async def timeout_slash(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: str,
        proof: Optional[discord.Attachment] = None
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

        if not is_director(actor):
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

            metadata: Dict = {"until": until.isoformat()}
            if proof:
                metadata["proof_url"] = proof.url

            await self.cases_manager.log_case(
                guild=guild,
                case_type=CaseType.TIMEOUT,
                moderator=actor,
                reason=reason,
                target_user=member,
                duration=duration,
                metadata=metadata
            )

            embed = discord.Embed(
                title="Member Timed Out",
                color=COLOR_ORANGE,
                timestamp=datetime.now()
            )
            embed.add_field(name="Member", value=member.mention, inline=True)
            embed.add_field(name="Moderator", value=actor.mention, inline=True)
            embed.add_field(name="Duration", value=duration, inline=True)
            embed.add_field(name="Expires", value=discord.utils.format_dt(until, "R"), inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            if proof:
                embed.set_image(url=proof.url)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await send_major_error(
                interaction,
                "I lack the necessary permissions to timeout this member.",
                subtitle="Invalid configuration. Contact the owner."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .timeout Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="timeout", aliases=["tt", "mute", "m"])
    async def timeout_prefix(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        flags: TimeoutFlags
    ):
        actor = ctx.author
        if not isinstance(actor, discord.Member):
            return

        if not self.can_moderate(actor):
            return

        if not flags.r:
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
                f"Please provide a reason for the timeout."
            )
            return

        if not flags.d:
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
                f"Please provide a duration. Use: 30s, 5m, 1h, 2d, 1w"
            )
            return

        reason = flags.r
        duration = flags.d

        if member.id == actor.id:
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
                f"You cannot timeout yourself."
            )
            return

        can_moderate, error_msg = self.check_can_moderate_target(actor, member)
        if not can_moderate:
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
                f"{error_msg}"
            )
            return

        duration_seconds = self.parse_duration(duration)
        if not duration_seconds:
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
                f"Invalid duration format. Use: 30s, 5m, 1h, 2d, 1w"
            )
            return

        max_duration = 28 * 86400
        if duration_seconds > max_duration:
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
                f"Timeout duration cannot exceed 28 days. You provided: {duration}"
            )
            return

        guild = ctx.guild
        if not guild:
            return

        if not is_director(actor):
            can_proceed, error_msg = self.check_rate_limit(str(actor.id), "timeout")
            if not can_proceed:
                await ctx.send(
                    f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
                    f"Rate limit exceeded. {error_msg}."
                )
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

            if flags.s:
                await ctx.message.delete()
                return

            embed = discord.Embed(
                title="Member Timed Out",
                color=COLOR_ORANGE,
                timestamp=datetime.now()
            )
            embed.add_field(name="Member", value=member.mention, inline=True)
            embed.add_field(name="Moderator", value=actor.mention, inline=True)
            embed.add_field(name="Duration", value=duration, inline=True)
            embed.add_field(name="Expires", value=discord.utils.format_dt(until, "R"), inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)

            await ctx.send(embed=embed)

        except discord.Forbidden:
            await ctx.send(
                f"{DENIED_EMOJI_ID} **Failed to timeout member!**\n"
                f"I lack the necessary permissions to timeout members.\n"
                f"-# Contact the owner."
            )

    @timeout_prefix.error
    async def timeout_prefix_error(self, ctx: commands.Context, error: Exception):
        actor = ctx.author
        if not isinstance(actor, discord.Member) or not self.can_moderate(actor):
            return

        if isinstance(error, commands.MemberNotFound):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
                f"Please provide a valid user to timeout."
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
                f"Please provide a member to timeout."
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
                f"Please provide a valid user to timeout."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /un-timeout Command
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
    # .un-timeout Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="un-timeout", aliases=["untimeout", "utt", "unmute", "um"])
    async def untimeout_prefix(
        self,
        ctx: commands.Context,
        member: discord.Member,
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
                f"{CONTESTED_EMOJI_ID} **Failed to remove timeout!**\n"
                f"Please provide a reason."
            )
            return

        reason = flags.r

        if not member.is_timed_out():
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to remove timeout!**\n"
                f"{member.mention} is not currently timed out."
            )
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

            if flags.s:
                await ctx.message.delete()
                return

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
            await ctx.send(
                f"{DENIED_EMOJI_ID} **Failed to remove timeout!**\n"
                f"I lack the necessary permissions to remove timeouts.\n"
                f"-# Contact the owner."
            )

    @untimeout_prefix.error
    async def untimeout_prefix_error(self, ctx: commands.Context, error: Exception):
        actor = ctx.author
        if not isinstance(actor, discord.Member) or not self.can_unban_untimeout(actor):
            return

        if isinstance(error, commands.MemberNotFound):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to remove timeout!**\n"
                f"Please provide a valid user."
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to remove timeout!**\n"
                f"Please provide a member."
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to remove timeout!**\n"
                f"Please provide a valid user."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /timeouts Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

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
                value = (
                    f"Timed out: {discord.utils.format_dt(timed_out_at, 'R')}\n"
                    f"Expires: {discord.utils.format_dt(member.timed_out_until, 'R')}\n"
                    f"Reason: {reason}"
                )
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
    # .mute-list Command
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
                value = (
                    f"Timed out: {discord.utils.format_dt(timed_out_at, 'R')}\n"
                    f"Expires: {discord.utils.format_dt(member.timed_out_until, 'R')}\n"
                    f"Reason: {reason}"
                )
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
    await bot.add_cog(TimeoutCommands(cast(UtilityBot, bot)))
