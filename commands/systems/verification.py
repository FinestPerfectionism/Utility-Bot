import discord
from discord.ext import commands

from datetime import datetime

from constants import GOOBERS_ROLE_ID, STAFF_ROLE_ID

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Verification Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class VerificationCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.GOOBERS_ROLE_ID = GOOBERS_ROLE_ID
        self.data = {"unverified": {}}

    def save_data(self):
        pass

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ~verify/v Commands
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.guild_only()
    @commands.command(name="verify", aliases=["v"])
    async def manual_verify(self, ctx: commands.Context, member: discord.Member):
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
                reason=f"Manual verification by {ctx.author}"
            )

            if str(member.id) in self.data["unverified"]:
                del self.data["unverified"][str(member.id)]
                self.save_data()

        except discord.Forbidden:
            return

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            return

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ~un-verify/uv Commands
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.guild_only()
    @commands.command(
        name="unverify",
        aliases=["un-verify", "uv", "deverify", "de-verify", "dv"]
    )
    async def unverify(self, ctx: commands.Context, member: discord.Member):
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
                reason=f"Manual de-verification by {ctx.author}"
            )

            self.data["unverified"][str(member.id)] = {
                "joined_at": datetime.now().isoformat(),
                "warned": False,
                "warning_message_id": None
            }
            self.save_data()

        except discord.Forbidden:
            return

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            return

async def setup(bot: commands.Bot):
    await bot.add_cog(VerificationCommands(bot))