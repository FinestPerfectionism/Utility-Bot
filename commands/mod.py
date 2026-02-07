import discord
from discord.ext import commands

from core.permissions import has_director_role
from core.utils import (
    send_notice,
    parse_duration
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Moderation Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ~ban/~b Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name="ban",
        aliases=["b"]
    )
    @has_director_role()
    async def ban(self, ctx, member: discord.Member | discord.User):
        await ctx.guild.ban(member, reason=f"Banned by {ctx.author}")
        await send_notice(ctx, "banned", "banning")

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ~kick/~k Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name="kick",
        aliases=["k"]
    )
    @has_director_role()
    async def kick(self, ctx, member: discord.Member):
        await member.kick(reason=f"Kicked by {ctx.author}")
        await send_notice(ctx, "kicked", "kicking")

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ~timeout/~t/~mute/~m Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name="timeout",
        aliases=["t", "mute", "m"])

    @has_director_role()
    async def timeout(self, ctx, member: discord.Member, *, length: str):
        duration = parse_duration(length)
        if duration is None:
            return

        await member.timeout(duration, reason=f"Timed out by {ctx.author}")
        await send_notice(ctx, "muted", "muting", length)

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))