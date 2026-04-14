from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import discord

if TYPE_CHECKING:
    from ._group_cog import CasesCommands

from constants import (
    ACCEPTED_EMOJI_ID,
    DIRECTOR_TASKS_CHANNEL_ID,
    DIRECTORS_ROLE_ID,
)
from core.permissions import is_director
from core.responses import multi_custom_message, send_custom_message

from ._base import ClassificationView

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /cases classify Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_classify(
    self        : CasesCommands,
    interaction : discord.Interaction,
    case_id     : int,
    visibility  : Literal["moderators", "senior_moderators", "directors"],
) -> None:
    actor = interaction.user
    if not isinstance(actor, discord.Member):
        return

    if not self.can_view(actor):
        await send_custom_message(
            interaction,
            msg_type = "error",
            title    = "run command",
            subtitle = "You are not authorized to run this command.",
            footer   = "No permissions",
        )
        return

    guild = interaction.guild
    if not guild:
        return

    case = self.cases_manager.get_case_by_id(case_id)

    if not case or case["guild_id"] != guild.id:
        await send_custom_message(
            interaction,
            msg_type = "warning",
            title    = "classify case",
            subtitle = f"Case **#{case_id}** was not found.",
            footer   = "Bad argument",
        )
        return

    if is_director(actor):
        label = visibility.replace("_", " ").title()
        _ = self.cases_manager.set_visibility(case_id, visibility)
        await send_custom_message(
            interaction,
            msg_type = "success",
            title    = f"set #{case_id} visibility to {label}",
        )
        return

    errors = multi_custom_message(interaction)

    if visibility == "directors":
        _ = errors.add_field(
            title     = "classify case",
            msg_type  = "warning",
            subfields = [
                errors.add_subfield(
                    subtitle = "Only Directors can apply or request director-level classification.",
                    footer   = "No permissions",
                ),
            ],
        )

    if case.get("pending_visibility"):
        _ = errors.add_field(
            title     = "classify case",
            msg_type  = "warning",
            subfields = [
                errors.add_subfield(
                    subtitle = (
                        f"Case **#{case_id}** already has a pending classification request. "
                        "It must be resolved before a new one can be submitted."
                    ),
                    footer   = "Bad request",
                ),
            ],
        )

    if errors.has_errors():
        await errors.send()
        return

    forum_channel = self.bot.get_channel(DIRECTOR_TASKS_CHANNEL_ID)
    if not isinstance(forum_channel, discord.ForumChannel):
        await send_custom_message(
            interaction,
            msg_type          = "error",
            title             = "classify case",
            subtitle          = "The Director tasks channel could not be found or is not a forum.",
            footer            = "Invalid IDs",
            contact_bot_owner = True,
        )
        return

    label = visibility.replace("_", " ").title()

    _ = self.cases_manager.request_visibility(case_id, visibility)

    view           = ClassificationView(case_id, self.cases_manager)
    thread_name    = f"DR: Classification Request by {actor.display_name}"
    thread_content = (
        f"{ACCEPTED_EMOJI_ID} **A new classification to {label} request has been made affecting case #{case_id}.**\n"
        f"<@&{DIRECTORS_ROLE_ID}>"
    )

    thread_with_message = await forum_channel.create_thread(
        name    = thread_name,
        content = thread_content,
        view    = view,
    )

    self.bot.add_view(view, message_id=thread_with_message.message.id)

    await send_custom_message(
        interaction,
        msg_type = "information",
        title    = (
            f"Visibility request submitted for Case **#{case_id}**. "
            f"A Director must approve the **{label}** restriction"
        ),
    )
