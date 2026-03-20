import discord
from discord.ext import commands
from discord import app_commands

from typing import (
    TYPE_CHECKING,
    cast
)

if TYPE_CHECKING:
    from bot import UtilityBot

from core.help import (
    help_description,
    ArgumentInfo,
    RoleConfig,
)
from ._base import (
    ModerationBase,
    BanFlags,
    UnbanFlags,
    QuarantineFlags,
    UnquarantineFlags,
    KickFlags,
    TimeoutFlags,
    UntimeoutFlags,
    PurgeFlags,
)

from .ban import (
    run_ban,
    run_ban_prefix,
)
from .bans import (
    run_bans,
    run_bans_prefix,
)
from .unban import (
    run_unban,
    run_unban_prefix,
)
from .kick import (
    run_kick,
    run_kick_prefix,
)
from .timeout import (
    run_timeout,
    run_timeout_prefix,
)
from .timeouts import (
    run_timeouts,
    run_timeouts_prefix,
)
from .untimeout import (
    run_untimeout,
    run_untimeout_prefix,
)
from .quarantine import (
    run_quarantine,
    run_quarantine_prefix,
)
from .quarantines import (
    run_quarantines,
    run_quarantines_prefix,
)
from .unquarantine import (
    run_unquarantine,
    run_unquarantine_prefix,
)
from .purge import (
    run_purge,
    run_purge_prefix,
)

