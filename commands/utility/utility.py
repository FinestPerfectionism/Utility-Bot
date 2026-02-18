import discord
from discord.ext import commands
from discord import app_commands

import json
import os
from typing import Optional, cast
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
        json.dump(data, f, indent=2)

def is_staff(member: discord.Member):
    return any(role.id == STAFF_ROLE_ID for role in member.roles)

def is_director(member: discord.Member):
    return any(role.id == DIRECTORS_ROLE_ID for role in member.roles)

def extract_name(nickname: str):
    if nickname and "|" in nickname:
        return nickname.split("|")[-1].strip()
    return nickname

def can_manage_leave(invocator: discord.Member, target: discord.Member):
    if not is_staff(invocator):
        return False

    modifying_other = target.id != invocator.id

    if modifying_other:
        return is_director(invocator)

    return True

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

        await interaction.response.defer(ephemeral=True)

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
            await send_major_error(
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

        if not can_manage_leave(invocator, target_member):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to add personal leave to other Staff Members.",
                subtitle="No permissions."
            )
            return

        if str(target_member.id) in self.data:
            await send_minor_error(
                interaction,
                "User is already on personal leave.",
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

        if role in target_member.roles:
            await send_minor_error(
                interaction,
                "User already has the Personal Leave role.",
            )
            return

        original_full_nick = target_member.nick or target_member.name
        actual_name = extract_name(original_full_nick)
        new_nick = f"P. Leave | {actual_name}"

        if len(new_nick) > 32:
            await send_minor_error(
                interaction,
                title="Error!",
                texts="The resulting nickname exceeds Discord's 32 character limit.",
                subtitle="Invalid operation."
            )
            return

        role_added = False
        nick_changed = False

        try:
            await target_member.add_roles(role)
            role_added = True

            await target_member.edit(nick=new_nick)
            nick_changed = True

            self.data[str(target_member.id)] = original_full_nick
            save_data(self.data)

            if target_member.id == interaction.user.id:
                await interaction.followup.send(
                    "You have been placed on personal leave.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"{target_member.mention} has been placed on personal leave.",
                    ephemeral=True
                )

        except discord.Forbidden:
            if role_added:
                try:
                    await target_member.remove_roles(role)
                except discord.HTTPException:
                    pass

            if not role_added:
                await send_major_error(
                    interaction,
                    title="Error!",
                    texts="I lack the necessary permissions to assign the Personal Leave role.",
                    subtitle="Invalid configuration. Contact the owner."
                )
            elif not nick_changed:
                if target_member.id == interaction.guild.owner_id:
                    await send_minor_error(
                        interaction,
                        title="Error!",
                        texts="The role was added, but I cannot change the server owner's nickname. Please change it manually.",
                    )
                else:
                    await send_major_error(
                        interaction,
                        title="Error!",
                        texts="I lack the necessary permissions to change this user's nickname.",
                        subtitle="Invalid configuration. Contact the owner."
                    )
            return

        except discord.HTTPException:
            if role_added:
                try:
                    await target_member.remove_roles(role)
                except discord.HTTPException:
                    pass

            await send_major_error(
                interaction,
                title="Error!",
                texts="A Discord API error occurred. Please try again later.",
                subtitle=f"Invalid operation. Contact <@{BOT_OWNER_ID}> if this persists."
            )
            return

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

        await interaction.response.defer(ephemeral=True)

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
            await send_major_error(
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

        if not can_manage_leave(invocator, target_member):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to remove personal leave from other Staff Members.",
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
                title="Error!",
                texts="I could not fetch the Personal Leave role.",
                subtitle=f"Invalid configuration. Contact an administrator and <@{BOT_OWNER_ID}>."
            )
            return

        if role not in target_member.roles:
            self.data.pop(str(target_member.id), None)
            save_data(self.data)
            await send_minor_error(
                interaction,
                "User does not have the Personal Leave role.",
            )
            return

        nickname_error = None

        try:
            await target_member.remove_roles(role)

            current_nick = target_member.nick or target_member.name
            expected_nick = f"P. Leave | {extract_name(stored_name)}"

            if current_nick == expected_nick:
                try:
                    await target_member.edit(nick=stored_name)
                except discord.Forbidden:
                    nickname_error = "forbidden"
                except discord.HTTPException:
                    nickname_error = "http"

            self.data.pop(str(target_member.id), None)
            save_data(self.data)

        except discord.Forbidden:
            await send_major_error(
                interaction,
                title="Error!",
                texts="I lack the necessary permissions to remove the Personal Leave role.",
                subtitle="Invalid configuration. Contact the owner."
            )
            return

        except discord.HTTPException:
            await send_major_error(
                interaction,
                title="Error!",
                texts="A Discord API error occurred while removing the role. Please try again later.",
                subtitle=f"Invalid operation. Contact <@{BOT_OWNER_ID}>."
            )
            return

        if nickname_error == "forbidden":
            if target_member.id == interaction.guild.owner_id:
                await send_minor_error(
                    interaction,
                    title="Error!",
                    texts="The role was removed, but I cannot change the server owner's nickname. Please change it back manually.",
                )
            else:
                await send_major_error(
                    interaction,
                    title="Error!",
                    texts="The role was removed, but I lack the necessary permissions to change the nickname. Please change it back manually.",
                )
        elif nickname_error == "http":
            await send_minor_error(
                interaction,
                title="Error!",
                texts="The role was removed, but a Discord API error prevented the nickname from being restored.",
            )
        else:
            if target_member.id == interaction.user.id:
                await interaction.followup.send(
                    "You have been removed from personal leave.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"{target_member.mention} has been removed from personal leave.",
                    ephemeral=True
                )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ~ti Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    class TimezoneFlags(commands.FlagConverter, prefix="/", delimiter=" "):
        set: bool = commands.flag(name="s", default=False)
        tz: Optional[str] = commands.flag(name="tz", default=None)

    async def resolve_member_with_partial(self, ctx: commands.Context, query: str):
        guild = ctx.guild
        if not guild:
            return None

        query_lower = query.lower()

        for member in guild.members:
            if member.name.lower() == query_lower or (member.nick and member.nick.lower() == query_lower):
                return member

        matches = [
            m for m in guild.members
            if query_lower in m.name.lower()
            or (m.nick and query_lower in m.nick.lower())
        ]

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            view = self.UserMatchPaginator(ctx, matches)
            await ctx.send(content=view.get_page_content(), view=view)
            return None
        else:
            await ctx.send("No users matched that name.")
            return None

    def resolve_timezone(self, tz_input: str) -> Optional[str]:
        if not tz_input:
            return None

        tz_clean = tz_input.strip()

        for key, value in self.TIMEZONE_ALIASES.items():
            if key.lower() == tz_clean.lower():
                return value

        try:
            pytz.timezone(tz_clean)
            return tz_clean
        except Exception:
            return None

    TIMEZONE_ALIASES = {
        "Maine": "America/New_York",
        "Augusta": "America/New_York",
        "New Hampshire": "America/New_York",
        "Concord": "America/New_York",
        "Vermont": "America/New_York",
        "Montpelier": "America/New_York",
        "Massachusetts": "America/New_York",
        "Boston": "America/New_York",
        "Rhode Island": "America/New_York",
        "Providence": "America/New_York",
        "Connecticut": "America/New_York",
        "Hartford": "America/New_York",
        "New York": "America/New_York",
        "Albany": "America/New_York",
        "New Jersey": "America/New_York",
        "Trenton": "America/New_York",
        "Pennsylvania": "America/New_York",
        "Harrisburg": "America/New_York",
        "Delaware": "America/New_York",
        "Dover": "America/New_York",
        "Maryland": "America/New_York",
        "Annapolis": "America/New_York",
        "District of Columbia": "America/New_York",
        "Washington DC": "America/New_York",
        "Virginia": "America/New_York",
        "Richmond": "America/New_York",
        "North Carolina": "America/New_York",
        "Raleigh": "America/New_York",
        "South Carolina": "America/New_York",
        "Columbia": "America/New_York",
        "Georgia": "America/New_York",
        "Atlanta": "America/New_York",
        "Florida": "America/New_York",
        "Tallahassee": "America/New_York",
        "Miami": "America/New_York",
        "Detroit": "America/Detroit",
        "Michigan": "America/Detroit",

        "Ohio": "America/New_York",
        "Indiana": "America/Indiana/Indianapolis",
        "Kentucky": "America/Kentucky/Louisville",
        "Tennessee": "America/Chicago",
        "Missouri": "America/Chicago",
        "Mississippi": "America/Chicago",
        "Alabama": "America/Chicago",
        "Wisconsin": "America/Chicago",
        "Illinois": "America/Chicago",
        "Minnesota": "America/Chicago",
        "Iowa": "America/Chicago",
        "Louisiana": "America/Chicago",
        "North Dakota": "America/Chicago",
        "South Dakota": "America/Chicago",
        "Kansas": "America/Chicago",
        "Oklahoma": "America/Chicago",
        "Texas": "America/Chicago",
        "Chicago": "America/Chicago",
        "Dallas": "America/Chicago",
        "Houston": "America/Chicago",
        "Minneapolis": "America/Chicago",
        "St. Louis": "America/Chicago",

        "Montana": "America/Denver",
        "Helena": "America/Denver",
        "Wyoming": "America/Denver",
        "Cheyenne": "America/Denver",
        "Colorado": "America/Denver",
        "Denver": "America/Denver",
        "New Mexico": "America/Denver",
        "Santa Fe": "America/Denver",
        "Idaho": "America/Boise",
        "Boise": "America/Boise",
        "Utah": "America/Denver",
        "Salt Lake City": "America/Denver",
        "Arizona": "America/Phoenix",
        "Phoenix": "America/Phoenix",

        "California": "America/Los_Angeles",
        "Sacramento": "America/Los_Angeles",
        "Los Angeles": "America/Los_Angeles",
        "San Francisco": "America/Los_Angeles",
        "Oregon": "America/Los_Angeles",
        "Salem": "America/Los_Angeles",
        "Washington": "America/Los_Angeles",
        "Olympia": "America/Los_Angeles",
        "Nevada": "America/Los_Angeles",
        "Carson City": "America/Los_Angeles",

        "Alaska": "America/Anchorage",
        "Juneau": "America/Anchorage",
        "Anchorage": "America/Anchorage",

        "Hawaii": "Pacific/Honolulu",
        "Honolulu": "Pacific/Honolulu",

        "PST": "America/Los_Angeles",
        "PDT": "America/Los_Angeles",
        "MST": "America/Denver",
        "MDT": "America/Denver",
        "CST": "America/Chicago",
        "CDT": "America/Chicago",
        "EST": "America/New_York",
        "EDT": "America/New_York",
        "AKST": "America/Anchorage",
        "AKDT": "America/Anchorage",
        "HST": "Pacific/Honolulu",
    }

    @commands.command(name="ti")
    async def timezone(self, ctx: commands.Context, *, raw: Optional[str] = None):
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return

        invocator: discord.Member = ctx.author

        if not raw:
            target: discord.Member = invocator
            tz_target = user_timezones.get(str(target.id))
            if not tz_target:
                await ctx.send(f"{target.mention} does not have a timezone set.")
                return
            now_target = datetime.now(pytz.timezone(tz_target))
            await ctx.send(f"It is **{now_target.strftime('%H:%M')}** for you. Your timezone is **{tz_target}**.")
            return

        parts = raw.split()

        if parts[0].startswith("/@"):
            tz_input = parts[0][2:] or (" ".join(parts[1:]) if len(parts) > 1 else "")
            if not tz_input:
                await ctx.send("Please provide a timezone. Example: `.ti /@ EST`")
                return
            resolved = self.resolve_timezone(tz_input)
            if not resolved:
                await ctx.send(f"`{tz_input}` is not a valid timezone.")
                return
            now = datetime.now(pytz.timezone(resolved)).strftime("%H:%M")
            await ctx.send(f"It is **{now}** in **{resolved}**.")
            return

        set_flag = False
        tz_value = None
        member_query = None

        i = 0
        while i < len(parts):
            token = parts[i]
            if token == "/s":
                set_flag = True
            elif token == "/tz":
                if i + 1 < len(parts):
                    i += 1
                    tz_value = parts[i]
            elif not token.startswith("/"):
                member_query = token
            i += 1

        target: discord.Member = invocator

        if member_query:
            member = await self.resolve_member_with_partial(ctx, member_query)
            if member is None:
                return
            target = member

        if set_flag:
            if not tz_value:
                await ctx.send("You must provide a timezone. Example: `.ti /s /tz EST`")
                return

            resolved = self.resolve_timezone(tz_value)
            if not resolved:
                await ctx.send(f"`{tz_value}` is not a valid timezone.")
                return

            if target.id != invocator.id:
                if DIRECTORS_ROLE_ID not in [r.id for r in invocator.roles]:
                    await ctx.send("You lack permission to set other users' timezones.")
                    return

            user_timezones[str(target.id)] = resolved
            save_timezones()

            if target.id == invocator.id:
                await ctx.send(f"Your timezone has been set to **{resolved}**.")
            else:
                await ctx.send(f"Timezone for {target.mention} set to **{resolved}**.")
            return

        tz_target = user_timezones.get(str(target.id))
        if not tz_target:
            await ctx.send(f"{target.mention} does not have a timezone set.")
            return

        now_target = datetime.now(pytz.timezone(tz_target))
        time_target = now_target.strftime("%H:%M")

        tz_author = user_timezones.get(str(invocator.id))

        if target.id == invocator.id:
            await ctx.send(f"It is **{time_target}** for you. Your timezone is **{tz_target}**.")
            return

        if not tz_author:
            await ctx.send(f"It is **{time_target}** for {target.mention}. Their timezone is **{tz_target}**.")
            return

        now_author = datetime.now(pytz.timezone(tz_author))

        t_delta = now_target.utcoffset()
        a_delta = now_author.utcoffset()

        if t_delta is None or a_delta is None:
            return

        target_offset = t_delta.total_seconds()
        author_offset = a_delta.total_seconds()
        diff_hours = int((target_offset - author_offset) / 3600)
        diff_hours = int((target_offset - author_offset) / 3600)

        if diff_hours == 0:
            relation = "the same timezone as you"
        elif diff_hours > 0:
            relation = f"{diff_hours} hour{'s' if abs(diff_hours) != 1 else ''} ahead of you"
        else:
            relation = f"{abs(diff_hours)} hour{'s' if abs(diff_hours) != 1 else ''} behind you"

        await ctx.send(
            f"It is **{time_target}** for {target.mention}. Their timezone is **{tz_target}**, {relation}."
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ~ui Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    class UserMatchPaginator(discord.ui.View):
        def __init__(self, ctx: commands.Context, matches: list[discord.Member]):
            super().__init__(timeout=120)
            self.ctx = ctx
            self.matches = matches
            self.per_page = 20
            self.page = 0
            self.max_page = (len(matches) - 1) // self.per_page

            self.update_buttons()

        def update_buttons(self):
            total_pages = self.max_page
            no_pagination_needed = len(self.matches) <= self.per_page

            self.first_page.disabled = no_pagination_needed or self.page == 0
            self.previous_page.disabled = no_pagination_needed or self.page == 0
            self.next_page.disabled = no_pagination_needed or self.page >= total_pages
            self.last_page.disabled = no_pagination_needed or self.page >= total_pages

        def get_page_content(self) -> str:
            start = self.page * self.per_page
            end = start + self.per_page
            page_members = self.matches[start:end]

            lines = [
                f"{i+1}. {member} ({member.id})"
                for i, member in enumerate(page_members, start=start)
            ]

            return (
                f"**User Matches (Page {self.page+1}/{self.max_page+1})**\n\n"
                + "\n".join(lines)
            )

        async def update_message(self, interaction: discord.Interaction):
            await interaction.response.edit_message(
                content=self.get_page_content(),
                view=self
            )

        @discord.ui.button(label="<<", style=discord.ButtonStyle.secondary)
        async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.page = 0
            self.update_buttons()
            await interaction.response.edit_message(
                content=self.get_page_content(),
                view=self
            )

        @discord.ui.button(label="<", style=discord.ButtonStyle.secondary)
        async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.page > 0:
                self.page -= 1
            self.update_buttons()
            await interaction.response.edit_message(
                content=self.get_page_content(),
                view=self
            )

        @discord.ui.button(label=">", style=discord.ButtonStyle.secondary)
        async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.page < self.max_page:
                self.page += 1
            self.update_buttons()
            await interaction.response.edit_message(
                content=self.get_page_content(),
                view=self
            )

        @discord.ui.button(label=">>", style=discord.ButtonStyle.secondary)
        async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.page = self.max_page
            self.update_buttons()
            await interaction.response.edit_message(
                content=self.get_page_content(),
                view=self
            )

    @commands.command(name="ui")
    async def userinfo(self, ctx: commands.Context, *, user: Optional[str] = None):
        if ctx.guild is None:
            return

        target_user = cast(discord.Member, ctx.author)

        if ctx.message.reference and user is None:
            replied = ctx.message.reference.resolved
            if isinstance(replied, discord.Message) and isinstance(replied.author, discord.Member):
                target_user = replied.author

        elif user:
            user_lower = user.lower()

            for member in ctx.guild.members:
                if member.name.lower() == user_lower or (member.nick and member.nick.lower() == user_lower):
                    target_user = member
                    break
            else:
                matches = [
                    m for m in ctx.guild.members
                    if user_lower in m.name.lower()
                    or (m.nick and user_lower in m.nick.lower())
                ]

                if len(matches) == 1:
                    target_user = matches[0]
                elif len(matches) > 1:
                    view = self.UserMatchPaginator(ctx, matches)
                    await ctx.send(
                        content=view.get_page_content(),
                        view=view
                    )
                    return
                else:
                    await ctx.send("No users matched that name.")
                    return

        guild = ctx.guild

        def format_dt(dt: Optional[datetime]) -> str:
            if not dt:
                return "Unknown"
            return dt.strftime("%A, %B %d, %Y, at %I:%M %p")

        name = target_user.name
        nickname = target_user.nick or "None"
        joined_at = format_dt(target_user.joined_at)
        created_at = format_dt(target_user.created_at)

        roles = [role.mention for role in target_user.roles if role != guild.default_role]
        roles_display = ", ".join(roles) if roles else "None"

        sorted_members = sorted(
            guild.members,
            key=lambda m: m.joined_at or datetime.min
        )

        user_index = sorted_members.index(target_user)
        join_order_lines = []

        width = len(str(len(sorted_members)))

        for i in range(user_index - 3, user_index + 4):
            if 0 <= i < len(sorted_members):
                member = sorted_members[i]
                marker = ">" if member.id == target_user.id else " "
                join_order_lines.append(f"{str(i+1).rjust(width)}. {marker} {member}")

        join_order_block = "```\n" + "\n".join(join_order_lines) + "\n```"

        embed = discord.Embed(
            title=f"{target_user} —— {target_user.id}",
            color=target_user.color
        )

        embed.description = (
            f"`      Name:` {name}\n"
            f"`  Nickname:` {nickname}\n"
            f"` Joined at:` {joined_at}\n"
            f"`Created at:` {created_at}\n\n"
            f"**Roles**\n"
            f"{roles_display}\n\n"
            f"**Join Order**\n"
            f"{join_order_block}"
        )

        embed.set_thumbnail(url=target_user.display_avatar.url)

        fetched_user = await ctx.bot.fetch_user(target_user.id)
        if fetched_user.banner:
            embed.set_image(url=fetched_user.banner.url)

        await ctx.send(embed=embed)

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