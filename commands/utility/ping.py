import discord
from discord.ext import commands

import logging

from constants import (
    STAFF_PROPOSALS_CHANNEL_ID,
    DIRECTORS_ROLE_ID,
    STAFF_COMMITTEE_ROLE_ID,
    STAFF_ROLE_ID,
    SENIOR_ADMINISTRATORS_ROLE_ID,
    ADMINISTRATORS_ROLE_ID,
    SENIOR_MODERATORS_ROLE_ID,
    MODERATORS_ROLE_ID,
)

log = logging.getLogger("Utility Bot")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Ping Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class PingCommands(commands.Cog, name="ping"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _check_and_ping(self, ctx: commands.Context[commands.Bot], required_role_id: int, ping_role_id: int) -> None:
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return

        require_role = ctx.guild.get_role(required_role_id)
        target_role = ctx.guild.get_role(ping_role_id)

        if require_role and target_role and require_role in ctx.author.roles:
            try:
                await ctx.send(target_role.mention)
            except Exception as e:
                log.error(f"Failed to ping role {ping_role_id}: {e}")

    @commands.group(name="ping", invoke_without_command=True)
    async def ping_group(self, ctx: commands.Context[commands.Bot]) -> None:
        return

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .ping staff Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @ping_group.command(
        name="staff",
        aliases=[
            "s",
            "stf"
        ]
    )
    async def ping_staff(self, ctx: commands.Context[commands.Bot]) -> None:
        await self._check_and_ping(ctx, STAFF_ROLE_ID, STAFF_ROLE_ID)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .ping senior-moderators Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @ping_group.command(
        name="senior-moderators",
        aliases=[
                                 "senior-mods", "senior-mod", "s-mods", "s-mod", "s-m",
            "senior_moderators", "senior_mods", "senior_mod", "s_mods", "s_mod", "s_m",
            "seniormoderators" , "seniormods" , "seniormod" , "smods" , "smod" , "sm"
        ]
    )
    async def ping_senior_moderators(self, ctx: commands.Context[commands.Bot]) -> None:
        await self._check_and_ping(ctx, MODERATORS_ROLE_ID, SENIOR_MODERATORS_ROLE_ID)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .ping senior-administrators Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @ping_group.command(
        name="senior-administrators",
        aliases=[
                                     "senior-admins", "senior-admin", "s-admins", "s-admin", "s-a",
            "senior_administrators", "senior_admins", "senior_admin", "s_admins", "s_admin", "s_a",
            "senioradministrators" , "senioradmins" , "senioradmin" , "sadmins" , "sadmin" , "sa"
        ]
    )
    async def ping_senior_administrators(self, ctx: commands.Context[commands.Bot]) -> None:
        await self._check_and_ping(ctx, ADMINISTRATORS_ROLE_ID, SENIOR_ADMINISTRATORS_ROLE_ID)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .ping directors Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @ping_group.command(
        name="directors",
        aliases=[
            "director",
            "dir",
            "d"
        ]
    )
    async def ping_directors(self, ctx: commands.Context[commands.Bot]) -> None:
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return

        directors = ctx.guild.get_role(DIRECTORS_ROLE_ID)
        s_admins = ctx.guild.get_role(SENIOR_ADMINISTRATORS_ROLE_ID)
        s_mods = ctx.guild.get_role(SENIOR_MODERATORS_ROLE_ID)

        if directors and ((s_admins and s_admins in ctx.author.roles) or (s_mods and s_mods in ctx.author.roles)):
            await ctx.send(directors.mention)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .ping staff-committee Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @ping_group.command(
        name="staff-committee",
        aliases=[
                               "s-committee", "s-c",
            "staff_committee", "s_committee", "s_c",
            "staffcommittee" , "scommittee" , "sc",
            "committee"      , "com"
        ]
    )
    async def ping_committee(self, ctx: commands.Context[commands.Bot]) -> None:
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return

        committee = ctx.guild.get_role(STAFF_COMMITTEE_ROLE_ID)
        staff = ctx.guild.get_role(STAFF_ROLE_ID)

        if not committee or not staff:
            return

        is_in_valid_thread = (
            isinstance(ctx.channel, discord.Thread) and 
            ctx.channel.parent_id == STAFF_PROPOSALS_CHANNEL_ID
        )

        if committee in ctx.author.roles or (staff in ctx.author.roles and is_in_valid_thread):
            await ctx.send(committee.mention)

async def setup(bot: commands.Bot) -> None:
    cog = PingCommands(bot)
    await bot.add_cog(cog)