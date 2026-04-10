import contextlib

import discord
from discord import app_commands
from discord.ext import commands

from constants import ACCEPTED_EMOJI_ID, CONTESTED_EMOJI_ID, DIRECTORS_ROLE_ID, STAFF_ROLE_ID
from core.help import ArgumentInfo, RoleConfig, help_description
from core.permissions import directors_only, main_guild_only
from core.state.application_state import APPLICATIONS_OPEN, save_application_state
from core.state.blacklist_state import BLACKLIST, save_blacklist
from core.utils import send_minor_error
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
        run_roles = [RoleConfig(role_id=DIRECTORS_ROLE_ID)],
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
            await send_minor_error(
                interaction,
                "You cannot blacklist yourself.",
            )
            return

        guild = interaction.guild
        if guild and isinstance(user, discord.Member):
            staff_role = guild.get_role(STAFF_ROLE_ID)
            if staff_role and staff_role in user.roles:
                await send_minor_error(
                    interaction,
                    "You cannot blacklist staff.",
                )
                return

        if action.value == "add":
            if user_id in target_list:
                await send_minor_error(
                    interaction,
                    "This user is already blacklisted from Applications.",
                )
                return

            target_list.append(user_id)
            save_blacklist()

            _ = await interaction.response.send_message(
                f"{user.mention} has been blacklisted from Applications.",
                ephemeral = True,
            )

        else:
            if user_id not in target_list:
                await send_minor_error(
                    interaction,
                    "This user is not blacklisted from Applications.",
                )
                return

            target_list.remove(user_id)
            save_blacklist()

            _ = await interaction.response.send_message(
                f"{user.mention} has been removed from the Applications blacklist.",
                ephemeral = True,
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
                name = "Administrators",
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
            await send_minor_error(
                interaction,
                f"{application.name} applications are already {state.value}.",
            )
            return

        APPLICATIONS_OPEN[application.value] = new_state
        save_application_state()

        _ = await interaction.response.send_message(
            f"{application.name} applications have been {state.value}.",
            ephemeral = True,
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
    async def cancel(self, ctx: commands.Context[commands.Bot]) -> None:
        if ctx.guild is not None:
            _ = await ctx.send(
              f"{CONTESTED_EMOJI_ID} **Failed to cancel application!**"
                "This command can only be used in DMs.",
            )
            return

        if ctx.author.id not in ACTIVE_APPLICATIONS:
            _ = await ctx.send(
               f"{CONTESTED_EMOJI_ID} **Failed to cancel application!**"
                "This command can only be used with an active application to cancel.",
            )
            return

        with contextlib.suppress(discord.Forbidden, discord.NotFound):
            await ctx.message.delete(delay=300)

        await delete_application_messages(client=self.bot, user_id=ctx.author.id)

        confirm = await ctx.send(
           f"{ACCEPTED_EMOJI_ID} **Successfully cancelled application.**\n"
            "Your application has been cancelled and deleted.",
        )
        await confirm.delete(delay=300)

async def setup(bot: commands.Bot) -> None:
    cog = ApplicationsCommands(bot)
    await bot.add_cog(cog)
