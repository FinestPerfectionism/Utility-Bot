import discord
from discord import app_commands
from discord.ext import commands

from datetime import datetime
from typing import List, TYPE_CHECKING, cast

from core.utils import send_minor_error

from constants import(
    ACCEPTED_EMOJI_ID,
    DENIED_EMOJI_ID,

    COLOR_RED,
    COLOR_ORANGE,
    COLOR_GREEN,
)

if TYPE_CHECKING:
    from events.systems.antinuke import AntiNukeSystem

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Anti-Nuke Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class AntiNukeCommands(commands.Cog):
    def __init__(self, antinuke_system: "AntiNukeSystem"):
        self.antinuke_system = antinuke_system
        self.config = antinuke_system.config
        self.is_director = antinuke_system.is_director
        self.save_config = antinuke_system.save_config

    def permission_error(self, custom_text: str):
        class PermissionError(discord.ui.LayoutView):
            container1 = discord.ui.Container(
                discord.ui.TextDisplay(content=(
                    f"### {DENIED_EMOJI_ID} Unauthorized!\n"
                    "-# No permissions.\n"
                    f"{custom_text}")),
                accent_color=COLOR_RED,
            )

        return PermissionError()

    antinuke_group = app_commands.Group(
        name="anti-nuke",
        description="Directors only —— Anti-nuke management."
    )

    @antinuke_group.command(
        name="status",
        description="Status of the anti-nuke system."
    )
    async def antinuke_status(self, interaction: discord.Interaction):
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.is_director(actor):
            denied = self.permission_error("You lack the necessary permissions to view anti-nuke settings.")
            await interaction.response.send_message(view=denied, ephemeral=True)
            return

        enabled = self.config.get("enabled", True)
        log_channel_id = self.config.get("log_channel_id")

        embed = discord.Embed(
            title="Anti-Nuke Configuration",
            color=COLOR_GREEN if enabled else COLOR_RED,
            timestamp=datetime.now()
        )

        status_text = "Enabled" if enabled else "Disabled"
        embed.add_field(
            name="Status",
            value=status_text,
            inline=True
        )

        if log_channel_id:
            log_channel = interaction.guild.get_channel(log_channel_id) if interaction.guild else None
            embed.add_field(
                name="Log Channel",
                value=log_channel.mention if log_channel else f"<#{log_channel_id}> (deleted)",
                inline=True
            )
        else:
            embed.add_field(name="Log Channel", value="Not configured", inline=True)

        embed.add_field(name="\u200b", value="\u200b", inline=False)

        limits = self.config["limits"]
        for action_type, settings in limits.items():
            action_name = action_type.replace("_", " ").title()
            hourly = settings.get("hourly", "N/A")
            daily = settings.get("daily", "N/A")
            limit_text = f"Hourly: {hourly}\nDaily: {daily}"
            embed.add_field(name=action_name, value=limit_text, inline=True)

        embed.set_footer(text="Directors are exempt from all limits")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @antinuke_group.command(name="toggle", description="Enable or disable anti-nuke protection.")
    async def antinuke_toggle(self, interaction: discord.Interaction):
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.is_director(actor):
            denied = self.permission_error("You lack the necessary permissions to configure anti-nuke settings.")
            await interaction.response.send_message(view=denied, ephemeral=True)
            return

        self.config["enabled"] = not self.config.get("enabled", True)
        self.save_config()

        status = "enabled" if self.config["enabled"] else "disabled"

        embed = discord.Embed(
            title=f"{ACCEPTED_EMOJI_ID} Anti-Nuke {status.title()}",
            description=f"Anti-nuke protection has been {status}.",
            color=COLOR_GREEN if self.config["enabled"] else COLOR_ORANGE,
            timestamp=datetime.now()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @antinuke_group.command(name="set-limit", description="Configure limits for a specific action type.")
    @app_commands.describe(
        action="The action type to configure.",
        hourly="Maximum number of actions allowed per hour.",
        daily="Maximum number of actions allowed per day."
    )
    async def antinuke_setlimit(
        self,
        interaction: discord.Interaction,
        action: str,
        hourly: int,
        daily: int
    ):
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.is_director(actor):
            denied = self.permission_error("You lack the necessary permissions to configure anti-nuke settings.")
            await interaction.response.send_message(view=denied, ephemeral=True)
            return

        if action not in self.config["limits"]:
            await send_minor_error(
                interaction,
                f"Invalid action type. Valid types: {', '.join(self.config['limits'].keys())}"
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
            "daily": daily
        }
        self.save_config()

        embed = discord.Embed(
            title=f"{ACCEPTED_EMOJI_ID} Limit Updated",
            description=f"Updated limits for {action.replace('_', ' ')}.",
            color=COLOR_GREEN,
            timestamp=datetime.now()
        )
        embed.add_field(name="Action", value=action.replace("_", " ").title(), inline=True)
        embed.add_field(name="Hourly Limit", value=str(hourly), inline=True)
        embed.add_field(name="Daily Limit", value=str(daily), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @antinuke_setlimit.autocomplete('action')
    async def antinuke_setlimit_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        actions = list(self.config["limits"].keys())
        return [
            app_commands.Choice(name=action.replace("_", " ").title(), value=action)
            for action in actions
            if current.lower() in action.lower()
        ][:25]

    @antinuke_group.command(name="config", description="Configure the anti-nuke log channel.")
    @app_commands.describe(
        channel="The channel where anti-nuke alerts will be sent."
    )
    async def antinuke_config(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.is_director(actor):
            denied = self.permission_error("You lack the necessary permissions to configure anti-nuke settings.")
            await interaction.response.send_message(view=denied, ephemeral=True)
            return

        self.config["log_channel_id"] = channel.id
        self.save_config()

        embed = discord.Embed(
            title=f"{ACCEPTED_EMOJI_ID} Log Channel Configured",
            description=f"Anti-nuke alerts will now be sent to {channel.mention}.",
            color=COLOR_GREEN,
            timestamp=datetime.now()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    antinuke_system = bot.get_cog("AntiNukeSystem")
    if antinuke_system is None:
        raise RuntimeError("AntiNukeSystem cog must be loaded before AntiNukeCommands")

    await bot.add_cog(AntiNukeCommands(
        cast("AntiNukeSystem", antinuke_system)
    ))