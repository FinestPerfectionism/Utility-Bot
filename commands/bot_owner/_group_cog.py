import logging

import discord
from discord import app_commands
from discord.ext import commands

from constants import BOT_OWNER_ID
from core.help import ArgumentInfo, UserConfig, help_description

from ._base import cog_autocomplete, get_cogs
from .cogs.load import run_load
from .cogs.pull_reload import run_pull_reload
from .cogs.reload import run_reload
from .cogs.unload import run_unload
from .misc import run_eval, run_say, run_status
from .state.restart import run_restart
from .state.shutdown import run_shutdown

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Owner Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class BotOwnerCommands(
    commands.GroupCog,
    name        = "bot-owner",
    description = "Bot Owner only —— Bot owner commands.",
):
    def __init__(self, bot : commands.Bot) -> None:
        self.bot            = bot
        self.logger         = logging.getLogger("bot")
        self.restarting_ref = [False]
        super().__init__()

    @property
    def cogs(self) -> list[str]:
        return get_cogs()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /bot-owner pull-reload Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name        = "pull-reload",
        description = "Pull from main, then reload all cogs.",
    )
    @help_description(
        desc      = "Bot Owner only —— Pulls the latest code from github and reloads all cogs.",
        prefix    = False,
        slash     = True,
        run_users = [UserConfig(user_id = BOT_OWNER_ID)],
    )
    async def pull_reload(self, interaction : discord.Interaction) -> None:
        await run_pull_reload(self.bot, interaction, get_cogs())

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /bot-owner reload Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name        = "reload",
        description = "Reload a cog or all cogs.",
    )
    @app_commands.describe(
        cog = "The cog to reload. Leave empty to reload all cogs.",
    )
    @app_commands.autocomplete(cog=cog_autocomplete)
    @help_description(
        desc      = "Bot Owner only —— Reloads a cog or all cogs.",
        prefix    = False,
        slash     = True,
        run_users = [UserConfig(user_id=BOT_OWNER_ID)],
        arguments = {"cog": ArgumentInfo(required = False, description = "Cog name to reload. Omittion reloads all cogs.")},
    )
    async def reload(self, interaction : discord.Interaction, cog: str | None = None) -> None:
        await run_reload(self.bot, interaction, cog, get_cogs())

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /bot-owner load Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name        = "load",
        description = "Load a cog.",
    )
    @app_commands.describe(
        cog = "The cog to load.",
    )
    @app_commands.autocomplete(cog = cog_autocomplete)
    @help_description(
        desc      = "Bot Owner only —— Loads a cog",
        prefix    = False,
        slash     = True,
        run_users = [UserConfig(user_id=BOT_OWNER_ID)],
        arguments = {"cog": ArgumentInfo(description = "Cog name to load.")},
    )
    async def load(self, interaction : discord.Interaction, cog: str) -> None:
        await run_load(self.bot, interaction, cog, get_cogs())

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /bot-owner unload Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name        = "unload",
        description = "Unload a cog.",
    )
    @app_commands.describe(
        cog = "The cog to unload.",
    )
    @app_commands.autocomplete(cog = cog_autocomplete)
    @help_description(
        desc      = "Bot Owner only —— Unloads a cog",
        prefix    = False,
        slash     = True,
        run_users = [UserConfig(user_id=BOT_OWNER_ID)],
        arguments = {"cog": ArgumentInfo(description = "Cog name to unload.")},
    )
    async def unload(self, interaction : discord.Interaction, cog: str) -> None:
        await run_unload(self.bot, interaction, cog, get_cogs())

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .shutdown/.shut Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name = "shutdown", aliases=["shut"])
    @help_description(
        desc      = "Bot Owner only —— Shutdown the bot.",
        prefix    = True,
        slash     = False,
        run_users = [UserConfig(user_id = BOT_OWNER_ID)],
        aliases   = ["shut"],
    )
    async def shutdown(self, ctx : commands.Context[commands.Bot]) -> None:
        await run_shutdown(self.bot, ctx)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .restart/.r Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name = "restart", aliases=["r"])
    @help_description(
        desc      = "Bot Owner only —— Restarts the bot",
        prefix    = True,
        slash     = False,
        run_users = [UserConfig(user_id = BOT_OWNER_ID)],
        aliases   = ["r"],
    )
    async def restart(self, ctx : commands.Context[commands.Bot]) -> None:
        await run_restart(self.bot, ctx, self.restarting_ref, self.logger)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /bot-owner status Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name        = "status",
        description = "Sets the bot's presence status.",
    )
    @app_commands.describe(
        activity_type  = "Activity type.",
        text           = "Status text.",
        url            = "Twitch URL.",
        state          = "Online status.",
    )
    @app_commands.rename(
        activity_type = "type",
    )
    @help_description(
        desc      = "Bot Owner only —— Sets the bot's presence status.",
        prefix    = False,
        slash     = True,
        run_users = [UserConfig(user_id=BOT_OWNER_ID)],
        arguments = {
            "type"  : ArgumentInfo(description = "Presence activity type.", choices = ["playing", "watching", "listening", "competing", "streaming", "custom"]),
            "text"  : ArgumentInfo(description = "Status text to display."),
            "state" : ArgumentInfo(required = False, description = "Optional online status.", choices = ["online", "idle", "dnd", "invisible"]),
            "url"   : ArgumentInfo(required = False, description = "Optional Twitch URL used for streaming status."),
        },
    )
    @app_commands.choices(
        activity_type = [
            app_commands.Choice(name = "Playing",   value = "playing"),
            app_commands.Choice(name = "Watching",  value = "watching"),
            app_commands.Choice(name = "Listening", value = "listening"),
            app_commands.Choice(name = "Competing", value = "competing"),
            app_commands.Choice(name = "Streaming", value = "streaming"),
            app_commands.Choice(name = "Custom",    value = "custom"),
        ],
        state         = [
            app_commands.Choice(name = "Online",         value = "online"),
            app_commands.Choice(name = "Idle",           value = "idle"),
            app_commands.Choice(name = "Do Not Disturb", value = "dnd"),
            app_commands.Choice(name = "Invisible",      value = "invisible"),
        ],
    )
    async def status(
        self,
        interaction   : discord.Interaction,
        activity_type : app_commands.Choice[str],
        text          : str,
        state         : app_commands.Choice[str] | None = None,
        url           : str                      | None = None,
    ) -> None:
        await run_status(self.bot, interaction, activity_type, text, state, url)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .eval Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name = "eval")
    @help_description(
        desc      = "Bot Owner only —— Evaluate python code.",
        prefix    = True,
        slash     = False,
        run_users = [UserConfig(user_id = BOT_OWNER_ID)],
        arguments = {"body" : ArgumentInfo(description = "Python code to evaluate.")},
    )
    async def _eval(
        self,
        ctx  : commands.Context[commands.Bot],
        *,
        body : str,
    ) -> None:
        await run_eval(self.bot, ctx, body)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /bot-owner say Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "say", description = "Make the bot say something.")
    @help_description(
        desc      = "Bot Owner only —— Make the bot say something.",
        prefix    = False,
        slash     = True,
        run_users = [UserConfig(user_id = BOT_OWNER_ID)],
        arguments = {
            "text"           : ArgumentInfo(description = "The text to send."),
            "target-channel" : ArgumentInfo(description = "The channel to send the message in."),
            "reply-id"       : ArgumentInfo(description = "The ID of the message to reply to." ),
        },
    )
    @app_commands.describe(
        message        = "The text to send.",
        target_channel = "The channel to send the message in.",
        reply_id       = "The ID of the message to reply to.",
    )
    @app_commands.rename(
        target_channel = "target-channel",
        reply_id       = "reply-id",
    )
    async def say(
        self,
        interaction    : discord.Interaction,
        message        : str,
        target_channel : discord.TextChannel | None = None,
        reply_id       : str                 | None = None,
    ) -> None:
        target = target_channel or interaction.channel

        if not isinstance(target, discord.abc.Messageable):
            return

        await run_say(
            interaction = interaction,
            channel     = target,
            text        = message,
            message_id  = reply_id,
        )

async def setup(bot : commands.Bot) -> None:
    await bot.add_cog(BotOwnerCommands(bot))
