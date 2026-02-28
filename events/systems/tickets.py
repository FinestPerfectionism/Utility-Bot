import discord
from discord.ext import commands

from core.state import BLACKLIST

from constants import (
    MODERATORS_ROLE_ID,
    DIRECTORS_ROLE_ID,
    STAFF_ROLE_ID,
    COLOR_GREEN,
    ACCEPTED_EMOJI_ID,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Tickets System
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class TicketComponents(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        for item in self.walk_children():
            if isinstance(item, discord.ui.Select):
                if item.custom_id == "ticket:select":
                    item.callback = self.open_ticket

    container1 = discord.ui.Container(
        discord.ui.TextDisplay(
            content=(
                "# Support Tickets\n"
                "Tickets are used to contact the moderation team for support, reports, or questions that cannot be handled publicly.\n\n"
                "- **How to Start:** Open the correct ticket category and clearly explain your issue from the start.\n"
                "- **Be Specific:** Provide usernames, IDs, timestamps, or screenshots if applicable.\n"
                "- **Respect Moderators:** Remain calm and respectful at all times.\n\n"
                "Tickets are handled in the order they are received, and response times may vary.\n\n"
                "**Note:** You may run `.archive` to close your ticket."
            )
        ),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large),
        discord.ui.TextDisplay(
            content=(
                "We look forward to assisting you! Sincerely,\n"
                "-# The Goobers Moderator team."
            )
        ),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large),
        discord.ui.ActionRow(
            discord.ui.Select(
                placeholder="Select ticket type...",
                custom_id="ticket:select",
                options=[
                    discord.SelectOption(
                        label="Contact Moderators",
                        value="moderator",
                        description="Open a ticket with moderators for issues or questions.",
                    ),
                    discord.SelectOption(
                        label="Contact Directors",
                        value="director",
                        description="Open a ticket with Directors for staff issues.",
                    ),
                ],
            ),
        ),
        accent_color=COLOR_GREEN
    )

    async def open_ticket(self, interaction: discord.Interaction):
        if interaction.response.is_done():
            return

        guild = interaction.guild
        if guild is None:
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                f"{CONTESTED_EMOJI_ID} **Failed to open ticket!**\n"
                "Tickets can only be opened in text channels.",
                ephemeral=True,
            )
            return

        user = interaction.user

        if user.id in BLACKLIST["tickets"]:
            await interaction.response.send_message(
                f"{DENIED_EMOJI_ID} **You have been blacklisted from opening tickets!**\n"
                "You are blacklisted from opening tickets. Contact a Director.",
                ephemeral=True,
            )
            return

        if not interaction.data or "values" not in interaction.data:
            return

        ticket_type = interaction.data["values"][0]

        if isinstance(user, discord.Member):
            role_ids = {role.id for role in user.roles}

            if isinstance(user, discord.Member):
                role_ids = {role.id for role in user.roles}

                if DIRECTORS_ROLE_ID in role_ids or STAFF_ROLE_ID in role_ids:
                    await interaction.response.send_message(
                        f"{CONTESTED_EMOJI_ID} **Failed to open ticket!**\n"
                        "Please do not open a ticket as a staff member. Instead, contact a higher up or other directors.",
                        ephemeral=True,
                    )
                    return

        if ticket_type == "moderator":
            thread_name = f"ticket——{user.id}"
            ping_role_id = MODERATORS_ROLE_ID
        else:
            thread_name = f"sd-ticket——{user.id}"
            ping_role_id = DIRECTORS_ROLE_ID

        mod_name = f"ticket——{user.id}"
        dir_name = f"sd-ticket——{user.id}"

        for thread in channel.threads:
            if thread.archived:
                continue

            if thread.name in (mod_name, dir_name):
                await interaction.response.send_message(
                    f"{CONTESTED_EMOJI_ID} **Failed to open ticket!**\n"
                    f"You already have an open ticket: {thread.mention}",
                    ephemeral=True,
                )
                return

        thread = await channel.create_thread(
            name=thread_name,
            type=discord.ChannelType.private_thread,
            invitable=False,
        )

        await thread.add_user(user)

        role = guild.get_role(ping_role_id)
        if role:
            await thread.send(role.mention)

        await interaction.response.send_message(
            f"{ACCEPTED_EMOJI_ID} **Successfully opened ticket!**\n"
            f"Ticket created: {thread.mention}",
            ephemeral=True,
        )

class TicketsSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

async def setup(bot: commands.Bot):
    await bot.add_cog(TicketsSystem(bot))