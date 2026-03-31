import logging

import discord
from discord.ext import commands

from constants import BOT_OWNER_ID
from core.utils import (
    send_major_error,
    send_minor_error,
)
from events.logging.errors import PermissionError

log = logging.getLogger("Utility Bot")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /unload Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_unload(
    bot         : commands.Bot,
    interaction : discord.Interaction,
    cog         : str,
    cogs        : list[str],
) -> None:
    if interaction.user.id != BOT_OWNER_ID:
        _ = await interaction.response.send_message(
            view = PermissionError(),
            ephemeral = True,
        )
        return

    if cog not in cogs:
        await send_minor_error(interaction, f"Cog `{cog}` not found.")
        return

    if cog not in bot.extensions:
        await send_minor_error(interaction, f"Cog `{cog}` is already not loaded.")
        return

    try:
        await bot.unload_extension(cog)
        _ = await interaction.response.send_message(
            f"Unloaded cog `{cog}`.",
            ephemeral = True,
        )
        log.info("Unloaded cog %s", cog)
    except Exception as e:
        await send_major_error(
            interaction,
            f"Failed to unload `{cog}`: {e}",
            subtitle = "Invalid operation.",
        )
        log.error("Failed to unload cog %s: %s", cog, e)
