import discord
from discord import app_commands
from discord.ext import commands

from constants import (
    DIRECTORS_ROLE_ID,
    MODERATORS_ROLE_ID,
    STAFF_ROLE_ID,
    TICKET_CHANNEL_ID,
)
from core.help import ArgumentInfo, RoleConfig, help_description
from core.permissions import directors_only, main_guild_only
from core.responses import send_custom_message
from core.state.blacklist_state import BLACKLIST, save_blacklist
from core.state.ticket_state import (
    THREAD_OPENERS,
    TICKET_CLAIMS,
    TICKET_TYPES,
    save_ticket_state,
    unregister_ticket,
)
from events.systems.tickets import stop_resolution

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Tickets Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class TicketsCommands(
    commands.GroupCog,
    name        = "tickets",
    description = "Moderators only —— Tickets commands.",
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /tickets blacklist Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name        = "blacklist",
        description = "Blacklist or un-blacklist a user from tickets.",
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
        desc      = "Directors only —— Add or remove a user from the ticket blacklist.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id = DIRECTORS_ROLE_ID)],
        arguments = {
            "action": ArgumentInfo(description = "Choose whether to add or remove the blacklist entry.", choices=["Add", "Remove"]),
            "user":   ArgumentInfo(description = "User to blacklist or unblacklist from tickets."),
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
        target_list = BLACKLIST["tickets"]

        if interaction.user.id == user.id:
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "modify blacklist",
                subtitle = "You cannot blacklist yourself.",
                footer   = "Bad request",
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
                    footer   = "Bad request",
                )
                return

        if action.value == "add":
            if user_id in target_list:
                await send_custom_message(
                    interaction,
                    msg_type = "warning",
                    title    = "modify blacklist",
                    subtitle = "This user is already blacklisted from Tickets.",
                    footer   = "Bad argument",
                )
                return

            target_list.append(user_id)
            save_blacklist()

            await send_custom_message(
                interaction,
                msg_type = "success",
                title    = f"blacklisted {user.mention} from Tickets",
            )

        else:
            if user_id not in target_list:
                await send_custom_message(
                    interaction,
                    msg_type = "warning",
                    title    = "modify blacklist",
                    subtitle = "This user is not blacklisted from Tickets.",
                    footer   = "Bad argument",
                )
                return

            target_list.remove(user_id)
            save_blacklist()

            await send_custom_message(
                interaction,
                msg_type = "success",
                title    = f"un-blacklisted {user.mention} from Tickets",
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .archive/.a Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name    = "archive",
        aliases = ["a"],
    )
    @help_description(
        desc    = "Moderators only —— Archives the current ticket thread. Only the ticket opener or a moderator can use it inside a ticket thread.",
        prefix  = True,
        slash   = False,
        aliases = ["a"],
    )
    async def archive(self, ctx : commands.Context[commands.Bot]) -> None:
        channel = ctx.channel

        if not isinstance(channel, discord.Thread):
            await send_custom_message(
                ctx,
                msg_type = "warning",
                title    = "archive ticket",
                subtitle = "This command can only be used in a ticket thread.",
                footer   = "Bad environment",
            )
            return

        if channel.parent is None or channel.parent.id != TICKET_CHANNEL_ID:
            await send_custom_message(
                ctx,
                msg_type = "warning",
                title    = "archive ticket",
                subtitle = "This command can only be used in a ticket thread.",
                footer   = "Bad environment",
            )
            return

        if not isinstance(ctx.author, discord.Member):
            return

        guild = ctx.guild
        if guild is None:
            return

        mod_role  = guild.get_role(MODERATORS_ROLE_ID)
        is_mod    = mod_role is not None and mod_role in ctx.author.roles
        opener_id = THREAD_OPENERS.get(channel.id)

        if not is_mod and ctx.author.id != opener_id:
            await send_custom_message(
                ctx,
                msg_type = "error",
                title    = "run command",
                subtitle = "You are not authorized to run this command.",
                footer   = "No permissions",
            )
            return

        stop_resolution(channel.id)
        unregister_ticket(channel.id)
        _ = await ctx.send("Archiving ticket.")
        _ = await channel.edit(locked=True, archived=True)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .claim Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name = "claim")
    @help_description(
        desc   = "Moderators only —— Claims the current ticket thread.",
        prefix = True,
        slash  = False,
    )
    async def claim(self, ctx : commands.Context[commands.Bot]) -> None:
        channel = ctx.channel

        if not isinstance(channel, discord.Thread):
            await send_custom_message(
                ctx,
                msg_type = "warning",
                title    = "claim ticket",
                subtitle = "This command can only be used in a ticket thread.",
                footer   = "Bad environment",
            )
            return

        if channel.parent is None or channel.parent.id != TICKET_CHANNEL_ID:
            await send_custom_message(
                ctx,
                msg_type = "warning",
                title    = "claim ticket",
                subtitle = "This command can only be used in a ticket thread.",
                footer   = "Bad environment",
            )
            return

        if not isinstance(ctx.author, discord.Member):
            return

        guild = ctx.guild
        if guild is None:
            return

        mod_role      = guild.get_role(MODERATORS_ROLE_ID)
        director_role = guild.get_role(DIRECTORS_ROLE_ID)
        is_staff      = (
            (mod_role is not None and mod_role in ctx.author.roles)
            or (director_role is not None and director_role in ctx.author.roles)
        )

        if not is_staff:
            await send_custom_message(
                ctx,
                msg_type = "error",
                title    = "run command",
                subtitle = "You are not authorized to run this command.",
                footer   = "No permissions",
            )
            return

        existing_claimer_id = TICKET_CLAIMS.get(channel.id)
        if existing_claimer_id == ctx.author.id:
            await send_custom_message(
                ctx,
                msg_type = "warning",
                title    = "claim ticket",
                subtitle = "You have already claimed this ticket.",
                footer   = "Bad request",
            )
            return

        TICKET_CLAIMS[channel.id] = ctx.author.id
        save_ticket_state()

        await send_custom_message(
            ctx,
            msg_type = "success",
            title    = f"claimed ticket by {ctx.author.mention}",
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .escalate/.esc/.e Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name    = "escalate",
        aliases = ["e", "esc"],
    )
    @help_description(
        desc    = "Moderators only —— Escalates the current ticket thread to Directors.",
        prefix  = True,
        slash   = False,
        aliases = ["e", "esc"],
    )
    async def escalate(self, ctx : commands.Context[commands.Bot]) -> None:
        channel = ctx.channel

        if not isinstance(channel, discord.Thread):
            await send_custom_message(
                ctx,
                msg_type = "warning",
                title    = "escalate ticket",
                subtitle = "This command can only be used in a ticket thread.",
                footer   = "Bad environment",
            )
            return

        if channel.parent is None or channel.parent.id != TICKET_CHANNEL_ID:
            await send_custom_message(
                ctx,
                msg_type = "warning",
                title    = "escalate ticket",
                subtitle = "This command can only be used in a ticket thread.",
                footer   = "Bad environment",
            )
            return

        if not isinstance(ctx.author, discord.Member):
            return

        guild = ctx.guild
        if guild is None:
            return

        mod_role = guild.get_role(MODERATORS_ROLE_ID)
        if mod_role is None or mod_role not in ctx.author.roles:
            await send_custom_message(
                ctx,
                msg_type = "error",
                title    = "run command",
                subtitle = "You are not authorized to run this command.",
                footer   = "No permissions",
            )
            return

        if TICKET_TYPES.get(channel.id) != "moderator":
            await send_custom_message(
                ctx,
                msg_type = "warning",
                title    = "escalate ticket",
                subtitle = "This ticket is not a moderator ticket or is already escalated.",
                footer   = "Bad request",
            )
            return

        opener_id = THREAD_OPENERS.get(channel.id)
        if opener_id is None:
            await send_custom_message(
                ctx,
                msg_type          = "error",
                title             = "escalate ticket",
                subtitle          = "This ticket does not have a parsed opener. The ticket may not be tracked.",
                footer            = "Invalid IDs",
                contact_bot_owner = True,
            )
            return

        try:
            opener   = guild.get_member(opener_id) or await guild.fetch_member(opener_id)
            new_name = f"dir-ticket · {opener.display_name}"[:100]
        except (discord.NotFound, discord.HTTPException):
            new_name = f"dir-ticket · {channel.name.removeprefix('ticket · ')}"[:100]

        TICKET_TYPES[channel.id] = "director"
        save_ticket_state()

        _ = await channel.edit(name = new_name)

        director_role = guild.get_role(DIRECTORS_ROLE_ID)
        if director_role:
            _ = await channel.send(director_role.mention)

        await send_custom_message(
            ctx,
            msg_type = "success",
            title    = "escalated ticket to Directors",
        )

async def setup(bot: commands.Bot) -> None:
    cog = TicketsCommands(bot)
    await bot.add_cog(cog)
