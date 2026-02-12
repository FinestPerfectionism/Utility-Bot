import discord
from discord.ext import (
    commands,
    tasks
)

import logging
from typing import cast
import asyncio

from events.systems.applications import ApplicationComponents
from events.systems.tickets import TicketComponents
from events.systems.leave import LeaveComponents
from events.member.verification import (
    VerificationCog,
    VerificationComponents
)

from core.state import (
    load_layout_message_ids,
    save_layout_message_ids
)
from core.utils import MESSAGE_LOG_QUEUE

from constants import (
    TICKET_CHANNEL_ID,
    APPLICATION_CHANNEL_ID,
    STAFF_LEAVE_CHANNEL_ID,
    MESSAGE_SEND_LOG_CHANNEL_ID,
    VERIFICATION_CHANNEL_ID,
)

log = logging.getLogger("Utility Bot")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Startup Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class Startup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.process_message_logs.start()
        self.layout_message_ids = load_layout_message_ids()

    async def restore_or_send_layouts(self):
        view_mapping = {
            "tickets": (TICKET_CHANNEL_ID, TicketComponents),
            "applications": (APPLICATION_CHANNEL_ID, ApplicationComponents),
            "leave": (STAFF_LEAVE_CHANNEL_ID, LeaveComponents),
            "verification": (VERIFICATION_CHANNEL_ID, VerificationComponents),
        }

        for key, (channel_id, view_cls) in view_mapping.items():
            channel = self.bot.get_channel(channel_id)

            if not isinstance(channel, discord.TextChannel):
                log.warning("Layout '%s' skipped: channel not found", key)
                continue

            log.info("Initializing layout: %s", key)

            try:
                if key == "verification":
                    await self._handle_verification_layout(channel)
                    continue

                msg_id = self.layout_message_ids.get(key)

                if msg_id:
                    try:
                        await channel.fetch_message(msg_id)
                        self.bot.add_view(view_cls(), message_id=msg_id)
                        log.info("Layout '%s' restored", key)
                        log.debug("Layout '%s' message_id=%s", key, msg_id)
                        continue
                    except discord.NotFound:
                        log.debug("Layout '%s' message_id=%s not found", key, msg_id)

                msg = await channel.send(view=view_cls())
                self.layout_message_ids[key] = msg.id
                self.bot.add_view(view_cls(), message_id=msg.id)
                save_layout_message_ids(self.layout_message_ids)

                log.info("Layout '%s' created", key)
                log.debug("Layout '%s' message_id=%s", key, msg.id)

            except Exception:
                log.exception("Layout '%s' failed to initialize", key)

    async def _handle_verification_layout(self, channel: discord.TextChannel):
        verification_cog = cast(
            VerificationCog,
            self.bot.get_cog("VerificationCog")
        )

        if not verification_cog:
            log.error("Verification layout skipped: VerificationCog not loaded")
            return

        msg_id = verification_cog.get_verification_message_id()
        view = VerificationComponents(verification_cog)

        if msg_id:
            try:
                await channel.fetch_message(msg_id)
                self.bot.add_view(view, message_id=msg_id)
                log.info("Verification layout restored")
                log.debug("Verification message_id=%s", msg_id)
                return
            except discord.NotFound:
                log.debug("Verification message_id=%s not found", msg_id)
            except Exception:
                log.exception("Failed restoring verification layout")

        try:
            message = await channel.send(view=view)
            verification_cog.set_verification_message_id(message.id)
            self.bot.add_view(view, message_id=message.id)

            log.info("Verification layout created")
            log.debug("Verification message_id=%s", message.id)

        except Exception:
            log.exception("Failed creating verification layout")

    async def cog_unload(self):
        self.process_message_logs.cancel()

    @tasks.loop(seconds=1)
    async def process_message_logs(self):
        while not MESSAGE_LOG_QUEUE.empty():
            embed = await MESSAGE_LOG_QUEUE.get()
            channel = self.bot.get_channel(MESSAGE_SEND_LOG_CHANNEL_ID)
            if isinstance(channel, discord.TextChannel):
                try:
                    await channel.send(embed=embed)
                except discord.HTTPException:
                    pass

    @process_message_logs.before_loop
    async def before_logs(self):
        await self.bot.wait_until_ready()
        verification_cog = None
        while not verification_cog:
            verification_cog = self.bot.get_cog("VerificationCog")
            if not verification_cog:
                await asyncio.sleep(0.25)

        await self.restore_or_send_layouts()

async def setup(bot: commands.Bot):
    await bot.add_cog(Startup(bot))