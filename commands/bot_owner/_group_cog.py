import discord
from discord.ext import commands
from discord import app_commands

import logging

from constants import BOT_OWNER_ID

from core.help import (
    help_description,
    ArgumentInfo,
)
from ._base import (
    get_cogs,
    cog_autocomplete,
)
from .cogs.reload import run_reload
from .cogs.load import run_load
from .cogs.unload import run_unload
from .cogs.pull_reload import run_pull_reload
from .state.shutdown import run_shutdown
from .state.restart import run_restart
from .misc import (
    run_status,
    run_eval,
    run_say,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Owner Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class BotOwnerCommands(
    commands.GroupCog,
    name="bot-owner",
    description="Bot Owner only —— Bot owner commands."
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot            = bot
        self.logger         = logging.getLogger("bot")
        self.restarting_ref = [False]
        super().__init__()

    @property
    def COGS(self):
        return get_cogs()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /reload Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="reload",
        description="Reload a cog or all cogs."
    )
    @app_commands.describe(
        cog="The cog to reload. Leave empty to reload all cogs."
    )
    @app_commands.autocomplete(cog=cog_autocomplete)
    @help_description(
        desc="Reloads one cog, or reloads every registered cog when the cog argument is omitted. This command is reserved for the single configured bot owner account, so the restriction is documented here in prose instead of a role-based help restriction.",
        prefix=False,
        slash=True,
        arguments={"cog": ArgumentInfo(required=False, description="Optional cog name to reload. If omitted, the bot attempts to reload every registered cog.")},
    )
    async def reload(self, interaction: discord.Interaction, cog: str | None = None) -> None:
        await run_reload(self.bot, interaction, cog, get_cogs())

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /load Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="load",
        description="Load a cog."
    )
    @app_commands.describe(
        cog="The cog to load."
    )
    @app_commands.autocomplete(cog=cog_autocomplete)
    @help_description(
        desc="Loads a cog that is currently available but not active. Like the other bot-owner maintenance commands, access is controlled by the configured owner user ID rather than any Discord role.",
        prefix=False,
        slash=True,
        arguments={"cog": ArgumentInfo(description="Cog name to load.")},
    )
    async def load(self, interaction: discord.Interaction, cog: str) -> None:
        await run_load(self.bot, interaction, cog, get_cogs())

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /unload Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="unload",
        description="Unload a cog."
    )
    @app_commands.describe(
        cog="The cog to unload."
    )
    @app_commands.autocomplete(cog=cog_autocomplete)
    @help_description(
        desc="Unloads an active cog so its commands and listeners stop running. Access is limited to the configured bot owner account rather than a Discord role.",
        prefix=False,
        slash=True,
        arguments={"cog": ArgumentInfo(description="Cog name to unload.")},
    )
    async def unload(self, interaction: discord.Interaction, cog: str) -> None:
        await run_unload(self.bot, interaction, cog, get_cogs())

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .shutdown/.shut Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="shutdown", aliases=["shut"])
    @help_description(
        desc="Shuts the bot process down immediately after deleting the invoking message when possible. This prefix command is reserved for the configured bot owner account, not a staff role.",
        prefix=True,
        slash=False,
        aliases=["shut"],
    )
    async def shutdown(self, ctx: commands.Context[commands.Bot]) -> None:
        await run_shutdown(self.bot, ctx)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .restart/.r Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="restart", aliases=["r"])
    @help_description(
        desc="Restarts the bot process, writes restart bookkeeping when possible, and attempts to restore service cleanly. This command is restricted by the configured bot owner user ID rather than a Discord role.",
        prefix=True,
        slash=False,
        aliases=["r"],
    )
    async def restart(self, ctx: commands.Context[commands.Bot]) -> None:
        await run_restart(self.bot, ctx, self.restarting_ref, self.logger)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /status Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="status",
        description="Set the bot's presence status."
    )
    @app_commands.describe(
        type="Activity type.",
        text="Status text.",
        url="Twitch URL.",
        state="Online status.",
    )
    @help_description(
        desc="Updates the bot's visible presence, including activity type, display text, optional online status, and optional streaming URL. Only the configured bot owner account can use it, so the restriction is documented here instead of as a role mention.",
        prefix=False,
        slash=True,
        arguments={
            "type": ArgumentInfo(description="Presence activity type.", choices=["playing", "watching", "listening", "competing", "streaming", "custom"]),
            "text": ArgumentInfo(description="Status text to display."),
            "state": ArgumentInfo(required=False, description="Optional online status.", choices=["online", "idle", "dnd", "invisible"]),
            "url": ArgumentInfo(required=False, description="Optional Twitch URL used for streaming status."),
        },
    )
    @app_commands.choices(
        type=[
            app_commands.Choice(name="Playing",   value="playing"),
            app_commands.Choice(name="Watching",  value="watching"),
            app_commands.Choice(name="Listening", value="listening"),
            app_commands.Choice(name="Competing", value="competing"),
            app_commands.Choice(name="Streaming", value="streaming"),
            app_commands.Choice(name="Custom",    value="custom"),
        ],
        state=[
            app_commands.Choice(name="Online",          value="online"),
            app_commands.Choice(name="Idle",            value="idle"),
            app_commands.Choice(name="Do Not Disturb",  value="dnd"),
            app_commands.Choice(name="Invisible",       value="invisible"),
        ],
    )
    async def status(
        self,
        interaction: discord.Interaction,
        type:        app_commands.Choice[str],
        text:        str,
        state:       app_commands.Choice[str] | None = None,
        url:         str | None = None,
    ) -> None:
        await run_status(self.bot, interaction, type, text, state, url)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .eval Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="eval")
    @help_description(
        desc="Evaluates Python code inside the running bot process with access to the bot, context, channel, author, guild, message, and Discord modules. It is intentionally reserved for the configured bot owner account and should be considered highly dangerous.",
        prefix=True,
        slash=False,
        arguments={"body": ArgumentInfo(description="Python code to evaluate.")},
    )
    async def _eval(self, ctx: commands.Context[commands.Bot], *, body: str) -> None:
        await run_eval(self.bot, ctx, body)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .say Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="say")
    @help_description(
        desc="Sends a message through the bot, optionally redirecting it to another text channel or replying through the referenced message chain. Access is limited to the configured bot owner account rather than a Discord role.",
        prefix=True,
        slash=False,
        arguments={
            "target_channel": ArgumentInfo(required=False, description="Optional text channel to send into; defaults to the current channel."),
            "message": ArgumentInfo(description="Message content to send."),
        },
    )
    async def say(
        self,
        ctx:            commands.Context[commands.Bot],
        target_channel: discord.TextChannel | None = None,
        *,
        message: str,
    ) -> None:
        await run_say(ctx, target_channel, message)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /pull-reload Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="pull-reload",
        description="Pull from main, then reload all cogs."
    )
    @help_description(
        desc="Pulls the latest code from the main branch and then reloads every cog so the running bot matches the updated checkout. As with the other maintenance controls, this is restricted by the configured bot owner user ID rather than a Discord role.",
        prefix=False,
        slash=True,
    )
    async def pull_reload(self, interaction: discord.Interaction) -> None:
        await run_pull_reload(self.bot, interaction, get_cogs())

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BotOwnerCommands(bot))
