import discord
from discord.ext import commands

import logging
from typing import cast
import asyncio
import time

from events.systems.applications import ApplicationComponents
from events.systems.tickets import TicketComponents
from events.systems.leave import LeaveComponents
from events.member.verification import (
    VerificationHandler,
    VerificationComponents
)

from core.state import (
    load_layout_message_ids,
    save_layout_message_ids
)

from guild_info.staff_proposals import (
    StaffProposalComponents1,
    StaffProposalComponents2,
    StaffProposalComponents3,
    StaffProposalComponents4
)

from constants import (
    TICKET_CHANNEL_ID,
    APPLICATION_CHANNEL_ID,
    STAFF_LEAVE_CHANNEL_ID,
    STAFF_PROPOSALS_INFO_CHANNEL_ID,
    VERIFICATION_CHANNEL_ID,
)

log = logging.getLogger("Utility Bot")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Startup Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class Startup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.layout_message_ids = load_layout_message_ids()

    async def cog_load(self):
        self.bot.loop.create_task(self._wait_and_restore())

    async def _wait_and_restore(self):
        await self.bot.wait_until_ready()

        verification_cog = None
        while not verification_cog:
            verification_cog = self.bot.get_cog("VerificationHandler")
            if not verification_cog:
                await asyncio.sleep(0.25)

        await self.restore_or_send_layouts()

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

        staff_proposals_channel = self.bot.get_channel(STAFF_PROPOSALS_INFO_CHANNEL_ID)
        if isinstance(staff_proposals_channel, discord.TextChannel):
            try:
                await self._handle_staff_proposals_layout(staff_proposals_channel)
            except Exception as e:
                log.exception(f"Staff proposals layout failed to initialize: {e}")
        else:
            log.warning("Staff proposals layout skipped: channel not found")

    async def _handle_verification_layout(self, channel: discord.TextChannel):
        verification_cog = cast(
            VerificationHandler,
            self.bot.get_cog("VerificationHandler")
        )

        if not verification_cog:
            log.error("Verification layout skipped: VerificationHandler not loaded")
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

    async def _handle_staff_proposals_layout(self, channel: discord.TextChannel):
        msg_ids = self.layout_message_ids.get("staff_proposals", [])

        all_exist = False
        if len(msg_ids) == 4:
            try:
                for msg_id in msg_ids:
                    await channel.fetch_message(msg_id)
                all_exist = True
            except discord.NotFound:
                pass

        if not all_exist:
            if msg_ids:
                for msg_id in msg_ids:
                    try:
                        msg = await channel.fetch_message(msg_id)
                        await msg.delete()
                    except (discord.NotFound, discord.HTTPException):
                        pass

            current_timestamp = int(time.time())

            msg1 = await channel.send(view=StaffProposalComponents1())
            msg2 = await channel.send(view=StaffProposalComponents2(timestamp=current_timestamp))
            msg3 = await channel.send(view=StaffProposalComponents3())
            msg4 = await channel.send(view=StaffProposalComponents4())

            self.layout_message_ids["staff_proposals"] = [msg1.id, msg2.id, msg3.id, msg4.id]
            save_layout_message_ids(self.layout_message_ids)

            self.bot.add_view(StaffProposalComponents2(timestamp=current_timestamp), message_id=msg2.id)
            log.info("Staff proposals layout created")
            log.debug("Staff proposals message_ids=%s", self.layout_message_ids["staff_proposals"])
        else:
            current_timestamp = int(time.time())
            self.bot.add_view(StaffProposalComponents2(timestamp=current_timestamp), message_id=msg_ids[1])
            log.info("Staff proposals layout restored")
            log.debug("Staff proposals message_ids=%s", msg_ids)

    async def cog_unload(self):
        pass

async def setup(bot: commands.Bot):
    await bot.add_cog(Startup(bot))