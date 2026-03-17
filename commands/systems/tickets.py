import discord
from discord.ext import commands
from discord import app_commands

from core.permissions import (
    directors_only,
    main_guild_only
)
from core.state import BLACKLIST
from core.state import save_blacklist
from core.ticket_state import (
    THREAD_OPENERS,
    TICKET_CLAIMS,
    TICKET_TYPES,
    unregister_ticket,
    save_ticket_state,
)
from core.utils import send_minor_error

from events.systems.tickets import stop_resolution

from constants import (
    DIRECTORS_ROLE_ID,
    MODERATORS_ROLE_ID,
    STAFF_ROLE_ID,

    TICKET_CHANNEL_ID
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Tickets Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class TicketsCommands(
    commands.GroupCog,
    name="tickets",
    description="Moderators only —— Tickets commands."
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /tickets blacklist Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="blacklist",
        description="Blacklist or un-blacklist a user from tickets."
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

            await interaction.response.send_message(
                f"{user.mention} has been blacklisted from Tickets.",
                ephemeral=True
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

            await interaction.response.send_message(
                f"{user.mention} has been removed from the Tickets blacklist.",
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
        is_mod   = mod_role is not None and mod_role in ctx.author.roles

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
    # .claim Command
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

        mod_role      = guild.get_role(MODERATORS_ROLE_ID)
        director_role = guild.get_role(DIRECTORS_ROLE_ID)
        is_staff      = (
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
            opener  = guild.get_member(opener_id) or await guild.fetch_member(opener_id)
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
    cog = TicketsCommands(bot)
    await bot.add_cog(cog)