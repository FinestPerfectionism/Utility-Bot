import asyncio
import contextlib
import io
import textwrap
from typing import (
    TYPE_CHECKING,
    cast,
)

import discord
from discord import app_commands, ui
from discord.ext import commands

if TYPE_CHECKING:
    from collections.abc import (
        Awaitable,
        Callable,
    )

import core.responses as cr
from constants import (
    ACCEPTED_EMOJI,
    CONTESTED_EMOJI,
    DENIED_EMOJI,
    BOT_OWNER_ID,
)
from core.responses import multi_custom_message, send_custom_message
from events.messages.on_edit import MessageEditHandler

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /bot-owner status Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_status(
    bot           : commands.Bot,
    interaction   : discord.Interaction,
    activity_type : app_commands.Choice[str],
    text          : str,
    state         : app_commands.Choice[str] | None,
    url           : str                  | None,
) -> None:
    presence_status = getattr(discord.Status, state.value) if state else discord.Status.online

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
                _ = await send_custom_message(
                    interaction,
                    msg_type = cr.warning,
                    title    = "update status",
                    subtitle = "Streaming status requires a Twitch URL.",
                    footer   = "Bad argument",
                )
                return
            activity = discord.Streaming(name = text, url = url)

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

    _ = await send_custom_message(
        interaction,
        msg_type = cr.success,
        title    = "updated status",
        subtitle = f"Status updated: `{activity_type.name}`: `{text}`",
    )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .eval Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_eval(
    bot  : commands.Bot,
    ctx  : commands.Context[commands.Bot],
    body : str,
) -> None:
    if ctx.author.id != BOT_OWNER_ID:
        _ = await ctx.message.add_reaction(DENIED_EMOJI)
        return
    env : dict[str, object] = {
        "bot"                  : bot,
        "ctx"                  : ctx,
        "channel"              : ctx.channel,
        "author"               : ctx.author,
        "guild"                : ctx.guild,
        "message"              : ctx.message,

        "commands"             : commands,

        "ACCEPTED_EMOJI"       : ACCEPTED_EMOJI,
        "CONTESTED_EMOJI"      : CONTESTED_EMOJI,
        "DENIED_EMOJI"         : DENIED_EMOJI,

        "discord"              : discord,
        "ui"                   : ui,

        "send_custom_message"  : send_custom_message,
        "multi_custom_message" : multi_custom_message,

        "select"               : ui.select,
        "button"               : ui.button,

        "Button"               : ui.Button,
        "Select"               : ui.Select,
        "UserSelect"           : ui.UserSelect,
        "RoleSelect"           : ui.RoleSelect,
        "MentionableSelect"    : ui.MentionableSelect,
        "ChannelSelect"        : ui.ChannelSelect,
        "TextInput"            : ui.TextInput,

        "View"                 : ui.View,
        "LayoutView"           : ui.LayoutView,
        "Modal"                : ui.Modal,

        "Container"            : ui.Container,
        "Section"              : ui.Section,
        "Separator"            : ui.Separator,
        "ActionRow"            : ui.ActionRow,
        "TextDisplay"          : ui.TextDisplay,
        "Thumbnail"            : ui.Thumbnail,
        "MediaGallery"         : ui.MediaGallery,
        "File"                 : ui.File,
        "FileUpload"           : ui.FileUpload,
        "Label"                : ui.Label,

        "RadioGroup"           : ui.RadioGroup,
        "Checkbox"             : ui.Checkbox,
        "CheckboxGroup"        : ui.CheckboxGroup,

        "SeparatorSpacing"     : discord.SeparatorSpacing,
        "MediaGalleryItem"     : discord.MediaGalleryItem,
        "SelectOption"         : discord.SelectOption,
        "ButtonStyle"          : discord.ButtonStyle,
        "TextStyle"            : discord.TextStyle,
        "RadioGroupOption"     : discord.RadioGroupOption,
        "CheckboxGroupOption"  : discord.CheckboxGroupOption,
        "SelectDefaultValue"   : discord.SelectDefaultValue,

        "Embed"                : discord.Embed,
        "Poll"                 : discord.Poll,

        "Item"                 : ui.Item,
        "DynamicItem"          : ui.DynamicItem,
    }
    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]
        bytes_body = await attachment.read()
        body       = bytes_body.decode("utf-8")
    else:
        body = "\n".join(body.split("\n")[1:-1]) if body.startswith("```") else body.strip("` \n")
    stdout     = io.StringIO()
    to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'
    try:
        import builtins
        builtins.exec(to_compile, env)
    except Exception as e:  # noqa: BLE001
        _ = await ctx.message.add_reaction(f"{DENIED_EMOJI}")
        _ = await ctx.send(f"```py\n{e.__class__.__name__}: {e}\n```")
        return
    func = cast("Callable[[], Awaitable[object]]", env["func"])
    try:
        with contextlib.redirect_stdout(stdout):
            ret = await func()
    except Exception:  # noqa: BLE001
        value = stdout.getvalue()
    else:
        value = stdout.getvalue()

        _ = await ctx.message.add_reaction(f"{ACCEPTED_EMOJI}")

        resp = None
        if ret is None:
            if value:
                resp = await ctx.send(f"```py\n{value}\n```")
        else:
            resp = await ctx.send(f"```py\n{value}{ret}\n```")

        handler = bot.get_cog("MessageEditHandler")
        if resp and isinstance(handler, MessageEditHandler):
            handler.eval_responses[ctx.message.id] = resp.id

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /bot-owner say Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_say(
    interaction : discord.Interaction,
    channel     : discord.abc.Messageable,
    text        : str,
    message_id  : str | None = None,
) -> None:
    if interaction.user.id != BOT_OWNER_ID:
        _ = await send_custom_message(
            interaction,
            msg_type = cr.error,
            title    = "run command",
            subtitle = "You are not authorized to run this command.",
            footer   = "No permissions.",
        )
        return

    _ = await interaction.response.defer(ephemeral = True)

    typing_speed = len(text) * 0.05
    typing_delay = min(typing_speed, 10.0)

    try:
        reply_reference : discord.Message | None = None

        if message_id:
            try:
                if channel:
                    reply_reference = await channel.fetch_message(int(message_id))
            except (discord.NotFound, ValueError, discord.HTTPException):
                _ = await send_custom_message(
                    interaction,
                    msg_type = cr.warning,
                    title    = "run command",
                    subtitle = "The message does not exist, I lack permissions to access it, or it is not a valid ID.",
                    footer   = "Bad argument",
                )
                return

        if hasattr(channel, "typing"):
            async with channel.typing():
                await asyncio.sleep(typing_delay)

        if reply_reference:
            _ = await reply_reference.reply(content = text)
        else:
            _ = await channel.send(content = text)

        await interaction.followup.send("Sent!", ephemeral = True)

    except discord.Forbidden:
        _ = await send_custom_message(
            interaction,
            msg_type = cr.error,
            title       = "run command",
            subtitle    = "I lack permissions to run this command.",
            footer      = "Unknown error.",
        )
