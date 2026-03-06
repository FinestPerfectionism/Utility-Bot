import discord
from discord.ext import commands
from discord import app_commands

from datetime import datetime
from typing import (
    TYPE_CHECKING,
    cast
)

from commands.moderation.cases import CaseType

if TYPE_CHECKING:
    from bot import UtilityBot

from core.utils import (
    send_major_error,
    send_minor_error
)
from core.permissions import is_director

from constants import (
    COLOR_ORANGE,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,
)

from ._base import (
    ModerationBase,
    KickFlags,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Kick Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class KickCommands(ModerationBase):
    def __init__(self, bot: "UtilityBot") -> None:
        super().__init__(bot)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /kick Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(
        member="The member to kick.",
        reason="Reason for the kick.",
        proof="Optional proof attachment."
    )
    async def kick_slash(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
        proof: discord.Attachment | None = None
    ) -> None:
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

        if not is_director(actor):
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

            metadata: dict = {}
            if proof:
                metadata["proof_url"] = proof.url

            await self.cases_manager.log_case(
                guild=guild,
                case_type=CaseType.KICK,
                moderator=actor,
                reason=reason,
                target_user=member,
                metadata=metadata if metadata else None
            )

            embed = discord.Embed(
                title="Member Kicked",
                color=COLOR_ORANGE,
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
                "I lack the necessary permissions to kick this member.",
                subtitle="Invalid configuration. Contact the owner."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .kick Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="kick", aliases=["k"])
    async def kick_prefix(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        flags: KickFlags
    ) -> None:
        actor = ctx.author
        if not isinstance(actor, discord.Member):
            return

        if not self.can_moderate(actor):
            return

        if not flags.r:
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to kick member!**\n"
                f"Please provide a reason for the kick."
            )
            return

        reason = flags.r

        if member.id == actor.id:
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to kick member!**\n"
                f"You cannot kick yourself."
            )
            return

        can_moderate, error_msg = self.check_can_moderate_target(actor, member)
        if not can_moderate:
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to kick member!**\n"
                f"{error_msg}"
            )
            return

        guild = ctx.guild
        if not guild:
            return

        if not is_director(actor):
            can_proceed, error_msg = self.check_rate_limit(str(actor.id), "kick")
            if not can_proceed:
                await ctx.send(
                    f"{CONTESTED_EMOJI_ID} **Failed to kick member!**\n"
                    f"Rate limit exceeded. {error_msg}."
                )
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

            if flags.s:
                await ctx.message.delete()
                return

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
            await ctx.send(
                f"{DENIED_EMOJI_ID} **Failed to kick member!**\n"
                f"I lack the necessary permissions to kick members.\n"
                f"-# Contact the owner."
            )

    @kick_prefix.error
    async def kick_prefix_error(self, ctx: commands.Context, error: Exception) -> None:
        actor = ctx.author
        if not isinstance(actor, discord.Member) or not self.can_moderate(actor):
            return

        if isinstance(error, commands.MemberNotFound):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to kick member!**\n"
                f"Please provide a valid user to kick."
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to kick member!**\n"
                f"Please provide a member to kick."
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to kick member!**\n"
                f"Please provide a valid user to kick."
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(KickCommands(cast("UtilityBot", bot)))
