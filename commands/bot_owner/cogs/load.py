import logging

import discord
from discord.ext import commands

from constants import BOT_OWNER_ID
from core.utils import send_major_error, send_minor_error
from events.logging.errors import PermissionsError

log = logging.getLogger("Utility Bot")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /load Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_load(
    bot         : commands.Bot,
    interaction : discord.Interaction,
    cog         : str,
    cogs        : list[str],
) -> None:
    if interaction.user.id != BOT_OWNER_ID:
        _ = await interaction.response.send_message(
            view      = PermissionsError(),
            ephemeral = True,
        )
        return

    if cog not in cogs:
        await send_minor_error(interaction, f"Cog `{cog}` not found.")
        return

    if cog in bot.extensions:
        await send_minor_error(interaction, f"Cog `{cog}` is already loaded.")
        return

    try:
        await bot.load_extension(cog)
        _ = await interaction.response.send_message(
            f"Loaded cog `{cog}`.",
            ephemeral = True,
        )
        log.info("Loaded cog %s", cog)
    except Exception as e:
        await send_major_error(
            interaction,
            texts    = f"Failed to load `{cog}`: {e}",
            subtitle = "Invalid operation.",
        )
        log.exception("Failed to load cog %s:", cog)
