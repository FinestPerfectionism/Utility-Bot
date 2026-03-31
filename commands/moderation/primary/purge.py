from __future__ import annotations

import discord
from datetime import (
    datetime,
    timezone
)
from typing import (
    TYPE_CHECKING,
    Any
)

if TYPE_CHECKING:
    from ._base import ModerationBase

from commands.moderation.cases import CaseType

from core.utils import (
    send_major_error,
    send_minor_error
)

from constants import (
    COLOR_BLURPLE,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Purge Helpers
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

PurgeableChannel = (
    discord.TextChannel
    | discord.VoiceChannel
    | discord.Thread
)

def _get_purgeable_channel(
    channel: Any 
) -> PurgeableChannel | None:
    if isinstance(channel, discord.TextChannel | discord.VoiceChannel | discord.Thread):
        return channel
    return None

def _build_purge_embed(
    deleted_count: int,
    moderator:     discord.Member,
    member:        discord.Member | None = None,
    proof:         discord.Attachment | None = None,
) -> discord.Embed:
    embed = discord.Embed(
        title = "Messages Purged",
        color = COLOR_BLURPLE,
        timestamp = datetime.now(tz=timezone.utc)
    )
    _ = embed.add_field(name = "Deleted",   value = str(deleted_count), inline = True)
    _ = embed.add_field(name = "Moderator", value = moderator.mention,  inline = True)
    if member:
        _ = embed.add_field(name = "From User", value = member.mention, inline = True)
    if proof:
        _ = embed.set_image(url=proof.url)
    return embed

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation purge Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_purge(
    base:        "ModerationBase",
    interaction: discord.Interaction,
    amount:      int,
    reason:      str,
    member:      discord.Member     | None = None,
    proof:       discord.Attachment | None = None,
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not base.can_apply_standard_actions(actor):
        await send_major_error(
            interaction,
            title = "Unauthorized!",
            texts="You lack the necessary permissions to purge messages.",
            subtitle = "Invalid permissions."
        )
        return

    if amount < 1 or amount > 100:
        await send_minor_error(interaction, "Amount must be between 1 and 100.")
        return

    channel = _get_purgeable_channel(interaction.channel) 

    if channel is None:
        await send_minor_error(interaction, "This command cannot be used in this channel type.", subtitle = "Bad command environment.")
        return

    guild = interaction.guild
    if not guild:
        return

    _ = await interaction.response.defer(ephemeral = True)

    try:
        if member:
            target_id = member.id
            cutoff    = datetime.now(tz=timezone.utc)
            deleted   = await channel.purge(
                limit=amount,
                check=lambda m: (
                    m.author.id == target_id
                    and (cutoff - m.created_at).days < 14
                ),
                before=interaction.created_at,
                bulk=True
            )
        else:
            deleted = await channel.purge(
                limit=amount,
                before=interaction.created_at,
                bulk=True
            )

        metadata: dict[str, Any] = {
            "deleted_messages": len(deleted),
            "channel_id":       channel.id
        }
        if proof:
            metadata["proof_url"] = proof.url

        _ = await base.cases_manager.log_case(
            guild       = guild,
            case_type   = CaseType.PURGE,
            moderator   = actor,
            reason      = reason,
            target_user = member if member else None,
            metadata    = metadata
        )

        embed = _build_purge_embed(len(deleted), actor, member, proof)
        await interaction.followup.send(embed=embed, ephemeral = True)

    except discord.Forbidden:
        await send_major_error(
            interaction,
            texts    = "I lack the necessary permissions to purge messages.",
            subtitle = "Invalid configuration. Contact the owner."
        )