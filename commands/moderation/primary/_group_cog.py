import discord
from discord.ext import commands
from discord import app_commands

from typing import (
    TYPE_CHECKING,
    cast
)

if TYPE_CHECKING:
    from bot import UtilityBot

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

from constants import CONTESTED_EMOJI_ID

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
        if not isinstance(actor, discord.Member) or not self.can_moderate(actor):
            return

        if isinstance(error, commands.MemberNotFound):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to ban member!**\n"
                f"Please provide a valid user to ban."
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to ban member!**\n"
                f"Please provide a member to ban."
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to ban member!**\n"
                f"Please provide a valid user to ban."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation un-ban Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="un-ban", description="Unban a user from the server.")
    @app_commands.describe(
        user   = "The user ID, username, or tag to unban.",
        reason = "Reason for the ban removal."
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
    async def unban_prefix(
        self,
        ctx:   commands.Context[commands.Bot],
        user:  str,
        *,
        flags: UnbanFlags
    ) -> None:
        await run_unban_prefix(self, ctx, user, flags)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation bans Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="bans", description="View all banned members.")
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
    async def bans_prefix(self, ctx: commands.Context[commands.Bot]) -> None:
        await run_bans_prefix(self, ctx)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation kick Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="kick", description="Kick a member from the server.")
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
        if not isinstance(actor, discord.Member) or not self.can_moderate(actor):
            return

        if isinstance(error, commands.MemberNotFound):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to kick member!**\n"
                f"Please provide a valid user to kick."
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to kick member!**\n"
                f"Please provide a member to kick."
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to kick member!**\n"
                f"Please provide a valid user to kick."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation timeout Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="timeout", description="Timeout a member.")
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
                        "tt" , "to" , "m"
        ]
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
        if not isinstance(actor, discord.Member) or not self.can_moderate(actor):
            return

        if isinstance(error, commands.MemberNotFound):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
                f"Please provide a valid user to timeout."
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
                f"Please provide a member to timeout."
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to timeout member!**\n"
                f"Please provide a valid user to timeout."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation un-timeout Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="un-timeout", description="Remove timeout from a member.")
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
                          "un-time-out", "un-mute", "un-t-o", "un-t-t", "u-t-t", "u-t-o", "u-m", "u-t", "un-to", "un-m",
            "un_timeout", "un_time_out", "un_mute", "un_t_o", "un_t_t", "u_t_t", "u_t_o", "u_m", "u_t", "un_to", "un_m",
            "untimeout" ,                "unmute" , "unt_o" , "untt"  , "utt"  , "uto"  , "um" , "ut" , "unto" , "unm"
        ]
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
        if not isinstance(actor, discord.Member) or not self.can_unban_untimeout(actor):
            return

        if isinstance(error, commands.MemberNotFound):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to remove timeout!**\n"
                f"Please provide a valid user."
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to remove timeout!**\n"
                f"Please provide a member."
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to remove timeout!**\n"
                f"Please provide a valid user."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation timeouts Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="timeouts", description="View all timed out members.")
    async def timeouts(self, interaction: discord.Interaction) -> None:
        await run_timeouts(self, interaction)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .timeouts Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name    = "timeouts",
        aliases = [
            "mute-list", "time-outs", "m-l-s", "t-l-s", "mutes-l", "t-o-s",
            "mute_list", "time_outs", "m_l_s", "t_l_s", "mutes_l", "t_o_s",
            "mutelist" ,              "mls"  , "tls"  , "mutesl" , "tos"
        ]
    )
    async def timeouts_prefix(self, ctx: commands.Context[commands.Bot]) -> None:
        await run_timeouts_prefix(self, ctx)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation purge Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="purge", description="Delete a specified number of messages.")
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
        if not isinstance(actor, discord.Member) or not self.can_moderate(actor):
            return

        if isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == "amount":
                await ctx.send(
                    f"{CONTESTED_EMOJI_ID} **Failed to purge messages!**\n"
                    f"Please provide the number of messages to delete."
                )
            else:
                await ctx.send(
                    f"{CONTESTED_EMOJI_ID} **Failed to purge messages!**\n"
                    f"Please provide all required arguments."
                )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to purge messages!**\n"
                f"Please provide a valid number of messages to delete."
            )
        elif isinstance(error, commands.MissingFlagArgument):
            await ctx.send(
                f"{CONTESTED_EMOJI_ID} **Failed to purge messages!**\n"
                f"Please provide a reason using `/r <reason>`."
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation quarantines Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="quarantines", description="View all quarantined members.")
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
    async def quarantines_prefix(self, ctx: commands.Context[commands.Bot]) -> None:
        await run_quarantines_prefix(self, ctx)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation quarantine Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="quarantine", description="Quarantine a member.")
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
    async def quarantine_prefix(
        self,
        ctx:    commands.Context[commands.Bot],
        member: discord.Member,
        *,
        flags:  QuarantineFlags
    ) -> None:
        await run_quarantine_prefix(self, ctx, member, flags)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation un-quarantine Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="un-quarantine", description="Unquarantine a member.")
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
    async def unquarantine_prefix(
        self,
        ctx:    commands.Context[commands.Bot],
        member: discord.Member,
        *,
        flags:  UnquarantineFlags
    ) -> None:
        await run_unquarantine_prefix(self, ctx, member, flags)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationCommands(cast("UtilityBot", bot)))