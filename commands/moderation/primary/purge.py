import discord
from discord.ext import commands
from discord import app_commands

from datetime import datetime
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

from constants import (
    COLOR_BLURPLE,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,
)

from ._base import (
    ModerationBase,
    PurgeFlags,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Purge Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class PurgeCommands(ModerationBase):
    def __init__(self, bot: "UtilityBot"):
        super().__init__(bot)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /purge Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="purge", description="Delete a specified number of messages.")
    @app_commands.describe(
        amount="Number of messages to delete.",
        member="Only delete messages from this member.",
        reason="Reason for purging messages.",
        proof="Optional proof attachment."
    )
    async def purge_slash(
        self,
        interaction: discord.Interaction,
        amount: int,
        reason: str,
        member: Optional[discord.Member] = None,
        proof: Optional[discord.Attachment] = None
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

            metadata: Dict = {
                "deleted_messages": len(deleted),
                "channel_id": channel.id
            }
            if proof:
                metadata["proof_url"] = proof.url

            await self.cases_manager.log_case(
                guild=guild,
                case_type=CaseType.PURGE,
                moderator=actor,
                reason=reason,
                target_user=member if member else None,
                metadata=metadata
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
            if proof:
                embed.set_image(url=proof.url)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await send_major_error(
                interaction,
                "I lack the necessary permissions to delete messages.",
                subtitle="Invalid configuration. Contact the owner."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .purge Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

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
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to purge messages!**\n"
                f"Amount must be between 1 and 100."
            )
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
                deleted = await channel.purge(limit=amount, before=ctx.message)

            await ctx.message.delete()

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

            if flags.s:
                return

            embed = discord.Embed(
                title="Messages Purged",
                color=COLOR_BLURPLE,
                timestamp=datetime.now()
            )
            embed.add_field(name="Deleted", value=str(len(deleted)), inline=True)
            embed.add_field(name="Moderator", value=actor.mention, inline=True)
            if member:
                embed.add_field(name="From User", value=member.mention, inline=True)

            await ctx.send(embed=embed)

        except discord.Forbidden:
            await ctx.send(
                f"{DENIED_EMOJI_ID} **Failed to purge messages!**\n"
                f"I lack the necessary permissions to delete messages.\n"
                f"-# Contact the owner."
            )

    @purge_prefix.error
    async def purge_prefix_error(self, ctx: commands.Context, error: Exception):
        actor = ctx.author
        if not isinstance(actor, discord.Member) or not self.can_moderate(actor):
            return

        if isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == "amount":
                await ctx.send(
                    f"{CONTESTED_EMOJI_ID} **Failed to purge messages!**\n"
                    f"Please provide the number of messages to delete."
                )
            else:
                await ctx.send(
                    f"{CONTESTED_EMOJI_ID} **Failed to purge messages!**\n"
                    f"Please provide all required arguments."
                )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to purge messages!**\n"
                f"Please provide a valid number of messages to delete."
            )
        elif isinstance(error, commands.MissingFlagArgument):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to purge messages!**\n"
                f"Please provide a reason using `/r <reason>`."
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(PurgeCommands(cast(UtilityBot, bot)))
