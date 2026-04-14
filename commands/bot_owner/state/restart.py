import asyncio
import contextlib
import json
import logging
import os
import sys
from datetime import UTC, datetime

import discord
from discord.ext import commands

import core.responses as cr
from constants import BOT_OWNER_ID, DENIED_EMOJI_ID
from core.responses import send_custom_message

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .restart Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_restart(
    bot            : commands.Bot,
    ctx            : commands.Context[commands.Bot],
    restarting_ref : list[bool],
    log            : logging.Logger,
) -> None:
    if ctx.author.id != BOT_OWNER_ID:
        _ = await send_custom_message(
            ctx,
            msg_type = cr.error,
            title    = "run command",
            subtitle = "You are not authorized to run this command.",
            footer   = "No permissions.",
        )
        return

    if restarting_ref[0]:
        _ = await send_custom_message(
            ctx,
            msg_type = cr.warning,
            title    = "restart bot",
            subtitle = "A restart is already in progress.",
            footer   = "Bad operation.",
        )
        return

    restarting_ref[0] = True
    confirm_msg = await send_custom_message(
        ctx,
        msg_type = "information",
        title    = "Restarting bot.",
        subtitle = "Restarting bot...",
    )

    with contextlib.suppress(discord.HTTPException, discord.Forbidden):
        await ctx.message.delete()

    loop         = asyncio.get_running_loop()
    restart_task = loop.create_task(restart_bot(bot, log, restarting_ref, confirm_msg))
    restart_task.add_done_callback(lambda t : t.exception() if not t.cancelled() else None)

async def restart_bot(
    bot            : commands.Bot,
    log            : logging.Logger,
    restarting_ref : list[bool],
    confirm_msg    : discord.Message | None = None,
) -> None:
    try:
        await bot.change_presence(
            status   = discord.Status.idle,
            activity = discord.CustomActivity(name = "Restarting..."),
        )

        import anyio

        if confirm_msg:
            try:
                restart_data = json.dumps({
                    "channel_id" : confirm_msg.channel.id,
                    "message_id" : confirm_msg.id,
                    "timestamp"  : datetime.now(UTC).isoformat(),
                })
                path = anyio.Path("restart_info.json")
                _ = await path.write_text(restart_data)
            except Exception:
                log.exception("Failed to save restart info")

        await asyncio.sleep(1)
        await bot.close()

        pending = [
            t for t in asyncio.all_tasks()
            if not t.done() and t is not asyncio.current_task()
        ]

        if pending:
            for task in pending:
                _ = task.cancel()
            try:
                _ = await asyncio.wait_for(
                    asyncio.gather(*pending, return_exceptions=True),
                    timeout = 5.0,
                )
            except TimeoutError:
                log.exception("Some tasks did not cancel in time")

        for handler in log.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        sys.stdout.flush()
        sys.stderr.flush()

        os.execv(sys.executable, [sys.executable, *sys.argv]) # noqa: S606

    except (OSError, discord.DiscordException) as e:
        log.critical("Fatal error during restart: %s", e, exc_info=True)
        restarting_ref[0] = False

        if confirm_msg:
            with contextlib.suppress(Exception):
                _ = await confirm_msg.edit(
                    content =
                   f"{DENIED_EMOJI_ID} **Failed to restart bot!**\n"
                    "Restart failed:\n"
                    "```py\n"
                   f"{e}\n"
                    "```",
                )

        with contextlib.suppress(Exception):
            await bot.change_presence(status=discord.Status.online)
