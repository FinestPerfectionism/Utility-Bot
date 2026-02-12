import discord
from discord.ext import commands
from discord import app_commands

from typing import cast

from core.permissions import (
    main_guild_only,
    staff_only,
    has_director_role
)
from core.utils import (
    resolve_forum_tags,
    resolve_single_tag,
    assert_forum_thread,
    format_body
)
from core.utils import (
    send_minor_error,
    send_major_error
)

from constants import (
    EMOJI_FORUM_LOCK_ID,
    EMOJI_FORUM_ID,
    TAG_STATUS, TAG_SPECIAL,
    EMOJI_STATUS,
    STAFF_PROPOSALS_CHANNEL_ID
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Proposal Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class Proposal(
    commands.GroupCog,
    name="proposal",
    description="Staff only —— Proposal commands."):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /proposal edit Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="edit",
        description="Set the status, lock state, revision state, and implementation state of the current proposal."
    )
    @app_commands.describe(
        status="Status of the proposal.",
        lock="Lock state of the proposal.",
        needs_revision="Revision state of the proposal.",
        needs_implementation="Implementation state of the proposal.",
        reason="Reason for the update of the proposal.",
        notes="Additional notes."
    )
    @app_commands.choices(
        status=[
            app_commands.Choice(
                name="Accepted",
                value="accepted"
            ),
            app_commands.Choice(
                name="Contested",
                value="contested"
            ),
            app_commands.Choice(
                name="Denied",
                value="denied"
            ),
            app_commands.Choice(
                name="Standstill",
                value="standstill"
            )
        ],
        reason=[
            app_commands.Choice(
                name="Majority rule for.",
                value="Majority rule for."
            ),
            app_commands.Choice(
                name="Majority rule against.",
                value="Majority rule against."
            ),
            app_commands.Choice(
                name="Staff versus Staff.",
                value="Staff versus Staff."
            ),
            app_commands.Choice(
                name="Unique circumstances.",
                value="Unique circumstances."
            ),
            app_commands.Choice(
                name="Proposand unimplementable.",
                value="Proposand unimplementable."
            ),
            app_commands.Choice(
                name="Veto.",
                value="Veto."
            )
        ]
    )
    @main_guild_only()
    @staff_only()
    async def edit(
        self,
        interaction: discord.Interaction,
        status: app_commands.Choice[str],
        lock: bool,
        needs_revision: bool,
        needs_implementation: bool,
        reason: app_commands.Choice[str],
        notes: str | None = None
    ):

        errors: list[str] = []

        status_value = status.value
        reason_value = reason.value

        try:
            thread, forum = assert_forum_thread(interaction)
        except ValueError as e:
            errors.append(str(e))
            thread = cast(discord.Thread, interaction.channel)
            forum = cast(discord.ForumChannel, getattr(thread, "parent", None))

        REASON_WHITELISTS = {
            "accepted": {"Majority rule for."},
            "contested": {"Staff versus Staff.", "Proposand unimplementable."},
            "denied": {"Veto.", "Majority rule against.", "Proposand unimplementable."},
            "standstill": {"Unique circumstances."},
        }

        if reason_value not in REASON_WHITELISTS[status_value]:
            errors.append(
                f"{status_value.capitalize()} proposals cannot use the reason '{reason_value}'."
            )

        if needs_revision and needs_implementation:
            errors.append(
                "Needs Revision and Needs Implementation cannot both be true!"
            )

        if needs_revision and lock:
            errors.append(
                "Needs Revision cannot be true when Locked!"
            )

        if needs_implementation and lock:
            errors.append(
                "Needs Implementation cannot be true when Locked!"
            )

        if status_value == "accepted" and needs_revision:
            errors.append(
                "Accepted proposals cannot need revision!"
            )

        if status_value == "contested":
            if lock:
                errors.append(
                    "Contested proposals cannot be locked!"
                )
            if needs_implementation:
                errors.append(
                    "Contested proposals cannot need implementation!"
                )

        if status_value == "denied":
            if not lock:
                errors.append(
                    "Denied proposals must be locked!"
                )
            if needs_revision:
                errors.append(
                    "Denied proposals cannot need revision!"
                )
            if needs_implementation:
                errors.append(
                    "Denied proposals cannot need implementation!"
                )

        if status_value == "standstill":
            if lock:
                errors.append(
                    "Standstill proposals cannot be locked!"
                )
            if needs_revision or needs_implementation:
                errors.append(
                    "Standstill proposals cannot need revision or implementation!"
                )

        if errors:
            return await send_minor_error(interaction, errors)
        await interaction.response.defer()

        excluded_ids = set(TAG_STATUS.values()) | set(TAG_SPECIAL.values())
        tags = [t for t in thread.applied_tags if t.id not in excluded_ids]

        try:
            tags.append(
                resolve_single_tag(
                    forum,
                    TAG_STATUS[status_value],
                    f"Status tag '{status_value}' not found."
                )
            )

            if needs_implementation:
                tags.append(
                    resolve_single_tag(
                        forum,
                        TAG_SPECIAL["needs_implementation"],
                        "Special tag 'Needs Implementation' not found."
                    )
                )

            if needs_revision:
                tags.append(
                    resolve_single_tag(
                        forum,
                        TAG_SPECIAL["needs_revision"],
                        "Special tag 'Needs Revision' not found."
                    )
                )

            if lock:
                tags.append(
                    resolve_single_tag(
                        forum,
                        TAG_SPECIAL["locked"],
                        "Special tag 'Locked' not found."
                    )
                )
        except ValueError as e:
            return await send_major_error(interaction, str(e))

        await thread.edit(applied_tags=tags, locked=lock)

        header = (
            f"{EMOJI_STATUS[status_value]} "
            f"**Proposal {status_value.capitalize()}"
            f"{f' —— {EMOJI_FORUM_LOCK_ID} Locking Thread' if lock else ''}**"
        )

        reason_line = reason.value
        if needs_implementation:
            reason_line += " Needs implementation."
        if needs_revision:
            reason_line += " Needs revision."

        await interaction.followup.send(
            f"{header}\n{format_body(reason_line, notes)}"
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /proposal lock Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    LOCK_REASONS = [
        app_commands.Choice(
            name="Proposand implemented.",
            value="Proposand implemented."
        ),
        app_commands.Choice(
            name="Issue resolved.",
            value="Issue resolved."
        )
    ]

    @app_commands.command(
        name="lock",
        description="Lock the current proposal."
    )
    @app_commands.describe(
        reason="Reason for the update of the proposal.",
        notes="Additional notes."
    )
    @app_commands.choices(
        reason=LOCK_REASONS
    )
    @main_guild_only()
    @staff_only()
    async def lock_thread(
        self,
        interaction: discord.Interaction,
        reason: app_commands.Choice[str],
        notes: str | None = None
    ):

        try:
            thread, forum = assert_forum_thread(interaction)
        except ValueError as e:
            return await send_minor_error(interaction, str(e))

        await interaction.response.defer()

        tags = [
            t for t in thread.applied_tags
            if t.id not in (
                TAG_SPECIAL["needs_revision"],
                TAG_SPECIAL["needs_implementation"],
                TAG_SPECIAL["locked"],
            )
        ]

        try:
            tags.append(
                resolve_single_tag(
                    forum,
                    TAG_SPECIAL["locked"],
                    "Special tag 'Locked' not found."
                )
            )
        except ValueError as e:
            return await send_major_error(interaction, str(e))

        await thread.edit(applied_tags=tags, locked=True)

        header = f"**{EMOJI_FORUM_LOCK_ID} Locking Thread**"

        await interaction.followup.send(
            f"{header}\n{format_body(reason.value, notes)}"
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /proposal unlock Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    UNLOCK_REASONS = [
        app_commands.Choice(
            name="New issue.",
            value="New issue."
        ),
        app_commands.Choice(
            name="Further discussion needed.",
            value="Further discussion needed."
        )
    ]

    @app_commands.command(
        name="unlock",
        description="Unlock the current proposal."
    )
    @app_commands.describe(
        reason="Reason for the update of the proposal.",
        notes="Additional notes."
    )
    @app_commands.choices(
        reason=UNLOCK_REASONS
    )
    @main_guild_only()
    @staff_only()
    async def unlock_thread(
        self,
        interaction: discord.Interaction,
        reason: app_commands.Choice[str],
        notes: str | None = None
    ):

        try:
            thread, _forum = assert_forum_thread(interaction)
        except ValueError as e:
            return await send_minor_error(interaction, str(e))

        await interaction.response.defer()

        tags = [
            t for t in thread.applied_tags
            if t.id != TAG_SPECIAL["locked"]
        ]

        await thread.edit(applied_tags=tags, locked=False)

        header = f"**{EMOJI_FORUM_ID} Unlocking Thread**"

        await interaction.followup.send(
            f"{header}\n{format_body(reason.value, notes)}"
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /proposal unstandstill Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="unstandstill",
        description="Remove the Standstill status from this thread."
    )
    @main_guild_only()
    @staff_only()
    async def unstandstill(self, interaction: discord.Interaction):

        try:
            thread, forum = assert_forum_thread(interaction)
        except ValueError as e:
            return await send_minor_error(interaction, str(e))

        await interaction.response.defer()

        try:
            standstill_tag = resolve_forum_tags(
                forum, [TAG_STATUS["standstill"]]
            )[0]
        except ValueError:
            return await send_major_error(
                interaction,
                "Standstill tag not found in this forum."
            )

        if standstill_tag.id not in {t.id for t in thread.applied_tags}:
            return await send_minor_error(
                interaction,
                "Standstill tag is not applied to this thread."
            )

        tags = [
            t for t in thread.applied_tags
            if t.id != standstill_tag.id
        ]

        await thread.edit(applied_tags=tags)

        await interaction.followup.send(
            "**Proposal Unstandstilled**"
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ~delete Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name="delete",
        aliases=["d", "del"]
    )
    @has_director_role()
    async def delete_thread(self, ctx: commands.Context):
        if not isinstance(ctx.channel, discord.Thread):
            return

        if ctx.channel.parent_id != STAFF_PROPOSALS_CHANNEL_ID:
            return 

        await ctx.channel.delete()

async def setup(bot: commands.Bot):
    cog = Proposal(bot)
    await bot.add_cog(cog)

    assert cog.app_command is not None