from typing import TYPE_CHECKING, cast

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from bot import UtilityBot

from constants import SENIOR_MODERATORS_ROLE_ID
from core.help import ArgDependency, ArgType, ArgumentInfo, OrNode, RoleNode, help_description

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
    @app_commands.rename(delete_messages = "delete-messages")
    @help_description(
        desc         = "Bans a member from the server.",
        command_name = "moderation ban",
        prefix       = False,
        slash        = True,
        access_node  = OrNode(children = [RoleNode(role_id = SENIOR_MODERATORS_ROLE_ID)]),
        arguments   = {
            "member"          : ArgumentInfo(
                arg_type          = ArgType.MemberSelect,
                description       = "Member to ban.",
                required          = True,
                shown_as_optional = True,
                empty_behavior    = "Mass Moderation — See `.help mm` for help",
            ),
            "reason"          : ArgumentInfo(
                arg_type          = ArgType.Text,
                description       = "Reason for the ban.",
                required          = True,
                shown_as_optional = True,
                depends_on        = [ArgDependency(argument = "member")],
            ),
            "delete-messages" : ArgumentInfo(
                arg_type        = ArgType.Integer,
                arg_type_detail = "1-7",
                description     = "Delete messages from the last 1-7 days.",
                required        = False,
                default         = "7",
                depends_on      = [ArgDependency(argument = "member")],
            ),
            "proof"           : ArgumentInfo(
                arg_type    = ArgType.Attachment,
                description = "File proof.",
                required    = False,
                depends_on  = [ArgDependency(argument = "member")],
            ),
        },
    )
    async def ban(
        self,
        interaction     : discord.Interaction,
        member          : discord.Member     | None,
        reason          : str                | None = None,
        delete_messages : int                | None = 7,
        proof           : discord.Attachment | None = None,
    ) -> None:
        await run_ban(self, interaction, member, reason, delete_messages, proof)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation un-ban Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "un-ban", description = "Un-ban a member from the server.")
    @app_commands.describe(
        user   = "The member ID, username, or tag to un-ban.",
        users  = "Comma-separated member IDs/tags for mass un-ban.",
        reason = "Reason for the un-ban.",
    )
    async def unban(
        self,
        interaction : discord.Interaction,
        user        : str | None = None,
        users       : str | None = None,
        reason      : str | None = None,
    ) -> None:
        await run_unban(self, interaction, user, users, reason)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation bans Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "bans", description = "View all banned members.")
    async def bans(self, interaction : discord.Interaction) -> None:
        await run_bans(self, interaction)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation kick Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "kick", description = "Kick a member from the server.")
    @app_commands.describe(
        member = "The member to kick.",
        reason = "Reason for the kick.",
        proof  = "Optional proof attachment.",
    )
    async def kick(
        self,
        interaction : discord.Interaction,
        member      : discord.Member     | None,
        reason      : str                | None = None,
        proof       : discord.Attachment | None = None,
    ) -> None:
        await run_kick(self, interaction, member, reason, proof)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation timeout Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "timeout", description = "Timeout a member.")
    @app_commands.describe(
        member   = "The member to timeout.",
        duration = "Duration (e.g. 30s, 5m, 1h, 2d, 1w).",
        reason   = "Reason for the timeout.",
        proof    = "Optional proof attachment.",
    )
    async def timeout(
        self,
        interaction : discord.Interaction,
        member      : discord.Member     | None,
        duration    : str = "5m",
        reason      : str                | None = None,
        proof       : discord.Attachment | None = None,
    ) -> None:
        await run_timeout(self, interaction, member, duration, reason, proof)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation un-timeout Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "un-timeout", description = "Un-timeout a member.")
    @app_commands.describe(
        member = "The member to un-timeout.",
        reason = "Reason for the un-timeout.",
    )
    async def untimeout(
        self,
        interaction : discord.Interaction,
        member      : discord.Member | None,
        reason      : str            | None = None,
    ) -> None:
        await run_untimeout(self, interaction, member, reason)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation timeouts Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "timeouts", description = "View all timed out members.")
    async def timeouts(self, interaction : discord.Interaction) -> None:
        await run_timeouts(self, interaction)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation purge Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "purge", description = "Delete a specified number of messages.")
    @app_commands.describe(
        amount = "Number of messages to delete (1-100).",
        reason = "Reason for the purge.",
        member = "Only delete messages from this member. Leave empty for mass moderation.",
        proof  = "Optional proof attachment.",
    )
    async def purge(
        self,
        interaction : discord.Interaction,
        amount      : int                | None = 25,
        reason      : str                | None = None,
        member      : discord.Member     | None = None,
        proof       : discord.Attachment | None = None,
    ) -> None:
        await run_purge(self, interaction, amount or 25, reason, member, proof)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation quarantines Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "quarantines", description = "View all quarantined members.")
    async def quarantines(self, interaction : discord.Interaction) -> None:
        await run_quarantines(self, interaction)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation quarantine Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "quarantine", description = "Quarantine a member.")
    @app_commands.describe(
        member = "The member to quarantine.",
        reason = "Reason for the quarantine.",
        proof  = "Optional proof attachment.",
    )
    async def quarantine(
        self,
        interaction : discord.Interaction,
        member      : discord.Member     | None,
        reason      : str                | None = None,
        proof       : discord.Attachment | None = None,
    ) -> None:
        await run_quarantine(self, interaction, member, reason, proof)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation un-quarantine Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name = "un-quarantine", description = "Un-quarantine a member.")
    @app_commands.describe(
        member = "The member to un-quarantine.",
        reason = "Reason for the un-quarantine.",
        proof  = "Optional proof attachment.",
    )
    async def unquarantine(
        self,
        interaction : discord.Interaction,
        member      : discord.Member     | None,
        reason      : str                | None = None,
        proof       : discord.Attachment | None = None,
    ) -> None:
        await run_unquarantine(self, interaction, member, reason, proof)

async def setup(bot : commands.Bot) -> None:
    await bot.add_cog(ModerationCommands(cast("UtilityBot", bot)))
