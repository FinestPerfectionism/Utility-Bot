import asyncio
import contextlib
import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import discord
from discord.ext import commands

from constants import BOT_OWNER_ID, DENIED_EMOJI_ID

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
        await ctx.message.add_reaction(DENIED_EMOJI_ID)
        return

    if restarting_ref[0]:
        _ = await ctx.send("Restart already in progress.", delete_after=1)
        return

    restarting_ref[0] = True

    confirm_msg = await ctx.send("Restarting bot...", delete_after=1)

    with contextlib.suppress(discord.HTTPException, discord.Forbidden):
        await ctx.message.delete()

    loop = asyncio.get_running_loop()
    restart_task = loop.create_task(restart_bot(bot, log, restarting_ref, confirm_msg))
    restart_task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)

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

        if confirm_msg:
            try:
                with Path("restart_info.json").open("w") as f:
                    json.dump({
                        "channel_id": confirm_msg.channel.id,
                        "message_id": confirm_msg.id,
                        "timestamp":  datetime.now(UTC).isoformat(),
                    }, f)
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

        os.execv(sys.executable, [sys.executable, *sys.argv])

    except (OSError, discord.DiscordException) as e:
        log.critical("Fatal error during restart: %s", e, exc_info=True)
        restarting_ref[0] = False

        if confirm_msg:
            with contextlib.suppress(Exception):
                _ = await confirm_msg.edit(content = f"Restart failed: {str(e)[:100]}")

        with contextlib.suppress(Exception):
            await bot.change_presence(status=discord.Status.online)
