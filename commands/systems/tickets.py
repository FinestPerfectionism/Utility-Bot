import discord
from discord import app_commands
from discord.ext import commands

from constants import (
    CONTESTED_EMOJI_ID,
    DIRECTORS_ROLE_ID,
    MODERATORS_ROLE_ID,
    STAFF_ROLE_ID,
    TICKET_CHANNEL_ID,
)
from core.help import ArgumentInfo, RoleConfig, help_description
from core.permissions import directors_only, main_guild_only
from core.state.blacklist_state import BLACKLIST, save_blacklist
from core.state.ticket_state import (
    THREAD_OPENERS,
    TICKET_CLAIMS,
    TICKET_TYPES,
    save_ticket_state,
    unregister_ticket,
)
from core.utils import send_minor_error
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
                name = "Add",
                value = "add",
            ),
            app_commands.Choice(
                name = "Remove",
                value = "remove",
            ),
        ],
    )
    @help_description(
        desc      = "Directors only —— Add or remove a user from the ticket blacklist.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id=DIRECTORS_ROLE_ID)],
        arguments = {
            "action": ArgumentInfo(description="Choose whether to add or remove the blacklist entry.", choices=["Add", "Remove"]),
            "user": ArgumentInfo(description="User to blacklist or unblacklist from tickets."),
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
                    "This user is already blacklisted from Tickets.",
                )
                return

            target_list.append(user_id)
            save_blacklist()

            _ = await interaction.response.send_message(
                f"{user.mention} has been blacklisted from Tickets.",
                ephemeral = True,
            )

        else:
            if user_id not in target_list:
                await send_minor_error(
                    interaction,
                    "This user is not blacklisted from Tickets.",
                )
                return

            target_list.remove(user_id)
            save_blacklist()

            _ = await interaction.response.send_message(
                f"{user.mention} has been removed from the Tickets blacklist.",
                ephemeral = True,
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
    async def archive(self, ctx: commands.Context[commands.Bot]) -> None:
        channel = ctx.channel

        if not isinstance(channel, discord.Thread):
            _ = await ctx.send(
               f"{CONTESTED_EMOJI_ID} **Failed to archive ticket!**\n"
                "This command can only be used in a ticket thread.",
            )
            return

        if channel.parent is None or channel.parent.id != TICKET_CHANNEL_ID:
            _ = await ctx.send(
               f"{CONTESTED_EMOJI_ID} **Failed to archive ticket!**\n"
                "This command can only be used in a ticket thread.",
            )
            return

        if not isinstance(ctx.author, discord.Member):
            return

        guild = ctx.guild
        if guild is None:
            return

        mod_role = guild.get_role(MODERATORS_ROLE_ID)
        is_mod   = mod_role is not None and mod_role in ctx.author.roles

        opener_id = THREAD_OPENERS.get(channel.id)

        if not is_mod and ctx.author.id != opener_id:
            _ = await ctx.send(
               f"{CONTESTED_EMOJI_ID} **Failed to archive ticket!**\n"
                "Only the ticket opener or a moderator can close this ticket.",
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
    async def claim(self, ctx: commands.Context[commands.Bot]) -> None:
        channel = ctx.channel

        if not isinstance(channel, discord.Thread):
            _ = await ctx.send(
               f"{CONTESTED_EMOJI_ID} **Failed to claim ticket!**\n"
                "This command can only be used in a ticket thread.",
            )
            return

        if channel.parent is None or channel.parent.id != TICKET_CHANNEL_ID:
            _ = await ctx.send(
               f"{CONTESTED_EMOJI_ID} **Failed to claim ticket!**\n"
                "This command can only be used in a ticket thread.",
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
            _ = await ctx.send(
               f"{CONTESTED_EMOJI_ID} **Failed to claim ticket!**\n"
                "Only moderators can claim tickets.",
            )
            return

        existing_claimer_id = TICKET_CLAIMS.get(channel.id)
        if existing_claimer_id == ctx.author.id:
            _ = await ctx.send(
               f"{CONTESTED_EMOJI_ID} **Failed to claim ticket!**\n"
                "You have already claimed this ticket.",
            )
            return

        TICKET_CLAIMS[channel.id] = ctx.author.id
        save_ticket_state()
        _ = await ctx.send(
            f"{CONTESTED_EMOJI_ID} **Successfully claimed ticket!**\n"
            f"Ticket claimed by {ctx.author.mention}.",
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .escalate/.esc/.e Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name    = "escalate",
        aliases = ["e", "esc"],
    )
    @help_description(
        desc = "Moderators only —— Escalates the current ticket thread to Directors.",
        prefix  = True,
        slash   = False,
        aliases = ["e", "esc"],
    )
    async def escalate(self, ctx: commands.Context[commands.Bot]) -> None:
        channel = ctx.channel

        if not isinstance(channel, discord.Thread):
            _ = await ctx.send(
               f"{CONTESTED_EMOJI_ID} **Failed to escalate ticket!**\n"
                "This command can only be used in a ticket thread.",
            )
            return

        if channel.parent is None or channel.parent.id != TICKET_CHANNEL_ID:
            _ = await ctx.send(
               f"{CONTESTED_EMOJI_ID} **Failed to escalate ticket!**\n"
                "This command can only be used in a ticket thread.",
            )
            return

        if not isinstance(ctx.author, discord.Member):
            return

        guild = ctx.guild
        if guild is None:
            return

        mod_role = guild.get_role(MODERATORS_ROLE_ID)
        if mod_role is None or mod_role not in ctx.author.roles:
            _ = await ctx.send(
               f"{CONTESTED_EMOJI_ID} **Failed to escalate ticket!**\n"
                "Only moderators can escalate tickets.",
            )
            return

        if TICKET_TYPES.get(channel.id) != "moderator":
            _ = await ctx.send(
               f"{CONTESTED_EMOJI_ID} **Failed to escalate ticket!**\n"
                "This ticket is not a moderator ticket or is already escalated.",
            )
            return

        opener_id = THREAD_OPENERS.get(channel.id)
        if opener_id is None:
            _ = await ctx.send(
               f"{CONTESTED_EMOJI_ID} **Failed to escalate ticket!**\n"
                "This ticket does not have a parsed opener. The ticket may not be tracked.",
            )
            return

        try:
            opener  = guild.get_member(opener_id) or await guild.fetch_member(opener_id)
            new_name = f"dir-ticket · {opener.display_name}"[:100]
        except (discord.NotFound, discord.HTTPException):
            new_name = f"dir-ticket · {channel.name.removeprefix('ticket · ')}"[:100]

        TICKET_TYPES[channel.id] = "director"
        save_ticket_state()

        _ = await channel.edit(name = new_name)

        director_role = guild.get_role(DIRECTORS_ROLE_ID)
        if director_role:
            _ = await channel.send(director_role.mention)

        _ = await ctx.send(
           f"{CONTESTED_EMOJI_ID} **Successfully escalated ticket!**\n"
            "Ticket has been escalated to Directors.",
        )

async def setup(bot: commands.Bot) -> None:
    cog = TicketsCommands(bot)
    await bot.add_cog(cog)
