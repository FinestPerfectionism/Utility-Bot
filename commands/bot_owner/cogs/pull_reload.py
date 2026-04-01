import asyncio
import logging

import discord
from discord.ext import commands

from constants import BOT_OWNER_ID
from core.utils import (
    send_major_error,
    send_minor_error,
)
from events.logging.errors import PermissionsError

log = logging.getLogger("Utility Bot")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /pull-reload Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_pull_reload(
    bot         : commands.Bot,
    interaction : discord.Interaction,
    cogs        : list[str],
) -> None:
    if interaction.user.id != BOT_OWNER_ID:
        _ = await interaction.response.send_message(
            view      = PermissionsError(),
            ephemeral = True,
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
        await send_major_error(
            interaction,
            texts    =  "Pull failed. All cogs failed to reload.\n"
                        "```py\n"
                       f"{pull_output[:1800]}\n"
                        "```",
            subtitle = "Invalid operation.",
        )
        log.error("git pull failed (exit %s):\n%s", proc.returncode, pull_output)
        return

    failed: list[tuple[str, Exception]] = []
    for c in cogs:
        try:
            await bot.reload_extension(c)
            log.info("Reloaded cog %s", c)
        except Exception as e:
            failed.append((c, e))
            log.exception("Failed to reload cog %s", c)

    if failed:
        msg = "\n".join(f"{c}: {e}" for c, e in failed)
        await send_minor_error(
            interaction,
            texts    = f"Pull succeeded. Some cogs failed to reload.\n{msg}",
            subtitle = "Invalid operation.",
        )
    else:
        await interaction.followup.send(
            f"Pulled and reloaded all cogs successfully.\n```\n{pull_output[:1800]}\n```",
            ephemeral = True,
        )
