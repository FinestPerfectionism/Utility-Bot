import discord
from discord.ext import commands
from discord import app_commands

from datetime import datetime
import pytz
import json
import random
from typing import Optional

from core.utils import send_minor_error

from constants import (
    DIRECTORS_ROLE_ID,

    BOT_OWNER_ID,
    HOLY_FATHER_ID,

    CAT_SHOOT_EMOJI_ID
)

USER_TZ_FILE = "user_timezones.json"

try:
    with open(USER_TZ_FILE, "r") as f:
        user_timezones = json.load(f)
except FileNotFoundError:
    user_timezones = {}

def save_timezones():
    with open(USER_TZ_FILE, "w") as f:
        json.dump(user_timezones, f)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Miscellaneous Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class Ping(discord.ui.LayoutView):
    def __init__(self, ping: int):
        super().__init__()

        self.add_item(
            discord.ui.TextDisplay(content="# I HAVE BEEN AWAKENEDDDD.")
        )
        self.add_item(
            discord.ui.Separator(
                visible=True,
                spacing=discord.SeparatorSpacing.small
            )
        )
        self.add_item(
            discord.ui.TextDisplay(
                content=f"*cough cough* My ping is {ping} milliseconds."
            )
        )

class MiscCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /femboy Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="femboy",
        description="Such a good little utility kitten."
    )
    async def femboy(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(
            "i-i'm such a submissive wittle kitty UwU. *snuggles* I hewp cwose proposals... naa~~"
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ~super_secret_command Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name="super_secret_command"
    )
    async def super_secret_command(self, ctx: commands.Context):
        author_id = ctx.author.id

        if author_id == BOT_OWNER_ID:
            await ctx.send(
                "This is a super super secret command that is used by people that will use it super super secretly."
            )
            return

        if author_id == HOLY_FATHER_ID:
            await ctx.send(
                "Hello daddy! <:puppy3:1464256700344303771> This is a super super secret command that is used by people that will use it super super secretly."
            )
            return

        await ctx.send(
            "Hmm… I don’t think you’re super super secret enough to use this super super secret command."
        ) 

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ~ping Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name="ping"
    )
    async def ping(self, ctx: commands.Context):
        latency_ms = round(self.bot.latency * 1000)
        await ctx.send(
            view=Ping(latency_ms)
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /roulette Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="roulette",
        description="Have fun..."
    )
    async def roulette(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user

        if guild is None:
            await send_minor_error(
                interaction,
                "This command can only be used in a server.",
                subtitle="Bad command environment."
            )
            return

        await interaction.response.defer(ephemeral=False)

        chamber = random.randint(1, 6)

        if chamber == 1:
            try:
                await guild.ban(
                    member,
                    reason="Played a stupid game, won a stupid prize."
                )
                await interaction.followup.send(
                    f"{CAT_SHOOT_EMOJI_ID} *Click,* ***BAM***."
                )
            except discord.Forbidden:
                await interaction.followup.send(
                    "*Click,* ***Ba***… wait… the gun’s jammed!"
                )
        else:
            await interaction.followup.send(
                "*Click.* You live."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ~ti Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="ti")
    async def timezone(self, ctx: commands.Context, action: Optional[str] = None, user: Optional[discord.Member] = None, tz: Optional[str] = None):
        if action == "set":
            if not tz:
                await ctx.send("Usage: `~ti set {user} {timezone}` or `~ti set {timezone}` for yourself")
                return
            if user is None:
                try:
                    pytz.timezone(tz)
                except Exception:
                    await ctx.send(f"`{tz}` is not a valid timezone.")
                    return
                user_timezones[str(ctx.author.id)] = tz
                save_timezones()
                await ctx.send(f"Your timezone has been set to **{tz}**.")
                return
            if isinstance(ctx.author, discord.Member) and DIRECTORS_ROLE_ID in [role.id for role in ctx.author.roles]:
                try:
                    pytz.timezone(tz)
                except Exception:
                    await ctx.send(f"`{tz}` is not a valid timezone.")
                    return
                user_timezones[str(user.id)] = tz
                save_timezones()
                await ctx.send(f"Timezone for {user.mention} set to **{tz}**.")
            return

        target_user = ctx.author
        if ctx.message.reference:
            replied = ctx.message.reference.resolved
            if isinstance(replied, discord.Message) and isinstance(replied.author, discord.Member):
                target_user = replied.author

        tz_target = user_timezones.get(str(target_user.id))
        tz_author = user_timezones.get(str(ctx.author.id))

        if tz_target:
            time_target = datetime.now(pytz.timezone(tz_target)).strftime("%H:%M")
            if tz_author:
                dt_target = datetime.now(pytz.timezone(tz_target))
                dt_author = datetime.now(pytz.timezone(tz_author))
                diff_hours = round((dt_target - dt_author).total_seconds() / 3600)
                if diff_hours == 0:
                    message = f"It is **{time_target}** for {target_user.mention}. Their timezone is **{tz_target}**, the same timezone as you!"
                elif diff_hours > 0:
                    message = f"It is **{time_target}** for {target_user.mention}. Their timezone is **{tz_target}**, {diff_hours} hours ahead of you."
                else:
                    message = f"It is **{time_target}** for {target_user.mention}. Their timezone is **{tz_target}**, {abs(diff_hours)} hours behind you."
            else:
                message = f"It is **{time_target}** for {target_user.mention}. Their timezone is **{tz_target}**."
        else:
            message = f"{target_user.mention} does not have a timezone set."

        await ctx.send(message)

async def setup(bot: commands.Bot):
    cog = MiscCommands(bot)
    await bot.add_cog(cog)