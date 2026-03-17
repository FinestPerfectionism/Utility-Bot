import discord
from discord.ext import commands

import asyncio
import contextlib
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any
)

if TYPE_CHECKING:
    from ._base import ModerationBase, PurgeFlags

from commands.moderation.cases import CaseType

from core.utils import (
    send_major_error,
    send_minor_error
)

from constants import (
    COLOR_BLURPLE,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation purge Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_purge(
    base:        "ModerationBase",
    interaction: discord.Interaction,
    amount:      int,
    reason:      str,
    member:      discord.Member | None = None,
    proof:       discord.Attachment | None = None,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_moderate(actor):
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

        metadata: dict[str, Any] = {
            "deleted_messages": len(deleted),
            "channel_id":       channel.id
        }

        if proof:
            metadata["proof_url"] = proof.url

        await base.cases_manager.log_case(
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
        embed.add_field(name="Deleted",   value=str(len(deleted)), inline=True)
        embed.add_field(name="Moderator", value=actor.mention,     inline=True)
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
# .purge Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_purge_prefix(
    base:   "ModerationBase",
    ctx:    commands.Context[commands.Bot],
    amount: int,
    flags:  "PurgeFlags",
) -> None:
    actor = ctx.author
    if not isinstance(actor, discord.Member):
        return

    if not base.can_moderate(actor):
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

        await base.cases_manager.log_case(
            guild=guild,
            case_type=CaseType.PURGE,
            moderator=actor,
            reason=flags.r,
            target_user=member if member else None,
            metadata={
                "deleted_messages": len(deleted),
                "channel_id":       channel.id
            }
        )

        if flags.s:
            return

        embed = discord.Embed(
            title="Messages Purged",
            color=COLOR_BLURPLE,
            timestamp=datetime.now()
        )
        embed.add_field(name="Deleted",   value=str(len(deleted)), inline=True)
        embed.add_field(name="Moderator", value=actor.mention,     inline=True)
        if member:
            embed.add_field(name="From User", value=member.mention, inline=True)

        msg = await ctx.send(embed=embed)
        await asyncio.sleep(10)
        with contextlib.suppress(discord.NotFound):
            await msg.delete()

    except discord.Forbidden:
        await ctx.send(
            f"{DENIED_EMOJI_ID} **Failed to purge messages!**\n"
            f"I lack the necessary permissions to delete messages.\n"
            f"-# Contact the owner."
        )
