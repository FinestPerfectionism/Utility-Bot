from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import cast

from typing_extensions import override

from constants import (
    ADMINISTRATORS_GUIDELINES_CHANNEL_ID,
    APPLICATION_CHANNEL_ID,
    DIRECTORATE_GUIDELINES_CHANNEL_ID,
    HIERARCHY_CHANNEL_ID,
    MODERATORS_GUIDELINES_CHANNEL_ID,
    PARTNERSHIP_REQUIREMENTS_CHANNEL_ID,
    PARTNERSHIPS_CHANNEL_ID,
    RULES_CHANNEL_ID,
    STAFF_GUIDELINES_CHANNEL_ID,
    STAFF_LEAVE_CHANNEL_ID,
    STAFF_PROPOSALS_INFO_CHANNEL_ID,
    TICKET_CHANNEL_ID,
    VERIFICATION_CHANNEL_ID,
)
from core.partnership_state import (
    PartnershipData,
    load_partnership_data,
)
from core.state import (
    load_layout_message_ids,
    save_layout_message_ids,
)
from events.member.verification import (
    VerificationComponents,
    VerificationHandler,
)
from events.systems.applications import ApplicationComponents
from events.systems.leave import LeaveComponents
from events.systems.tickets import TicketComponents
from guild_info.guidelines.administrator_guidelines import (
    AdministratorComponents1,
    AdministratorComponents2,
    AdministratorComponents3,
    AdministratorComponents4,
)
from guild_info.guidelines.director_guidelines import (
    DirectorateComponents1,
    DirectorateComponents2,
    DirectorateComponents3,
    DirectorateComponents4,
    DirectorateComponents5,
)
from guild_info.guidelines.moderator_guidelines import (
    ModerationComponents1,
    ModerationComponents2,
    ModerationComponents3,
)
from guild_info.guidelines.staff_guidelines import (
    StaffComponents1,
    StaffComponents2,
    StaffComponents3,
    StaffComponents4,
)
from guild_info.hierarchy import (
    HierarchyComponents1,
    HierarchyComponents2,
    HierarchyComponents3,
    HierarchyComponents4,
    HierarchyComponents5,
    HierarchyComponents6,
    HierarchyComponents7,
)
from guild_info.partnership_requirements import (
    RequirementComponents1,
    RequirementComponents2,
)
from guild_info.partnerships import (
    rebuild_partnership_layout,
    split_partnerships,
)
from guild_info.rules import (
    RuleComponents1,
    RuleComponents2,
)
from guild_info.staff_proposal_info import (
    StaffProposalComponents1,
    StaffProposalComponents2a,
    StaffProposalComponents2b,
    StaffProposalComponents3,
    StaffProposalComponents4,
)

log = logging.getLogger("Utility Bot")

LAYOUT_CONFIG_PATH = Path("data/layout_config.json")

DEFAULT_LAYOUT_CONFIG: dict[str, bool] = {
    "tickets": True,
    "applications": True,
    "leave": True,
    "verification": True,
    "rules": True,
    "staff_proposals": True,
    "partnership_requirements": True,
    "partnerships": True,
    "hierarchy": True,
    "moderation_guidelines": True,
    "administrator_guidelines": True,
    "staff_guidelines": True,
    "directorate_guidelines": True,
}


