import discord
from discord.ext import commands
from discord import app_commands

from datetime import (
    datetime,
    timedelta
)
import json
import os
from typing import (
    Optional,
    cast
)
import pytz

from core.help import (
    help_description,
    ArgumentInfo
)
from core.utils import (
    send_minor_error,
    send_major_error
)

from constants import (
    BOT_OWNER_ID,
    DIRECTORS_ROLE_ID,
    PERSONAL_LEAVE_ROLE_ID,
    STAFF_ROLE_ID,

    MODERATORS_ROLE_ID,

    TICKET_CHANNEL_ID,
    STAFF_PROPOSALS_REVIEW_CHANNEL_ID
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

    def resolve_timezone(self, tz_str: str) -> pytz.BaseTzInfo | list[str] | None:
        ABBREV_MAP = {
            "EST": "America/New_York",
            "EDT": "America/New_York",
            "CST": "America/Chicago",
            "CDT": "America/Chicago",
            "MST": "America/Denver",
            "MDT": "America/Denver",
            "PST": "America/Los_Angeles",
            "PDT": "America/Los_Angeles",
            "AKST": "America/Anchorage",
            "AKDT": "America/Anchorage",
            "HST": "Pacific/Honolulu",
            "HDT": "Pacific/Honolulu",
            "AST": "America/Halifax",
            "ADT": "America/Halifax",
            "NST": "America/St_Johns",
            "NDT": "America/St_Johns",
            "MST_AZ": "America/Phoenix",

            # Central & South America
            "ART": "America/Argentina/Buenos_Aires",
            "BRT": "America/Sao_Paulo",
            "BRST": "America/Sao_Paulo",
            "CLT": "America/Santiago",
            "CLST": "America/Santiago",
            "COT": "America/Bogota",
            "ECT": "America/Guayaquil",
            "GYT": "America/Guyana",
            "PET": "America/Lima",
            "PYT": "America/Asuncion",
            "PYST": "America/Asuncion",
            "UYT": "America/Montevideo",
            "VET": "America/Caracas",
            "BOT": "America/La_Paz",
            "SRT": "America/Paramaribo",
            "GFT": "America/Cayenne",

            # Europe
            "GMT": "Etc/GMT",
            "UTC": "UTC",
            "BST": "Europe/London",
            "IST_IE": "Europe/Dublin",
            "WET": "Europe/Lisbon",
            "WEST": "Europe/Lisbon",
            "CET": "Europe/Paris",
            "CEST": "Europe/Paris",
            "EET": "Europe/Helsinki",
            "EEST": "Europe/Helsinki",
            "MSK": "Europe/Moscow",
            "MSD": "Europe/Moscow",
            "TRT": "Europe/Istanbul",
            "FET": "Europe/Minsk",
            "SAMT": "Europe/Samara",
            "VOLT": "Europe/Volgograd",

            # Africa
            "WAT": "Africa/Lagos",
            "WAST": "Africa/Windhoek",
            "CAT": "Africa/Harare",
            "EAT": "Africa/Nairobi",
            "SAST": "Africa/Johannesburg",
            "GMT_GH": "Africa/Accra",
            "CVT": "Atlantic/Cape_Verde",
            "MUT": "Indian/Mauritius",
            "SCT": "Indian/Mahe",
            "IOT": "Indian/Chagos",
            "TFT": "Indian/Kerguelen",
            "RET": "Indian/Reunion",

            # Middle East
            "AST_AR": "Asia/Riyadh",
            "ADT_AR": "Asia/Baghdad",
            "GST": "Asia/Dubai",
            "IRST": "Asia/Tehran",
            "IRDT": "Asia/Tehran",
            "IST": "Asia/Kolkata",
            "PKT": "Asia/Karachi",

            # Central Asia
            "AFT": "Asia/Kabul",
            "UZT": "Asia/Tashkent",
            "TJT": "Asia/Dushanbe",
            "TMT": "Asia/Ashgabat",
            "KGT": "Asia/Bishkek",
            "ALMT": "Asia/Almaty",
            "YEKT": "Asia/Yekaterinburg",
            "OMST": "Asia/Omsk",
            "KRAT": "Asia/Krasnoyarsk",
            "NOVT": "Asia/Novosibirsk",

            # South & Southeast Asia
            "NPT": "Asia/Kathmandu",
            "BST_BD": "Asia/Dhaka",
            "MMT": "Asia/Rangoon",
            "ICT": "Asia/Bangkok",
            "WIB": "Asia/Jakarta",
            "WITA": "Asia/Makassar",
            "WIT": "Asia/Jayapura",
            "SGT": "Asia/Singapore",
            "MYT": "Asia/Kuala_Lumpur",
            "PHT": "Asia/Manila",
            "BNT": "Asia/Brunei",

            # East Asia
            "CST_CN": "Asia/Shanghai",
            "HKT": "Asia/Hong_Kong",
            "TWT": "Asia/Taipei",
            "KST": "Asia/Seoul",
            "JST": "Asia/Tokyo",
            "IRKST": "Asia/Irkutsk",
            "YAKT": "Asia/Yakutsk",
            "VLAT": "Asia/Vladivostok",
            "MAGT": "Asia/Magadan",
            "SAKT": "Asia/Sakhalin",
            "PETT": "Asia/Kamchatka",

            # Oceania
            "AEST": "Australia/Sydney",
            "AEDT": "Australia/Sydney",
            "ACST": "Australia/Darwin",
            "ACDT": "Australia/Adelaide",
            "AWST": "Australia/Perth",
            "LHST": "Australia/Lord_Howe",
            "LHDT": "Australia/Lord_Howe",
            "NZST": "Pacific/Auckland",
            "NZDT": "Pacific/Auckland",
            "FJT": "Pacific/Fiji",
            "FJST": "Pacific/Fiji",
            "PGT": "Pacific/Port_Moresby",
            "SBT": "Pacific/Guadalcanal",
            "VUT": "Pacific/Efate",
            "NCT": "Pacific/Noumea",
            "TOT": "Pacific/Tongatapu",
            "WST": "Pacific/Apia",
            "SST": "Pacific/Pago_Pago",
            "CHAST": "Pacific/Chatham",
            "CHADT": "Pacific/Chatham",
            "LINT": "Pacific/Kiritimati",
            "PHOT": "Pacific/Enderbury",
            "TKT": "Pacific/Fakaofo",
            "TVT": "Pacific/Funafuti",
            "WFST": "Pacific/Wallis",
            "PONT": "Pacific/Pohnpei",
            "CHUT": "Pacific/Chuuk",
            "PWT": "Pacific/Palau",
            "MHT": "Pacific/Majuro",
            "GILT": "Pacific/Tarawa",
            "NRT": "Pacific/Nauru",
            "CKT": "Pacific/Rarotonga",
            "TAHT": "Pacific/Tahiti",
            "MART": "Pacific/Marquesas",
            "GAMT": "Pacific/Gambier",

            # Atlantic
            "AZOT": "Atlantic/Azores",
            "AZOST": "Atlantic/Azores",
            "FKST": "Atlantic/Stanley",
            "FKT": "Atlantic/Stanley",
            "SGT_GS": "Atlantic/South_Georgia",
            "PMST": "America/Miquelon",
            "PMDT": "America/Miquelon",

            # Antartic (I wonder who would ever be using these)
            "MAWT": "Antarctica/Mawson",
            "DAVT": "Antarctica/Davis",
            "DDUT": "Antarctica/DumontDUrville",
            "SYOT": "Antarctica/Syowa",
            "ROTT": "Antarctica/Rothera",
            "CAST": "Antarctica/Casey",
        }

        normalized = tz_str.upper()
        if normalized in ABBREV_MAP:
            tz_str = ABBREV_MAP[normalized]

        for tz in pytz.all_timezones:
            if tz.lower() == tz_str.lower():
                return pytz.timezone(tz)

        matches = [
            tz for tz in pytz.all_timezones
            if tz_str.lower() in tz.lower()
        ]

        if not matches:
            return None

        if len(matches) == 1:
            return pytz.timezone(matches[0])

        return sorted(matches)

    async def parse_user(
        self, ctx: commands.Context, value: str | list[str]
    ) -> discord.Member | None:
        if isinstance(value, list):
            value = " ".join(value)
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
    @help_description(
        desc        = f"The leave add command adds the <@{PERSONAL_LEAVE_ROLE_ID}> role to a staff member, and changes their nickname to \"P. Leave | username\". Their username is stored and restored upon /leave remove.",
        prefix      = False,
        slash       = True,
        run_role    = DIRECTORS_ROLE_ID,
        has_inverse = "/leave remove",
        arguments   = {
            "target": ArgumentInfo(
                role=DIRECTORS_ROLE_ID,
                required=False,
                description="The user to add personal leave to."
            ),
        },
    )
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
                subtitle="Invalid permissions."
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
                subtitle="Invalid permissions."
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
    @help_description(
        desc        = f"The leave remove command removes the <@{PERSONAL_LEAVE_ROLE_ID}> role from a staff member, and changes their nickname back to before they were on leave.",
        prefix      = False,
        slash       = True,
        run_role    = STAFF_ROLE_ID,
        has_inverse = "/leave add",
        arguments   = {
            "target": ArgumentInfo(
                role=DIRECTORS_ROLE_ID,
                required=False,
                description="The user to remove leave from."
            ),
        },
    )
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
                subtitle="Invalid permissions."
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
                subtitle="Invalid permissions."
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
                    subtitle="Not an error."
                )
            else:
                await send_major_error(
                    interaction,
                    title="Error!",
                    texts="The role was removed, but I lack the necessary permissions to change the nickname. Please change it back manually.",
                    subtitle="Invalid configuration. Contact the owner."
                )
        elif nickname_error == "http":
            await send_minor_error(
                interaction,
                title="Error!",
                texts="The role was removed, but a Discord API error prevented the nickname from being restored.",
                subtitle=f"Invalid operation. Contact <@{BOT_OWNER_ID}>."
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
    # .ti Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    class TimezoneMatchPaginator(discord.ui.View):
        def __init__(self, ctx: commands.Context, matches: list[str]):
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
            page_items = self.matches[start:end]

            lines = [
                f"{i+1}. {tz}"
                for i, tz in enumerate(page_items, start=start)
            ]

            return (
                f"**Timezone Matches (Page {self.page+1}/{self.max_page+1})**\n\n"
                + "\n".join(lines)
                + "\n\nReply with the number of the timezone you want."
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

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            return interaction.user == self.ctx.author

    class TimezoneFlags(commands.FlagConverter, prefix="/", delimiter=" "):
        s: str | None = commands.flag(
            name="s",
            default=None,
            description="Set timezone for yourself or a user. Usage: /s [user]",
            max_args=-1,
        )
        tz: str | None = commands.flag(
            name="tz",
            default=None,
            description="Timezone to use with /s or standalone. Usage: /tz {timezone}",
        )
        at: str | None = commands.flag(
            name="@",
            default=None,
            description="View time for a timezone. Usage: /@ {timezone}",
        )

    @commands.command(name="timezone", aliases=["ti"])
    @help_description(
        desc        = "The timezone command allows users to set and view their timezone, or view the current time in a specific timezone. It also allows users to view the current time of other users if they have set their timezone.",
        prefix      = True,
        slash       = False,
        has_inverse = False,
        aliases     = ["ti"],
        arguments   = {
            "s": ArgumentInfo(
                role=None,
                required=False,
                description="Set timezone for yourself or a user.",
                is_flag=True,
            ),
            "user": ArgumentInfo(
                role=None,
                required=False,
                description="The user to view the timezone of.",
                is_flag=False,
            ),
            "tz": ArgumentInfo(
                role=None,
                required=False,
                description="The timezone to view or set to.",
                is_flag=True,
            ),
        }
    )
    async def timezone(self, ctx: commands.Context, user: Optional[discord.User] = None, *, flags: TimezoneFlags):
        timezones = self.load_timezones()
        if ctx.guild is None:
            return
        if flags.s is not None:
            s_value = " ".join(flags.s) if isinstance(flags.s, list) else flags.s.strip()
            if s_value:
                member = await self.parse_user(ctx, s_value)
                target = member or ctx.author
            else:
                target = ctx.author

            if not flags.tz:
                return await ctx.send(
                    "You must provide a timezone with `/tz`. Example: `.ti /s @user /tz EST`"
                )

            tz_str = flags.tz.strip()
            result = self.resolve_timezone(tz_str)

            if result is None:
                return await ctx.send(
                    f"Unknown timezone `{tz_str}`."
                )

            if isinstance(result, list):
                view = self.TimezoneMatchPaginator(ctx, result)
                await ctx.send(
                    content=view.get_page_content(),
                    view=view
                )
                return

            tz = result

            if target.id == 1436054709700919477:
                return await ctx.send("One should not dare to alter the clock of the immortal.")

            if target.bot:
                return await ctx.send(
                    f"**{target.display_name}** is a bot and cannot have a timezone."
                )

            timezones[str(target.id)] = tz.zone
            self.save_timezones(timezones)

            abbr = datetime.now(tz).strftime("%Z")

            if target.id == ctx.author.id:
                return await ctx.send(
                    f"Your timezone has been set to **{abbr}**."
                )

            return await ctx.send(
                f"Timezone for **{target.display_name}** has been set to **{abbr}**."
            )

        if user is not None and flags.s is None:
            if user.id == 1436054709700919477:
                return await ctx.send(f"Is my time ∞:∞..? Or maybe null... It's whatever you wish, {ctx.author.mention}.")
            
            if user.id == ctx.author.id:
                return

            target_user: Optional[discord.Member] = None

            if user.bot:
                return await ctx.send(
                    f"**{user.display_name}** is a bot and doesn't have a timezone."
                )

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

            abbr = now.strftime("%Z")

            if offset is None:
                return await ctx.send(
                    f"It is **{time_str}** for **{target_user.display_name}**. "
                    f"Their timezone is **{abbr}**."
                )

            if offset == "the same timezone as you!":
                return await ctx.send(
                    f"It is **{time_str}** for **{target_user.display_name}**. "
                    f"Their timezone is **{abbr}**, the same timezone as you!"
                )

            return await ctx.send(
                f"It is **{time_str}** for **{target_user.display_name}**. "
                f"Their timezone is **{abbr}**, {offset}"
            )

        if flags.at is not None:
            tz_str = flags.at.strip()
            if not tz_str:
                return await ctx.send(
                    "You must provide a timezone. Example: `.ti /@ PDT`"
                )

            result = self.resolve_timezone(tz_str)

            if result is None:
                return await ctx.send(
                    f"Unknown timezone `{tz_str}`."
                )

            if isinstance(result, list):
                view = self.TimezoneMatchPaginator(ctx, result)
                await ctx.send(
                    content=view.get_page_content(),
                    view=view
                )

                def check(m: discord.Message):
                    return (
                        m.author == ctx.author
                        and m.channel == ctx.channel
                        and m.content.isdigit()
                    )

                try:
                    msg = await self.bot.wait_for("message", timeout=30, check=check)
                except Exception:
                    return

                index = int(msg.content) - 1
                if 0 <= index < len(result):
                    tz = pytz.timezone(result[index])
                    now = datetime.now(tz)
                    formatted = now.strftime("%A, %B %d %Y — %I:%M %p")
                    abbr = now.strftime("%Z")
                    await ctx.send(
                        f"Current time in **{abbr}**: `{formatted}`"
                    )
                return

            tz = result
            now = datetime.now(tz)
            formatted = now.strftime("%A, %B %d %Y — %I:%M %p")
            abbr = now.strftime("%Z")
            return await ctx.send(
                f"Current time in **{abbr}**: `{formatted}`"
            )

        await ctx.send(
            "**Timezone command usage:**\n"
            "```\n"
            ".ti @user                      –– View a user's current time\n"
            ".ti /s [user] /tz {timezone}   –– Set a timezone\n"
            ".ti /@ {timezone}              –– View current time in a timezone\n"
            "```"
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .ui Command
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
    @help_description(
        desc        = "The userinfo command displays information about a user, including their username, display name, guild nickname, time (if set by the user), roles, time, join date, and account creation date.",
        prefix      = True,
        slash       = False,
        has_inverse = False,
        aliases     = ["ui"],
    )
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

        name = target_user.display_name
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
    # .ping Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="ping")
    @help_description(
        desc        = "The ping command displays the bot's current latency in milliseconds.",
        prefix      = True,
        slash       = False,
        has_inverse = False,
    )
    async def ping(self, ctx: commands.Context):
        latency_ms = round(self.bot.latency * 1000)
        await ctx.send(
            view=Ping(latency_ms)
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .lock/.l Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    def is_moderator(self, member: discord.Member):
        return any(role.id == MODERATORS_ROLE_ID for role in member.roles)

    def is_staff(self, member: discord.Member):
        return any(role.id == STAFF_ROLE_ID for role in member.roles)

    def allowed_in_thread(self, ctx: commands.Context) -> bool:
        if not isinstance(ctx.channel, discord.Thread):
            return False

        if not isinstance(ctx.author, discord.Member):
            return False

        parent = ctx.channel.parent
        if parent is None:
            return False

        if parent.id == TICKET_CHANNEL_ID:
            return self.is_moderator(ctx.author)

        if parent.id == STAFF_PROPOSALS_REVIEW_CHANNEL_ID:
            return self.is_staff(ctx.author)

        return False

    @commands.command(
        name="lock",
        aliases=["l"]
    )
    async def lock(self, ctx: commands.Context):
        if not self.allowed_in_thread(ctx):
            return

        if not isinstance(ctx.channel, discord.Thread):
            return

        await ctx.channel.edit(locked=True)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .close/.c Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name="close",
        aliases=["c"]
    )
    async def close(self, ctx: commands.Context):
        if not self.allowed_in_thread(ctx):
            return

        if not isinstance(ctx.channel, discord.Thread):
            return
        
        await ctx.channel.edit(archived=True)

async def setup(bot):
    await bot.add_cog(UtilityCommands(bot))