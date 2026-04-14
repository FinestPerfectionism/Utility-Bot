import asyncio
import logging

import discord
from discord.ext import commands

import core.responses as cr
from constants import BOT_OWNER_ID
from core.responses import send_custom_message

log = logging.getLogger("Utility Bot")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /bot-owner pull-reload Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_pull_reload(
    bot         : commands.Bot,
    interaction : discord.Interaction,
    cogs        : list[str],
) -> None:
    if interaction.user.id != BOT_OWNER_ID:
        await send_custom_message(
            interaction,
            msg_type = cr.error,
            title    = "run command",
            subtitle = "You are not authorized to run this command.",
            footer   = "No permissions.",
        )
        return

    _ = await interaction.response.defer(ephemeral = True)

    proc = await asyncio.create_subprocess_exec(
        "git", "pull", "origin", "main",
        stdout = asyncio.subprocess.PIPE,
        stderr = asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    pull_output = stdout.decode().strip() or stderr.decode().strip()

    if proc.returncode != 0:
        await send_custom_message(
            interaction,
            msg_type = cr.error,
            title    =  "pull from git",
            subtitle = f"Failed to pull from git:\n"
                        "```py\n"
                       f"{pull_output[:1800]}\n"
                        "```",
            footer   =  "Bad operation.",
        )
        log.error("git pull failed (exit %s):\n%s", proc.returncode, pull_output)
        return

    failed : list[tuple[str, Exception]] = []

    for c in cogs:
        try:
            await bot.reload_extension(c)
            log.info("Reloaded cog %s", c)
        except Exception as e:
            failed.append((c, e))
            log.exception("Failed to reload cog %s", c)

    if failed:
        msg = "\n".join(f"{c}: {e}" for c, e in failed)

        if len(failed) == len(cogs):
            status = "All cogs failed to reload."
        elif len(failed) > 1:
            status = "Multiple cogs failed to reload."
        else:
            status = "A cog failed to reload."

        await send_custom_message(
            interaction,
            msg_type = cr.warning,
            title    =  "reload cog",
            subtitle = f"Pull succeeded. {status}\n"
                        "```py\n"
                       f"{msg[:1800]}\n"
                        "```",
            footer   =  "Bad operation.",
        )
    else:
        await send_custom_message(
            interaction,
            msg_type = cr.success,
            title    =  "reloaded cogs",
            subtitle = f"Pulled from git and reloaded all cogs.\n"
                        "```py\n"
                       f"{pull_output[:1800]}\n"
                        "```",
        )
