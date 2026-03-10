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
from core.ticket_state import (
    THREAD_OPENERS,
    TICKET_CLAIMS,
    TICKET_TYPES,
    unregister_ticket,
    save_ticket_state,
)
from core.utils import send_minor_error

from events.systems.applications import (
    delete_application_messages,
    ACTIVE_APPLICATIONS
)
from events.systems.tickets import stop_resolution

from constants import (
    DIRECTORS_ROLE_ID,
    MODERATORS_ROLE_ID,

    TICKET_CHANNEL_ID
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Applications & Tickets Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ApplicationsTicketsCommands(
    commands.GroupCog,
    name="app-tickets",
    description="Moderators only —— Applications and tickets commands."
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /blacklist Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="blacklist",
        description="Blacklist or un-blacklist a user from applications or tickets."
    )
    @app_commands.describe(
        action="Add or remove a blacklist.",
        scope="What the blacklist applies to.",
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
        ],
        scope=[
            app_commands.Choice(
                name="Applications",
                value="applications"
            ),
            app_commands.Choice(
                name="Tickets",
                value="tickets"
            )
        ]
    )
    @main_guild_only()
    @directors_only()
    async def blacklist(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        scope: app_commands.Choice[str],
        user: discord.User
    ) -> None:
        user_id = user.id
        target_list = BLACKLIST[scope.value]

        if interaction.user.id == user.id:
            await send_minor_error(
                interaction,
                "You cannot blacklist yourself.",
            )
            return

        guild = interaction.guild
        if guild and isinstance(user, discord.Member):
            staff_role = guild.get_role(DIRECTORS_ROLE_ID)
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
                    f"This user is already blacklisted in {scope.name}.",
                )
                return

            target_list.append(user_id)
            save_blacklist()

            await interaction.response.send_message(
                f"{user.mention} has been blacklisted from {scope.name}.",
                ephemeral=True
            )

        else:
            if user_id not in target_list:
                await send_minor_error(
                    interaction,
                    f"This user is not blacklisted in {scope.name}.",
                )
                return

            target_list.remove(user_id)
            save_blacklist()

            await interaction.response.send_message(
                f"{user.mention} has been removed from the {scope.name} blacklist.",
                ephemeral=True
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .archive/.a Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name="archive",
        aliases=["a"]
    )
    async def archive(self, ctx: commands.Context[commands.Bot]) -> None:
        channel = ctx.channel

        if not isinstance(channel, discord.Thread):
            await ctx.send(
                "This command can only be used in a ticket thread."
            )
            return

        if channel.parent is None or channel.parent.id != TICKET_CHANNEL_ID:
            await ctx.send(
                "This command can only be used in a ticket thread."
            )
            return

        if not isinstance(ctx.author, discord.Member):
            return

        guild = ctx.guild
        if guild is None:
            return

        mod_role = guild.get_role(MODERATORS_ROLE_ID)
        is_mod = mod_role is not None and mod_role in ctx.author.roles

        opener_id = THREAD_OPENERS.get(channel.id)

        if not is_mod and ctx.author.id != opener_id:
            await ctx.send(
                "Only the ticket opener or a moderator can close this ticket."
            )
            return

        stop_resolution(channel.id)
        unregister_ticket(channel.id)
        await ctx.send("Archiving ticket.")
        await channel.edit(locked=True, archived=True)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .claim/.c Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="claim")
    async def claim(self, ctx: commands.Context[commands.Bot]) -> None:
        channel = ctx.channel

        if not isinstance(channel, discord.Thread):
            await ctx.send(
                "This command can only be used in a ticket thread."
            )
            return

        if channel.parent is None or channel.parent.id != TICKET_CHANNEL_ID:
            await ctx.send(
                "This command can only be used in a ticket thread."
            )
            return

        if not isinstance(ctx.author, discord.Member):
            return

        guild = ctx.guild
        if guild is None:
            return

        mod_role = guild.get_role(MODERATORS_ROLE_ID)
        director_role = guild.get_role(DIRECTORS_ROLE_ID)
        is_staff = (
            (mod_role is not None and mod_role in ctx.author.roles)
            or (director_role is not None and director_role in ctx.author.roles)
        )

        if not is_staff:
            await ctx.send(
                "Only moderators and directors can claim tickets."
            )
            return

        existing_claimer_id = TICKET_CLAIMS.get(channel.id)
        if existing_claimer_id == ctx.author.id:
            await ctx.send(
                "You have already claimed this ticket."
            )
            return

        TICKET_CLAIMS[channel.id] = ctx.author.id
        save_ticket_state()
        await ctx.send(
            f"Ticket claimed by {ctx.author.mention}."
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /state-modify Command
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
        new_state = state.value == "open"
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

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .escalate/.esc/.e Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name="escalate",
        aliases=["e", "esc"]
    )
    async def escalate(self, ctx: commands.Context[commands.Bot]) -> None:
        channel = ctx.channel

        if not isinstance(channel, discord.Thread):
            await ctx.send(
                "This command can only be used in a ticket thread."
            )
            return

        if channel.parent is None or channel.parent.id != TICKET_CHANNEL_ID:
            await ctx.send(
                "This command can only be used in a ticket thread."
            )
            return

        if not isinstance(ctx.author, discord.Member):
            return

        guild = ctx.guild
        if guild is None:
            return

        mod_role = guild.get_role(MODERATORS_ROLE_ID)
        if mod_role is None or mod_role not in ctx.author.roles:
            await ctx.send(
                "Only moderators can escalate tickets."
            )
            return

        if TICKET_TYPES.get(channel.id) != "moderator":
            await ctx.send(
                "This ticket is not a moderator ticket or is already escalated."
            )
            return

        opener_id = THREAD_OPENERS.get(channel.id)
        if opener_id is None:
            await ctx.send(
                "Could not find the ticket opener. The ticket may not be tracked."
            )
            return

        try:
            opener = guild.get_member(opener_id) or await guild.fetch_member(opener_id)
            new_name = f"dir-ticket · {opener.display_name}"[:100]
        except (discord.NotFound, discord.HTTPException):
            new_name = f"dir-ticket · {channel.name.removeprefix('ticket · ')}"[:100]

        TICKET_TYPES[channel.id] = "director"
        save_ticket_state()

        await channel.edit(name=new_name)

        director_role = guild.get_role(DIRECTORS_ROLE_ID)
        if director_role:
            await channel.send(director_role.mention)

        await ctx.send(
            "Ticket has been escalated to Directors."
        )

async def setup(bot: commands.Bot) -> None:
    cog = ApplicationsTicketsCommands(bot)
    await bot.add_cog(cog)