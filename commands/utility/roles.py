import discord
from discord.ext import commands
from discord import app_commands

from core.help import (
    help_description,
    ArgumentInfo,
    RoleConfig
)
from core.permissions import directors_only
from core.utils import send_minor_error

from constants import (
    COLOR_BLURPLE,
    ACCEPTED_EMOJI_ID,
    DENIED_EMOJI_ID,
    DIRECTORS_ROLE_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Role Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class RoleCommands(
    commands.GroupCog,
    name        = "role",
    description = "Directors only —— Role commands."
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /role permissions Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name        = "permissions",
        description = "List all permissions for a selected role."
    )
    @app_commands.rename(perm_filter = "filter")
    @app_commands.describe(
        role        = "The role to list permissions for.",
        perm_filter = "Whether to show enabled, disabled, or all permissions."
    )
    @app_commands.choices(
        perm_filter = [
            app_commands.Choice(name = "All",      value = "all"),
            app_commands.Choice(name = "Enabled",  value = "enabled"),
            app_commands.Choice(name = "Disabled", value = "disabled"),
        ]
    )
    @help_description(
        desc        = "Directors only —— Lists all permissions for a selected role.",
        prefix      = False,
        slash       = True,
        run_roles   = [RoleConfig(role_id = DIRECTORS_ROLE_ID)],
        has_inverse = False,
        arguments   = {
            "role": ArgumentInfo(
                roles       = [DIRECTORS_ROLE_ID],
                required    = True,
                description = "The role to list permissions for."
            ),
            "filter": ArgumentInfo(
                roles       = [DIRECTORS_ROLE_ID],
                required    = False,
                description = "Whether to show enabled, disabled, or all permissions.",
                choices     = ["All", "Enabled", "Disabled"]
            ),
        },
    )
    @directors_only()
    async def rolepermissions(
        self,
        interaction : discord.Interaction,
        role        : discord.Role,
        perm_filter : str = "all",
    ) -> None:
        _ = await interaction.response.defer(ephemeral = False)

        lines: list[str] = []
        for perm_name, value in role.permissions:
            if perm_filter == "enabled" and not value:
                continue
            if perm_filter == "disabled" and value:
                continue
            label : str = perm_name.replace("_", " ").title()
            mark  : str = ACCEPTED_EMOJI_ID if value else DENIED_EMOJI_ID
            lines.append(f"- {label} {mark}")

        embed: discord.Embed = discord.Embed(
            title       = f"Permissions for {role.name}",
            description = f"**{role.name}:**\n" + "\n".join(lines) if lines else "No permissions match this filter.",
            color       = COLOR_BLURPLE
        )

        await interaction.followup.send(embed = embed)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /role permissions-compare Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name        = "permissions-compare",
        description = "List all differing permissions for two selected roles."
    )
    @app_commands.rename(
        role1 = "role-1",
        role2 = "role-2"
    )
    @app_commands.describe(
        role1 = "The first role to compare.",
        role2 = "The second role to compare.",
    )
    @help_description(
        desc        = "Directors only —— Lists all differing permissions for two selected roles.",
        prefix      = False,
        slash       = True,
        run_roles   = [RoleConfig(role_id = DIRECTORS_ROLE_ID)],
        has_inverse = False,
        arguments   = {
            "role-1": ArgumentInfo(
                roles       = [DIRECTORS_ROLE_ID],
                required    = True,
                description = "The first role to compare."
            ),
            "role-2": ArgumentInfo(
                roles       = [DIRECTORS_ROLE_ID],
                required    = True,
                description = "The second role to compare."
            ),
        },
    )
    @directors_only()
    async def rolepermissionscompare(
        self,
        interaction : discord.Interaction,
        role1       : discord.Role,
        role2       : discord.Role
    ) -> None:
        _ = await interaction.response.defer(ephemeral = False)

        diffs_role1 : list[str] = []
        diffs_role2 : list[str] = []

        for perm_name, value1 in role1.permissions:
            value2: bool = getattr(role2.permissions, perm_name)
            if value1 != value2:
                label : str = perm_name.replace("_", " ").title()
                mark1 : str = ACCEPTED_EMOJI_ID if value1 else DENIED_EMOJI_ID
                mark2 : str = ACCEPTED_EMOJI_ID if value2 else DENIED_EMOJI_ID

                diffs_role1.append(f"- {label} {mark1}")
                diffs_role2.append(f"- {label} {mark2}")

        embed: discord.Embed = discord.Embed(
            title = f"Permission Differences for {role1.name} and {role2.name}",
            color = COLOR_BLURPLE
        )

        if not diffs_role1:
            embed.description = "Roles have identical permissions."
        else:
            _ = embed.add_field(
                name   = role1.name,
                value  = "\n".join(diffs_role1),
                inline = True
            )
            _ = embed.add_field(
                name   = role2.name,
                value  = "\n".join(diffs_role2),
                inline = True
            )

        await interaction.followup.send(embed = embed)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /role members Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name        = "members",
        description = "List members based on role possession and human/bot filtering."
    )
    @app_commands.describe(
        role          = "Select a role.",
        role_filter   = "Select whether to check who has or who doesn't have the role.",
        person_filter = "Select whether to list humans, bots, or both."
    )
    @app_commands.rename(
        role_filter   = "role-filter",
        person_filter = "person-filter"
    )
    @app_commands.choices(
        role_filter = [
            app_commands.Choice(
                name  = "Member of",
                value = "whohas"
            ),
            app_commands.Choice(
                name  = "Not a Member of",
                value = "whodoesnthave"
            ),
        ],
        person_filter = [
            app_commands.Choice(
                name  = "Humans",
                value = "humans"
            ),
            app_commands.Choice(
                name  = "Bots",
                value = "bots"
            ),
            app_commands.Choice(
                name  = "Both",
                value = "both"
            ),
        ],
    )
    @help_description(
        desc      = "Directors only —— Lists members by whether they have a role and whether they are humans, bots, or both.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id=DIRECTORS_ROLE_ID)],
        arguments = {
            "role": ArgumentInfo(roles = [DIRECTORS_ROLE_ID], description = "Role to inspect."),
            "role-filter": ArgumentInfo(
                roles       = [DIRECTORS_ROLE_ID],
                description = "Whether to list members who have or do not have the role.",
                choices     = ["Who has", "Who doesnt have"]
            ),
            "person-filter": ArgumentInfo(
                roles       = [DIRECTORS_ROLE_ID],
                description = "Whether to list humans, bots, or both.",
                choices     = ["Humans", "Bots", "Both"]
            ),
        },
    )
    @directors_only()
    async def members(
        self,
        interaction   : discord.Interaction,
        role          : discord.Role,
        role_filter   : app_commands.Choice[str],
        person_filter : app_commands.Choice[str],
    ) -> None:
        _ = await interaction.response.defer(ephemeral = False)

        guild = interaction.guild
        if guild is None:
            await send_minor_error(
                interaction,
                texts    = "This command can only be used in a server.",
                subtitle = "Bad command environment."
            )
            return

        if role_filter.value == "whohas":
            filtered = [m for m in guild.members if role in m.roles]
        else:
            filtered = [m for m in guild.members if role not in m.roles]

        if person_filter.value == "humans":
            filtered = [m for m in filtered if not m.bot]
        elif person_filter.value == "bots":
            filtered = [m for m in filtered if m.bot]

        formatted : str = "\n".join(f"- {m.display_name}" for m in filtered) if filtered else "No members found."

        embed: discord.Embed = discord.Embed(
            title       = f"Members for {role.name}",
            description = formatted,
            color       = COLOR_BLURPLE
        )
        _ = embed.add_field(name = "Role Filter",   value = role_filter.name,   inline = True)
        _ = embed.add_field(name = "Person Filter", value = person_filter.name, inline = True)
        _ = embed.set_footer(text = f"{len(filtered)} member(s) found.")

        await interaction.followup.send(embed = embed)

async def setup(bot: commands.Bot) -> None:
    cog = RoleCommands(bot)
    await bot.add_cog(cog)