from constants import (
    CONTESTED_EMOJI_ID,
    DIRECTORS_ROLE_ID,
    SENIOR_MODERATORS_ROLE_ID,
    ADMINISTRATORS_ROLE_ID,
    MODERATORS_ROLE_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Moderation Commmands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ModerationCommands(
    commands.GroupCog,
    ModerationBase,
    name        = "moderation",
    description = "Moderators only —— Moderation commands."
):
    def __init__(self, bot: "UtilityBot") -> None:
        ModerationBase.__init__(self, bot)
        commands.GroupCog.__init__(self)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation ban Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.describe(
        member          = "The member to ban.",
        reason          = "Reason for the ban.",
        delete_messages = "Delete messages from the last 1-7 days.",
        proof           = "Optional proof attachment."
    )
    @help_description(
        desc="Bans a member from the server, optionally deleting up to seven days of recent messages and attaching proof. Only Senior Moderators can use the command, and the moderation system still enforces hierarchy checks, protected-role checks, rate limits, and any other runtime safety checks before the ban is applied.",
        prefix=False,
        slash=True,
        run_roles=[RoleConfig(role_id=SENIOR_MODERATORS_ROLE_ID)],
        has_inverse="moderation un-ban",
        arguments={
            "member": ArgumentInfo(description="Member to ban."),
            "reason": ArgumentInfo(required=False, description="Reason for the ban."),
            "delete_messages": ArgumentInfo(required=False, description="Delete messages from the last 1-7 days."),
            "proof": ArgumentInfo(required=False, description="Optional proof attachment."),
        },
    )
    async def ban(
        self,
        interaction:     discord.Interaction,
        member:          discord.Member,
        reason:          str,
        delete_messages: int                | None = 0,
        proof:           discord.Attachment | None = None
    ) -> None:
        await run_ban(self, interaction, member, reason, delete_messages, proof)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .ban Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="ban", aliases=["b"])
    @help_description(
        desc="Bans a member from the prefix command flow using flag-based input for the reason, proof, and optional message deletion window. Only Senior Moderators can use it, and all of the same hierarchy, protected-role, and rate-limit checks still apply at runtime.",
        prefix=True,
        slash=False,
        run_roles=[RoleConfig(role_id=SENIOR_MODERATORS_ROLE_ID)],
        aliases=["b"],
        has_inverse="un-ban",
        arguments={"member": ArgumentInfo(description="Member to ban.")},
    )
    async def ban_prefix(
        self,
        ctx:    commands.Context[commands.Bot],
        member: discord.Member,
        *,
        flags:  BanFlags
    ) -> None:
        await run_ban_prefix(self, ctx, member, flags)

    @ban_prefix.error
    async def ban_prefix_error(self, ctx: commands.Context[commands.Bot], error: Exception) -> None:
        actor = ctx.author
        if not isinstance(actor, discord.Member) or not self.can_apply_standard_actions(actor):
            return

        if isinstance(error, commands.MissingRequiredFlag):
            _ = await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to ban member!**\n"
                f"Please provide a reason using `/r <reason>`."
            )
        elif isinstance(error, commands.BadFlagArgument):
            _ = await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to ban member!**\n"
                f"Please provide a valid number of days to purge using `/d <1-7>`."
            )
        elif isinstance(error, commands.MissingRequiredArgument | commands.BadArgument):
            _ = await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to ban member!**\n"
                f"Please provide a valid member to ban."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation un-ban Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="un-ban", description="Unban a user from the server.")
    @app_commands.describe(
        user   = "The user ID, username, or tag to unban.",
        reason = "Reason for the ban removal."
    )
    @help_description(
        desc="Removes an existing ban from a user identified by ID, username, or tag. This reversal path is restricted to Directors, and the moderation system still applies its reverse-action checks before the unban is carried out.",
        prefix=False,
        slash=True,
        run_roles=[RoleConfig(role_id=DIRECTORS_ROLE_ID)],
        has_inverse="moderation ban",
        arguments={
            "user": ArgumentInfo(description="User ID, username, or tag to unban."),
            "reason": ArgumentInfo(required=False, description="Reason for the unban."),
        },
    )
    async def unban(
        self,
        interaction: discord.Interaction,
        user:        str,
        reason:      str
    ) -> None:
        await run_unban(self, interaction, user, reason)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .un-ban Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name    = "un-ban",
        aliases = [
                      "u-b",
            "un_ban", "u_b",
            "unban" , "ub"
        ]
    )
    @help_description(
        desc="Removes an existing ban from the prefix command flow using the command's flag-based reason syntax. Only Directors can use this reversal command, and the normal reverse-action safeguards still apply at runtime.",
        prefix=True,
        slash=False,
        run_roles=[RoleConfig(role_id=DIRECTORS_ROLE_ID)],
        aliases=["u-b", "un-b", "unban", "ub"],
        has_inverse="ban",
        arguments={"user": ArgumentInfo(description="User ID, username, or tag to unban.")},
    )
    async def unban_prefix(
        self,
        ctx:   commands.Context[commands.Bot],
        user:  str,
        *,
        flags: UnbanFlags
    ) -> None:
        await run_unban_prefix(self, ctx, user, flags)

    @unban_prefix.error
    async def unban_prefix_error(self, ctx: commands.Context[commands.Bot], error: Exception) -> None:
        actor = ctx.author
        if not isinstance(actor, discord.Member) or not self.can_reverse_actions(actor):
            return

        if isinstance(error, commands.MissingRequiredFlag):
            _ = await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to unban user!**\n"
                f"Please provide a reason using `/r <reason>`."
            )
        elif isinstance(error, commands.MissingRequiredArgument | commands.BadArgument):
            _ = await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to unban user!**\n"
                f"Please provide a valid user to unban."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation bans Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="bans", description="View all banned members.")
    @help_description(
        desc="Displays the current list of banned users known to the guild. Anyone who is allowed to view moderation data—Moderators, Administrators, Senior Moderators, or Directors—can use this read-only command.",
        prefix=False,
        slash=True,
        run_roles=[RoleConfig(role_id=MODERATORS_ROLE_ID), RoleConfig(role_id=ADMINISTRATORS_ROLE_ID), RoleConfig(role_id=SENIOR_MODERATORS_ROLE_ID), RoleConfig(role_id=DIRECTORS_ROLE_ID)],
    )
    async def bans(self, interaction: discord.Interaction) -> None:
        await run_bans(self, interaction)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .bans Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name    = "bans",
        aliases = [
            "ban-list", "b-l-s", "b-s",
            "ban_list", "b_l_s", "b_s",
            "banlist" , "bls"  , "bs"
        ]
    )
    @help_description(
        desc="Displays the current ban list from the prefix command flow. Anyone who can view moderation data—Moderators, Administrators, Senior Moderators, or Directors—can use it.",
        prefix=True,
        slash=False,
        run_roles=[RoleConfig(role_id=MODERATORS_ROLE_ID), RoleConfig(role_id=ADMINISTRATORS_ROLE_ID), RoleConfig(role_id=SENIOR_MODERATORS_ROLE_ID), RoleConfig(role_id=DIRECTORS_ROLE_ID)],
        aliases=["ban-list", "b-l-s", "b-s", "banlist", "bls", "bs"],
    )
    async def bans_prefix(self, ctx: commands.Context[commands.Bot]) -> None:
        await run_bans_prefix(self, ctx)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation kick Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="kick", description="Kick a member from the server.")
    @help_description(
        desc="Kicks a member from the server and optionally records a reason or proof attachment. Only Senior Moderators can use the command, and the action still respects hierarchy checks, protected-role restrictions, and the moderation rate-limit safeguards enforced at runtime.",
        prefix=False,
        slash=True,
        run_roles=[RoleConfig(role_id=SENIOR_MODERATORS_ROLE_ID)],
        arguments={
            "member": ArgumentInfo(description="Member to kick."),
            "reason": ArgumentInfo(required=False, description="Reason for the kick."),
            "proof": ArgumentInfo(required=False, description="Optional proof attachment."),
        },
    )
    @app_commands.describe(
        member = "The member to kick.",
        reason = "Reason for the kick.",
        proof  = "Optional proof attachment."
    )
    async def kick(
        self,
        interaction: discord.Interaction,
        member:      discord.Member,
        reason:      str,
        proof:       discord.Attachment | None = None
    ) -> None:
        await run_kick(self, interaction, member, reason, proof)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .kick Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="kick", aliases=["k"])
    @help_description(
        desc="Kicks a member through the prefix command flow using the command's flag-based reason and proof syntax. Only Senior Moderators can use it, and the same hierarchy, protected-role, and rate-limit checks still apply at runtime.",
        prefix=True,
        slash=False,
        run_roles=[RoleConfig(role_id=SENIOR_MODERATORS_ROLE_ID)],
        aliases=["k"],
        arguments={"member": ArgumentInfo(description="Member to kick.")},
    )
    async def kick_prefix(
        self,
        ctx:    commands.Context[commands.Bot],
        member: discord.Member,
        *,
        flags:  KickFlags
    ) -> None:
        await run_kick_prefix(self, ctx, member, flags)

    @kick_prefix.error
    async def kick_prefix_error(self, ctx: commands.Context[commands.Bot], error: Exception) -> None:
        actor = ctx.author
        if not isinstance(actor, discord.Member) or not self.can_apply_standard_actions(actor):
            return

        if isinstance(error, commands.MissingRequiredFlag):
            _ = await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to kick member!**\n"
                f"Please provide a reason using `/r <reason>`."
            )
        elif isinstance(error, commands.MissingRequiredArgument | commands.BadArgument):
            _ = await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to kick member!**\n"
                f"Please provide a valid member to kick."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation timeout Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="timeout", description="Timeout a member.")
    @help_description(
        desc="Applies a timed timeout to a member for the supplied duration, with optional reason and proof metadata. Only Senior Moderators can use it, and the moderation system still enforces hierarchy checks, protected-role checks, duration parsing, and rate-limit safeguards before the timeout is applied.",
        prefix=False,
        slash=True,
        run_roles=[RoleConfig(role_id=SENIOR_MODERATORS_ROLE_ID)],
        has_inverse="moderation un-timeout",
        arguments={
            "member": ArgumentInfo(description="Member to timeout."),
            "duration": ArgumentInfo(description="Duration such as 30s, 5m, 1h, 2d, or 1w."),
            "reason": ArgumentInfo(required=False, description="Reason for the timeout."),
            "proof": ArgumentInfo(required=False, description="Optional proof attachment."),
        },
    )
    @app_commands.describe(
        member   = "The member to timeout.",
        duration = "Duration (e.g. 30s, 5m, 1h, 2d, 1w).",
        reason   = "Reason for the timeout.",
        proof    = "Optional proof attachment."
    )
    async def timeout(
        self,
        interaction: discord.Interaction,
        member:      discord.Member,
        duration:    str,
        reason:      str,
        proof:       discord.Attachment | None = None
    ) -> None:
        await run_timeout(self, interaction, member, duration, reason, proof)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .timeout Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name    = "timeout",
        aliases = [
            "time-out", "t-t", "t-o",
            "time_out", "t_t", "t_o",
                        "tt" , "to"
        ]
    )
    @help_description(
        desc="Applies a timed timeout from the prefix command flow using the command's flag-based duration, reason, and proof syntax. Only Senior Moderators can use it, and the same hierarchy and safety checks still apply at runtime.",
        prefix=True,
        slash=False,
        run_roles=[RoleConfig(role_id=SENIOR_MODERATORS_ROLE_ID)],
        aliases=["time-out", "t-t", "t-o", "tt", "to"],
        has_inverse="un-timeout",
        arguments={"member": ArgumentInfo(description="Member to timeout.")},
    )
    async def timeout_prefix(
        self,
        ctx:    commands.Context[commands.Bot],
        member: discord.Member,
        *,
        flags:  TimeoutFlags
    ) -> None:
        await run_timeout_prefix(self, ctx, member, flags)

    @timeout_prefix.error
    async def timeout_prefix_error(self, ctx: commands.Context[commands.Bot], error: Exception) -> None:
        actor = ctx.author
        if not isinstance(actor, discord.Member) or not self.can_apply_standard_actions(actor):
            return

        if isinstance(error, commands.MissingRequiredFlag):
            _ = await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
                f"Please provide a duration using `/d <duration>` and a reason using `/r <reason>`."
            )
        elif isinstance(error, commands.MissingRequiredArgument | commands.BadArgument):
            _ = await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
                f"Please provide a valid member to timeout."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation un-timeout Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="un-timeout", description="Remove timeout from a member.")
    @help_description(
        desc="Removes an existing timeout from a member and records the reversal reason. Only Directors can use this reversal path, and the moderation system still enforces its reverse-action checks before the timeout is lifted.",
        prefix=False,
        slash=True,
        run_roles=[RoleConfig(role_id=DIRECTORS_ROLE_ID)],
        has_inverse="moderation timeout",
        arguments={
            "member": ArgumentInfo(description="Member to untimeout."),
            "reason": ArgumentInfo(required=False, description="Reason for removing the timeout."),
        },
    )
    @app_commands.describe(
        member = "The member to remove timeout from.",
        reason = "Reason for the timeout removal."
    )
    async def untimeout(
        self,
        interaction: discord.Interaction,
        member:      discord.Member,
        reason:      str
    ) -> None:
        await run_untimeout(self, interaction, member, reason)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .un-timeout Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name    = "un-timeout",
        aliases = [
                          "un-time-out",            "un-t-o", "un-t-t", "u-t-t", "u-t-o",        "u-t", "un-to",
            "un_timeout", "un_time_out",            "un_t_o", "un_t_t", "u_t_t", "u_t_o",        "u_t", "un_to",
            "untimeout" ,                           "unt_o" , "untt"  , "utt"  , "uto"  ,        "ut" , "unto"
        ]
    )
    @help_description(
        desc="Removes an existing timeout from the prefix command flow using the command's flag-based reason syntax. Only Directors can use it, and the normal reverse-action safeguards still apply at runtime.",
        prefix=True,
        slash=False,
        run_roles=[RoleConfig(role_id=DIRECTORS_ROLE_ID)],
        aliases=["un-time-out", "un-t-o", "un-t-t", "u-t-t", "u-t-o", "u-t", "un-to", "untimeout", "unt_o", "untt", "utt", "uto", "ut", "unto"],
        has_inverse="timeout",
        arguments={"member": ArgumentInfo(description="Member to untimeout.")},
    )
    async def untimeout_prefix(
        self,
        ctx:    commands.Context[commands.Bot],
        member: discord.Member,
        *,
        flags:  UntimeoutFlags
    ) -> None:
        await run_untimeout_prefix(self, ctx, member, flags)

    @untimeout_prefix.error
    async def untimeout_prefix_error(self, ctx: commands.Context[commands.Bot], error: Exception) -> None:
        actor = ctx.author
        if not isinstance(actor, discord.Member) or not self.can_reverse_actions(actor):
            return

        if isinstance(error, commands.MissingRequiredFlag):
            _ = await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to remove timeout!**\n"
                f"Please provide a reason using `/r <reason>`."
            )
        elif isinstance(error, commands.MissingRequiredArgument | commands.BadArgument):
            _ = await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to remove timeout!**\n"
                f"Please provide a valid member."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation timeouts Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="timeouts", description="View all timed out members.")
    @help_description(
        desc="Displays the current list of timed out members. Anyone who is allowed to view moderation data—Moderators, Administrators, Senior Moderators, or Directors—can use this read-only command.",
        prefix=False,
        slash=True,
        run_roles=[RoleConfig(role_id=MODERATORS_ROLE_ID), RoleConfig(role_id=ADMINISTRATORS_ROLE_ID), RoleConfig(role_id=SENIOR_MODERATORS_ROLE_ID), RoleConfig(role_id=DIRECTORS_ROLE_ID)],
    )
    async def timeouts(self, interaction: discord.Interaction) -> None:
        await run_timeouts(self, interaction)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .timeouts Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name    = "timeouts",
        aliases = [
                         "time-outs",          "t-l-s",            "t-o-s",
                         "time_outs",          "t_l_s",            "t_o_s",
                                              "tls"  ,            "tos"
        ]
    )
    @help_description(
        desc="Displays the current list of timed out members from the prefix command flow. Anyone who can view moderation data—Moderators, Administrators, Senior Moderators, or Directors—can use it.",
        prefix=True,
        slash=False,
        run_roles=[RoleConfig(role_id=MODERATORS_ROLE_ID), RoleConfig(role_id=ADMINISTRATORS_ROLE_ID), RoleConfig(role_id=SENIOR_MODERATORS_ROLE_ID), RoleConfig(role_id=DIRECTORS_ROLE_ID)],
        aliases=["time-outs", "t-l-s", "t-o-s", "tls", "tos"],
    )
    async def timeouts_prefix(self, ctx: commands.Context[commands.Bot]) -> None:
        await run_timeouts_prefix(self, ctx)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation purge Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="purge", description="Delete a specified number of messages.")
    @help_description(
        desc="Bulk deletes a requested number of recent messages, optionally narrowing the purge to a single member and attaching proof or a written reason. Only Senior Moderators can use it, and the command still relies on the runtime purge safeguards implemented in the moderation subsystem.",
        prefix=False,
        slash=True,
        run_roles=[RoleConfig(role_id=SENIOR_MODERATORS_ROLE_ID)],
        arguments={
            "amount": ArgumentInfo(description="Number of messages to delete."),
            "reason": ArgumentInfo(required=False, description="Reason for the purge."),
            "member": ArgumentInfo(required=False, description="Optional member filter."),
            "proof": ArgumentInfo(required=False, description="Optional proof attachment."),
        },
    )
    @app_commands.describe(
        amount = "Number of messages to delete.",
        reason = "Reason for the message purge.",
        member = "Only delete messages from this member.",
        proof  = "Optional proof attachment."
    )
    async def purge(
        self,
        interaction: discord.Interaction,
        amount:      int,
        reason:      str,
        member:      discord.Member     | None = None,
        proof:       discord.Attachment | None = None
    ) -> None:
        await run_purge(self, interaction, amount, reason, member, proof)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .purge Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="purge", aliases=["p"])
    @help_description(
        desc="Bulk deletes recent messages from the prefix command flow using the command's flag-based reason, proof, and member-filter syntax. Only Senior Moderators can use it, and all purge-specific runtime checks still apply.",
        prefix=True,
        slash=False,
        run_roles=[RoleConfig(role_id=SENIOR_MODERATORS_ROLE_ID)],
        aliases=["p"],
        arguments={"amount": ArgumentInfo(description="Number of messages to delete.")},
    )
    async def purge_prefix(
        self,
        ctx:    commands.Context[commands.Bot],
        amount: int,
        *,
        flags:  PurgeFlags
    ) -> None:
        await run_purge_prefix(self, ctx, amount, flags)

    @purge_prefix.error
    async def purge_prefix_error(self, ctx: commands.Context[commands.Bot], error: Exception) -> None:
        actor = ctx.author
        if not isinstance(actor, discord.Member) or not self.can_apply_standard_actions(actor):
            return

        if isinstance(error, commands.MissingRequiredFlag):
            _ = await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to purge messages!**\n"
                f"Please provide a reason using `/r <reason>`."
            )
        elif isinstance(error, commands.BadFlagArgument):
            _ = await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to purge messages!**\n"
                f"Please provide a valid member using `/u <user>`."
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            _ = await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to purge messages!**\n"
                f"Please provide the number of messages to delete."
            )
        elif isinstance(error, commands.BadArgument):
            _ = await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to purge messages!**\n"
                f"Please provide a valid number of messages to delete."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation quarantines Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="quarantines", description="View all quarantined members.")
    @help_description(
        desc="Displays the current list of quarantined members. Anyone who is allowed to view moderation data—Moderators, Administrators, Senior Moderators, or Directors—can use this read-only command.",
        prefix=False,
        slash=True,
        run_roles=[RoleConfig(role_id=MODERATORS_ROLE_ID), RoleConfig(role_id=ADMINISTRATORS_ROLE_ID), RoleConfig(role_id=SENIOR_MODERATORS_ROLE_ID), RoleConfig(role_id=DIRECTORS_ROLE_ID)],
    )
    async def quarantines(self, interaction: discord.Interaction) -> None:
        await run_quarantines(self, interaction)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .quarantines Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name    = "quarantines",
        aliases = [
            "quarantine-list", "quarantine-v", "q-l-s", "q-v",
            "quarantine_list", "quarantine_v", "q_l_s", "q_v",
            "quarantinelist" , "quarantinev" , "qls"  , "qv"
        ]
    )
    @help_description(
        desc="Displays the current list of quarantined members from the prefix command flow. Anyone who can view moderation data—Moderators, Administrators, Senior Moderators, or Directors—can use it.",
        prefix=True,
        slash=False,
        run_roles=[RoleConfig(role_id=MODERATORS_ROLE_ID), RoleConfig(role_id=ADMINISTRATORS_ROLE_ID), RoleConfig(role_id=SENIOR_MODERATORS_ROLE_ID), RoleConfig(role_id=DIRECTORS_ROLE_ID)],
        aliases=["quarantine-list", "quarantine-v", "q-l-s", "q-v", "quarantinelist", "quarantinev", "qls", "qv"],
    )
    async def quarantines_prefix(self, ctx: commands.Context[commands.Bot]) -> None:
        await run_quarantines_prefix(self, ctx)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation quarantine Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="quarantine", description="Quarantine a member.")
    @help_description(
        desc="Places a member into quarantine and records the reason and optional proof attachment. Only Senior Moderators can use the command, and the same hierarchy, protected-role, and moderation safety checks still apply before the quarantine is added.",
        prefix=False,
        slash=True,
        run_roles=[RoleConfig(role_id=SENIOR_MODERATORS_ROLE_ID)],
        has_inverse="moderation un-quarantine",
        arguments={
            "member": ArgumentInfo(description="Member to quarantine."),
            "reason": ArgumentInfo(required=False, description="Reason for the quarantine."),
            "proof": ArgumentInfo(required=False, description="Optional proof attachment."),
        },
    )
    @app_commands.describe(
        member = "The member to quarantine.",
        reason = "Reason for the quarantine.",
        proof  = "Optional proof attachment."
    )
    async def quarantine(
        self,
        interaction: discord.Interaction,
        member:      discord.Member,
        reason:      str,
        proof:       discord.Attachment | None = None
    ) -> None:
        await run_quarantine(self, interaction, member, reason, proof)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .quarantine Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name    = "quarantine",
        aliases = [
            "quarantine-add", "q-add", "q-a",
            "quarantine_add", "q_add", "q_a",
            "quarantineadd" , "add"  , "qa" , "q"
        ]
    )
    @help_description(
        desc="Places a member into quarantine from the prefix command flow using the command's flag-based reason and proof syntax. Only Senior Moderators can use it, and all of the same hierarchy and safety checks still apply at runtime.",
        prefix=True,
        slash=False,
        run_roles=[RoleConfig(role_id=SENIOR_MODERATORS_ROLE_ID)],
        aliases=["quarantine-add", "q-add", "q-a", "quarantineadd", "add", "qa", "q"],
        has_inverse="un-quarantine",
        arguments={"member": ArgumentInfo(description="Member to quarantine.")},
    )
    async def quarantine_prefix(
        self,
        ctx:    commands.Context[commands.Bot],
        member: discord.Member,
        *,
        flags:  QuarantineFlags
    ) -> None:
        await run_quarantine_prefix(self, ctx, member, flags)

    @quarantine_prefix.error
    async def quarantine_prefix_error(self, ctx: commands.Context[commands.Bot], error: Exception) -> None:
        actor = ctx.author
        if not isinstance(actor, discord.Member) or not self.can_apply_standard_actions(actor):
            return

        if isinstance(error, commands.MissingRequiredFlag):
            _ = await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to quarantine member!**\n"
                f"Please provide a reason using `/r <reason>`."
            )
        elif isinstance(error, commands.MissingRequiredArgument | commands.BadArgument):
            _ = await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to quarantine member!**\n"
                f"Please provide a valid member to quarantine."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation un-quarantine Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="un-quarantine", description="Unquarantine a member.")
    @help_description(
        desc="Removes quarantine from a member and records the reason and optional proof attachment for the reversal. Only Directors can use this reversal path, and the normal reverse-action safeguards still apply at runtime.",
        prefix=False,
        slash=True,
        run_roles=[RoleConfig(role_id=DIRECTORS_ROLE_ID)],
        has_inverse="moderation quarantine",
        arguments={
            "member": ArgumentInfo(description="Member to unquarantine."),
            "reason": ArgumentInfo(required=False, description="Reason for removing quarantine."),
            "proof": ArgumentInfo(required=False, description="Optional proof attachment."),
        },
    )
    @app_commands.describe(
        member = "The member to remove from quarantine.",
        reason = "Reason for the quarantine removal.",
        proof  = "Optional proof attachment."
    )
    async def unquarantine(
        self,
        interaction: discord.Interaction,
        member:      discord.Member,
        reason:      str,
        proof:       discord.Attachment | None = None
    ) -> None:
        await run_unquarantine(self, interaction, member, reason, proof)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .un-quarantine Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name    = "un-quarantine",
        aliases = [
                             "quarantine-remove", "q-remove", "q-r",
            "un_quarantine", "quarantine_remove", "q_remove", "q_r",
            "unquarantine" , "quarantineremove" , "qremove" , "qr"
        ]
    )
    @help_description(
        desc="Removes quarantine from a member through the prefix command flow using the command's flag-based reason and proof syntax. Only Directors can use it, and the usual reverse-action safeguards still apply at runtime.",
        prefix=True,
        slash=False,
        run_roles=[RoleConfig(role_id=DIRECTORS_ROLE_ID)],
        aliases=["quarantine-remove", "q-remove", "q-r", "unquarantine", "quarantineremove", "qremove", "qr"],
        has_inverse="quarantine",
        arguments={"member": ArgumentInfo(description="Member to unquarantine.")},
    )
    async def unquarantine_prefix(
        self,
        ctx:    commands.Context[commands.Bot],
        member: discord.Member,
        *,
        flags:  UnquarantineFlags
    ) -> None:
        await run_unquarantine_prefix(self, ctx, member, flags)

    @unquarantine_prefix.error
    async def unquarantine_prefix_error(self, ctx: commands.Context[commands.Bot], error: Exception) -> None:
        actor = ctx.author
        if not isinstance(actor, discord.Member) or not self.can_reverse_actions(actor):
            return

        if isinstance(error, commands.MissingRequiredFlag):
            _ = await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to unquarantine member!**\n"
                f"Please provide a reason using `/r <reason>`."
            )
        elif isinstance(error, commands.MissingRequiredArgument | commands.BadArgument):
            _ = await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to unquarantine member!**\n"
                f"Please provide a valid member to unquarantine."
            )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationCommands(cast("UtilityBot", bot)))
