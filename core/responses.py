from __future__ import annotations

from typing import Literal, cast, overload

import discord
from discord import Interaction
from discord.ext import commands
from discord.ext.commands import Context  # type: ignore[reportMissingModuleSource]
from discord.ui import LayoutView, Separator, TextDisplay

from constants import (
    ACCEPTED_EMOJI_ID,
    BOT_OWNER_ID,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,
    STANDSTILL_EMOJI_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Response Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

success     : Literal["success"]     = "success"
information : Literal["information"] = "information"
warning     : Literal["warning"]     = "warning"
error       : Literal["error"]       = "error"

MessageType      = Literal["success", "warning", "error", "information"]
SubMessageType   = Literal["warning", "error"]
CtxOrInteraction = Context[commands.Bot] | Interaction[discord.Client]

class _Subfield:
    def __init__(
        self,
        *,
        subtitle          : str | None,
        footer            : str | None,
        contact_bot_owner : bool,
    ) -> None:
        self.subtitle          = subtitle
        self.footer            = footer
        self.contact_bot_owner = contact_bot_owner

class _Field:
    def __init__(
        self,
        *,
        title     : str,
        msg_type  : SubMessageType,
        subfields : list[_Subfield],
    ) -> None:
        self.title     = title
        self.msg_type  = msg_type
        self.subfields = subfields

def _emoji(msg_type : MessageType | SubMessageType) -> str:
    match msg_type:
        case "success":
            return f"{ACCEPTED_EMOJI_ID}"
        case "information":
            return f"{STANDSTILL_EMOJI_ID}"
        case "warning":
            return f"{CONTESTED_EMOJI_ID}"
        case "error":
            return f"{DENIED_EMOJI_ID}"

def _type_prefix(msg_type : MessageType | SubMessageType) -> str:
    match msg_type:
        case "success":
            return "Successfully"
        case "information":
            return ""
        case "warning":
            return "Failed to"
        case "error":
            return "Failed to"

def _build_header(msg_type : MessageType | SubMessageType, title : str) -> str:
    prefix      = _type_prefix(msg_type)
    punctuation = "!" if msg_type in ("warning", "error") else "."
    clean_title = title.rstrip(".!") + punctuation

    if prefix:
        return f"{_emoji(msg_type)} **{prefix} {clean_title}**"
    return f"{_emoji(msg_type)} **{clean_title}**"

def _build_footer_text(footer : str | None, *, contact_bot_owner : bool) -> str | None:
    if footer is None and not contact_bot_owner:
        return None

    base = footer or ""

    if contact_bot_owner:
        if base:
            return f"{base.rstrip('. ')}. Contact <@{BOT_OWNER_ID}>."
        return f"Contact <@{BOT_OWNER_ID}>."
    return f"{base.rstrip('. ')}."

async def _send(target : CtxOrInteraction, view : LayoutView, *, ephemeral : bool = True) -> None:
    if isinstance(target, Interaction):
        if target.response.is_done():
            await target.followup.send(view = view, ephemeral = ephemeral)
        else:
            _ = await target.response.send_message(view = view, ephemeral = ephemeral)
    else:
        _ = await target.send(view = view)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# send_custom_message Response
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

@overload
async def send_custom_message(
    target   : CtxOrInteraction,
    *,
    msg_type : Literal["success", "information"],
    title    : str,
    subtitle : str | None = ...,
    footer   : str | None = ...,
    ephemeral: bool       = ...,
) -> None: ...

@overload
async def send_custom_message(
    target            : CtxOrInteraction,
    *,
    msg_type          : Literal["warning", "error"],
    title             : str,
    subtitle          : str | None = ...,
    footer            : str | None = ...,
    contact_bot_owner : bool       = ...,
    ephemeral         : bool       = ...,
) -> None: ...

async def send_custom_message(
    target            : CtxOrInteraction,
    *,
    msg_type          : MessageType,
    title             : str,
    subtitle          : str | None = None,
    footer            : str | None = None,
    contact_bot_owner : bool       = False,
    ephemeral         : bool       = True,
) -> None:
    allow_contact = contact_bot_owner if msg_type in ("warning", "error") else False

    lines: list[str] = [_build_header(msg_type, title)]
    if subtitle:
        lines.append(subtitle)
    footer_text = _build_footer_text(footer, contact_bot_owner = allow_contact)
    if footer_text:
        lines.append(f"-# {footer_text}")

    content = "\n".join(lines)

    class _SingleView(LayoutView):
        text : TextDisplay[_SingleView] = TextDisplay(content = content)

    await _send(target, _SingleView(), ephemeral = ephemeral)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# multi_custom_message Response
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class _MultiCustomMessage:
    def __init__(self, target : CtxOrInteraction) -> None:
        self._target    : CtxOrInteraction = target
        self._fields    : list[_Field] = []
        self._ephemeral : bool = True

    def set_ephemeral(self, *, value : bool = True) -> _MultiCustomMessage:
        self._ephemeral = value
        return self

    @staticmethod
    def add_subfield(
        *,
        subtitle          : str | None = None,
        footer            : str | None = None,
        contact_bot_owner : bool       = False,
    ) -> _Subfield:
        return _Subfield(
            subtitle          = subtitle,
            footer            = footer,
            contact_bot_owner = contact_bot_owner,
        )

    def add_field(
        self,
        *,
        title     : str,
        msg_type  : SubMessageType,
        subfields : list[_Subfield],
    ) -> _MultiCustomMessage:
        self._fields.append(
            _Field(title = title, msg_type = msg_type, subfields = subfields),
        )
        return self

    def _render_field_blocks(self, field : _Field) -> list[str]:
        def _build_block(index : int, subfield : _Subfield) -> str:
            lines : list[str] = []

            if index == 0:
                lines.append(_build_header(cast(MessageType, field.msg_type), field.title))

            if subfield.subtitle:
                lines.append(subfield.subtitle)

            footer_text = _build_footer_text(
                subfield.footer,
                contact_bot_owner = subfield.contact_bot_owner,
            )
            if footer_text:
                lines.append(f"-# {footer_text}")

            return "\n".join(lines)

        return [_build_block(i, sf) for i, sf in enumerate(field.subfields)]

    def has_errors(self) -> bool:
        return len(self._fields) > 0

    async def send(self) -> None:
        if not self.has_errors():
            return

        all_components : list[TextDisplay[LayoutView] | Separator[LayoutView]] = []

        for field_index, field in enumerate(self._fields):
            if field_index > 0:
                all_components.append(
                    Separator[LayoutView](
                        spacing = discord.SeparatorSpacing.large,
                        visible = True,
                    ),
                )
            all_components.extend(
                TextDisplay(content = block)
                for block in self._render_field_blocks(field)
            )

        class _MultiView(LayoutView):
            pass

        view = _MultiView()
        for component in all_components:
            _ = view.add_item(component)

        await _send(self._target, view, ephemeral = self._ephemeral)

def multi_custom_message(target : CtxOrInteraction) -> _MultiCustomMessage:
    return _MultiCustomMessage(target)
