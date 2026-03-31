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
# /reload Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_reload(
    bot         : commands.Bot,
    interaction : discord.Interaction,
    cog         : str | None,
    cogs        : list[str],
) -> None:
    if interaction.user.id != BOT_OWNER_ID:
        _ = await interaction.response.send_message(
            view      = PermissionError(),
            ephemeral = True,
        )
        return

    if cog:
        if cog not in cogs:
            await send_minor_error(interaction, f"Cog `{cog}` not found.")
            return
        try:
            await bot.reload_extension(cog)
            _ = await interaction.response.send_message(
                f"Reloaded cog `{cog}` successfully.",
                ephemeral = True,
            )
            log.info("Reloaded cog %s", cog)
        except Exception as e:
            await send_major_error(
                interaction,
                texts    = f"Failed to reload cog `{cog}`: {e}",
                subtitle = "Invalid operation.",
            )
            log.error("Failed to reload cog %s: %s", cog, e)
    else:
        failed: list[tuple[str, Exception]] = []
        for c in cogs:
            try:
                await bot.reload_extension(c)
                log.info("Reloaded cog %s", c)
            except Exception as e:
                failed.append((c, e))
                log.error("Failed to reload cog %s: %s", c, e)

        if failed:
            msg = "\n".join(f"{c}: {e}" for c, e in failed)
            await send_minor_error(
                interaction,
                texts    = f"Reload completed, but some cogs failed:\n{msg}",
                subtitle = "Invalid operation.",
            )
        else:
            _ = await interaction.response.send_message(
                "All cogs reloaded successfully.",
                ephemeral = True,
            )
