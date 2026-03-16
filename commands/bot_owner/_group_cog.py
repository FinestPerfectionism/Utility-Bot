import discord
from discord.ext import commands
from discord import app_commands

import logging

from ._base import (
    COGS as _COGS,
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

    COGS = _COGS

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
    async def reload(self, interaction: discord.Interaction, cog: str | None = None) -> None:
        await run_reload(self.bot, interaction, cog, self.COGS)

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
    async def load(self, interaction: discord.Interaction, cog: str) -> None:
        await run_load(self.bot, interaction, cog, self.COGS)

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
    async def unload(self, interaction: discord.Interaction, cog: str) -> None:
        await run_unload(self.bot, interaction, cog, self.COGS)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .shutdown/.shut Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="shutdown", aliases=["shut"])
    async def shutdown(self, ctx: commands.Context[commands.Bot]) -> None:
        await run_shutdown(self.bot, ctx)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .restart/.r Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="restart", aliases=["r"])
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
    async def _eval(self, ctx: commands.Context[commands.Bot], *, body: str) -> None:
        await run_eval(self.bot, ctx, body)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .say Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="say")
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
    async def pull_reload(self, interaction: discord.Interaction) -> None:
        await run_pull_reload(self.bot, interaction, self.COGS)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BotOwnerCommands(bot))
