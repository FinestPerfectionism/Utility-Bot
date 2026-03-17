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
    KickFlags,
    TimeoutFlags,
    PurgeFlags,
)

from .bans import (
    run_ban,
    run_ban_prefix,
    run_bans,
    run_bans_prefix,
)
from .unbans import (
    run_unban,
    run_unban_prefix,
)
from .kicks import (
    run_kick,
    run_kick_prefix,
)
from .timeouts import (
    run_timeout,
    run_timeout_prefix,
    run_timeouts,
    run_timeouts_prefix,
)
from .untimeouts import (
    run_untimeout,
    run_untimeout_prefix,
)
from .purges import (
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
    name="moderation",
    description="Moderators only —— Moderation commands."
):
    def __init__(self, bot: "UtilityBot") -> None:
        ModerationBase.__init__(self, bot)
        commands.GroupCog.__init__(self)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation ban Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.describe(
        member="The member to ban.",
        reason="Reason for the ban.",
        delete_messages="Delete messages from the last 1-7 days.",
        proof="Optional proof attachment."
    )
    async def ban(
        self,
        interaction:     discord.Interaction,
        member:          discord.Member,
        reason:          str,
        delete_messages: int | None = 0,
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
        user="The user ID, username, or tag to unban.",
        reason="Reason for the unban."
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

    @commands.command(name="un-ban", aliases=["unban", "ub"])
    async def unban_prefix(
        self,
        ctx:   commands.Context[commands.Bot],
        user:  str,
        *,
        flags: KickFlags
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

    @commands.command(name="bans", aliases=["banlist", "bls"])
    async def bans_prefix(self, ctx: commands.Context[commands.Bot]) -> None:
        await run_bans_prefix(self, ctx)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation kick Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(
        member="The member to kick.",
        reason="Reason for the kick.",
        proof="Optional proof attachment."
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
        member="The member to timeout.",
        duration="Duration (e.g. 30s, 5m, 1h, 2d, 1w).",
        reason="Reason for the timeout.",
        proof="Optional proof attachment."
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

    @commands.command(name="timeout", aliases=["tt", "mute", "m"])
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
        member="The member to remove timeout from.",
        reason="Reason for removing timeout."
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

    @commands.command(name="un-timeout", aliases=["untimeout", "utt", "unmute", "um"])
    async def untimeout_prefix(
        self,
        ctx:    commands.Context[commands.Bot],
        member: discord.Member,
        *,
        flags:  KickFlags
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
    # .mute-list Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="mute-list", aliases=["mutelist", "mutes", "mls", "time-outs", "timeouts", "tls"])
    async def timeouts_prefix(self, ctx: commands.Context[commands.Bot]) -> None:
        await run_timeouts_prefix(self, ctx)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /moderation purge Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="purge", description="Delete a specified number of messages.")
    @app_commands.describe(
        amount="Number of messages to delete.",
        reason="Reason for purging messages.",
        member="Only delete messages from this member.",
        proof="Optional proof attachment."
    )
    async def purge(
        self,
        interaction: discord.Interaction,
        amount:      int,
        reason:      str,
        member:      discord.Member | None = None,
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

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationCommands(cast("UtilityBot", bot)))
