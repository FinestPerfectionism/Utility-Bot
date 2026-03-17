from __future__ import annotations

import discord
from discord.ext import commands

import asyncio
import contextlib
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._base import (
        ModerationBase,
    
        UnbanFlags
    )

from commands.moderation.cases import CaseType

from core.utils import (
    send_major_error,
    send_minor_error
)

from constants import (
    COLOR_GREEN,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation un-ban Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_unban(
    base:        "ModerationBase",
    interaction: discord.Interaction,
    user:        str,
    reason:      str,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_unban_untimeout(actor):
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

    user_to_unban: discord.User | None = None

    if user.isdigit():
        with contextlib.suppress(discord.NotFound):
            user_to_unban = await base.bot.fetch_user(int(user))

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

        if "bans" in base.data and str(user_to_unban.id) in base.data["bans"]:
            del base.data["bans"][str(user_to_unban.id)]
            base.save_data()

        await base.cases_manager.log_case(
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
        embed.add_field(name="User",     value=f"{user_to_unban.mention} ({user_to_unban.id})", inline=True)
        embed.add_field(name="Director", value=actor.mention,                                   inline=True)
        embed.add_field(name="Reason",   value=reason,                                          inline=False)

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
# .un-ban Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_unban_prefix(
    base:  "ModerationBase",
    ctx:   commands.Context[commands.Bot],
    user:  str,
    flags: UnbanFlags,
) -> None:
    actor = ctx.author
    if not isinstance(actor, discord.Member):
        return

    if not base.can_unban_untimeout(actor):
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

    user_to_unban: discord.User | None = None

    if user.isdigit():
        with contextlib.suppress(discord.NotFound):
            user_to_unban = await base.bot.fetch_user(int(user))

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

        if "bans" in base.data and str(user_to_unban.id) in base.data["bans"]:
            del base.data["bans"][str(user_to_unban.id)]
            base.save_data()

        await base.cases_manager.log_case(
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
        embed.add_field(name="User",     value=f"{user_to_unban.mention} ({user_to_unban.id})", inline=True)
        embed.add_field(name="Director", value=actor.mention,                                   inline=True)
        embed.add_field(name="Reason",   value=reason,                                          inline=False)

        msg = await ctx.send(embed=embed)
        await asyncio.sleep(10)
        with contextlib.suppress(discord.NotFound):
            await msg.delete()

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
