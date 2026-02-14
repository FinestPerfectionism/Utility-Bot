import discord
from discord.ext import commands
from discord import app_commands

import json
import os
from typing import Optional
import pytz
from datetime import datetime

from core.utils import (
    send_minor_error,
    send_major_error
)

from constants import (
    BOT_OWNER_ID,

    DIRECTORS_ROLE_ID,
    PERSONAL_LEAVE_ROLE_ID,
    STAFF_ROLE_ID,
)

DATA_FILE = "leave_data.json"
USER_TZ_FILE = "user_timezones.json"

try:
    with open(USER_TZ_FILE, "r") as f:
        user_timezones = json.load(f)
except FileNotFoundError:
    user_timezones = {}

def save_timezones():
    with open(USER_TZ_FILE, "w") as f:
        json.dump(user_timezones, f)

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def is_staff(member: discord.Member):
    return any(role.id == STAFF_ROLE_ID for role in member.roles)

def is_director(member: discord.Member):
    return any(role.id == DIRECTORS_ROLE_ID for role in member.roles)

def extract_name(nickname: str):
    if nickname and "|" in nickname:
        return nickname.split("|")[-1].strip()
    return nickname

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

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Utility Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class UtilityCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_data()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /leave Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    leave_group = app_commands.Group(
        name="leave",
        description="Staff only —— Leave commands."
    )

    @leave_group.command(name="add", description="Add personal leave to yourself or another user.")
    @app_commands.describe(target="The user to add personal leave to.")
    async def leave_add(
        self,
        interaction: discord.Interaction,
        target: discord.Member | None = None
    ):
        if not interaction.guild:
            await send_minor_error(
                interaction,
                "This command can only be used in a server.",
                subtitle="Bad command environment."
            )
            return

        invocator = interaction.user
        if not isinstance(invocator, discord.Member):
            return

        target_member = target or invocator

        if target_member.bot:
            await send_minor_error(
                interaction,
                "Bots cannot go on personal leave.",
            )
            return

        if not is_staff(invocator):
            await send_minor_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to run this command.",
                subtitle="No permissions."
            )
            return

        if not is_staff(target_member):
            await send_minor_error(
                interaction,
                "Target must exist within the Goobers Staff Team.",
            )
            return

        if not is_director(invocator):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to add personal leave to Staff Members.",
                subtitle="No permissions."
            )
            return

        role = interaction.guild.get_role(PERSONAL_LEAVE_ROLE_ID)
        if role is None:
            await send_major_error(
                interaction,
                "I could not fetch the Personal Leave role.",
                subtitle=f"Invalid Configuration. Contact an administrator and <@{BOT_OWNER_ID}>."
            )
            return

        original_nick = target_member.nick or target_member.name
        self.data[str(target_member.id)] = original_nick
        save_data(self.data)

        await target_member.add_roles(role)

        new_nick = f"P. Leave | {original_nick}"

        try:
            await target_member.edit(nick=new_nick)
        except Exception:
            await send_major_error(
                interaction,
                "I couldn't edit the nickname. This is likely a length issue of the username, but it may be a permission issue.",
                subtitle="Potentially invalid configuration. Contact the owner."
            )
            return

        await interaction.response.send_message(
            f"{target_member.mention} has been placed on personal leave.",
            ephemeral=True
        )

    @leave_group.command(name="remove", description="Remove personal leave from yourself or another user.")
    @app_commands.describe(target="The user to remove personal leave from.")
    async def leave_remove(
        self,
        interaction: discord.Interaction,
        target: discord.Member | None = None
    ):
        if not interaction.guild:
            await send_minor_error(
                interaction,
                "This command can only be used in a server.",
                subtitle="Bad command environment."
            )
            return

        invocator = interaction.user
        if not isinstance(invocator, discord.Member):
            return

        target_member = target or invocator

        if target_member.bot:
            await send_minor_error(
                interaction,
                "Bots cannot go on personal leave.",
            )
            return

        if target and not is_director(invocator):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to remove personal leave from Staff Members.",
                subtitle="No permissions."
            )
            return

        stored_name = self.data.get(str(target_member.id))
        if not stored_name:
            await send_minor_error(
                interaction,
                "User is not on personal leave.",
            )
            return

        role = interaction.guild.get_role(PERSONAL_LEAVE_ROLE_ID)
        if role is None:
            await send_major_error(
                interaction,
                "I could not fetch the Personal Leave role.",
                subtitle=f"Invalid Configuration. Contact an administrator and <@{BOT_OWNER_ID}>."
            )
            return

        await target_member.remove_roles(role)

        try:
            await target_member.edit(nick=stored_name)
        except Exception:
            await send_major_error(
                interaction,
                "I couldn't restore the nickname.",
                subtitle="Invalid configuration. Contact the owner."
            )
            return

        self.data.pop(str(target_member.id), None)
        save_data(self.data)

        await interaction.response.send_message(
            f"{target_member.mention} has been removed from personal leave.",
            ephemeral=True
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

async def setup(bot):
    await bot.add_cog(UtilityCommands(bot))