import discord
from discord.ext import commands
from discord import app_commands

import contextlib
from datetime import datetime
from typing import Literal

from constants import (
    COLOR_GREEN,
    COLOR_BLURPLE,
    DIRECTORS_ROLE_ID,
    SENIOR_MODERATORS_ROLE_ID,
    MODERATORS_ROLE_ID,
    ADMINISTRATORS_ROLE_ID,
)
from core.utils import (
    send_minor_error,
    send_major_error,
)
from core.permissions import (
    is_administrator,
    is_director,
    is_moderator,
)
from core.cases import (
    CaseType,
    CasesManager
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Cases Cog
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class CasesCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.cases_manager = CasesManager(bot)

        self.DIRECTORS_ROLE_ID = DIRECTORS_ROLE_ID
        self.SENIOR_MODERATORS_ROLE_ID = SENIOR_MODERATORS_ROLE_ID
        self.MODERATORS_ROLE_ID = MODERATORS_ROLE_ID
        self.ADMINISTRATORS_ROLE_ID = ADMINISTRATORS_ROLE_ID

    def can_view(self, member: discord.Member) -> bool:
        return (
            is_director(member)
            or is_administrator(member)
            or is_moderator(member)
        )

    def can_configure(self, member: discord.Member) -> bool:
        return is_director(member)

    cases_group = app_commands.Group(
        name="cases",
        description="Moderators only —— Cases management."
    )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /cases view
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @cases_group.command(name="view", description="View moderation cases with filters.")
    @app_commands.describe(
        user      = "Filter by user.",
        moderator = "Filter by moderator.",
        case_type = "Filter by case type."
    )
    @app_commands.rename(case_type="case-type")
    async def cases_view(
        self,
        interaction: discord.Interaction,
        user:        discord.User | None = None,
        moderator:   discord.User | None = None,
        case_type:   Literal[
            "ban", "unban", "kick", "timeout", "untimeout",
            "quarantine", "unquarantine", "lockdown", "unlockdown", "purge"
        ]                         | None = None
    ) -> None:
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_view(actor):
            await send_major_error(
                interaction,
                title    = "Unauthorized!",
                texts    = "You lack the necessary permissions to view cases.",
                subtitle = "Invalid permissions."
            )
            return

        guild = interaction.guild
        if not guild:
            return

        if case_type == "purge" and user is not None:
            await send_minor_error(
                interaction,
                texts = "You cannot filter purge cases by user. Purge actions affect channels, not individual users."
            )
            return

        await interaction.response.defer(ephemeral=True)

        type_mapping = {
            "ban"          : CaseType.BAN.value,
            "unban"        : CaseType.UNBAN.value,
            "kick"         : CaseType.KICK.value,
            "timeout"      : CaseType.TIMEOUT.value,
            "untimeout"    : CaseType.UNTIMEOUT.value,
            "quarantine"   : CaseType.QUARANTINE_ADD.value,
            "unquarantine" : CaseType.QUARANTINE_REMOVE.value,
            "lockdown"     : CaseType.LOCKDOWN_ADD.value,
            "unlockdown"   : CaseType.LOCKDOWN_REMOVE.value,
            "purge"        : CaseType.PURGE.value,
        }

        internal_case_type = type_mapping.get(case_type) if case_type else None

        cases = self.cases_manager.get_cases(
            guild_id     = guild.id,
            user_id      = user.id if user else None,
            moderator_id = moderator.id if moderator else None,
            case_type    = internal_case_type
        )

        if not cases:
            filters: list[str] = []
            if user:
                filters.append(f"user {user.mention}")
            if moderator:
                filters.append(f"moderator {moderator.mention}")
            if case_type:
                filters.append(f"type **{case_type}**")

            filter_text = " and ".join(filters) if filters else ""
            description = f"No cases found{' for ' + filter_text if filter_text else ''}."

            embed = discord.Embed(description=description, color=COLOR_GREEN)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        title_parts: list[str] = []
        if user:
            title_parts.append(f"for {user.name}")
        if moderator:
            title_parts.append(f"by {moderator.name}")
        if case_type:
            title_parts.append(f"({case_type})")

        title = "Cases " + " ".join(title_parts) if title_parts else "All Cases"

        embed = discord.Embed(
            title     = title,
            color     = COLOR_BLURPLE,
            timestamp = datetime.now()
        )

        for case in cases[:25]:
            case_type_display = case["type"].replace("_", " ").title()
            timestamp = datetime.fromisoformat(case["timestamp"])

            value_parts: list[str] = []
            value_parts.append(f"**Type:** {case_type_display}")

            if case.get("target_user_id"):
                with contextlib.suppress(discord.NotFound, discord.HTTPException):
                    target = await self.bot.fetch_user(case["target_user_id"])
                    value_parts.append(f"**User:** {target.mention}")

                if not any(p.startswith("**User:**") for p in value_parts):
                    value_parts.append(f"**User:** {case['target_user_name']} ({case['target_user_id']})")

            with contextlib.suppress(discord.NotFound, discord.HTTPException):
                mod = await self.bot.fetch_user(case["moderator_id"])
                value_parts.append(f"**Moderator:** {mod.mention}")

            if not any(p.startswith("**Moderator:**") for p in value_parts):
                value_parts.append(f"**Moderator:** {case['moderator_name']}")

            if case.get("duration"):
                value_parts.append(f"**Duration:** {case['duration']}")

            value_parts.append(f"**Reason:** {case['reason']}")
            value_parts.append(f"**When:** {discord.utils.format_dt(timestamp, 'R')}")

            embed.add_field(
                name=f"Case #{case['case_id']}",
                value="\n".join(value_parts),
                inline=False
            )

        if len(cases) > 25:
            embed.set_footer(text=f"Showing 25 of {len(cases)} cases")

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /cases config
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @cases_group.command(name="config", description="Configure the cases log channel.")
    @app_commands.describe(channel="The channel where case logs will be sent.")
    async def cases_config(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ) -> None:
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_configure(actor):
            await send_major_error(
                interaction,
                title    = "Unauthorized!",
                texts    = "You lack the necessary permissions to configure cases.",
                subtitle = "Invalid permissions."
            )
            return

        self.cases_manager.config["log_channel_id"] = channel.id
        self.cases_manager.save_config()

        await interaction.response.send_message(
            f"Case logs will now be sent to {channel.mention}.",
            ephemeral = True
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CasesCommands(bot))