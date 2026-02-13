import discord
from discord.ext import commands
from discord import app_commands

from core.permissions import directors_only

from constants import (
    COLOR_BLURPLE,
    ACCEPTED_EMOJI_ID,
    DENIED_EMOJI_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Role Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class RoleCommands(
    commands.GroupCog,
    name="role",
    description="Directors only —— Role commands."):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /role permissions Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="permissions",
        description="List all permissions for a selected role."
    )
    @app_commands.describe(
        role="Select a role."
    )
    @directors_only()
    async def rolepermissions(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):
        await interaction.response.defer(ephemeral=False)

        lines = []
        for perm_name, value in role.permissions:
            label = perm_name.replace("_", " ").title()
            mark = ACCEPTED_EMOJI_ID if value else DENIED_EMOJI_ID
            lines.append(f"- {label} {mark}")

        embed = discord.Embed(
            title=f"Permissions for {role.name}",
            description=f"**{role.name}:**\n" + "\n".join(lines),
            color=COLOR_BLURPLE
        )

        await interaction.followup.send(
            embed=embed
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /role permissions-compare Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="permissions-compare",
        description="List all differing permissions for two selected roles."
    )
    @app_commands.rename(role1="role_1", role2="role_2")
    @app_commands.describe(
        role1="Select the first role.",
        role2="Select the second role."
    )
    @directors_only()
    async def rolepermissionscompare(
        self,
        interaction: discord.Interaction,
        role1: discord.Role,
        role2: discord.Role
    ):
        await interaction.response.defer(ephemeral=False)

        diffs_role1 = []
        diffs_role2 = []

        for perm_name, value1 in role1.permissions:
            value2 = getattr(role2.permissions, perm_name)
            if value1 != value2:
                label = perm_name.replace("_", " ").title()
                mark1 = ACCEPTED_EMOJI_ID if value1 else DENIED_EMOJI_ID
                mark2 = ACCEPTED_EMOJI_ID if value2 else DENIED_EMOJI_ID

                diffs_role1.append(f"- {label} {mark1}")
                diffs_role2.append(f"- {label} {mark2}")

        embed = discord.Embed(
            title=f"Permission Differences for {role1.name} and {role2.name}",
            color=COLOR_BLURPLE
        )

        if not diffs_role1:
            embed.description = "Roles have identical permissions."
        else:
            embed.add_field(
                name=role1.name,
                value="\n".join(diffs_role1),
                inline=True
            )
            embed.add_field(
                name=role2.name,
                value="\n".join(diffs_role2),
                inline=True
            )

        await interaction.followup.send(
            embed=embed
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /role members Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="members",
        description="List members based on role possession and human/bot filtering."
    )
    @app_commands.describe(
        role="Select a role.",
        role_filter="Select whether to check who has or who doesn't have the role.",
        person_filter="Select whether to list humans, bots, or both."
    )
    @app_commands.choices(
        role_filter=[
            app_commands.Choice(
                name="Who has",
                value="whohas"
            ),
            app_commands.Choice(
                name="Who doesn't have",
                value="whodoesnthave"
            ),
        ],
        person_filter=[
            app_commands.Choice(
                name="humans",
                value="humans"
            ),
            app_commands.Choice(
                name="bots",
                value="bots"
            ),
            app_commands.Choice(
                name="both",
                value="both"
            ),
        ],
    )
    @directors_only()
    async def members(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        role_filter: app_commands.Choice[str],
        person_filter: app_commands.Choice[str],
    ):
        await interaction.response.defer(ephemeral=False)

        guild = interaction.guild
        if guild is None:
            await interaction.followup.send(
                "Guild not found."
            )
            return

        if role_filter.value == "whohas":
            members = [m for m in guild.members if role in m.roles]
        else:
            members = [m for m in guild.members if role not in m.roles]

        if person_filter.value == "humans":
            members = [m for m in members if not m.bot]
        elif person_filter.value == "bots":
            members = [m for m in members if m.bot]

        if members:
            formatted = "\n".join(f"- {m.display_name}" for m in members)
        else:
            formatted = "No members found."

        await interaction.followup.send(
            f"**Results for role {role.name}:**\n"
            f"```\nFilter: {role_filter.name}, {person_filter.name}\n```\n"
            f"{formatted}"
        )

async def setup(bot: commands.Bot):
    cog = RoleCommands(bot)
    await bot.add_cog(cog)

    assert cog.app_command is not None