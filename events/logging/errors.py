import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import CommandOnCooldown

from typing import Coroutine, Any
import traceback
import sys
import asyncio
import aiohttp

from core.permissions import (
    PermissionDenied,
    WrongGuild
)
from core.utils import send_minor_error

from constants import (
    BOT_LOG_CHANNEL_ID,
    BOT_OWNER_ID,
    COLOR_BLURPLE,
    ERRORS_LOG_CHANNEL_ID,
    COLOR_RED,
    COLOR_YELLOW,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Errors Handling
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ErrorLogger(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.tree.error(self.app_command_error_handler)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Central Error Sender
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def send_info(self, *, title: str, description: str | None = None):
        channel = self.bot.get_channel(BOT_LOG_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            return

        embed = discord.Embed(
            title=title,
            description=description,
            color=COLOR_BLURPLE,
            timestamp=discord.utils.utcnow(),
        )

        await channel.send(embed=embed)

    async def send_error(
        self,
        *,
        title: str,
        user: discord.abc.User | None = None,
        guild: discord.Guild | None = None,
        command_display: str | None = None,
        error_text: str | None = None,
        traceback_text: str | None = None,
    ):
        channel = self.bot.get_channel(ERRORS_LOG_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            return

        embed = discord.Embed(
            title=title,
            color=COLOR_RED,
            timestamp=discord.utils.utcnow(),
        )

        if user:
            embed.add_field(
                name="User",
                value=f"`{user}`\n`{user.id}`",
                inline=True,
            )

        if guild:
            embed.add_field(
                name="Guild",
                value=f"`{guild}`\n`{guild.id}`",
                inline=True,
            )

        if command_display:
            embed.add_field(
                name="Command",
                value=f"```{command_display}```",
                inline=True,
            )

        if error_text:
            embed.add_field(
                name="Error",
                value=f"```python\n{error_text}\n```",
                inline=False,
            )

        if traceback_text:
            embed.description = (
                f"**Traceback:**\n```python\n{traceback_text[:3900]}\n```"
            )
        else:
            embed.description = None

        await channel.send(
            content=f"<@{BOT_OWNER_ID}>",
            embed=embed,
            allowed_mentions=discord.AllowedMentions(users=True),
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Discord Event Errors
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        if event in {
            "on_command_error",
            "on_interaction",
        }:
            return
        exc_type, exc, tb = sys.exc_info()

        if exc is None:
            await self.send_error(
                title="Bot Event Error",
                error_text=f"{event}: Unknown exception",
            )
            return

        tb_text = "".join(traceback.format_exception(exc_type, exc, tb))

        await self.send_error(
            title="Bot Event Error",
            error_text=f"{event}: {exc}",
            traceback_text=tb_text,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Prefix Command Errors
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context,
                               error: commands.CommandError):
        if isinstance(error,
                      (commands.CheckFailure, commands.CommandNotFound)):
            return

        tb_text = "".join(
            traceback.format_exception(type(error), error,
                                       error.__traceback__))

        await self.send_error(
            title="Prefix Command Error",
            user=ctx.author,
            guild=ctx.guild,
            command_display=ctx.message.content,
            error_text=str(error),
            traceback_text=tb_text,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Application Command Errors
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def app_command_error_handler(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ):
        if isinstance(error, CommandOnCooldown):
            await send_minor_error(
                interaction,
                f"Cooldown active. Try again in {error.retry_after:.1f}s.",
                subtitle="Cooldown active."
            )
            return

        if isinstance(error, WrongGuild):
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    view=WrongGuildError(),
                    ephemeral=True,
                )
            return

        if isinstance(error, PermissionDenied):
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    view=PermissionError(),
                    ephemeral=True,
                )
            return

        tb_text = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )

        cmd = interaction.command
        cmd_name = f"/{cmd.qualified_name}" if cmd else "Unknown"

        await self.send_error(
            title="Application Command Error",
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
    async def on_extension_error(self, extension, error):
        tb_text = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )

        await self.send_error(
            title="Extension Error",
            error_text=f"{extension}: {error}",
            traceback_text=tb_text,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # HTTP Errors
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.Cog.listener()
    async def on_socket_raw_receive(self, payload):
        if payload.get("t") == "INVALID_SESSION":
            await self.send_info(title="Invalid Gateway Session")

    async def guard_http(self, coro: Coroutine[Any, Any, Any]):
        try:
            return await coro
        except (
            discord.Forbidden,
            discord.NotFound,
            discord.HTTPException,
            aiohttp.ClientError,
        ) as exc:
            tb_text = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )

            await self.send_error(
                title="HTTP / REST Error",
                error_text=str(exc),
                traceback_text=tb_text,
            )
            raise

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Task Errors
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    def create_task(self, coro: Coroutine[Any, Any, Any], *, name: str):
        task = asyncio.create_task(coro, name=name)
        task.add_done_callback(self.task_done)
        return task

    def task_done(self, task: asyncio.Task):
        if task.cancelled():
            return

        exc = task.exception()
        if exc is None:
            return

        tb_text = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )

        asyncio.create_task(
            self.send_error(
                title="Background Task Error",
                error_text=str(exc),
                traceback_text=tb_text,
            )
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Shard Errors / Logging
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.Cog.listener()
    async def on_disconnect(self):
        await self.send_info(
            title="Gateway Disconnected"
        )

    @commands.Cog.listener()
    async def on_resumed(self):
        await self.send_info(
            title="Gateway Resumed"
        )

    @commands.Cog.listener()
    async def on_shard_disconnect(self, shard_id):
        await self.send_info(
            title="Shard Disconnected",
            description=f"Shard {shard_id}"
        )

    @commands.Cog.listener()
    async def on_shard_connect(self, shard_id):
        await self.send_info(
            title="Shard Connected",
            description=f"Shard {shard_id}"
        )

    @commands.Cog.listener()
    async def on_shard_ready(self, shard_id):
        await self.send_info(
            title="Shard Ready",
            description=f"Shard {shard_id}"
        )

    @commands.Cog.listener()
    async def on_shard_resumed(self, shard_id):
        await self.send_info(
            title="Shard Resumed",
            description=f"Shard {shard_id}"
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Loop Exception Errors
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    def loop_exception_handler(self, loop, context):
        if loop.is_closed():
            return
        exc = context.get("exception")
        msg = context.get("message", "No message")

        tb_text = (
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            if exc else msg
        )

        loop.create_task(
            self.send_error(
                title="Asyncio Event Loop Error",
                error_text=str(msg),
                traceback_text=tb_text,
            )
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Cog Load
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def cog_load(self):
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(self.loop_exception_handler)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Views
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class WrongGuildError(discord.ui.LayoutView):
    container1 = discord.ui.Container(
        discord.ui.TextDisplay(content=(
            f"### {CONTESTED_EMOJI_ID} Error!\n"
            "-# Bad command environment.\n"
            "Although you have the necessary permissions to run this command (Bot Owner), using it in this current Guild/DM will not work."
        )),
        accent_color=COLOR_YELLOW,
    )

class PermissionError(discord.ui.LayoutView):
    container1 = discord.ui.Container(
        discord.ui.TextDisplay(content=(
            f"### {DENIED_EMOJI_ID} Unauthorized!\n"
            "-# No permissions.\n"
            "You lack the necessary permissions to run this command.")),
        accent_color=COLOR_RED,
    )

async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorLogger(bot))