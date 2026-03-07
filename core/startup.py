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

from guild_info.staff_proposal_info import (
    StaffProposalComponents1,
    StaffProposalComponents2a,
    StaffProposalComponents2b,
    StaffProposalComponents3,
    StaffProposalComponents4
)
from guild_info.rules import (
    RuleComponents1,
    RuleComponents2
)
from guild_info.partnership_requirements import (
    RequirementComponents1,
    RequirementComponents2
)
from guild_info.hierarchy import (
    HierarchyComponents1,
    HierarchyComponents2
)

from constants import (
    TICKET_CHANNEL_ID,
    APPLICATION_CHANNEL_ID,
    STAFF_LEAVE_CHANNEL_ID,
    STAFF_PROPOSALS_INFO_CHANNEL_ID,
    RULES_CHANNEL_ID,
    VERIFICATION_CHANNEL_ID,
    PARTNERSHIP_REQUIREMENTS_CHANNEL_ID,
    HIERARCHY_CHANNEL_ID,
)

log = logging.getLogger("Utility Bot")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Startup Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class Startup(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.layout_message_ids = load_layout_message_ids()

    async def cog_load(self) -> None:
        self.bot.loop.create_task(self._wait_and_restore())

    async def _wait_and_restore(self) -> None:
        await self.bot.wait_until_ready()

        verification_cog = None
        while not verification_cog:
            verification_cog = self.bot.get_cog("VerificationHandler")
            if not verification_cog:
                await asyncio.sleep(0.25)

        await self.restore_or_send_layouts()

    async def restore_or_send_layouts(self) -> None:
        view_mapping = {
            "tickets": (TICKET_CHANNEL_ID, TicketComponents),
            "applications": (APPLICATION_CHANNEL_ID, ApplicationComponents),
            "leave": (STAFF_LEAVE_CHANNEL_ID, LeaveComponents),
        }

        for key, (channel_id, view_cls) in view_mapping.items():
            channel = self.bot.get_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                continue

            msg_id = self.layout_message_ids.get(key)
            if msg_id:
                try:
                    await channel.fetch_message(msg_id)
                    self.bot.add_view(view_cls(), message_id=msg_id)
                    continue
                except discord.NotFound:
                    pass

            msg = await channel.send(view=view_cls())
            self.layout_message_ids[key] = msg.id
            self.bot.add_view(view_cls(), message_id=msg.id)
            save_layout_message_ids(self.layout_message_ids)

        verification_channel = self.bot.get_channel(VERIFICATION_CHANNEL_ID)
        if isinstance(verification_channel, discord.TextChannel):
            await self._handle_verification_layout(verification_channel)

        rules_channel = self.bot.get_channel(RULES_CHANNEL_ID)
        if isinstance(rules_channel, discord.TextChannel):
            await self._handle_rules_layout(rules_channel)

        staff_proposals_channel = self.bot.get_channel(STAFF_PROPOSALS_INFO_CHANNEL_ID)
        if isinstance(staff_proposals_channel, discord.TextChannel):
            await self._handle_staff_proposals_layout(staff_proposals_channel)

        partnership_requirements_channel = self.bot.get_channel(PARTNERSHIP_REQUIREMENTS_CHANNEL_ID)
        if isinstance(partnership_requirements_channel, discord.TextChannel):
            await self._handle_partnership_requirements_layout(partnership_requirements_channel)

        hierarchy_channel = self.bot.get_channel(HIERARCHY_CHANNEL_ID)
        if isinstance(hierarchy_channel, discord.TextChannel):
            await self._handle_hierarchy_layout(hierarchy_channel)

    async def _handle_verification_layout(self, channel: discord.TextChannel) -> None:
        verification_cog = cast(
            "VerificationHandler",
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

        except Exception as e:
            log.exception(f"Failed creating verification layout: {e}")

    async def _handle_rules_layout(self, channel: discord.TextChannel) -> None:
        msg_ids = self.layout_message_ids.get("rules", [])

        all_exist = False
        if len(msg_ids) == 2:
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

            msg1 = await channel.send(view=RuleComponents1())
            msg2 = await channel.send(view=RuleComponents2(timestamp=current_timestamp))

            self.layout_message_ids["rules"] = [msg1.id, msg2.id]
            save_layout_message_ids(self.layout_message_ids)

            self.bot.add_view(RuleComponents2(timestamp=current_timestamp), message_id=msg2.id)
            log.info("Rules layout created")
            log.debug("Rules message_ids=%s", self.layout_message_ids["rules"])
        else:
            current_timestamp = int(time.time())
            self.bot.add_view(RuleComponents2(timestamp=current_timestamp), message_id=msg_ids[1])
            log.info("Rules layout restored")
            log.debug("Rules message_ids=%s", msg_ids)

    async def _handle_staff_proposals_layout(self, channel: discord.TextChannel) -> None:
        msg_ids = self.layout_message_ids.get("staff_proposals", [])

        all_exist = False
        if len(msg_ids) == 5:
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
            msg2a = await channel.send(view=StaffProposalComponents2a(timestamp=current_timestamp))
            msg2b = await channel.send(view=StaffProposalComponents2b())
            msg3 = await channel.send(view=StaffProposalComponents3())
            msg4 = await channel.send(view=StaffProposalComponents4())

            self.layout_message_ids["staff_proposals"] = [msg1.id, msg2a.id, msg2b.id, msg3.id, msg4.id]
            save_layout_message_ids(self.layout_message_ids)

            self.bot.add_view(StaffProposalComponents2a(timestamp=current_timestamp), message_id=msg2a.id)
            log.info("Staff proposals layout created")
            log.debug("Staff proposals message_ids=%s", self.layout_message_ids["staff_proposals"])
        else:
            current_timestamp = int(time.time())
            self.bot.add_view(StaffProposalComponents2a(timestamp=current_timestamp), message_id=msg_ids[1])
            log.info("Staff proposals layout restored")
            log.debug("Staff proposals message_ids=%s", msg_ids)

    async def _handle_partnership_requirements_layout(self, channel: discord.TextChannel) -> None:
        msg_ids = self.layout_message_ids.get("partnership_requirements", [])

        all_exist = False
        if len(msg_ids) == 2:
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

            msg1 = await channel.send(view=RequirementComponents1())
            msg2 = await channel.send(view=RequirementComponents2(timestamp=current_timestamp))

            self.layout_message_ids["partnership_requirements"] = [msg1.id, msg2.id]
            save_layout_message_ids(self.layout_message_ids)

            self.bot.add_view(RequirementComponents2(timestamp=current_timestamp), message_id=msg2.id)
            log.info("Partnership requirements layout created")
            log.debug("Partnership requirements message_ids=%s", self.layout_message_ids["partnership_requirements"])
        else:
            current_timestamp = int(time.time())
            self.bot.add_view(RequirementComponents2(timestamp=current_timestamp), message_id=msg_ids[1])
            log.info("Partnership requirements layout restored")
            log.debug("Partnership requirements message_ids=%s", msg_ids)

    async def _handle_hierarchy_layout(self, channel: discord.TextChannel) -> None:
        msg_ids = self.layout_message_ids.get("hierarchy", [])

        all_exist = False
        if len(msg_ids) == 2:
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

            msg1 = await channel.send(view=HierarchyComponents1())
            msg2 = await channel.send(view=HierarchyComponents2(timestamp=current_timestamp))

            self.layout_message_ids["hierarchy"] = [msg1.id, msg2.id]
            save_layout_message_ids(self.layout_message_ids)

            self.bot.add_view(HierarchyComponents2(timestamp=current_timestamp), message_id=msg2.id)
            log.info("Hierarchy layout created")
            log.debug("Hierarchy message_ids=%s", self.layout_message_ids["hierarchy"])
        else:
            current_timestamp = int(time.time())
            self.bot.add_view(HierarchyComponents2(timestamp=current_timestamp), message_id=msg_ids[1])
            log.info("Hierarchy layout restored")
            log.debug("Hierarchy message_ids=%s", msg_ids)

    async def cog_unload(self) -> None:
        pass

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Startup(bot))