import discord
from discord.ext import commands
from discord import app_commands

from datetime import datetime, timedelta
import json
import os
from typing import Optional, cast
import pytz

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
TIMEZONE_FILE = "user_timezones.json"

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

    def load_timezones(self) -> dict:
        if os.path.exists(TIMEZONE_FILE):
            with open(TIMEZONE_FILE, "r") as f:
                return json.load(f)
        return {}

    def save_timezones(self, data: dict) -> None:
        with open(TIMEZONE_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def resolve_timezone(self, tz_str: str) -> pytz.BaseTzInfo | None:
        ABBREV_MAP = {
            "EST": "America/New_York",
            "EDT": "America/New_York",
            "CST": "America/Chicago",
            "CDT": "America/Chicago",
            "MST": "America/Denver",
            "MDT": "America/Denver",
            "PST": "America/Los_Angeles",
            "PDT": "America/Los_Angeles",
            "GMT": "Etc/GMT",
            "UTC": "UTC",
            "BST": "Europe/London",
            "CET": "Europe/Paris",
            "AEST": "Australia/Sydney",
            "JST": "Asia/Tokyo",
        }

        normalized = tz_str.upper()
        if normalized in ABBREV_MAP:
            tz_str = ABBREV_MAP[normalized]

        try:
            return pytz.timezone(tz_str)
        except pytz.UnknownTimeZoneError:
            return None

    async def parse_user_and_tz(
        self, ctx: commands.Context, value: str
    ) -> tuple[discord.Member | None, str | None]:
        parts = value.strip().split()
        if not parts:
            return None, None

        member = None
        tz_parts_start = 0
        try:
            member = await commands.MemberConverter().convert(ctx, parts[0])
            tz_parts_start = 1
        except commands.BadArgument:
            pass

        tz_str = " ".join(parts[tz_parts_start:]) if len(parts) > tz_parts_start else None
        return member, tz_str

    async def parse_user(
        self, ctx: commands.Context, value: str
    ) -> discord.Member | None:
        value = value.strip()
        if not value:
            return None
        try:
            return await commands.MemberConverter().convert(ctx, value)
        except commands.BadArgument:
            return None

    def format_offset(
        self, invoker: discord.Member, target: discord.Member, timezones: dict
    ) -> str | None:
        invoker_tz_name = timezones.get(str(invoker.id))
        if not invoker_tz_name:
            return None

        target_tz_name = timezones.get(str(target.id))
        if not target_tz_name:
            return None

        invoker_tz = pytz.timezone(invoker_tz_name)
        target_tz = pytz.timezone(target_tz_name)

        now = datetime.now(pytz.utc)

        invoker_offset = now.astimezone(invoker_tz).utcoffset() or timedelta(0)
        target_offset = now.astimezone(target_tz).utcoffset() or timedelta(0)

        delta_seconds = int((target_offset - invoker_offset).total_seconds())

        if delta_seconds == 0:
            return "the same timezone as you!"

        abs_seconds = abs(delta_seconds)
        hours, remainder = divmod(abs_seconds, 3600)
        minutes = remainder // 60
        direction = "ahead of" if delta_seconds > 0 else "behind"

        if hours and minutes:
            diff_str = f"{hours} hour{'s' if hours != 1 else ''} and {minutes} minute{'s' if minutes != 1 else ''}"
        elif hours:
            diff_str = f"{hours} hour{'s' if hours != 1 else ''}"
        else:
            diff_str = f"{minutes} minute{'s' if minutes != 1 else ''}"

        return f"{diff_str} {direction} you."

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
        s: str | None = commands.flag(
            name="s",
            default=None,
            description="Set timezone. Usage: /s [user] {timezone}",
            max_args=-1,
        )
        r: str | None = commands.flag(
            name="r",
            default=None,
            description="Reset timezone. Usage: /r [user]",
            max_args=-1,
        )
        at: str | None = commands.flag(
            name="@",
            default=None,
            description="View time for a timezone. Usage: /@ {timezone}",
        )

    @commands.command(name="timezone", aliases=["ti"])
    async def timezone(
        self,
        ctx: commands.Context,
        user: discord.Member | None = None,
        *,
        flags: TimezoneFlags,
    ):
        timezones = self.load_timezones()

        if ctx.guild is None:
            return

        if user is not None:
            target_user: Optional[discord.Member] = None

            for member in ctx.guild.members:
                if (
                    member.name.lower() == user.name.lower()
                    or (member.nick and member.nick.lower() == user.name.lower())
                ):
                    target_user = member
                    break
            else:
                matches = [
                    m for m in ctx.guild.members
                    if user.name.lower() in m.name.lower()
                    or (m.nick and user.name.lower() in m.nick.lower())
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

            uid = str(target_user.id)

            if uid not in timezones:
                return await ctx.send(
                    f"**{target_user.display_name}** hasn't set a timezone yet."
                )

            tz = pytz.timezone(timezones[uid])
            now = datetime.now(tz)
            time_str = now.strftime("%H:%M")
            offset = self.format_offset(
                cast(discord.Member, ctx.author),
                target_user,
                timezones
            )

            if offset is None:
                return await ctx.send(
                    f"It is **{time_str}** for **{target_user.display_name}**. "
                    f"Their timezone is **{tz.zone}**."
                )

            if offset == "the same timezone as you!":
                return await ctx.send(
                    f"It is **{time_str}** for **{target_user.display_name}**. "
                    f"Their timezone is **{tz.zone}**, the same timezone as you!"
                )

            return await ctx.send(
                f"It is **{time_str}** for **{target_user.display_name}**. "
                f"Their timezone is **{tz.zone}**, {offset}"
            )

        if flags.at is not None:
            tz_str = flags.at.strip()
            if not tz_str:
                return await ctx.send(
                    "You must provide a timezone. Example: `.ti /@ PDT`"
                )

            tz = self.resolve_timezone(tz_str)
            if tz is None:
                return await ctx.send(
                    f"Unknown timezone `{tz_str}`. "
                )

            now = datetime.now(tz)
            formatted = now.strftime("%A, %B %d %Y — %I:%M %p")
            return await ctx.send(f"Current time in **{tz.zone}**: `{formatted}`")

        await ctx.send(
            "**Timezone command usage:**\n"
            "```\n"
            ".ti @user                 –– View a user's current time\n"
            ".ti /s [user] {timezone}  –– Set a timezone\n"
            ".ti /r [user]             –– Reset a timezone\n"
            ".ti /@ {timezone}         –– View current time in a timezone\n"
            "```"
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

    @commands.command(name="userinfo", aliases=["ui"])
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

        timezones = self.load_timezones()
        uid = str(target_user.id)

        time_line = ""
        if uid in timezones:
            tz = pytz.timezone(timezones[uid])
            now = datetime.now(tz)
            jtime = now.strftime("%I:%M %p")
            time_line = f"`      Time:` {jtime}\n"

        embed.description = (
            f"`      Name:` {name}\n"
            f"`  Nickname:` {nickname}\n"
            f"{time_line}"
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