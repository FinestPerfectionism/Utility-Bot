from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

import discord
from discord import app_commands
from discord.ext import commands

from constants import ACCEPTED_EMOJI_ID, COLOR_GREEN, COLOR_ORANGE, COLOR_RED, DIRECTORS_ROLE_ID
from core.help import ArgumentInfo, RoleConfig, help_description
from core.utils import send_major_error, send_minor_error

if TYPE_CHECKING:
    from events.systems.antinuke import AntiNukeSystem

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Anti-Nuke Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class AntiNukeCommands(commands.Cog):
    def __init__(self, antinuke_system: "AntiNukeSystem") -> None:
        self.antinuke_system = antinuke_system
        self.config          = antinuke_system.config
        self.is_director     = antinuke_system.is_director
        self.save_config     = antinuke_system.save_config

    antinuke_group = app_commands.Group(
        name        = "anti-nuke",
        description = "Directors only —— Anti-nuke management.",
    )

    @antinuke_group.command(
        name        = "status",
        description = "Status of the anti-nuke system.",
    )
    @help_description(
        desc      = "Directors only —— Views the anti-nuke system configuration and per-action limits.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id=DIRECTORS_ROLE_ID)],
    )
    async def antinuke_status(self, interaction : discord.Interaction) -> None:
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.is_director(actor):
            await send_major_error(
                interaction,
                title    = "Unauthorized!",
                texts    = "You lack the necessary permissions to view anti-nuke settings.",
                subtitle = "Invalid permissions.",
            )
            return

        enabled        = self.config.get("enabled", True)
        log_channel_id = self.config.get("log_channel_id")

        embed = discord.Embed(
            title     = "Anti-Nuke Configuration",
            color     = COLOR_GREEN if enabled else COLOR_RED,
            timestamp = datetime.now(UTC),
        )

        status_text = "Enabled" if enabled else "Disabled"
        _ = embed.add_field(
            name   = "Status",
            value  = status_text,
            inline = True,
        )

        if log_channel_id:
            log_channel = interaction.guild.get_channel(log_channel_id) if interaction.guild else None
            _ = embed.add_field(
                name   = "Log Channel",
                value  = log_channel.mention if log_channel else f"<#{log_channel_id}> (deleted)",
                inline = True,
            )
        else:
            _ = embed.add_field(name = "Log Channel", value = "Not configured", inline = True)

        _ = embed.add_field(name = "\u200b", value = "\u200b", inline = False)

        limits = self.config["limits"]
        for action_type, settings in limits.items():
            action_name = action_type.replace("_", " ").title()
            hourly      = settings.get("hourly", "N/A")
            daily       = settings.get("daily", "N/A")
            limit_text  = f"Hourly: {hourly}\nDaily: {daily}"
            _ = embed.add_field(name = action_name, value = limit_text, inline = True)

        _ = embed.set_footer(text="Directors are exempt from all limits")
        _ = await interaction.response.send_message(embed=embed, ephemeral = True)

    @antinuke_group.command(name = "toggle", description = "Enable or disable anti-nuke protection.")
    @help_description(
        desc      = "Directors only —— Toggle anti-nuke system.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id=DIRECTORS_ROLE_ID)],
    )
    async def antinuke_toggle(self, interaction : discord.Interaction) -> None:
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.is_director(actor):
            await send_major_error(
                interaction,
                title    = "Unauthorized!",
                texts    = "You lack the necessary permissions to configure anti-nuke settings.",
                subtitle = "Invalid permissions.",
            )
            return

        self.config["enabled"] = not self.config.get("enabled", True)
        self.save_config()

        status = "enabled" if self.config["enabled"] else "disabled"

        embed = discord.Embed(
            title       = f"{ACCEPTED_EMOJI_ID} Anti-Nuke {status.title()}",
            description = f"Anti-nuke protection has been {status}.",
            color       = COLOR_GREEN if self.config["enabled"] else COLOR_ORANGE,
            timestamp   = datetime.now(UTC),
        )

        _ = await interaction.response.send_message(embed=embed, ephemeral = True)

    @antinuke_group.command(name = "set-limit", description = "Configure limits for a specific action type.")
    @help_description(
        desc = "Directors only —— Set hourly and daily anti-nuke limits for a tracked action type.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id=DIRECTORS_ROLE_ID)],
        arguments = {
            "action" : ArgumentInfo(description = "Tracked action key to configure."),
            "hourly" : ArgumentInfo(description = "Maximum allowed executions per hour."),
            "daily"  : ArgumentInfo(description = "Maximum allowed executions per day, and it must be at least the hourly limit."),
        },
    )
    @app_commands.describe(
        action = "The action type to configure.",
        hourly = "Maximum number of actions allowed per hour.",
        daily  = "Maximum number of actions allowed per day.",
    )
    async def antinuke_setlimit(
        self,
        interaction : discord.Interaction,
        action      : str,
        hourly      : int,
        daily       : int,
    ) -> None:
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.is_director(actor):
            await send_major_error(
                interaction,
                title    = "Unauthorized!",
                texts    = "You lack the necessary permissions to configure anti-nuke settings.",
                subtitle = "Invalid permissions.",
            )
            return

        if action not in self.config["limits"]:
            await send_minor_error(
                interaction,
                f"Invalid action type. Valid types: {', '.join(self.config['limits'].keys())}",
            )
            return

        if hourly < 1:
            await send_minor_error(interaction, "Hourly limit must be at least 1.")
            return

        if daily < hourly:
            await send_minor_error(interaction, "Daily limit must be greater than or equal to hourly limit.")
            return

        self.config["limits"][action] = {
            "hourly": hourly,
            "daily": daily,
        }
        self.save_config()

        embed = discord.Embed(
            title       = f"{ACCEPTED_EMOJI_ID} Limit Updated",
            description = f"Updated limits for {action.replace('_', ' ')}.",
            color       = COLOR_GREEN,
            timestamp   = datetime.now(UTC),
        )
        _ = embed.add_field(name = "Action", value = action.replace("_", " ").title(), inline = True)
        _ = embed.add_field(name = "Hourly Limit", value = str(hourly), inline = True)
        _ = embed.add_field(name = "Daily Limit", value = str(daily), inline = True)

        _ = await interaction.response.send_message(embed=embed, ephemeral = True)

    @antinuke_setlimit.autocomplete("action")
    async def antinuke_setlimit_autocomplete(
        self,
        _interaction : discord.Interaction,
        current      : str,
    ) -> list[app_commands.Choice[str]]:
        actions = list(self.config["limits"].keys())
        return [
            app_commands.Choice(name = action.replace("_", " ").title(), value = action)
            for action in actions
            if current.lower() in action.lower()
        ][:25]

    @antinuke_group.command(name = "configure", description = "Configure the anti-nuke log channel.")
    @help_description(
        desc      = "Directors only —— Configures the channel that receives anti-nuke alerts.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id=DIRECTORS_ROLE_ID)],
        arguments = {"channel": ArgumentInfo(description = "Text channel that should receive anti-nuke alerts.")},
    )
    @app_commands.describe(
        channel = "The channel where anti-nuke alerts will be sent.",
    )
    async def antinuke_config(
        self,
        interaction : discord.Interaction,
        channel     : discord.TextChannel,
    ) -> None:
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.is_director(actor):
            await send_major_error(
                interaction,
                title    = "Unauthorized!",
                texts    = "You lack the necessary permissions to configure anti-nuke settings.",
                subtitle = "Invalid permissions.",
            )
            return

        self.config["log_channel_id"] = channel.id
        self.save_config()

        _ = await interaction.response.send_message(
            f"Anti-nuke alerts will now be sent to {channel.mention}.",
            ephemeral = True,
        )

async def setup(bot: commands.Bot) -> None:
    antinuke_system = bot.get_cog("AntiNukeSystem")
    if antinuke_system is None:
        string = "AntiNukeSystem cog must be loaded before AntiNukeCommands"
        raise RuntimeError(string)

    await bot.add_cog(AntiNukeCommands(
        cast("AntiNukeSystem", antinuke_system),
    ))
