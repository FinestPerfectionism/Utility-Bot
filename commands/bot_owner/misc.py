import contextlib
import io
import textwrap
import traceback
from asyncio import sleep
from typing import (
    TYPE_CHECKING,
    Any,
    cast,
)

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from collections.abc import (
        Awaitable,
        Callable,
    )

from constants import (
    ACCEPTED_EMOJI_ID,
    BOT_OWNER_ID,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,
)
from events.logging.errors import PermissionsError

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /status Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_status(
    bot           : commands.Bot,
    interaction   : discord.Interaction,
    activity_type : app_commands.Choice[str],
    text          : str,
    state         : app_commands.Choice[str] | None,
    url           :                     str  | None,
) -> None:
    if interaction.user.id != BOT_OWNER_ID:
        _ = await interaction.response.send_message(
            view      = PermissionsError(),
            ephemeral = True,
        )
        return

    presence_status = (
        getattr(discord.Status, state.value)
        if state
        else discord.Status.online
    )

    activity: discord.BaseActivity | None = None

    match activity_type.value:
        case "playing":
            activity = discord.Game(name = text)

        case "watching":
            activity = discord.Activity(
                type = discord.ActivityType.watching,
                name = text,
            )

        case "listening":
            activity = discord.Activity(
                type = discord.ActivityType.listening,
                name = text,
            )

        case "competing":
            activity = discord.Activity(
                type = discord.ActivityType.competing,
                name = text,
            )

        case "streaming":
            if not url:
                _ = await interaction.response.send_message(
                    "Streaming status requires a Twitch URL.",
                    ephemeral = True,
                )
                return
            activity = discord.Streaming(name = text, url=url)

        case "custom":
            activity = discord.Activity(
                type  = discord.ActivityType.custom,
                state = text,
            )

        case _:
            pass

    await bot.change_presence(
        activity = activity,
        status   = presence_status,
    )

    _ = await interaction.response.send_message(
        f"Status updated: `{activity_type.name}`: `{text}`",
        ephemeral = True,
    )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .eval Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class EvalFlags(commands.FlagConverter, prefix="/", delimiter=" "):
    s: str | None = commands.flag(
        name        = "s",
        aliases     = ["silent", "supress", "shush"],
        default     = None,
        max_args    = -1,
    )

async def run_eval(
    bot   : commands.Bot,
    ctx   : commands.Context[commands.Bot],
    body  : str,
    *,
    flags : EvalFlags | None = None,
) -> None:
    silent = flags and flags.s is not None

    if ctx.author.id != BOT_OWNER_ID:
        _ = await ctx.message.add_reaction(DENIED_EMOJI_ID)
        return

    env: dict[str, Any] = {
        "bot"      : bot,
        "ctx"      : ctx,
        "channel"  : ctx.channel,
        "author"   : ctx.author,
        "guild"    : ctx.guild,
        "message"  : ctx.message,
        "discord"  : discord,
        "commands" : commands,
    }

    body = "\n".join(body.split("\n")[1:-1]) if body.startswith("```") else body.strip("` \n")

    stdout     = io.StringIO()
    to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

    try:
        import builtins
        builtins.exec(to_compile, env)
    except BaseException as e:
        if silent:
            _   = await ctx.message.delete()
            msg = await ctx.send(
                "```py\n"
               f"{e.__class__.__name__}: {e}\n"
                "```"
            )
            await sleep(5)
            await msg.delete()
            return
        _ = await ctx.message.add_reaction(f"{DENIED_EMOJI_ID}")
        _ = await ctx.send(f"```py\n{e.__class__.__name__}: {e}\n```")
        return

    func = cast("Callable[[], Awaitable[Any]]", env["func"])

    try:
        with contextlib.redirect_stdout(stdout):
            ret = await func()
    except BaseException:
        value = stdout.getvalue()
        if silent:
            _   = await ctx.message.delete()
            msg = await ctx.send(f"```py\n{value}{traceback.format_exc()}\n```")
            await sleep(5)
            await msg.delete()
            return
        _ = await ctx.message.add_reaction(f"{CONTESTED_EMOJI_ID}")
        _ = await ctx.send(f"```py\n{value}{traceback.format_exc()}\n```")
    else:
        value = stdout.getvalue()
        if silent:
            _ = await ctx.message.delete()
            return
        _ = await ctx.message.add_reaction(f"{ACCEPTED_EMOJI_ID}")

        if ret is None:
            if value:
                _ = await ctx.send(f"```py\n{value}\n```")
        else:
            _ = await ctx.send(f"```py\n{value}{ret}\n```")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .say Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_say(
    ctx            : commands.Context[commands.Bot],
    target_channel : discord.TextChannel | None,
    message        : str,
) -> None:
    if ctx.author.id != BOT_OWNER_ID:
        _ = await ctx.message.add_reaction(DENIED_EMOJI_ID)
        return

    _ = await ctx.message.delete()

    channel           = target_channel or ctx.channel
    formatted_message = message.replace("\\n", "\n")

    if ctx.message.reference and ctx.message.reference.message_id is not None:
        ref_channel_id = ctx.message.reference.channel_id
        ref_channel = ctx.bot.get_channel(ref_channel_id) or await ctx.bot.fetch_channel(ref_channel_id)
        if isinstance(ref_channel, discord.abc.Messageable):
            original_message = await ref_channel.fetch_message(ctx.message.reference.message_id)
            _ = await original_message.reply(formatted_message)
    else:
        _ = await channel.send(formatted_message)
