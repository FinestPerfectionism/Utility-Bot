import logging

import discord
from discord.ext import commands

import core.responses as cr
from constants import BOT_OWNER_ID
from core.responses import send_custom_message

log = logging.getLogger("Utility Bot")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /bot-owner reload Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_reload(
    bot         : commands.Bot,
    interaction : discord.Interaction,
    cog         : str | None,
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

    if cog:
        if cog not in cogs:
            await send_custom_message(
                interaction,
                msg_type = cr.warning,
                title    =  "reload cog",
                subtitle = f"Failed to reload cog `{cog}`: cog `{cog}` not found.",
                footer   =  "Bad argument.",
            )
            return

        try:
            await bot.reload_extension(cog)
            _ = await send_custom_message(
                interaction,
                msg_type = cr.success,
                title    = "reloaded cog",
                subtitle = f"Reloaded cog `{cog}`.",
            )
            log.info("Reloaded cog %s", cog)
        except Exception as e:
            await send_custom_message(
                interaction,
                msg_type = cr.error,
                title    =  "reload cog",
                subtitle = f"Failed to reload cog `{cog}`:\n"
                            "```py\n"
                           f"{e}"
                            "```",
                footer   = "Bad operation.",
            )
            log.exception("Failed to reload cog %s", cog)
    else:
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
                status_text = "All cogs failed to reload."
            elif len(failed) > 1:
                status_text = "Multiple cogs failed to reload."
            else:
                status_text = "A cog failed to reload."

            await send_custom_message(
                interaction,
                msg_type = cr.warning,
                title    =  "reload cog(s)",
                subtitle = f"{status_text}\n"
                            "```py\n"
                           f"{msg[:1800]}\n"
                            "```",
                footer   =  "Bad operation.",
            )
        else:
            _ = await send_custom_message(
                interaction,
                msg_type = cr.success,
                title    = "reloaded cogs",
                subtitle = "Reloaded all cogs successfully.",
            )
