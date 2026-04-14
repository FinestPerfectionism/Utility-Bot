import logging

import discord
from discord.ext import commands

import core.responses as cr
from constants import BOT_OWNER_ID
from core.responses import send_custom_message

log = logging.getLogger("Utility Bot")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /bot-owner load Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_load(
    bot         : commands.Bot,
    interaction : discord.Interaction,
    cog         : str,
    cogs        : list[str],
) -> None:
    if interaction.user.id != BOT_OWNER_ID:
        _ = await send_custom_message(
            interaction,
            msg_type = cr.error,
            title    = "run command",
            subtitle = "You are not authorized to run this command.",
            footer   = "No permissions",
        )
        return

    if cog not in cogs:
        await send_custom_message(
            interaction,
            msg_type = cr.warning,
            title    = "load cog",
            subtitle = f"Failed to load cog `{cog}`: cog `{cog}` not found.",
            footer   = "Bad argument",
        )
        return

    if cog in bot.extensions:
        await send_custom_message(
            interaction,
            msg_type = cr.warning,
            title    =  "load cog",
            subtitle = f"Failed to load cog `{cog}`: cog `{cog}` is already loaded.",
            footer   =  "Bad argument",
        )
        return

    try:
        await bot.load_extension(cog)
        _ = await send_custom_message(
            interaction,
            msg_type = cr.success,
            title    = "loaded cog",
            subtitle = f"Loaded cog `{cog}`.",
        )
        log.info("Loaded cog %s", cog)
    except Exception as e:
        await send_custom_message(
            interaction,
            msg_type = cr.error,
            title    =  "load cog",
            subtitle = f"Failed to load cog `{cog}`:\n"
                        "```py\n"
                       f"{e}"
                        "```",
            footer   =  "Bad operation",
        )
        log.exception("Failed to load cog %s:", cog)
