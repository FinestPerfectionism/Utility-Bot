from typing import TYPE_CHECKING, cast

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from bot import UtilityBot

from constants import (
    ADMINISTRATORS_ROLE_ID,
    DIRECTORS_ROLE_ID,
    MODERATORS_ROLE_ID,
    SENIOR_MODERATORS_ROLE_ID,
)
from core.help import ArgumentInfo, RoleConfig, help_description

from ._base import ModerationBase
from .ban import run_ban
from .bans import run_bans
from .kick import run_kick
from .purge import run_purge
from .quarantine import run_quarantine
from .quarantines import run_quarantines
from .timeout import run_timeout
from .timeouts import run_timeouts
from .unban import run_unban
from .unquarantine import run_unquarantine
from .untimeout import run_untimeout

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Moderation Commmands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ModerationCommands(
    commands.GroupCog,
    ModerationBase,
    name        = "moderation",
    description = "Moderators only —— Moderation commands.",
):
    def __init__(self, bot : "UtilityBot") -> None:
        ModerationBase.__init__(self, bot)
        commands.GroupCog.__init__(self)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation ban Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "ban", description = "Ban a member from the server.")
    @app_commands.describe(
        member          = "The member to ban.",
        reason          = "Reason for the ban.",
        delete_messages = "Delete messages from the last 1-7 days.",
        proof           = "Optional proof attachment.",
    )
    @app_commands.rename(delete_messages="delete-messages")
    @help_description(
        desc        = "Senior Moderators only —— Bans a member from the server.",
        prefix      = False,
        slash       = True,
        run_roles   = [RoleConfig(role_id = SENIOR_MODERATORS_ROLE_ID)],
        has_inverse = "moderation un-ban",
        arguments   = {
            "member"          : ArgumentInfo(description = "Member to ban."),
            "reason"          : ArgumentInfo(required=True, description = "Reason for the ban."),
            "delete-messages" : ArgumentInfo(required=False, description = "Delete messages from the last 1-7 days."),
            "proof"           : ArgumentInfo(required=False, description = "Proof attachment."),
        },
    )
    async def ban(
        self,
        interaction     : discord.Interaction,
        member          : discord.Member,
        reason          : str,
        delete_messages : int                | None = 0,
        proof           : discord.Attachment | None = None,
    ) -> None:
        await run_ban(self, interaction, member, reason, delete_messages, proof)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation un-ban Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "un-ban", description = "Un-ban a member from the server.")
    @app_commands.describe(
        user   = "The member ID, username, or tag to un-ban.",
        reason = "Reason for the un-ban.",
    )
    @help_description(
        desc        = "Unbans a user from the server.",
        prefix      = False,
        slash       = True,
        run_roles   = [RoleConfig(role_id = DIRECTORS_ROLE_ID)],
        has_inverse = "moderation ban",
        arguments   = {
            "user"   : ArgumentInfo(description = "User ID, username, or tag to unban."),
            "reason" : ArgumentInfo(required=True, description = "Reason for the unban."),
        },
    )
    async def unban(
        self,
        interaction : discord.Interaction,
        user        : str,
        reason      : str,
    ) -> None:
        await run_unban(self, interaction, user, reason)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation bans Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "bans", description = "View all banned members.")
    @help_description(
        desc      = "Staff* only —— Lists all currently banned users.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id = MODERATORS_ROLE_ID), RoleConfig(role_id = ADMINISTRATORS_ROLE_ID)],
    )
    async def bans(self, interaction : discord.Interaction) -> None:
        await run_bans(self, interaction)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation kick Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "kick", description = "Kick a member from the server.")
    @help_description(
        desc      = "Senior Moderators only —— Kicks a member from the server.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id = SENIOR_MODERATORS_ROLE_ID)],
        arguments = {
            "member" : ArgumentInfo(description = "Member to kick."),
            "reason" : ArgumentInfo(required=True, description = "Reason for the kick."),
            "proof"  : ArgumentInfo(required=False, description = "Proof attachment."),
        },
    )
    @app_commands.describe(
        member = "The member to kick.",
        reason = "Reason for the kick.",
        proof  = "Optional proof attachment.",
    )
    async def kick(
        self,
        interaction : discord.Interaction,
        member      : discord.Member,
        reason      : str,
        proof       : discord.Attachment | None = None,
    ) -> None:
        await run_kick(self, interaction, member, reason, proof)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation timeout Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "timeout", description = "Timeout a member.")
    @help_description(
        desc        = "Moderators only —— Times out a member for a given duration.",
        prefix      = False,
        slash       = True,
        run_roles   = [RoleConfig(role_id = MODERATORS_ROLE_ID)],
        has_inverse = "moderation un-timeout",
        arguments   = {
            "member"   : ArgumentInfo(description = "Member to timeout."),
            "duration" : ArgumentInfo(description = "Duration (e.g. 30s, 5m, 1h, 2d, 1w)."),
            "reason"   : ArgumentInfo(required=True, description = "Reason for the timeout."),
            "proof"    : ArgumentInfo(required=False, description = "Proof attachment."),
        },
    )
    @app_commands.describe(
        member   = "The member to timeout.",
        duration = "Duration (e.g. 30s, 5m, 1h, 2d, 1w).",
        reason   = "Reason for the timeout.",
        proof    = "Optional proof attachment.",
    )
    async def timeout(
        self,
        interaction : discord.Interaction,
        member      : discord.Member,
        duration    : str,
        reason      : str,
        proof       : discord.Attachment | None = None,
    ) -> None:
        await run_timeout(self, interaction, member, duration, reason, proof)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation un-timeout Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "un-timeout", description = "Un-timeout a member.")
    @help_description(
        desc        = "Senior Moderators only —— Removes an active timeout from a member.",
        prefix      = False,
        slash       = True,
        run_roles   = [RoleConfig(role_id = SENIOR_MODERATORS_ROLE_ID)],
        has_inverse = "moderation timeout",
        arguments   = {
            "member" : ArgumentInfo(description = "Member to un-timeout."),
            "reason" : ArgumentInfo(required=True, description = "Reason for removing the timeout."),
        },
    )
    @app_commands.describe(
        member = "The member to un-timeout.",
        reason = "Reason for the un-timeout.",
    )
    async def untimeout(
        self,
        interaction : discord.Interaction,
        member      : discord.Member,
        reason      : str,
    ) -> None:
        await run_untimeout(self, interaction, member, reason)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation timeouts Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "timeouts", description = "View all timed out members.")
    @help_description(
        desc      = "Staff* only —— Lists all currently timed out members.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id = MODERATORS_ROLE_ID), RoleConfig(role_id = ADMINISTRATORS_ROLE_ID)],
    )
    async def timeouts(self, interaction : discord.Interaction) -> None:
        await run_timeouts(self, interaction)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation purge Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "purge", description = "Delete a specified number of messages.")
    @help_description(
        desc      = "Moderators only —— Bulk deletes recent messages, optionally filtered to a single member.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id = MODERATORS_ROLE_ID)],
        arguments = {
            "amount" : ArgumentInfo(description = "Number of messages to delete."),
            "reason" : ArgumentInfo(required=True, description = "Reason for the purge."),
            "member" : ArgumentInfo(required=False, description = "Only delete messages from this member."),
            "proof"  : ArgumentInfo(required=False, description = "Proof attachment."),
        },
    )
    @app_commands.describe(
        amount = "Number of messages to delete.",
        reason = "Reason for the purge.",
        member = "Only delete messages from this member.",
        proof  = "Optional proof attachment.",
    )
    async def purge(
        self,
        interaction : discord.Interaction,
        amount      : int,
        reason      : str,
        member      : discord.Member     | None = None,
        proof       : discord.Attachment | None = None,
    ) -> None:
        await run_purge(self, interaction, amount, reason, member, proof)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation quarantines Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "quarantines", description = "View all quarantined members.")
    @help_description(
        desc      = "Staff\\* only —— Lists all currently quarantined members.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id = MODERATORS_ROLE_ID), RoleConfig(role_id = ADMINISTRATORS_ROLE_ID)],
    )
    async def quarantines(self, interaction : discord.Interaction) -> None:
        await run_quarantines(self, interaction)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation quarantine Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "quarantine", description = "Quarantine a member.")
    @help_description(
        desc        = "Senior Moderators only —— Places a member into quarantine.",
        prefix      = False,
        slash       = True,
        run_roles   = [RoleConfig(role_id = SENIOR_MODERATORS_ROLE_ID)],
        has_inverse = "moderation un-quarantine",
        arguments   = {
            "member" : ArgumentInfo(description = "Member to quarantine."),
            "reason" : ArgumentInfo(required=True, description = "Reason for the quarantine."),
            "proof"  : ArgumentInfo(required=False, description = "Proof attachment."),
        },
    )
    @app_commands.describe(
        member = "The member to quarantine.",
        reason = "Reason for the quarantine.",
        proof  = "Optional proof attachment.",
    )
    async def quarantine(
        self,
        interaction : discord.Interaction,
        member      : discord.Member,
        reason      : str,
        proof       : discord.Attachment | None = None,
    ) -> None:
        await run_quarantine(self, interaction, member, reason, proof)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation un-quarantine Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "un-quarantine", description = "Un-quarantine a member.")
    @help_description(
        desc        = "Directors only —— Removes a member from quarantine.",
        prefix      = False,
        slash       = True,
        run_roles   = [RoleConfig(role_id = DIRECTORS_ROLE_ID)],
        has_inverse = "moderation quarantine",
        arguments   = {
            "member" : ArgumentInfo(description = "Member to unquarantine."),
            "reason" : ArgumentInfo(required=True, description = "Reason for removing quarantine."),
            "proof"  : ArgumentInfo(required=False, description = "Proof attachment."),
        },
    )
    @app_commands.describe(
        member = "The member to un-quarantine.",
        reason = "Reason for the un-quarantine.",
        proof  = "Optional proof attachment.",
    )
    async def unquarantine(
        self,
        interaction : discord.Interaction,
        member      : discord.Member,
        reason      : str,
        proof       : discord.Attachment | None = None,
    ) -> None:
        await run_unquarantine(self, interaction, member, reason, proof)

async def setup(bot : commands.Bot) -> None:
    await bot.add_cog(ModerationCommands(cast("UtilityBot", bot)))
