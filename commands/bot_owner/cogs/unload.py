import logging

import discord
from discord.ext import commands

import core.responses as cr
from constants import BOT_OWNER_ID
from core.responses import send_custom_message

log = logging.getLogger("Utility Bot")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /bot-owner unload Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_unload(
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
            footer   = "No permissions.",
        )
        return

    if cog not in cogs:
        await send_custom_message(
            interaction,
            msg_type = cr.warning,
            title    = "unload cog",
            subtitle = f"Failed to unload cog `{cog}`: cog `{cog}` not found.",
            footer   = "Bad argument.",
        )
        return

    if cog not in bot.extensions:
        await send_custom_message(
            interaction,
            msg_type = cr.warning,
            title    =  "unload cog",
            subtitle = f"Cog `{cog}` is not currently loaded.",
            footer   =  "Bad argument.",
        )
        return

    try:
        await bot.unload_extension(cog)
        _ = await send_custom_message(
            interaction,
            msg_type = cr.success,
            title    =  "unloaded cog",
            subtitle = f"Unloaded cog `{cog}`.",
        )
        log.info("Unloaded cog %s", cog)
    except Exception as e:
        await send_custom_message(
            interaction,
            msg_type = cr.error,
            title    =  "unload cog",
            subtitle = f"Failed to unload cog `{cog}`:\n"
                        "```py\n"
                       f"{e}"
                        "```",
            footer   =  "Bad operation.",
        )
        log.exception("Failed to unload cog %s", cog)
