import contextlib

import discord
from discord import app_commands
from discord.ext import commands

from constants import (
    DIRECTORS_ROLE_ID,
    STAFF_ROLE_ID,
)
from core.help import ArgumentInfo, RoleConfig, help_description
from core.permissions import directors_only, main_guild_only
from core.responses import send_custom_message
from core.state.application_state import APPLICATIONS_OPEN, save_application_state
from core.state.blacklist_state import BLACKLIST, save_blacklist
from events.systems.applications import ACTIVE_APPLICATIONS, delete_application_messages

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Applications Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ApplicationsCommands(
    commands.GroupCog,
    name        = "applications",
    description = "Moderators only —— Applications commands.",
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /applications blacklist Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name        = "blacklist",
        description = "Blacklist or un-blacklist a user from applications.",
    )
    @app_commands.describe(
        action = "Add or remove a blacklist.",
        user   = "User to modify.",
    )
    @app_commands.choices(
        action = [
            app_commands.Choice(
                name  = "Add",
                value = "add",
            ),
            app_commands.Choice(
                name  = "Remove",
                value = "remove",
            ),
        ],
    )
    @help_description(
        desc      = "Directors only —— Add or remove a user from the applications blacklist.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id = DIRECTORS_ROLE_ID)],
        arguments = {
            "action" : ArgumentInfo(description = "Choose whether to add or remove the blacklist entry.", choices=["Add", "Remove"]),
            "user"   : ArgumentInfo(description = "User to blacklist or unblacklist from applications."),
        },
    )
    @main_guild_only()
    @directors_only()
    async def blacklist(
        self,
        interaction : discord.Interaction,
        action      : app_commands.Choice[str],
        user        : discord.User,
    ) -> None:
        user_id     = user.id
        target_list = BLACKLIST["applications"]

        if interaction.user.id == user.id:
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "modify blacklist",
                subtitle = "You cannot blacklist yourself.",
                footer   = "Bad argument",
            )
            return

        guild = interaction.guild
        if guild and isinstance(user, discord.Member):
            staff_role = guild.get_role(STAFF_ROLE_ID)
            if staff_role and staff_role in user.roles:
                await send_custom_message(
                    interaction,
                    msg_type = "warning",
                    title    = "modify blacklist",
                    subtitle = "You cannot blacklist staff.",
                    footer   = "Bad argument",
                )
                return

        if action.value == "add":
            if user_id in target_list:
                await send_custom_message(
                    interaction,
                    msg_type = "warning",
                    title    = "modify blacklist",
                    subtitle = "This user is already blacklisted from Applications.",
                    footer   = "Bad argument",
                )
                return

            target_list.append(user_id)
            save_blacklist()

            await send_custom_message(
                interaction,
                msg_type = "success",
                title    = f"blacklisted {user.mention} from Applications",
            )

        else:
            if user_id not in target_list:
                await send_custom_message(
                    interaction,
                    msg_type = "warning",
                    title    = "modify blacklist",
                    subtitle = "This user is not blacklisted from Applications.",
                    footer   = "Bad argument",
                )
                return

            target_list.remove(user_id)
            save_blacklist()

            await send_custom_message(
                interaction,
                msg_type = "success",
                title    = f"un-blacklisted {user.mention} from Applications",
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /applications state-modify Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name        = "state-modify",
        description = "Open or close staff applications.",
    )
    @app_commands.describe(
        application = "Which application to modify.",
        state       = "Application state.",
    )
    @app_commands.choices(
        application = [
            app_commands.Choice(
                name  = "Moderators",
                value = "mod",
            ),
            app_commands.Choice(
                name  = "Administrators",
                value = "admin",
            ),
        ],
        state = [
            app_commands.Choice(
                name  = "Open",
                value = "open",
            ),
            app_commands.Choice(
                name  = "Closed",
                value = "closed",
            ),
        ],
    )
    @help_description(
        desc      = "Directors only —— Open or close moderator or administrator applications.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id=DIRECTORS_ROLE_ID)],
        arguments = {
            "application" : ArgumentInfo(description = "Application type to modify.", choices=["Moderators", "Administrators"]),
            "state"       : ArgumentInfo(description = "Whether that application should be open or closed.", choices=["Open", "Closed"]),
        },
    )
    @directors_only()
    async def appmodify(
        self,
        interaction : discord.Interaction,
        application : app_commands.Choice[str],
        state       : app_commands.Choice[str],
    ) -> None:
        new_state     = state.value == "open"
        current_state = APPLICATIONS_OPEN.get(application.value, False)

        if current_state == new_state:
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "modify application state",
                subtitle = f"{application.name} applications are already {state.value}.",
                footer   = "Bad request",
            )
            return

        APPLICATIONS_OPEN[application.value] = new_state
        save_application_state()

        await send_custom_message(
            interaction,
            msg_type = "success",
            title    = f"set {application.name} applications to {state.value}",
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .cancel Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name = "cancel")
    @help_description(
        desc   = "Cancels your active application. This command only works in DMs while you have an active application.",
        prefix = True,
        slash  = False,
    )
    async def cancel(self, ctx : commands.Context[commands.Bot]) -> None:
        if ctx.guild is not None:
            await send_custom_message(
                ctx,
                msg_type = "warning",
                title    = "cancel application",
                subtitle = "This command can only be used in DMs.",
                footer   = "Bad environment",
            )
            return

        if ctx.author.id not in ACTIVE_APPLICATIONS:
            await send_custom_message(
                ctx,
                msg_type = "warning",
                title    = "cancel application",
                subtitle = "This command can only be used with an active application to cancel.",
                footer   = "Bad request",
            )
            return

        with contextlib.suppress(discord.Forbidden, discord.NotFound):
            await ctx.message.delete(delay=300)

        await delete_application_messages(client = self.bot, user_id = ctx.author.id)

        await send_custom_message(
            ctx,
            msg_type = "success",
            title    = "cancelled application",
            subtitle = "Your application has been cancelled and deleted.",
        )

async def setup(bot: commands.Bot) -> None:
    cog = ApplicationsCommands(bot)
    await bot.add_cog(cog)
