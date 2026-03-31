from datetime import datetime
from typing import TYPE_CHECKING, cast

import discord
from discord.ext import commands

from constants import GOOBERS_ROLE_ID, STAFF_ROLE_ID
from core.help import (
    ArgumentInfo,
    RoleConfig,
    help_description,
)

if TYPE_CHECKING:
    from events.member.verification import VerificationHandler

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Verification Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class VerificationCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.GOOBERS_ROLE_ID = GOOBERS_ROLE_ID

    def _get_verification_cog(self) -> "VerificationHandler | None":
        return cast("VerificationHandler", self.bot.get_cog("VerificationHandler"))

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .verify/.v Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name = "verify", aliases=["v"])
    @help_description(
        desc="Staff only —— Manually verifies a member inside the server.",
        prefix=True,
        slash=False,
        run_roles=[RoleConfig(role_id=STAFF_ROLE_ID)],
        aliases=["v"],
        arguments={"member": ArgumentInfo(description="Member to verify.")},
    )
    async def manual_verify(self, ctx: commands.Context[commands.Bot], member: discord.Member) -> None:
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return
        if not any(role.id == STAFF_ROLE_ID for role in ctx.author.roles):
            return

        goobers_role = ctx.guild.get_role(self.GOOBERS_ROLE_ID)
        if not goobers_role or goobers_role in member.roles:
            return

        try:
            await member.add_roles(
                goobers_role,
                reason=f"Manual verification by {ctx.author}",
            )
            verification_cog = self._get_verification_cog()
            if verification_cog and str(member.id) in verification_cog.data["unverified"]:
                del verification_cog.data["unverified"][str(member.id)]
                verification_cog.save_data()
        except discord.Forbidden:
            return

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            return

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .un-verify Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.guild_only()
    @commands.command(
        name = "unverify",
        aliases=["un-verify", "uv", "deverify", "de-verify", "dv"],
    )
    @help_description(
        desc="Staff only —— Manually unverifies a member inside the server.",
        prefix=True,
        slash=False,
        run_roles=[RoleConfig(role_id=STAFF_ROLE_ID)],
        aliases=["un-verify", "uv", "deverify", "de-verify", "dv"],
        arguments={"member": ArgumentInfo(description="Member to unverify.")},
    )
    async def unverify(self, ctx: commands.Context[commands.Bot], member: discord.Member) -> None:
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return
        if not any(role.id == STAFF_ROLE_ID for role in ctx.author.roles):
            return

        goobers_role = ctx.guild.get_role(self.GOOBERS_ROLE_ID)
        if not goobers_role or goobers_role not in member.roles:
            return

        try:
            await member.remove_roles(
                goobers_role,
                reason=f"Manual de-verification by {ctx.author}",
            )
            verification_cog = self._get_verification_cog()
            if verification_cog:
                verification_cog.data["unverified"][str(member.id)] = {
                    "joined_at": datetime.now().isoformat(),
                    "warned": False,
                    "warning_message_id": None,
                }
                verification_cog.save_data()
        except discord.Forbidden:
            return

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            return

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VerificationCommands(bot))
