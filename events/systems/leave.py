import discord
from discord.ext import commands

from constants import (
    DIRECTORS_ROLE_ID,
    STAFF_ROLE_ID,
    COLOR_GREEN,
    ACCEPTED_EMOJI_ID,
    CONTESTED_EMOJI_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Leave System
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class LeaveFormatView(discord.ui.LayoutView):
    container = discord.ui.Container( # type: ignore
        discord.ui.TextDisplay( # type: ignore
            content=(
                "# Leave Request Format\n\n"
                "```\n"
                "Beginning Date: MM/DD/YYYY\n"
                "Ending Date:    MM/DD/YYYY\n"
                "Timer:          1w2d3h4m"
                "Reason:         Reason (optional)\n"
                "Type:           Standard / Clean\n"
                "```\n"
                "Leave requests created not following the format above will be ignored."
            )
        ),
        accent_color = COLOR_GREEN,
    )

class LeaveComponents(discord.ui.LayoutView):
    def __init__(self) -> None:
        super().__init__(timeout = None)
        for item in self.walk_children():
            if isinstance(item, discord.ui.Button):
                if item.custom_id == "leave:open":
                    item.callback = self.open_leave
                elif item.custom_id == "leave:format":
                    item.callback = self.format_leave

    container = discord.ui.Container( # type: ignore
        discord.ui.TextDisplay( # type: ignore
            content=(
                "# Staff Leave\n"
                "When you plan to be unavailable for a period of time, you must notify directors using this channel. This system exists solely to track staff availability and ensure operational coverage. Taking leave is expected and acceptable, provided it is communicated properly.\n\n"
                "When submitting a leave request, include the following information:\n\n"
                "- **Beginning Date:** The exact date your leave will begin.\n"
                "   - **Note:** If you will be going on leave effective immediately, do __not__ provide a beginning date.\n"
                "- **Ending Date:** The exact date your leave will end.\n"
                "   - **Note:** If you do not know when you will return, do __not__ provide an ending date.\n"
                "- **Timer:** A timer for your leave (incompatible with ending date).\n"
                "- **Reason:** A reason for your leave (optional).\n\n"
                "## Types of Leave\n\n"
                "- **Standard:** Places you on personal leave while retaining your staff roles. This is used when you are temporarily unavailable but will resume normal duties after your leave ends.\n"
                "- **Clean:** Temporarily removes all staff roles while you are on leave. Your roles will automatically be restored when your leave ends.\n\n"
                "**Note:** If you do not have the personal leave role, you are expected to be online and active."
            )

        ),
        discord.ui.Separator(visible = True, spacing = discord.SeparatorSpacing.large), # type: ignore
        discord.ui.TextDisplay( # type: ignore
            content="Sincerely,\n-# The Goobers Directorate team."
        ),
        discord.ui.Separator(visible = True, spacing = discord.SeparatorSpacing.large), # type: ignore
        discord.ui.ActionRow( # type: ignore
            discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="Open Leave Request",
                custom_id="leave:open",
            ),
            discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="Leave Request Format",
                custom_id="leave:format",
            )
        ),
        accent_color = COLOR_GREEN,
    )

    async def format_leave(self, interaction: discord.Interaction) -> None:
        if interaction.response.is_done():
            return

        _ = await interaction.response.send_message(
            view      = LeaveFormatView(),
            ephemeral = True,
        )

    async def open_leave(self, interaction: discord.Interaction) -> None:
        if interaction.response.is_done():
            return

        guild = interaction.guild
        if guild is None:
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            _ = await interaction.response.send_message(
                f"{CONTESTED_EMOJI_ID} **Failed to open leave request!**\n"
                "Leave requests can only be opened in text channels.",
                ephemeral = True,
            )
            return

        user = interaction.user

        if isinstance(user, discord.Member):
            role_ids = {role.id for role in user.roles}

            if DIRECTORS_ROLE_ID in role_ids:
                _ = await interaction.response.send_message(
                    f"{CONTESTED_EMOJI_ID} **Failed to open leave request!**\n"
                    "Please do not open a leave request as a Director. Instead, contact other Directors in the proper union and use `/leave add` with the proper arguments.",
                    ephemeral = True,
                )
                return

            if STAFF_ROLE_ID not in role_ids:
                _ = await interaction.response.send_message(
                    f"{CONTESTED_EMOJI_ID} **Failed to open leave request!**\n"
                    "Please do not open a leave request while not existing within the Staff team.",
                    ephemeral = True,
                )
                return

        for thread in channel.threads:
            if thread.name == f"Leave —— {user.id}" and not thread.archived:
                _ = await interaction.response.send_message(
                    f"{CONTESTED_EMOJI_ID} **Failed to open leave request!**\n"
                    f"Please do not open a leave request while you already have an open leave request: {thread.mention}",
                    ephemeral = True,
                )
                return

        thread = await channel.create_thread(
            name = f"Leave —— {user.id}",
            type=discord.ChannelType.private_thread,
            invitable=False,
        )

        await thread.add_user(user)

        director_role = guild.get_role(DIRECTORS_ROLE_ID)
        if director_role:
            _ = await thread.send(director_role.mention)

        _ = await interaction.response.send_message(
            f"{ACCEPTED_EMOJI_ID} **Successfully opened leave request.**\n"
            f"Thread: {thread.mention}",
            ephemeral = True,
        )

class LeaveSystem(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LeaveSystem(bot))