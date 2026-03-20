import discord
from discord.ext import commands

import asyncio
import contextlib
import json
import logging
import os
import sys
from datetime import (
    datetime,
    UTC,
)

from constants import (
    BOT_OWNER_ID,
    DENIED_EMOJI_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .restart Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_restart(
    bot:            commands.Bot,
    ctx:            commands.Context[commands.Bot],
    restarting_ref: list[bool],
    logger:         logging.Logger,
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
    _ = loop.create_task(restart_bot(bot, logger, restarting_ref, confirm_msg))

async def restart_bot(
    bot            : commands.Bot,
    logger         : logging.Logger,
    restarting_ref : list[bool],
    confirm_msg    : discord.Message | None = None,
) -> None:
    try:
        await bot.change_presence(
            status   = discord.Status.idle,
            activity = discord.CustomActivity(name="Restarting...")
        )

        if confirm_msg:
            try:
                with open("restart_info.json", "w") as f:
                    json.dump({
                        "channel_id": confirm_msg.channel.id,
                        "message_id": confirm_msg.id,
                        "timestamp":  datetime.now(UTC).isoformat()
                    }, f)
            except Exception as e:
                logger.error("Failed to save restart info: %s", e)

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
                    timeout = 5.0
                )
            except TimeoutError:
                logger.warning("Some tasks did not cancel in time")

        for handler in logger.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        os.execv(sys.executable, [sys.executable, *sys.argv])

    except Exception as e:
        logger.critical("Fatal error during restart: %s", e, exc_info=True)
        restarting_ref[0] = False

        if confirm_msg:
            with contextlib.suppress(Exception):
                _ = await confirm_msg.edit(content=f"Restart failed: {str(e)[:100]}")

        with contextlib.suppress(Exception):
            await bot.change_presence(status=discord.Status.online)
