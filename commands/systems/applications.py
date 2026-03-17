import discord
from discord.ext import commands
from discord import app_commands

import contextlib

from core.permissions import (
    directors_only,
    main_guild_only
)
from core.state import BLACKLIST
from core.state import (
    APPLICATIONS_OPEN,
    save_application_state,
    save_blacklist
)
from core.utils import send_minor_error

from events.systems.applications import (
    delete_application_messages,
    ACTIVE_APPLICATIONS
)

from constants import STAFF_ROLE_ID

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Applications Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ApplicationsCommands(
    commands.GroupCog,
    name="applications",
    description="Moderators only —— Applications commands."
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /applications blacklist Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="blacklist",
        description="Blacklist or un-blacklist a user from applications."
    )
    @app_commands.describe(
        action="Add or remove a blacklist.",
        user="User to modify."
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(
                name="Add",
                value="add"
            ),
            app_commands.Choice(
                name="Remove",
                value="remove"
            )
        ]
    )
    @main_guild_only()
    @directors_only()
    async def blacklist(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        user: discord.User
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

            await interaction.response.send_message(
                f"{user.mention} has been blacklisted from Applications.",
                ephemeral=True
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

            await interaction.response.send_message(
                f"{user.mention} has been removed from the Applications blacklist.",
                ephemeral=True
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /applications state-modify Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="state-modify",
        description="Open or close staff applications."
    )
    @app_commands.describe(
        application="Which application to modify.",
        state="Application state."
    )
    @app_commands.choices(
        application=[
            app_commands.Choice(
                name="Moderators",
                value="mod"
            ),
            app_commands.Choice(
                name="Administrators",
                value="admin"
            ),
        ],
        state=[
            app_commands.Choice(
                name="Open",
                value="open"
            ),
            app_commands.Choice(
                name="Closed",
                value="closed"
            ),
        ],
    )
    @directors_only()
    async def appmodify(
        self,
        interaction: discord.Interaction,
        application: app_commands.Choice[str],
        state: app_commands.Choice[str],
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

        await interaction.response.send_message(
            f"{application.name} applications have been {state.value}.",
            ephemeral=True,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .cancel Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name="cancel"
    )
    async def cancel(self, ctx: commands.Context[commands.Bot]) -> None:
        if ctx.guild is not None:
            await ctx.send(
                "This command can only be used in DMs."
            )
            return

        if ctx.author.id not in ACTIVE_APPLICATIONS:
            await ctx.send(
                "This command can only be used with an active application to cancel."
            )
            return

        with contextlib.suppress(discord.Forbidden, discord.NotFound):
            await ctx.message.delete(delay=300)

        await delete_application_messages(client=self.bot, user_id=ctx.author.id)

        confirm = await ctx.send(
            "Your application has been cancelled and deleted."
        )
        await confirm.delete(delay=300)

async def setup(bot: commands.Bot) -> None:
    cog = ApplicationsCommands(bot)
    await bot.add_cog(cog)