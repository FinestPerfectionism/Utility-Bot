import asyncio
import time as time_mod

import discord
from discord import ButtonStyle, SeparatorSpacing
from discord.ext import commands
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Modal,
    Select,
    Separator,
    TextDisplay,
    TextInput,
    View,
)
from typing_extensions import override

from constants import (
    COLOR_GREEN,
    DIRECTORS_ROLE_ID,
    MODERATORS_ROLE_ID,
    STAFF_ROLE_ID,
)
from core.responses import send_custom_message
from core.state.blacklist_state import BLACKLIST
from core.state.ticket_state import (
    ACTIVE_TICKETS,
    RESOLUTION_STATE,
    RESOLUTION_STOPPED,
    THREAD_OPENERS,
    TICKET_CLAIMS,
    load_ticket_state,
    register_ticket,
    save_ticket_state,
    unregister_ticket,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Internal State
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

RESOLUTION_TASKS: dict[int, asyncio.Task[None]] = {}
_bot_ref: commands.Bot | None = None

def set_bot(bot : commands.Bot) -> None:
    global _bot_ref
    _bot_ref = bot

def _is_staff(member: discord.Member) -> bool:
    role_ids = {r.id for r in member.roles}
    return MODERATORS_ROLE_ID in role_ids or DIRECTORS_ROLE_ID in role_ids

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Resolution Check System
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

def stop_resolution(thread_id : int) -> None:
    RESOLUTION_STOPPED.add(thread_id)
    _    = RESOLUTION_STATE.pop(thread_id, None)
    task = RESOLUTION_TASKS.pop(thread_id, None)
    if task is not None and not task.done():
        _ = task.cancel()
    save_ticket_state()


async def _run_resolution_checks(
    thread_id        : int,
    user_id          : int,
    bot              : commands.Bot,
    interval_minutes : int = 15,
    delay            : float | None = None,
) -> None:
    await asyncio.sleep(delay if delay is not None else interval_minutes * 60.0)

    while thread_id not in RESOLUTION_STOPPED:
        try:
            channel = bot.get_channel(thread_id)
            if channel is None:
                channel = await bot.fetch_channel(thread_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            break

        if not isinstance(channel, discord.Thread):
            break

        if channel.archived or channel.locked:
            stop_resolution(thread_id)
            break

        _ = await channel.send(
            f"<@{user_id}>, has your issue been resolved?",
            view = ResolutionView(),
        )

        interval_minutes *= 2
        RESOLUTION_STATE[thread_id] = {
            "next_ts"  : time_mod.time() + interval_minutes * 60.0,
            "interval" : interval_minutes,
        }
        save_ticket_state()

        await asyncio.sleep(interval_minutes * 60.0)

    _ = RESOLUTION_TASKS.pop(thread_id, None)

def start_resolution_task(
    thread_id        : int,
    user_id          : int,
    bot              : commands.Bot,
    interval_minutes : int = 15,
    delay            : float | None = None,
) -> None:
    task = asyncio.create_task(
        _run_resolution_checks(
            thread_id        = thread_id,
            user_id          = user_id,
            bot              = bot,
            interval_minutes = interval_minutes,
            delay            = delay,
        ),
    )
    RESOLUTION_TASKS[thread_id] = task


# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Resolution View
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ResolutionView(View):
    def __init__(self) -> None:
        super().__init__(timeout = None)

    @discord.ui.button(
        label     = "Yes",
        style     = ButtonStyle.green,
        custom_id = "resolution:yes",
    )
    async def yes_button(
        self,
        interaction : discord.Interaction,
        _button     : Button[View],
    ) -> None:
        if not isinstance(interaction.channel, discord.Thread):
            return
        if not isinstance(interaction.user, discord.Member):
            return

        channel   = interaction.channel
        opener_id = THREAD_OPENERS.get(channel.id)

        if interaction.user.id != opener_id and not _is_staff(interaction.user):
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "respond to resolution check",
                subtitle = "Only the ticket opener can respond to this.",
            )
            return

        stop_resolution(channel.id)
        unregister_ticket(channel.id)
        await send_custom_message(
            interaction,
            msg_type  = "success",
            title     = "responded to resolution check",
            subtitle  = "Glad your issue was resolved! This ticket will now be archived.",
            ephemeral = False,
        )
        _ = await channel.edit(locked=True, archived=True)

    @discord.ui.button(
        label     = "No",
        style     = ButtonStyle.danger,
        custom_id = "resolution:no",
    )
    async def no_button(
        self,
        interaction : discord.Interaction,
        _button     : Button[View],
    ) -> None:
        if not isinstance(interaction.channel, discord.Thread):
            return

        opener_id = THREAD_OPENERS.get(interaction.channel.id)

        if interaction.user.id != opener_id:
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "respond to resolution check",
                subtitle = "Only the ticket opener can respond to this.",
            )
            return

        await send_custom_message(
            interaction,
            msg_type = "success",
            title    = "responded to resolution check",
            subtitle = "We'll check back in with you later.",
        )


# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Add Member Modal
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class AddMemberModal(Modal, title = "Add Member to Ticket"):
    user_input: TextInput[Modal] = TextInput(
        label       = "User ID",
        placeholder = "Enter a user ID...",
        required    = True,
        max_length  = 20,
    )

    @override
    async def on_submit(self, interaction : discord.Interaction) -> None:
        if not isinstance(interaction.channel, discord.Thread):
            return

        raw = self.user_input.value.strip()
        if raw.startswith("<@") and raw.endswith(">"):
            raw = raw[2:-1].lstrip("!")

        try:
            user_id = int(raw)
        except ValueError:
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "add member to ticket",
                subtitle = "Invalid user ID.",
            )
            return

        guild = interaction.guild
        if guild is None:
            return

        try:
            member = guild.get_member(user_id) or await guild.fetch_member(user_id)
        except (discord.NotFound, discord.HTTPException):
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "add member to ticket",
                subtitle = "User not found in this server.",
            )
            return

        await interaction.channel.add_user(member)
        await send_custom_message(
            interaction,
            msg_type = "success",
            title    = "added member to ticket",
            subtitle = f"Added {member.mention} to the ticket.",
        )


# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Ticket Control Panel
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class TicketControlPanel(LayoutView):
    def __init__(self) -> None:
        super().__init__(timeout = None)
        for item in self.walk_children():
            if not isinstance(item, Button):
                continue
            if item.custom_id == "ticket:panel:archive":
                item.callback = self._archive
            elif item.custom_id == "ticket:panel:lock":
                item.callback = self._lock
            elif item.custom_id == "ticket:panel:close":
                item.callback = self._close
            elif item.custom_id == "ticket:panel:add_members":
                item.callback = self._add_members
            elif item.custom_id == "ticket:panel:claim":
                item.callback = self._claim

    panel_container : Container[LayoutView] = Container(
        TextDisplay(content = "# Ticket Controls"),
        ActionRow(
            Button(
                label     = "Archive Ticket",
                style     = ButtonStyle.red,
                custom_id = "ticket:panel:archive",
            ),
            Button(
                label     = "Lock Ticket",
                style     = ButtonStyle.grey,
                custom_id = "ticket:panel:lock",
            ),
            Button(
                label     = "Close Ticket",
                style     = ButtonStyle.grey,
                custom_id = "ticket:panel:close",
            ),
        ),
        ActionRow(
            Button(
                label     = "Add Members",
                style     = ButtonStyle.blurple,
                custom_id = "ticket:panel:add_members",
            ),
            Button(
                label     = "Claim",
                style     = ButtonStyle.green,
                custom_id = "ticket:panel:claim",
            ),
        ),
        accent_color = COLOR_GREEN,
    )

    async def _archive(self, interaction : discord.Interaction) -> None:
        if not isinstance(interaction.channel, discord.Thread):
            return
        if not isinstance(interaction.user, discord.Member):
            return

        channel   = interaction.channel
        opener_id = THREAD_OPENERS.get(channel.id)

        if not _is_staff(interaction.user) and interaction.user.id != opener_id:
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "archive ticket",
                subtitle = "Only the ticket opener or a moderator can archive this ticket.",
            )
            return

        stop_resolution(channel.id)
        unregister_ticket(channel.id)
        await send_custom_message(
            interaction,
            msg_type  = "success",
            title     = "archived ticket",
            ephemeral = False,
        )
        _ = await channel.edit(locked=True, archived=True)

    async def _lock(self, interaction : discord.Interaction) -> None:
        if not isinstance(interaction.channel, discord.Thread):
            return
        if not isinstance(interaction.user, discord.Member):
            return

        if not _is_staff(interaction.user):
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "lock ticket",
                subtitle = "Only moderators can lock this ticket.",
            )
            return

        stop_resolution(interaction.channel.id)
        await send_custom_message(
            interaction,
            msg_type  = "success",
            title     = "locked ticket",
            ephemeral = False,
        )
        _ = await interaction.channel.edit(locked=True)

    async def _close(self, interaction : discord.Interaction) -> None:
        if not isinstance(interaction.channel, discord.Thread):
            return
        if not isinstance(interaction.user, discord.Member):
            return

        if not _is_staff(interaction.user):
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "close ticket",
                subtitle = "Only moderators can close this ticket.",
            )
            return

        channel = interaction.channel
        stop_resolution(channel.id)
        unregister_ticket(channel.id)
        await send_custom_message(
            interaction,
            msg_type  = "success",
            title     = "closed ticket",
            ephemeral = False,
        )
        _ = await interaction.channel.edit(archived=True)

    async def _add_members(self, interaction : discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            return

        if not _is_staff(interaction.user):
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "add member to ticket",
                subtitle = "Only moderators can add members to tickets.",
            )
            return

        _ = await interaction.response.send_modal(AddMemberModal())

    async def _claim(self, interaction : discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        if not isinstance(interaction.channel, discord.Thread):
            return

        if not _is_staff(interaction.user):
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "claim ticket",
                subtitle = "Only moderators can claim tickets.",
            )
            return

        channel            = interaction.channel
        existing_claimer_id = TICKET_CLAIMS.get(channel.id)

        if existing_claimer_id == interaction.user.id:
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "claim ticket",
                subtitle = "You have already claimed this ticket.",
            )
            return

        TICKET_CLAIMS[channel.id] = interaction.user.id
        save_ticket_state()
        await send_custom_message(
            interaction,
            msg_type  = "success",
            title     = "claimed ticket",
            subtitle  = f"Ticket claimed by {interaction.user.mention}.",
            ephemeral = False,
        )


# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Ticket Opener
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class TicketComponents(LayoutView):
    def __init__(self) -> None:
        super().__init__(timeout = None)
        for item in self.walk_children():
            if isinstance(item, Select) and item.custom_id == "ticket:select":
                item.callback = self.open_ticket

    container : Container[LayoutView] = Container(
        TextDisplay(
            content =
                "# Support Tickets\n"
                "Tickets are used to contact the moderation team for support, reports, or questions that cannot be handled publicly.\n\n"
                "- **How to Start:** Open the correct ticket category and clearly explain your issue from the start.\n"
                "- **Be Specific:** Provide usernames, IDs, timestamps, or screenshots if applicable.\n"
                "- **Respect Moderators:** Remain calm and respectful at all times.\n\n"
                "Tickets are handled in the order they are received, and response times may vary.\n\n"
                "**Note:** You may run `.archive` to close your ticket.",
        ),
        Separator(visible = True, spacing = SeparatorSpacing.large),
        TextDisplay(
            content =
                "We look forward to assisting you! Sincerely,\n"
                "-# The Goobers Moderator team.",
        ),
        Separator(visible = True, spacing = SeparatorSpacing.large),
        ActionRow(
            Select(
                placeholder = "Select ticket type...",
                custom_id   = "ticket:select",
                options     = [
                    discord.SelectOption(
                        label       = "Contact Moderators",
                        value       = "moderator",
                        description = "Open a ticket with moderators for issues or questions.",
                    ),
                    discord.SelectOption(
                        label       = "Contact Directors",
                        value       = "director",
                        description = "Open a ticket with Directors for staff issues.",
                    ),
                ],
            ),
        ),
        accent_color = COLOR_GREEN,
    )

    async def open_ticket(self, interaction : discord.Interaction) -> None:
        if interaction.response.is_done():
            return

        guild = interaction.guild
        if guild is None:
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "open ticket",
                subtitle = "Tickets can only be opened in text channels.",
            )
            return

        user = interaction.user

        if user.id in BLACKLIST["tickets"]:
            await send_custom_message(
                interaction,
                msg_type = "error",
                title    = "open ticket",
                subtitle = "You are blacklisted from opening tickets. Contact a Director.",
            )
            return

        if not interaction.data or "values" not in interaction.data:
            return

        ticket_type = interaction.data["values"][0]

        if isinstance(user, discord.Member):
            role_ids = {role.id for role in user.roles}
            if DIRECTORS_ROLE_ID in role_ids:
                await send_custom_message(
                    interaction,
                    msg_type = "warning",
                    title    = "open ticket",
                    subtitle = "Directors may not open tickets of any type.",
                )
                return
            if STAFF_ROLE_ID in role_ids and ticket_type == "moderator":
                await send_custom_message(
                    interaction,
                    msg_type = "warning",
                    title    = "open ticket",
                    subtitle = "Staff members may only open director tickets.",
                )
                return

        if user.id in ACTIVE_TICKETS:
            existing_thread_id = ACTIVE_TICKETS[user.id]
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "open ticket",
                subtitle = f"You already have an open ticket: <#{existing_thread_id}>",
            )
            return

        if ticket_type == "moderator":
            thread_name  = f"ticket · {user.display_name}"[:100]
            ping_role_id = MODERATORS_ROLE_ID
        else:
            thread_name  = f"dir-ticket · {user.display_name}"[:100]
            ping_role_id = DIRECTORS_ROLE_ID

        thread = await channel.create_thread(
            name      = thread_name,
            type      = discord.ChannelType.private_thread,
            invitable = False,
        )

        await thread.add_user(user)

        register_ticket(user.id, thread.id, ticket_type)

        role = guild.get_role(ping_role_id)
        if role:
            _ = await thread.send(role.mention)

        _ = await thread.send(view = TicketControlPanel())

        bot = _bot_ref
        if bot is not None:
            RESOLUTION_STATE[thread.id] = {
                "next_ts"  : time_mod.time() + 15 * 60.0,
                "interval" : 15,
            }
            save_ticket_state()
            start_resolution_task(
                thread_id = thread.id,
                user_id   = user.id,
                bot       = bot,
            )

        await send_custom_message(
            interaction,
            msg_type = "success",
            title    = "opened ticket",
            subtitle = f"Ticket created: {thread.mention}",
        )


# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Tickets System Cog
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class TicketsSystem(commands.Cog):
    def __init__(self, bot : commands.Bot) -> None:
        self.bot = bot

    @override
    async def cog_load(self) -> None:
        load_ticket_state()
        set_bot(self.bot)
        self.bot.add_view(TicketComponents())
        self.bot.add_view(TicketControlPanel())
        self.bot.add_view(ResolutionView())

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        now = time_mod.time()
        for thread_id, state in list(RESOLUTION_STATE.items()):
            if thread_id in RESOLUTION_STOPPED:
                continue
            if thread_id in RESOLUTION_TASKS:
                continue

            user_id = THREAD_OPENERS.get(thread_id)
            if user_id is None:
                continue

            remaining = max(0.0, state["next_ts"] - now)
            interval  = state.get("interval", 15)

            start_resolution_task(
                thread_id        = thread_id,
                user_id          = user_id,
                bot              = self.bot,
                interval_minutes = interval,
                delay            = remaining,
            )


async def setup(bot : commands.Bot) -> None:
    await bot.add_cog(TicketsSystem(bot))