def load_layout_config() -> dict[str, bool]:
    if not LAYOUT_CONFIG_PATH.exists():
        log.warning("layout_config.json not found, writing defaults and enabling all layouts")
        with LAYOUT_CONFIG_PATH.open("w") as f:
            json.dump(DEFAULT_LAYOUT_CONFIG, f, indent=4)
        return DEFAULT_LAYOUT_CONFIG.copy()

    try:
        with LAYOUT_CONFIG_PATH.open("r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.exception("Failed to read layout_config.json, enabling all layouts: %s", e)
        return DEFAULT_LAYOUT_CONFIG.copy()

    config = DEFAULT_LAYOUT_CONFIG.copy()
    for key in config:
        if key in data and isinstance(data[key], bool):
            config[key] = data[key]
        else:
            log.warning("layout_config.json missing or invalid key '%s', defaulting to True", key)

    return config

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Startup Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class Startup(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.layout_message_ids: dict[str, int | list[int]] = load_layout_message_ids()

    @override
    async def cog_load(self) -> None:
        _ = self.bot.loop.create_task(self._wait_and_restore())

    async def _wait_and_restore(self) -> None:
        await self.bot.wait_until_ready()

        verification_cog: commands.Cog | None = None
        while verification_cog is None:
            verification_cog = self.bot.get_cog("VerificationHandler")
            if verification_cog is None:
                await asyncio.sleep(0.25)

        await self.restore_or_send_layouts()

    async def restore_or_send_layouts(self) -> None:
        config = load_layout_config()

        view_mapping: dict[str, tuple[int, type[discord.ui.View]]] = {
            "tickets": (TICKET_CHANNEL_ID, cast("type[discord.ui.View]", TicketComponents)),
            "applications": (APPLICATION_CHANNEL_ID, cast("type[discord.ui.View]", ApplicationComponents)),
            "leave": (STAFF_LEAVE_CHANNEL_ID, cast("type[discord.ui.View]", LeaveComponents)),
        }

        for key, (channel_id, view_cls) in view_mapping.items():
            if not config.get(key, True):
                log.info("Layout '%s' is disabled in layout_config.json, skipping", key)
                continue

            channel = self.bot.get_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                continue

            raw_id = self.layout_message_ids.get(key)
            msg_id = raw_id if isinstance(raw_id, int) else None
            if msg_id is not None:
                try:
                    _ = await channel.fetch_message(msg_id)
                    self.bot.add_view(view_cls(), message_id = msg_id)
                    continue
                except discord.NotFound:
                    pass

            msg = await channel.send(view = view_cls())
            self.layout_message_ids[key] = msg.id
            self.bot.add_view(view_cls(), message_id = msg.id)
            save_layout_message_ids(self.layout_message_ids)

        layout_handlers: list[tuple[str, int, Callable[[discord.TextChannel], Coroutine[Any, Any, None]]]] = [
            ("verification", VERIFICATION_CHANNEL_ID, self._handle_verification_layout),
            ("rules", RULES_CHANNEL_ID, self._handle_rules_layout),
            ("staff_proposals", STAFF_PROPOSALS_INFO_CHANNEL_ID, self._handle_staff_proposals_layout),
            ("partnership_requirements", PARTNERSHIP_REQUIREMENTS_CHANNEL_ID, self._handle_partnership_requirements_layout),
            ("partnerships", PARTNERSHIPS_CHANNEL_ID, self._handle_partnership_layout),
            ("hierarchy", HIERARCHY_CHANNEL_ID, self._handle_hierarchy_layout),
            ("moderation_guidelines", MODERATORS_GUIDELINES_CHANNEL_ID, self._handle_moderation_guidelines_layout),
            ("administrator_guidelines", ADMINISTRATORS_GUIDELINES_CHANNEL_ID, self._handle_administrator_guidelines_layout),
            ("staff_guidelines", STAFF_GUIDELINES_CHANNEL_ID, self._handle_staff_guidelines_layout),
            ("directorate_guidelines", DIRECTORATE_GUIDELINES_CHANNEL_ID, self._handle_directorate_guidelines_layout),
        ]

        for key, channel_id, handler in layout_handlers:
            if not config.get(key, True):
                log.info("Layout '%s' is disabled in layout_config.json, skipping", key)
                continue

            channel = self.bot.get_channel(channel_id)
            if isinstance(channel, discord.TextChannel):
                await handler(channel)

    async def _handle_verification_layout(self, channel: discord.TextChannel) -> None:
        verification_cog = cast(
            "VerificationHandler",
            self.bot.get_cog("VerificationHandler"),
        )

        if not verification_cog:
            log.error("Verification layout skipped: VerificationHandler not loaded")
            return

        msg_id = verification_cog.get_verification_message_id()
        view = VerificationComponents(verification_cog)

        if msg_id:
            try:
                _ = await channel.fetch_message(msg_id)
                self.bot.add_view(view, message_id = msg_id)
                log.info("Verification layout restored")
                log.debug("Verification message_id = %s", msg_id)
                return
            except discord.NotFound:
                log.debug("Verification message_id = %s not found", msg_id)
            except discord.HTTPException as e:
                log.exception("Failed restoring verification layout: %s", e)

        try:
            message = await channel.send(view = view)
            verification_cog.set_verification_message_id(message.id)
            self.bot.add_view(view, message_id = message.id)

            log.info("Verification layout created")
            log.debug("Verification message_id = %s", message.id)

        except discord.HTTPException as e:
            log.exception("Failed creating verification layout: %s", e)

    async def _handle_rules_layout(self, channel: discord.TextChannel) -> None:
        raw = self.layout_message_ids.get("rules")
        msg_ids: list[int] = raw if isinstance(raw, list) else []

        all_exist = False
        if len(msg_ids) == 2:
            try:
                for msg_id in msg_ids:
                    _ = await channel.fetch_message(msg_id)
                all_exist = True
            except discord.NotFound:
                pass

        if not all_exist:
            for msg_id in msg_ids:
                try:
                    msg = _ = await channel.fetch_message(msg_id)
                    await msg.delete()
                except (discord.NotFound, discord.HTTPException):
                    pass

            current_timestamp = int(time.time())

            try:
                log.info("Rules: sending component 1")
                msg1 = await channel.send(view = RuleComponents1())
                log.info("Rules: sending component 2")
                msg2 = await channel.send(view = RuleComponents2(timestamp = current_timestamp))
            except discord.HTTPException as e:
                log.exception("Rules layout failed during send: %s", e)
                return

            self.layout_message_ids["rules"] = [msg1.id, msg2.id]
            save_layout_message_ids(self.layout_message_ids)

            self.bot.add_view(RuleComponents2(timestamp = current_timestamp), message_id = msg2.id)
            log.info("Rules layout created")
            log.debug("Rules message_ids=%s", self.layout_message_ids["rules"])
        else:
            current_timestamp = int(time.time())
            self.bot.add_view(RuleComponents2(timestamp = current_timestamp), message_id = msg_ids[1])
            log.info("Rules layout restored")
            log.debug("Rules message_ids=%s", msg_ids)

    async def _handle_staff_proposals_layout(self, channel: discord.TextChannel) -> None:
        raw = self.layout_message_ids.get("staff_proposals")
        msg_ids: list[int] = raw if isinstance(raw, list) else []

        all_exist = False
        if len(msg_ids) == 5:
            try:
                for msg_id in msg_ids:
                    _ = await channel.fetch_message(msg_id)
                all_exist = True
            except discord.NotFound:
                pass

        if not all_exist:
            for msg_id in msg_ids:
                try:
                    msg = _ = await channel.fetch_message(msg_id)
                    await msg.delete()
                except (discord.NotFound, discord.HTTPException):
                    pass

            current_timestamp = int(time.time())

            try:
                log.info("Staff proposals: sending component 1")
                msg1 = await channel.send(view = StaffProposalComponents1())
                log.info("Staff proposals: sending component 2a")
                msg2a = await channel.send(view = StaffProposalComponents2a(timestamp = current_timestamp))
                log.info("Staff proposals: sending component 2b")
                msg2b = await channel.send(view = StaffProposalComponents2b())
                log.info("Staff proposals: sending component 3")
                msg3 = await channel.send(view = StaffProposalComponents3())
                log.info("Staff proposals: sending component 4")
                msg4 = await channel.send(view = StaffProposalComponents4())
            except discord.HTTPException as e:
                log.exception("Staff proposals layout failed during send: %s", e)
                return

            self.layout_message_ids["staff_proposals"] = [msg1.id, msg2a.id, msg2b.id, msg3.id, msg4.id]
            save_layout_message_ids(self.layout_message_ids)

            self.bot.add_view(StaffProposalComponents2a(timestamp = current_timestamp), message_id = msg2a.id)
            log.info("Staff proposals layout created")
            log.debug("Staff proposals message_ids=%s", self.layout_message_ids["staff_proposals"])
        else:
            current_timestamp = int(time.time())
            self.bot.add_view(StaffProposalComponents2a(timestamp = current_timestamp), message_id = msg_ids[1])
            log.info("Staff proposals layout restored")
            log.debug("Staff proposals message_ids=%s", msg_ids)

    async def _handle_partnership_requirements_layout(self, channel: discord.TextChannel) -> None:
        raw = self.layout_message_ids.get("partnership_requirements")
        msg_ids: list[int] = raw if isinstance(raw, list) else []

        all_exist = False
        if len(msg_ids) == 2:
            try:
                for msg_id in msg_ids:
                    _ = await channel.fetch_message(msg_id)
                all_exist = True
            except discord.NotFound:
                pass

        if not all_exist:
            for msg_id in msg_ids:
                try:
                    msg = _ = await channel.fetch_message(msg_id)
                    await msg.delete()
                except (discord.NotFound, discord.HTTPException):
                    pass

            current_timestamp = int(time.time())

            try:
                log.info("Partnership requirements: sending component 1")
                msg1 = await channel.send(view = RequirementComponents1())
                log.info("Partnership requirements: sending component 2")
                msg2 = await channel.send(view = RequirementComponents2(timestamp = current_timestamp))
            except discord.HTTPException as e:
                log.exception("Partnership requirements layout failed during send: %s", e)
                return

            self.layout_message_ids["partnership_requirements"] = [msg1.id, msg2.id]
            save_layout_message_ids(self.layout_message_ids)

            self.bot.add_view(RequirementComponents2(timestamp = current_timestamp), message_id = msg2.id)
            log.info("Partnership requirements layout created")
            log.debug("Partnership requirements message_ids=%s", self.layout_message_ids["partnership_requirements"])
        else:
            current_timestamp = int(time.time())
            self.bot.add_view(RequirementComponents2(timestamp = current_timestamp), message_id = msg_ids[1])
            log.info("Partnership requirements layout restored")
            log.debug("Partnership requirements message_ids=%s", msg_ids)

    async def _handle_partnership_layout(self, channel: discord.TextChannel) -> None:
        data: PartnershipData = load_partnership_data()
        partnerships = data["partnerships"]
        header_msg_id = data["header_message_id"]
        msg_ids = data["message_ids"]

        expected_count = len(split_partnerships(partnerships)) if partnerships else 0

        all_exist = False
        if header_msg_id is not None and len(msg_ids) == expected_count:
            try:
                _ = await channel.fetch_message(header_msg_id)
                for msg_id in msg_ids:
                    _ = await channel.fetch_message(msg_id)
                all_exist = True
            except discord.NotFound:
                pass

        if all_exist:
            log.info("Partnership layout restored")
            log.debug("Partnership header_message_id = %s message_ids=%s", header_msg_id, msg_ids)
            return

        try:
            await rebuild_partnership_layout(channel, data)
            log.info("Partnership layout created")
            log.debug("Partnership header_message_id = %s message_ids=%s", data["header_message_id"], data["message_ids"])
        except discord.HTTPException as e:
            log.exception("Partnership layout failed: %s", e)

    async def _handle_hierarchy_layout(self, channel: discord.TextChannel) -> None:
        raw = self.layout_message_ids.get("hierarchy")
        msg_ids: list[int] = raw if isinstance(raw, list) else []

        all_exist = False
        if len(msg_ids) == 7:
            try:
                for msg_id in msg_ids:
                    _ = await channel.fetch_message(msg_id)
                all_exist = True
            except discord.NotFound:
                pass

        if not all_exist:
            for msg_id in msg_ids:
                try:
                    msg = _ = await channel.fetch_message(msg_id)
                    await msg.delete()
                except (discord.NotFound, discord.HTTPException):
                    pass

            current_timestamp = int(time.time())

            try:
                log.info("Hierarchy: sending component 1")
                msg1 = await channel.send(view = HierarchyComponents1())
                log.info("Hierarchy: sending component 2")
                msg2 = await channel.send(view = HierarchyComponents2(timestamp = current_timestamp))
                log.info("Hierarchy: sending component 3")
                msg3 = await channel.send(view = HierarchyComponents3())
                log.info("Hierarchy: sending component 4")
                msg4 = await channel.send(view = HierarchyComponents4())
                log.info("Hierarchy: sending component 5")
                msg5 = await channel.send(view = HierarchyComponents5())
                log.info("Hierarchy: sending component 6")
                msg6 = await channel.send(view = HierarchyComponents6())
                log.info("Hierarchy: sending component 7")
                msg7 = await channel.send(view = HierarchyComponents7())
            except discord.HTTPException as e:
                log.exception("Hierarchy layout failed during send: %s", e)
                return

            self.layout_message_ids["hierarchy"] = [msg1.id, msg2.id, msg3.id, msg4.id, msg5.id, msg6.id, msg7.id]
            save_layout_message_ids(self.layout_message_ids)

            self.bot.add_view(HierarchyComponents2(timestamp = current_timestamp), message_id = msg2.id)
            log.info("Hierarchy layout created")
            log.debug("Hierarchy message_ids=%s", self.layout_message_ids["hierarchy"])
        else:
            current_timestamp = int(time.time())
            self.bot.add_view(HierarchyComponents2(timestamp = current_timestamp), message_id = msg_ids[1])
            log.info("Hierarchy layout restored")
            log.debug("Hierarchy message_ids=%s", msg_ids)

    async def _handle_moderation_guidelines_layout(self, channel: discord.TextChannel) -> None:
        raw = self.layout_message_ids.get("moderation_guidelines")
        msg_ids: list[int] = raw if isinstance(raw, list) else []

        all_exist = False
        if len(msg_ids) == 3:
            try:
                for msg_id in msg_ids:
                    _ = await channel.fetch_message(msg_id)
                all_exist = True
            except discord.NotFound:
                pass

        if not all_exist:
            for msg_id in msg_ids:
                try:
                    msg = _ = await channel.fetch_message(msg_id)
                    await msg.delete()
                except (discord.NotFound, discord.HTTPException):
                    pass

            current_timestamp = int(time.time())

            try:
                log.info("Moderation guidelines: sending component 1")
                msg1 = await channel.send(view = ModerationComponents1())
                log.info("Moderation guidelines: sending component 2")
                msg2 = await channel.send(view = ModerationComponents2(timestamp = current_timestamp))
                log.info("Moderation guidelines: sending component 3")
                msg3 = await channel.send(view = ModerationComponents3())
            except discord.HTTPException as e:
                log.exception("Moderation guidelines layout failed during send: %s", e)
                return

            self.layout_message_ids["moderation_guidelines"] = [msg1.id, msg2.id, msg3.id]
            save_layout_message_ids(self.layout_message_ids)

            self.bot.add_view(ModerationComponents2(timestamp = current_timestamp), message_id = msg2.id)
            log.info("Moderation guidelines layout created")
            log.debug("Moderation guidelines message_ids=%s", self.layout_message_ids["moderation_guidelines"])
        else:
            current_timestamp = int(time.time())
            self.bot.add_view(ModerationComponents2(timestamp = current_timestamp), message_id = msg_ids[1])
            log.info("Moderation guidelines layout restored")
            log.debug("Moderation guidelines message_ids=%s", msg_ids)

    async def _handle_administrator_guidelines_layout(self, channel: discord.TextChannel) -> None:
        raw = self.layout_message_ids.get("administrator_guidelines")
        msg_ids: list[int] = raw if isinstance(raw, list) else []

        all_exist = False
        if len(msg_ids) == 4:
            try:
                for msg_id in msg_ids:
                    _ = await channel.fetch_message(msg_id)
                all_exist = True
            except discord.NotFound:
                pass

        if not all_exist:
            for msg_id in msg_ids:
                try:
                    msg = _ = await channel.fetch_message(msg_id)
                    await msg.delete()
                except (discord.NotFound, discord.HTTPException):
                    pass

            current_timestamp = int(time.time())

            try:
                log.info("Administrator guidelines: sending component 1")
                msg1 = await channel.send(view = AdministratorComponents1())
                log.info("Administrator guidelines: sending component 2")
                msg2 = await channel.send(view = AdministratorComponents2(timestamp = current_timestamp))
                log.info("Administrator guidelines: sending component 3")
                msg3 = await channel.send(view = AdministratorComponents3())
                log.info("Administrator guidelines: sending component 4")
                msg4 = await channel.send(view = AdministratorComponents4())
            except discord.HTTPException as e:
                log.exception("Administrator guidelines layout failed during send: %s", e)
                return

            self.layout_message_ids["administrator_guidelines"] = [msg1.id, msg2.id, msg3.id, msg4.id]
            save_layout_message_ids(self.layout_message_ids)

            self.bot.add_view(AdministratorComponents2(timestamp = current_timestamp), message_id = msg2.id)
            log.info("Administrator guidelines layout created")
            log.debug("Administrator guidelines message_ids=%s", self.layout_message_ids["administrator_guidelines"])
        else:
            current_timestamp = int(time.time())
            self.bot.add_view(AdministratorComponents2(timestamp = current_timestamp), message_id = msg_ids[1])
            log.info("Administrator guidelines layout restored")
            log.debug("Administrator guidelines message_ids=%s", msg_ids)

    async def _handle_staff_guidelines_layout(self, channel: discord.TextChannel) -> None:
        raw = self.layout_message_ids.get("staff_guidelines")
        msg_ids: list[int] = raw if isinstance(raw, list) else []

        all_exist = False
        if len(msg_ids) == 4:
            try:
                for msg_id in msg_ids:
                    _ = await channel.fetch_message(msg_id)
                all_exist = True
            except discord.NotFound:
                pass

        if not all_exist:
            for msg_id in msg_ids:
                try:
                    msg = _ = await channel.fetch_message(msg_id)
                    await msg.delete()
                except (discord.NotFound, discord.HTTPException):
                    pass

            current_timestamp = int(time.time())

            try:
                log.info("Staff guidelines: sending component 1")
                msg1 = await channel.send(view = StaffComponents1())
                log.info("Staff guidelines: sending component 2")
                msg2 = await channel.send(view = StaffComponents2(timestamp = current_timestamp))
                log.info("Staff guidelines: sending component 3")
                msg3 = await channel.send(view = StaffComponents3())
                log.info("Staff guidelines: sending component 4")
                msg4 = await channel.send(view = StaffComponents4())
            except discord.HTTPException as e:
                log.exception("Staff guidelines layout failed during send: %s", e)
                return

            self.layout_message_ids["staff_guidelines"] = [msg1.id, msg2.id, msg3.id, msg4.id]
            save_layout_message_ids(self.layout_message_ids)

            self.bot.add_view(StaffComponents2(timestamp = current_timestamp), message_id = msg2.id)
            log.info("Staff guidelines layout created")
            log.debug("Staff guidelines message_ids=%s", self.layout_message_ids["staff_guidelines"])
        else:
            current_timestamp = int(time.time())
            self.bot.add_view(StaffComponents2(timestamp = current_timestamp), message_id = msg_ids[1])
            log.info("Staff guidelines layout restored")
            log.debug("Staff guidelines message_ids=%s", msg_ids)

    async def _handle_directorate_guidelines_layout(self, channel: discord.TextChannel) -> None:
        raw = self.layout_message_ids.get("directorate_guidelines")
        msg_ids: list[int] = raw if isinstance(raw, list) else []

        all_exist = False
        if len(msg_ids) == 5:
            try:
                for msg_id in msg_ids:
                    _ = await channel.fetch_message(msg_id)
                all_exist = True
            except discord.NotFound:
                pass

        if not all_exist:
            for msg_id in msg_ids:
                try:
                    msg = _ = await channel.fetch_message(msg_id)
                    await msg.delete()
                except (discord.NotFound, discord.HTTPException):
                    pass

            current_timestamp = int(time.time())

            try:
                log.info("Directorate guidelines: sending component 1")
                msg1 = await channel.send(view = DirectorateComponents1())
                log.info("Directorate guidelines: sending component 2")
                msg2 = await channel.send(view = DirectorateComponents2(timestamp = current_timestamp))
                log.info("Directorate guidelines: sending component 3")
                msg3 = await channel.send(view = DirectorateComponents3())
                log.info("Directorate guidelines: sending component 4")
                msg4 = await channel.send(view = DirectorateComponents4())
                log.info("Directorate guidelines: sending component 5")
                msg5 = await channel.send(view = DirectorateComponents5())
            except discord.HTTPException as e:
                log.exception("Directorate guidelines layout failed during send: %s", e)
                return

            self.layout_message_ids["directorate_guidelines"] = [msg1.id, msg2.id, msg3.id, msg4.id, msg5.id]
            save_layout_message_ids(self.layout_message_ids)

            self.bot.add_view(DirectorateComponents2(timestamp = current_timestamp), message_id = msg2.id)
            log.info("Directorate guidelines layout created")
            log.debug("Directorate guidelines message_ids=%s", self.layout_message_ids["directorate_guidelines"])
        else:
            current_timestamp = int(time.time())
            self.bot.add_view(DirectorateComponents2(timestamp = current_timestamp), message_id = msg_ids[1])
            log.info("Directorate guidelines layout restored")
            log.debug("Directorate guidelines message_ids=%s", msg_ids)

    @override
    async def cog_unload(self) -> None:
        pass

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Startup(bot))
