import asyncio
import sys
import traceback
from collections.abc import Coroutine
from typing import Any

import aiohttp
import discord
from discord import app_commands
from discord.app_commands import CommandOnCooldown
from discord.app_commands.errors import CommandNotFound
from discord.ext import commands
from typing_extensions import override

import core.responses as cr
from constants import (
    BOT_ERRORS_LOG_CHANNEL_ID,
    BOT_LOG_CHANNEL_ID,
    BOT_OWNER_ID,
    COLOR_BLURPLE,
    COLOR_RED,
)
from core.permissions import PermissionDenied, WrongGuild
from core.responses import send_custom_message

MAX_n_429S = 5
n_429 = 429

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# User Input Errors
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

USER_INPUT_ERRORS = (
    commands.MissingRequiredArgument,
    commands.MissingRequiredAttachment,
    commands.TooManyArguments,
    commands.BadArgument,
    commands.BadUnionArgument,
    commands.BadLiteralArgument,
    commands.ArgumentParsingError,
    commands.MemberNotFound,
    commands.UserNotFound,
    commands.ChannelNotFound,
    commands.RoleNotFound,
    commands.EmojiNotFound,
    commands.GuildNotFound,
    commands.MessageNotFound,
    commands.ThreadNotFound,
    commands.ChannelNotReadable,
    commands.BadInviteArgument,
    commands.BadBoolArgument,
    commands.BadColourArgument,
    commands.MissingFlagArgument,
    commands.TooManyFlags,
    commands.BadFlagArgument,
    commands.MissingRequiredFlag,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Errors Handling
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ErrorLogger(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot                            = bot
        self._tasks: set[asyncio.Task[Any]] = set()
        self._rate_limit_hits               = 0
        _ = bot.tree.error(self.app_command_error_handler)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Central Error Sender
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def send_info(self, *, title: str, description: str | None = None) -> None:
        channel = self.bot.get_channel(BOT_LOG_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            return

        embed = discord.Embed(
            title       = title,
            description = description,
            color       = COLOR_BLURPLE,
            timestamp   = discord.utils.utcnow(),
        )

        _ = await channel.send(embed = embed)

    async def send_error(
        self,
        *,
        title           : str,
        user            : discord.abc.User | None = None,
        guild           : discord.Guild    | None = None,
        command_display : str              | None = None,
        error_text      : str              | None = None,
        traceback_text  : str              | None = None,
    ) -> None:
        channel = self.bot.get_channel(BOT_ERRORS_LOG_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            return

        embed = discord.Embed(
            title     = title,
            color     = COLOR_RED,
            timestamp = discord.utils.utcnow(),
        )

        if user:
            _ = embed.add_field(
                name   ="User",
                value  = f"`{user}`\n`{user.id}`",
                inline = True,
            )

        if guild:
            _ = embed.add_field(
                name = "Guild",
                value = f"`{guild}`\n`{guild.id}`",
                inline = True,
            )

        if command_display:
            _ = embed.add_field(
                name = "Command",
                value = f"```{command_display}```",
                inline = True,
            )

        if error_text:
            _ = embed.add_field(
                name = "Error",
                value = f"```python\n{error_text}\n```",
                inline = False,
            )

        if traceback_text:
            embed.description = (
                f"**Traceback:**\n```python\n{traceback_text[:3900]}\n```"
            )
        else:
            embed.description = None

        _ = await channel.send(
            content          = f"<@{BOT_OWNER_ID}>",
            embed            = embed,
            allowed_mentions = discord.AllowedMentions(users=True),
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # n_429 / Rate Limit Guard
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def handle_rate_limit(self, source: str) -> None:
        self._rate_limit_hits += 1

        await self.send_error(
            title = "Rate Limited (n_429)",
            error_text=(
                f"Source: {source}\n"
                f"Hit {self._rate_limit_hits}/{MAX_n_429S} this session."
            ),
        )

        if self._rate_limit_hits >= MAX_n_429S:
            await self.send_error(
                title = "Auto-Shutdown: Too Many n_429s",
                error_text=(
                    f"Received {MAX_n_429S} rate limit responses this session. "
                    "Shutting down to prevent an IP ban."
                ),
            )
            await self.bot.close()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Discord Event Errors
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.Cog.listener()
    async def on_error(self, event : str, *_args: str, **_kwargs : int) -> None:
        if event in {"on_command_error", "on_interaction"}:
            return

        exc_type, exc, tb = sys.exc_info()

        if isinstance(exc, CommandNotFound):
            return

        if exc is None:
            await self.send_error(
                title = "Bot Event Error",
                error_text=f"{event}: Unknown exception",
            )
            return

        if isinstance(exc, discord.HTTPException) and exc.status == n_429:
            await self.handle_rate_limit(f"event: {event}")
            return

        tb_text = "".join(traceback.format_exception(exc_type, exc, tb))

        await self.send_error(
            title = "Bot Event Error",
            error_text=f"{event}: {exc}",
            traceback_text=tb_text,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Prefix Command Errors
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.Cog.listener()
    async def on_command_error(self, ctx : commands.Context[commands.Bot], error: commands.CommandError) -> None:
        if hasattr(ctx.command, "on_error"):
            return

        actual_error: Exception = error
        if isinstance(error, commands.CommandInvokeError):
            actual_error = error.original

        if isinstance(actual_error, discord.HTTPException) and actual_error.status == n_429:
            await self.handle_rate_limit(ctx.message.content or "prefix command")
            return

        if isinstance(actual_error, commands.CheckFailure | commands.CommandNotFound):
            return

        if isinstance(actual_error, USER_INPUT_ERRORS):
            return

        tb_text: str = "".join(
            traceback.format_exception(type(actual_error), actual_error, actual_error.__traceback__),
        )

        await self.send_error(
            title = "Prefix Command Error",
            user=ctx.author,
            guild=ctx.guild,
            command_display=ctx.message.content,
            error_text=str(actual_error),
            traceback_text=tb_text,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Application Command Errors
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def app_command_error_handler(
        self,
        interaction : discord.Interaction,
        error       : app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, CommandOnCooldown):
            _ = await send_custom_message(
                interaction,
                msg_type = cr.warning,
                title    = "run command",
                subtitle = f"Cooldown active. Try again in {error.retry_after:.1f}s.",
                footer   = "Cooldown active.",
            )
            return

        if isinstance(error, WrongGuild):
            _ = await send_custom_message(
                interaction,
                msg_type = cr.warning,
                title    = "run command",
                subtitle = "You are authorized to run this command, but this command is for main guild usage.",
                footer   = "Bad environment.",
            )
            return

        if isinstance(error, PermissionDenied):
            _ = await send_custom_message(
                interaction,
                msg_type = cr.error,
                title    = "run command",
                subtitle = "You are not authorized to run this command.",
                footer   = "No permissions.",
            )
            return

        actual_error = error.original if isinstance(error, app_commands.CommandInvokeError) else error

        if isinstance(actual_error, discord.HTTPException) and actual_error.status == n_429:
            cmd      = interaction.command
            cmd_name = f"/{cmd.qualified_name}" if cmd else "Unknown"
            await self.handle_rate_limit(cmd_name)
            return

        tb_text = "".join(
            traceback.format_exception(type(error), error, error.__traceback__),
        )

        cmd      = interaction.command
        cmd_name = f"/{cmd.qualified_name}" if cmd else "Unknown"

        await self.send_error(
            title = "Application Command Error",
            user=interaction.user,
            guild=interaction.guild,
            command_display=cmd_name,
            error_text=str(error),
            traceback_text=tb_text,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Extension Errors
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.Cog.listener()
    async def on_extension_error(self, extension: str, error: commands.ExtensionError) -> None:
        tb_text = "".join(
            traceback.format_exception(type(error), error, error.__traceback__),
        )

        await self.send_error(
            title = "Extension Error",
            error_text=f"{extension}: {error}",
            traceback_text=tb_text,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # HTTP Errors
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.Cog.listener()
    async def on_socket_raw_receive(self, payload: dict[str, Any]) -> None:
        if payload.get("t") == "INVALID_SESSION":
            await self.send_info(title = "Invalid Gateway Session")

    async def guard_http(self, coro: Coroutine[Any, Any, Any]) -> None:
        try:
            return await coro
        except (
            discord.Forbidden,
            discord.NotFound,
            discord.HTTPException,
            aiohttp.ClientError,
        ) as exc:
            if isinstance(exc, discord.HTTPException) and exc.status == n_429:
                await self.handle_rate_limit("guard_http")
                raise

            tb_text = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__),
            )

            await self.send_error(
                title = "HTTP / REST Error",
                error_text=str(exc),
                traceback_text=tb_text,
            )
            raise

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Task Errors
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    def create_task(self, coro: Coroutine[Any, Any, Any], *, name: str) -> asyncio.Task[Any]:
        task = asyncio.create_task(coro, name = name)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        task.add_done_callback(self.task_done)
        return task

    def task_done(self, task: asyncio.Task[Any]) -> None:
        if task.cancelled():
            return

        try:
            exc = task.exception()
        except asyncio.InvalidStateError:
            return

        if exc is None:
            return

        if isinstance(exc, discord.HTTPException) and exc.status == n_429:
            _ = self.create_task(
                self.handle_rate_limit(f"task: {task.get_name()}"),
                name = "task_ratelimit_reporter",
            )
            return

        tb_text = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__),
        )

        _ = self.create_task(
            self.send_error(
                title          = "Background Task Error",
                error_text     = str(exc),
                traceback_text = tb_text,
            ),
            name = "task_error_reporter",
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Shard Errors / Logging
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.Cog.listener()
    async def on_disconnect(self) -> None:
        await self.send_info(title = "Gateway Disconnected")

    @commands.Cog.listener()
    async def on_resumed(self) -> None:
        await self.send_info(title = "Gateway Resumed")

    @commands.Cog.listener()
    async def on_shard_disconnect(self, shard_id : int) -> None:
        await self.send_info(
            title       = "Shard Disconnected",
            description = f"Shard {shard_id}",
        )

    @commands.Cog.listener()
    async def on_shard_connect(self, shard_id : int) -> None:
        await self.send_info(
            title       = "Shard Connected",
            description = f"Shard {shard_id}",
        )

    @commands.Cog.listener()
    async def on_shard_ready(self, shard_id : int) -> None:
        await self.send_info(
            title       = "Shard Ready",
            description = f"Shard {shard_id}",
        )

    @commands.Cog.listener()
    async def on_shard_resumed(self, shard_id : int) -> None:
        await self.send_info(
            title       = "Shard Resumed",
            description = f"Shard {shard_id}",
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Loop Exception Errors
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    def loop_exception_handler(self, loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
        if loop.is_closed():
            return
        exc = context.get("exception")
        msg = context.get("message", "No message")

        tb_text = (
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            if exc else msg
        )

        _ = loop.create_task(
            self.send_error(
                title          = "Asyncio Event Loop Error",
                error_text     = str(msg),
                traceback_text = tb_text,
            ),
        )

    @override
    async def cog_load(self) -> None:
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(self.loop_exception_handler)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ErrorLogger(bot))
