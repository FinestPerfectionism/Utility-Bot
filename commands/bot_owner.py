import discord
from discord.ext import commands
from discord import app_commands

import json
import asyncio
import os
import sys
from datetime import datetime, UTC

import logging
from typing import (
    Optional,
    List
)

from events.errors import PermissionError

import core.state
from core.utils import (
    send_major_error,
    send_minor_error
)

from constants import (
    BOT_OWNER_ID,
    DENIED_EMOJI_ID
)

log = logging.getLogger("utilitybot")

async def cog_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    return [
        app_commands.Choice(
            name=cog,
            value=cog
        )
        for cog in BotOwner.COGS
        if current.lower() in cog.lower()
    ][:25]

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Owner Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class BotOwner(
    commands.GroupCog,
    name="bot-owner",
    description="Bot Owner only -- Bot owner commands."):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.restarting = False
        self.logger = logging.getLogger("bot")
        super().__init__()

    COGS = [
        "commands.applications_tickets",
        "commands.automod",
        "commands.bot_owner",
        "commands.meme",
        "commands.misc",
        "commands.mod",
        "commands.proposal",
        "commands.roles",
        "events.applications",
        "events.automod",
        "events.commands",
        "events.errors",
        "events.leave",
        "events.messages",
        "events.on_leave",
        "events.on_message",
        "events.tickets",
        "core.startup",
    ]

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /privilege Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="privilege",
        description="Enable or disable bot owner bypass."
    )
    @app_commands.describe(
        boolean="Enable or disable bot owner bypass."
    )
    async def botowner_privilege(
        self,
        interaction: discord.Interaction,
        boolean: bool
    ):
        if interaction.user.id != BOT_OWNER_ID:
            await interaction.response.send_message(
                view=PermissionError(),
                ephemeral=True
            )
            return

        core.state.OWNER_PRIVILEGE_ENABLED = boolean

        await interaction.response.send_message(
            f"Bot owner privilege set to: `{boolean}`",
            ephemeral=True
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /reload Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="reload",
        description="Reload a cog or all cogs."
    )
    @app_commands.describe(
        cog="The cog to reload. Leave empty to reload all cogs."
    )
    @app_commands.autocomplete(cog=cog_autocomplete)
    async def reload(self, interaction: discord.Interaction, cog: Optional[str] = None):
        if interaction.user.id != BOT_OWNER_ID:
            await interaction.response.send_message(
                view=PermissionError(),
                ephemeral=True
            )
            return

        if cog:
            if cog not in self.COGS:
                _ = await send_minor_error(
                    interaction,
                    f"Cog `{cog}` not found.",
                )
                return
            try:
                await self.bot.reload_extension(cog)
                await interaction.response.send_message(
                    f"Reloaded cog `{cog}` successfully.",
                    ephemeral=True
                )
                log.info(f"Reloaded cog {cog}")
            except Exception as e:
                await send_major_error(
                    interaction,
                    f"Failed to reload cog `{cog}`: {e}",
                    subtitle="Reload error."
                )
                log.error(f"Failed to reload cog {cog}: {e}")
        else:
            failed = []
            for c in self.COGS:
                try:
                    await self.bot.reload_extension(c)
                    log.info(f"Reloaded cog {c}")
                except Exception as e:
                    failed.append((c, e))
                    log.error(f"Failed to reload cog {c}: {e}")

            if failed:
                msg = "\n".join(f"{c}: {e}" for c, e in failed)
                _ = await send_minor_error(
                    interaction,
                    f"Reload completed, but some cogs failed:\n{msg}",
                    subtitle="Reload error."
                )
            else:
                _ = await interaction.response.send_message(
                    "All cogs reloaded successfully.",
                    ephemeral=True
                )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /load Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="load",
        description="Load a cog."
    )
    @app_commands.describe(
        cog="The cog to load."
    )
    @app_commands.autocomplete(cog=cog_autocomplete)
    async def load(self, interaction: discord.Interaction, cog: str):
        if interaction.user.id != BOT_OWNER_ID:
            await interaction.response.send_message(
                view=PermissionError(),
                ephemeral=True
            )
            return

        if cog not in self.COGS:
            await send_minor_error(
                interaction,
                f"Cog `{cog}` not found.",
                )
            return

        if cog in self.bot.extensions:
            await send_minor_error(
                interaction,
                f"Cog `{cog}` is already loaded.",
                )
            return

        try:
            await self.bot.load_extension(cog)
            await interaction.response.send_message(
                f"Loaded cog `{cog}`.",
                ephemeral=True
            )
            log.info("Loaded cog %s", cog)
        except Exception as e:
            await send_major_error(
                interaction,
                f"Failed to load `{cog}`: {e}",
                subtitle="Reload error."
            )
            log.error("Failed to load cog %s: %s", cog, e)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /unload Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="unload",
        description="Unload a cog.")
    @app_commands.describe(
        cog="The cog to unload."
    )
    @app_commands.autocomplete(cog=cog_autocomplete)
    async def unload(self, interaction: discord.Interaction, cog: str):
        if interaction.user.id != BOT_OWNER_ID:
            await interaction.response.send_message(
                view=PermissionError(),
                ephemeral=True
            )
            return

        if cog not in self.COGS:
            await send_minor_error(
                interaction,
                f"Cog `{cog}` not found."
            )
            return

        if cog not in self.bot.extensions:
            await send_minor_error(
                interaction,
                f"Cog `{cog}` is already not loaded."
            )
            return

        try:
            await self.bot.unload_extension(cog)
            await interaction.response.send_message(
                f"Unloaded cog `{cog}`.",
                ephemeral=True
            )
            log.info("Unloaded cog %s", cog)
        except Exception as e:
            await send_major_error(
                interaction,
                f"Failed to unload `{cog}`: {e}",
                subtitle="Reload error."
            )
            log.error("Failed to unload cog %s: %s", cog, e)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ~restart Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="restart", aliases=["r"])
    async def restart(self, ctx: commands.Context):
        if ctx.author.id != BOT_OWNER_ID:
            await ctx.message.add_reaction(DENIED_EMOJI_ID)
            return

        if self.restarting:
            await ctx.send("Restart already in progress.", delete_after=1)
            return

        self.restarting = True

        confirm_msg = await ctx.send("Restarting bot...", delete_after=1)

        try:
            await ctx.message.delete()
        except (discord.HTTPException, discord.Forbidden):
            pass

        loop = asyncio.get_running_loop()
        loop.create_task(self.restart_bot(confirm_msg))

    async def restart_bot(self, confirm_msg: Optional[discord.Message] = None):
        try:
            await self.bot.change_presence(
                status=discord.Status.idle,
                activity=discord.CustomActivity(name="Restarting...")
            )

            if confirm_msg:
                try:
                    with open("restart_info.json", "w") as f:
                        json.dump({
                            "channel_id": confirm_msg.channel.id,
                            "message_id": confirm_msg.id,
                            "timestamp": datetime.now(UTC).isoformat()
                        }, f)
                except Exception as e:
                    self.logger.error(
                        f"Failed to save restart info: {e}"
                    )

            await asyncio.sleep(1)
            await self.bot.close()

            pending = [t for t in asyncio.all_tasks() if not t.done() and t is not asyncio.current_task()]

            if pending:
                for task in pending:
                    task.cancel()

                try:
                    await asyncio.wait_for(
                        asyncio.gather(*pending, return_exceptions=True),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    self.logger.warning(
                        "Some tasks did not cancel in time"
                    )

            for handler in self.logger.handlers:
                if hasattr(handler, "flush"):
                    handler.flush()

            python = sys.executable
            args = [python] + sys.argv

            os.execv(python, args)

        except Exception as e:
            self.logger.critical(
                f"Fatal error during restart: {e}",
                exc_info=True
            )
            self._restarting = False

            if confirm_msg:
                try:
                    await confirm_msg.edit(
                        content=f"Restart failed: {str(e)[:100]}"
                    )
                except Exception:
                    pass

            try:
                await self.bot.change_presence(
                    status=discord.Status.online
                )
            except Exception:
                pass

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /status Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="status",
        description="Set the bot's presence status."
    )
    @app_commands.describe(
        type="Activity type.",
        text="Status text.",
        url="Twitch URL (streaming only)",
        state="Online status",
    )
    @app_commands.choices(
        type=[
            app_commands.Choice(
                name="Playing",
                value="playing"
            ),
            app_commands.Choice(
                name="Watching",
                value="watching"
            ),
            app_commands.Choice(
                name="Listening",
                value="listening"
            ),
            app_commands.Choice(
                name="Competing",
                value="competing"
            ),
            app_commands.Choice(
                name="Streaming",
                value="streaming"
            ),
            app_commands.Choice(
                name="Custom",
                value="custom"
            ),
        ],
        state=[
            app_commands.Choice(
                name="Online",
                value="online"
            ),
            app_commands.Choice(
                name="Idle",
                value="idle"
            ),
            app_commands.Choice(
                name="Do Not Disturb",
                value="dnd"
            ),
            app_commands.Choice(
                name="Invisible",
                value="invisible"
            ),
        ],
    )
    async def status(
        self,
        interaction: discord.Interaction,
        type: app_commands.Choice[str],
        text: str,
        state: Optional[app_commands.Choice[str]] = None,
        url: Optional[str] = None,
    ):
        if interaction.user.id != BOT_OWNER_ID:
            await interaction.response.send_message(
                view=PermissionError(),
                ephemeral=True
            )
            return

        presence_status = (
            getattr(discord.Status, state.value)
            if state
            else discord.Status.online
        )

        activity: Optional[discord.BaseActivity] = None

        match type.value:
            case "playing":
                activity = discord.Game(name=text)

            case "watching":
                activity = discord.Activity(
                    type=discord.ActivityType.watching,
                    name=text,
                )

            case "listening":
                activity = discord.Activity(
                    type=discord.ActivityType.listening,
                    name=text,
                )

            case "competing":
                activity = discord.Activity(
                    type=discord.ActivityType.competing,
                    name=text,
                )

            case "streaming":
                if not url:
                    await interaction.response.send_message(
                        "Streaming status requires a Twitch URL.",
                        ephemeral=True,
                    )
                    return
                activity = discord.Streaming(name=text, url=url)

            case "custom":
                activity = discord.Activity(
                    type=discord.ActivityType.custom,
                    state=text,
                )

        await self.bot.change_presence(
            activity=activity,
            status=presence_status,
        )

        await interaction.response.send_message(
            f"Status updated: `{type.name}`: `{text}`",
            ephemeral=True,
        )

async def setup(bot: commands.Bot):
    cog = BotOwner(bot)
    await bot.add_cog(cog)

    assert cog.app_command is not None