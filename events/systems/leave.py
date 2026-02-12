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

class LeaveComponents(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        for item in self.walk_children():
            if isinstance(item, discord.ui.Button):
                if item.custom_id == "leave:open":
                    item.callback = self.open_leave

    container1 = discord.ui.Container(
        discord.ui.TextDisplay(
            content=(
                "# Staff Leave\n"
                "When you plan to be unavailable for a period of time, you must notify directors using this channel. "
                "This system exists solely to track staff availability and ensure operational coverage. "
                "Taking leave is expected and acceptable, provided it is communicated properly.\n\n"
                "- **Beginning Date:** The exact date you will begin your leave.\n"
                "- **Ending Date:** The exact date you will be available again.\n"
                "- **Reason:** A reason for your leave (optional).\n\n"
                "**Note:** If you do not have the personal leave role, you are expected to be online and active."
            )
        ),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large),
        discord.ui.TextDisplay(
            content="Sincerely,\n-# The Goobers Directorate team."
        ),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large),
        discord.ui.ActionRow(
            discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="Open Leave Request",
                custom_id="leave:open",
            )
        ),
        accent_color=COLOR_GREEN,
    )

    async def open_leave(self, interaction: discord.Interaction):
        if interaction.response.is_done():
            return

        guild = interaction.guild
        if guild is None:
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                f"{CONTESTED_EMOJI_ID} **Failed to open leave request!**\n"
                "Leave requests can only be opened in text channels.",
                ephemeral=True,
            )
            return

        user = interaction.user

        if isinstance(user, discord.Member):
            role_ids = {role.id for role in user.roles}

            if DIRECTORS_ROLE_ID in role_ids:
                await interaction.response.send_message(
                    f"{CONTESTED_EMOJI_ID} **Failed to open leave request!**\n"
                    "Please do not open a leave request as a Director. Instead, contact other Directors in the proper union.",
                    ephemeral=True,
                )
                return

            if STAFF_ROLE_ID not in role_ids:
                await interaction.response.send_message(
                    f"{CONTESTED_EMOJI_ID} **Failed to open leave request!**\n"
                    "Please do not open a leave request while not existing within the Staff team.",
                    ephemeral=True,
                )
                return

        for thread in channel.threads:
            if thread.name == f"Leave —— {user.id}" and not thread.archived:
                await interaction.response.send_message(
                    f"{CONTESTED_EMOJI_ID} **Failed to open leave request!**\n"
                    f"Please do not open a leave request while you already have an open leave request: {thread.mention}",
                    ephemeral=True,
                )
                return

        thread = await channel.create_thread(
            name=f"Leave —— {user.id}",
            type=discord.ChannelType.private_thread,
            invitable=False,
        )

        await thread.add_user(user)

        director_role = guild.get_role(DIRECTORS_ROLE_ID)
        if director_role:
            await thread.send(director_role.mention)

        await interaction.response.send_message(
            f"{ACCEPTED_EMOJI_ID} **Successfully created leave request!**\n"
            f"Thread: {thread.mention}",
            ephemeral=True,
        )

class Leave(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

async def setup(bot: commands.Bot):
    await bot.add_cog(Leave(bot))