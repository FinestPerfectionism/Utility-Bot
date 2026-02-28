import re
import time
import discord
from dataclasses import dataclass
from enum import Enum
from discord.ext import commands
from discord import app_commands

from core.permissions import (
    has_director_role,
    main_guild_only,
)
from core.utils import (
    resolve_forum_tags,
    resolve_single_tag,
    assert_forum_thread,
    format_body,
    send_minor_error,
    send_major_error,
)

from constants import (
    EMOJI_FORUM_LOCK_ID,
    EMOJI_FORUM_ID,
    TAG_STATUS, TAG_SPECIAL, TAG_ACTION,
    EMOJI_STATUS,
    STAFF_PROPOSALS_CHANNEL_ID,
    STAFF_COMMITTEE_ROLE_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# State Machine
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ProposalStatus(Enum):
    NONE       = "none"
    ACCEPTED   = "accepted"
    CONTESTED  = "contested"
    DENIED     = "denied"
    STANDSTILL = "standstill"

_VALID_TRANSITIONS: dict[ProposalStatus, set[ProposalStatus]] = {
    ProposalStatus.NONE:       {ProposalStatus.ACCEPTED, ProposalStatus.CONTESTED, ProposalStatus.DENIED, ProposalStatus.STANDSTILL},
    ProposalStatus.ACCEPTED:   {ProposalStatus.CONTESTED, ProposalStatus.DENIED,    ProposalStatus.STANDSTILL},
    ProposalStatus.CONTESTED:  {ProposalStatus.ACCEPTED,  ProposalStatus.DENIED,    ProposalStatus.STANDSTILL},
    ProposalStatus.DENIED:     {ProposalStatus.ACCEPTED,  ProposalStatus.CONTESTED, ProposalStatus.STANDSTILL},
    ProposalStatus.STANDSTILL: set(),
}

def _resolve_status(thread: discord.Thread) -> ProposalStatus:
    tag_ids = {t.id for t in thread.applied_tags}
    for key, tag_id in TAG_STATUS.items():
        if tag_id in tag_ids:
            return ProposalStatus(key)
    return ProposalStatus.NONE

def _has_tag(thread: discord.Thread, tag_id: int) -> bool:
    return any(t.id == tag_id for t in thread.applied_tags)

def _validate_transition(
    current:   ProposalStatus,
    target:    ProposalStatus,
    is_locked: bool,
) -> list[str]:
    errors: list[str] = []
    if is_locked:
        errors.append("This proposal is Locked. Use /proposal unlock before changing its status.")
        return errors
    if current == ProposalStatus.STANDSTILL:
        errors.append("This proposal is in Standstill. Use /proposal unstandstill before assigning a new status.")
        return errors
    if target not in _VALID_TRANSITIONS[current]:
        errors.append(f"Cannot transition from **{current.value}** to **{target.value}**.")
    return errors

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Permissions
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

_COMMITTEE_ROLE_IDS: frozenset[int] = frozenset({STAFF_COMMITTEE_ROLE_ID})

def is_committee(member: discord.Member) -> bool:
    return any(r.id in _COMMITTEE_ROLE_IDS for r in member.roles)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Control Message
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

_CONTROL_HEADER = "## Proposal Control"

_PROCESS_TAG_NAMES: dict[int, str] = {
    TAG_SPECIAL["needs_revision"]:       "Needs Revision",
    TAG_SPECIAL["needs_implementation"]: "Needs Implementation",
    TAG_SPECIAL["locked"]:               "Locked",
    TAG_ACTION["owner_action"]:          "Owner Action",
    TAG_ACTION["sdirector_action"]:      "S. Director Action",
}

@dataclass
class _ControlTimestamps:
    decision_ts:       int | None = None
    implementation_ts: int | None = None
    finalization_ts:   int | None = None

def _parse_timestamps(content: str) -> _ControlTimestamps:
    data = _ControlTimestamps()
    for attr, label in (
        ("decision_ts",       "Decision"),
        ("implementation_ts", "Implementation"),
        ("finalization_ts",   "Finalized"),
    ):
        m = re.search(rf"\*\*{label}:\*\* <t:(\d+):f>", content)
        if m:
            setattr(data, attr, int(m.group(1)))
    return data

def _build_control_content(
    applied_tags: list[discord.ForumTag],
    actor:        discord.Member,
    data:         _ControlTimestamps,
) -> str:
    status_key: str | None = None
    tag_ids = {t.id for t in applied_tags}
    for sk, tid in TAG_STATUS.items():
        if tid in tag_ids:
            status_key = sk
            break

    status_display = status_key.capitalize() if status_key else "None"
    process_names  = [
        _PROCESS_TAG_NAMES[t.id]
        for t in applied_tags
        if t.id in _PROCESS_TAG_NAMES
    ]
    tags_display = ", ".join(process_names) if process_names else "None"

    def _fmt(ts: int | None) -> str:
        return f"<t:{ts}:f>" if ts is not None else "—"

    now = int(time.time())
    return (
        f"{_CONTROL_HEADER}\n"
        f"**Status:** {status_display}\n"
        f"**Process Tags:** {tags_display}\n"
        f"**Decision:** {_fmt(data.decision_ts)}\n"
        f"**Implementation:** {_fmt(data.implementation_ts)}\n"
        f"**Finalized:** {_fmt(data.finalization_ts)}\n"
        f"-# Updated <t:{now}:R> by {actor.mention}"
    )

async def _find_control_message(
    thread: discord.Thread,
    bot_id: int,
) -> discord.Message | None:
    try:
        pins = await thread.pins()
    except discord.HTTPException:
        return None
    for msg in pins:
        if msg.author.id == bot_id and _CONTROL_HEADER in msg.content:
            return msg
    return None

async def _update_control_message(
    thread:       discord.Thread,
    bot:          commands.Bot,
    applied_tags: list[discord.ForumTag],
    actor:        discord.Member,
    *,
    set_decision:       bool = False,
    set_implementation: bool = False,
    set_finalization:   bool = False,
    clear_finalization: bool = False,
) -> None:
    if bot.user is None:
        return

    existing = await _find_control_message(thread, bot.user.id)
    data     = _parse_timestamps(existing.content) if existing else _ControlTimestamps()

    now = int(time.time())
    if set_decision:
        data.decision_ts = now
    if set_implementation:
        data.implementation_ts = now
    if set_finalization:
        data.finalization_ts = now
    if clear_finalization:
        data.finalization_ts = None

    content = _build_control_content(applied_tags, actor, data)

    try:
        if existing:
            await existing.edit(content=content)
        else:
            msg = await thread.send(content)
            await msg.pin()
    except discord.HTTPException:
        pass

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Proposal Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ProposalCommands(
    commands.GroupCog,
    name="proposal",
    description="Staff Committee only —— Proposal commands.",
):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /proposal status Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    REASON_WHITELISTS: dict[str, set[str]] = {
        "accepted":   {"Committee accepted."},
        "contested":  {"Committee contested.", "Proposand unimplementable.", "Out of scope."},
        "denied":     {"Committee denied.", "Veto.", "Proposand unimplementable.", "Out of scope."},
        "standstill": {"Unique circumstances."},
    }

    @app_commands.command(
        name="status",
        description="Set the official Staff Committee decision for this proposal."
    )
    @app_commands.describe(
        status="The formal decision to apply.",
        reason="Reason for this decision.",
        notes="Additional notes."
    )
    @app_commands.choices(
        status=[
            app_commands.Choice(name="Accepted",   value="accepted"),
            app_commands.Choice(name="Contested",  value="contested"),
            app_commands.Choice(name="Denied",     value="denied"),
            app_commands.Choice(name="Standstill", value="standstill"),
        ],
        reason=[
            app_commands.Choice(name="Committee accepted.",        value="Committee accepted."),
            app_commands.Choice(name="Committee contested.",       value="Committee contested."),
            app_commands.Choice(name="Committee denied.",          value="Committee denied."),
            app_commands.Choice(name="Out of scope.",              value="Out of scope."),
            app_commands.Choice(name="Proposand unimplementable.", value="Proposand unimplementable."),
            app_commands.Choice(name="Unique circumstances.",      value="Unique circumstances."),
            app_commands.Choice(name="Veto.",                      value="Veto."),
        ]
    )
    @main_guild_only()
    async def status(
        self,
        interaction: discord.Interaction,
        status: app_commands.Choice[str],
        reason: app_commands.Choice[str],
        notes: str | None = None,
    ):
        member = interaction.guild.get_member(interaction.user.id) if interaction.guild else None
        if member is None or not is_committee(member):
            return await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to run this command.",
                subtitle="Invalid permissions."
            )

        errors: list[str] = []

        try:
            thread, forum = assert_forum_thread(interaction)
        except ValueError as e:
            return await send_minor_error(interaction, str(e))

        status_value  = status.value
        reason_value  = reason.value
        current       = _resolve_status(thread)
        target        = ProposalStatus(status_value)
        is_locked     = _has_tag(thread, TAG_SPECIAL["locked"])

        if reason_value not in self.REASON_WHITELISTS[status_value]:
            errors.append(
                f"{status.name} proposals cannot use the reason \"{reason_value}\"."
            )

        errors.extend(_validate_transition(current, target, is_locked))

        if errors:
            return await send_minor_error(interaction, errors)

        await interaction.response.defer()

        excluded_ids = set(TAG_STATUS.values())
        tags = [t for t in thread.applied_tags if t.id not in excluded_ids]

        try:
            tags.append(
                resolve_single_tag(
                    forum,
                    TAG_STATUS[status_value],
                    f"Status tag '{status.name}' not found."
                )
            )
        except ValueError as e:
            return await send_major_error(interaction, str(e))

        if status_value == "accepted":
            impl_id = TAG_SPECIAL["needs_implementation"]
            if not any(t.id == impl_id for t in tags):
                try:
                    tags.append(
                        resolve_single_tag(
                            forum,
                            impl_id,
                            "Process tag 'Needs Implementation' not found."
                        )
                    )
                except ValueError as e:
                    return await send_major_error(interaction, str(e))

        await thread.edit(applied_tags=tags)

        await interaction.followup.send(
            f"{EMOJI_STATUS[status_value]} **Proposal {status.name}**\n"
            f"{format_body(reason_value, notes)}"
        )

        await _update_control_message(
            thread, self.bot, tags, member,
            set_decision=True,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /proposal tag Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    PROCESS_TAG_LABELS: dict[str, str] = {
        "needs_revision":       "Needs Revision",
        "needs_implementation": "Needs Implementation",
        "owner_action":         "Owner Action",
        "sdirector_action":     "S. Director Action",
    }

    @app_commands.command(
        name="tag",
        description="Apply or remove a process-related tag from this proposal."
    )
    @app_commands.describe(
        tag="The process tag to apply or remove.",
        enabled="True to apply the tag, False to remove it.",
        notes="Additional notes."
    )
    @app_commands.choices(
        tag=[
            app_commands.Choice(name="Needs Revision",       value="needs_revision"),
            app_commands.Choice(name="Needs Implementation", value="needs_implementation"),
            app_commands.Choice(name="Owner Action",         value="owner_action"),
            app_commands.Choice(name="S. Director Action",   value="sdirector_action"),
        ]
    )
    @main_guild_only()
    async def tag(
        self,
        interaction: discord.Interaction,
        tag: app_commands.Choice[str],
        enabled: bool,
        notes: str | None = None,
    ):
        member = interaction.guild.get_member(interaction.user.id) if interaction.guild else None
        if member is None or not is_committee(member):
            return await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to run this command.",
                subtitle="Invalid permissions."
            )

        errors: list[str] = []

        try:
            thread, forum = assert_forum_thread(interaction)
        except ValueError as e:
            return await send_minor_error(interaction, str(e))

        tag_key        = tag.value
        tag_label      = self.PROCESS_TAG_LABELS[tag_key]
        is_locked      = _has_tag(thread, TAG_SPECIAL["locked"])
        current_status = _resolve_status(thread)

        if enabled:
            if is_locked:
                errors.append(
                    "Process tags cannot be applied while this proposal is Locked."
                )

            if current_status == ProposalStatus.STANDSTILL:
                errors.append(
                    "Process tags cannot be applied while this proposal is in Standstill."
                )

            if tag_key == "needs_revision" and current_status == ProposalStatus.ACCEPTED:
                errors.append(
                    "Needs Revision cannot be applied to an Accepted proposal."
                )

            if tag_key == "needs_implementation" and current_status != ProposalStatus.ACCEPTED:
                errors.append(
                    "Needs Implementation can only be applied to Accepted proposals."
                )

        if errors:
            return await send_minor_error(interaction, errors)

        await interaction.response.defer()

        try:
            if tag_key in TAG_SPECIAL:
                tag_id = TAG_SPECIAL[tag_key]
            elif tag_key in TAG_ACTION:
                tag_id = TAG_ACTION[tag_key]
            else:
                return await send_major_error(
                    interaction,
                    f"Tag key '{tag_key}' is not registered."
                )

            target_tag = resolve_single_tag(
                forum,
                tag_id,
                f"Process tag '{tag_label}' not found."
            )
        except ValueError as e:
            return await send_major_error(interaction, str(e))

        tags = [t for t in thread.applied_tags if t.id != target_tag.id]
        if enabled:
            tags.append(target_tag)
            action = "Applied"
        else:
            action = "Removed"

        await thread.edit(applied_tags=tags)

        await interaction.followup.send(
            f"**{action}: {tag_label}**"
            f"{chr(10) + format_body('', notes) if notes else ''}",
            ephemeral=True,
        )

        await _update_control_message(
            thread, self.bot, tags, member,
            set_implementation=(not enabled and tag_key == "needs_implementation"),
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /proposal finalize Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="finalize",
        description="Lock this proposal after final resolution and implementation."
    )
    @app_commands.describe(
        reason="Reason for finalization.",
        notes="Additional notes."
    )
    @app_commands.choices(
        reason=[
            app_commands.Choice(name="Proposand implemented.", value="Proposand implemented."),
            app_commands.Choice(name="Issue resolved.",        value="Issue resolved."),
        ]
    )
    @main_guild_only()
    async def finalize(
        self,
        interaction: discord.Interaction,
        reason: app_commands.Choice[str],
        notes: str | None = None,
    ):
        member = interaction.guild.get_member(interaction.user.id) if interaction.guild else None
        if member is None or not is_committee(member):
            return await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to run this command.",
                subtitle="Invalid permissions."
            )

        errors: list[str] = []

        try:
            thread, forum = assert_forum_thread(interaction)
        except ValueError as e:
            return await send_minor_error(interaction, str(e))

        current_status = _resolve_status(thread)

        if _has_tag(thread, TAG_SPECIAL["locked"]):
            errors.append("This proposal is already finalized.")

        if current_status not in (ProposalStatus.ACCEPTED, ProposalStatus.DENIED):
            errors.append(
                "A proposal can only be finalized when its status is Accepted or Denied."
            )

        if _has_tag(thread, TAG_SPECIAL["needs_revision"]):
            errors.append(
                "This proposal cannot be finalized while Needs Revision is present."
            )

        implementing = reason.value == "Proposand implemented."

        if not implementing and _has_tag(thread, TAG_SPECIAL["needs_implementation"]):
            errors.append(
                "This proposal cannot be finalized while Needs Implementation is present."
            )

        if errors:
            return await send_minor_error(interaction, errors)

        await interaction.response.defer()

        strip_ids = {TAG_SPECIAL["locked"]}
        if implementing:
            strip_ids.add(TAG_SPECIAL["needs_implementation"])
        tags = [t for t in thread.applied_tags if t.id not in strip_ids]

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

        await interaction.followup.send(
            f"**{EMOJI_FORUM_LOCK_ID} Proposal Finalized —— Locking Thread**\n"
            f"{format_body(reason.value, notes)}"
        )

        await _update_control_message(
            thread, self.bot, tags, member,
            set_finalization=True,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /proposal unlock Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="unlock",
        description="Unlock a previously finalized proposal."
    )
    @app_commands.describe(
        reason="Reason for unlocking.",
        notes="Additional notes."
    )
    @app_commands.choices(
        reason=[
            app_commands.Choice(name="New issue.",                  value="New issue."),
            app_commands.Choice(name="Further discussion needed.",   value="Further discussion needed."),
        ]
    )
    @main_guild_only()
    async def unlock_thread(
        self,
        interaction: discord.Interaction,
        reason: app_commands.Choice[str],
        notes: str | None = None,
    ):
        member = interaction.guild.get_member(interaction.user.id) if interaction.guild else None
        if member is None or not is_committee(member):
            return await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to run this command.",
                subtitle="Invalid permissions."
            )

        try:
            thread, _forum = assert_forum_thread(interaction)
        except ValueError as e:
            return await send_minor_error(interaction, str(e))

        if not _has_tag(thread, TAG_SPECIAL["locked"]):
            return await send_minor_error(
                interaction,
                "This proposal is not currently Locked."
            )

        await interaction.response.defer()

        tags = [t for t in thread.applied_tags if t.id != TAG_SPECIAL["locked"]]

        await thread.edit(applied_tags=tags, locked=False)

        await interaction.followup.send(
            f"**{EMOJI_FORUM_ID} Proposal Unlocked**\n"
            f"{format_body(reason.value, notes)}"
        )

        await _update_control_message(
            thread, self.bot, tags, member,
            clear_finalization=True,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /proposal unstandstill Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="unstandstill",
        description="Remove the Standstill status so evaluation may resume."
    )
    @app_commands.describe(
        reason="Reason for removing Standstill.",
        notes="Additional notes."
    )
    @app_commands.choices(
        reason=[
            app_commands.Choice(name="Circumstances resolved.",          value="Circumstances resolved."),
            app_commands.Choice(name="Evaluation resuming.",             value="Evaluation resuming."),
            app_commands.Choice(name="Committee direction established.", value="Committee direction established."),
        ]
    )
    @main_guild_only()
    async def unstandstill(
        self,
        interaction: discord.Interaction,
        reason: app_commands.Choice[str],
        notes: str | None = None,
    ):
        member = interaction.guild.get_member(interaction.user.id) if interaction.guild else None
        if member is None or not is_committee(member):
            return await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to run this command.",
                subtitle="Invalid permissions."
            )

        try:
            thread, forum = assert_forum_thread(interaction)
        except ValueError as e:
            return await send_minor_error(interaction, str(e))

        try:
            standstill_tag = resolve_forum_tags(forum, [TAG_STATUS["standstill"]])[0]
        except ValueError:
            return await send_major_error(
                interaction,
                "Standstill tag not found in this forum."
            )

        if standstill_tag.id not in {t.id for t in thread.applied_tags}:
            return await send_minor_error(
                interaction,
                "This proposal is not currently in Standstill."
            )

        await interaction.response.defer()

        tags = [t for t in thread.applied_tags if t.id != standstill_tag.id]

        await thread.edit(applied_tags=tags)

        await interaction.followup.send(
            f"**Proposal Unstandstilled**\n"
            f"{format_body(reason.value, notes)}"
        )

        await _update_control_message(
            thread, self.bot, tags, member,
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .delete/.del/.d Command
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
    cog = ProposalCommands(bot)
    await bot.add_cog(cog)

    assert cog.app_command is not None