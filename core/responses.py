from __future__ import annotations

from typing import (
    Literal,
    cast,
    final,
    overload,
)

import discord
from discord import (
    Interaction,
    SeparatorSpacing,
)
from discord.ext import commands
from discord.ui import (
    LayoutView,
    Separator,
    TextDisplay,
)

from constants import (
    ACCEPTED_EMOJI,
    BOT_OWNER_ID,
    CONTESTED_EMOJI,
    DENIED_EMOJI,
    STANDSTILL_EMOJI,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Response Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

success     : Literal["success"]     = "success"
information : Literal["information"] = "information"
warning     : Literal["warning"]     = "warning"
error       : Literal["error"]       = "error"

MessageType      = Literal[
    "success",
    "warning",
    "error",
    "information",
]
SubMessageType   = Literal[
    "warning",
    "error",
]
CtxOrInteraction = commands.Context[commands.Bot] | Interaction[discord.Client]

@final
class _Subfield:
    def __init__(
        self,
        *,
        subtitle          : str | None,
        footer            : str | None,
        contact_bot_owner : bool,
    ) -> None:
        self.subtitle          : str | None = subtitle
        self.footer            : str | None = footer
        self.contact_bot_owner : bool       = contact_bot_owner

@final
class _Field:
    def __init__(
        self,
        *,
        title     : str,
        msg_type  : SubMessageType,
        subfields : list[_Subfield],
        override  : bool = False,
    ) -> None:
        self.title     : str             = title
        self.msg_type  : SubMessageType  = msg_type
        self.subfields : list[_Subfield] = subfields
        self.override  : bool            = override

def _emoji(msg_type : MessageType | SubMessageType) -> str:
    match msg_type:
        case "success":
            return f"{ACCEPTED_EMOJI}"
        case "information":
            return f"{STANDSTILL_EMOJI}"
        case "warning":
            return f"{CONTESTED_EMOJI}"
        case "error":
            return f"{DENIED_EMOJI}"

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

def _build_header(
    msg_type : MessageType | SubMessageType,
    title    : str,
    *,
    override : bool = False,
) -> str:
    if override:
        return f"{_emoji(msg_type)} **{title}**"

    prefix      = _type_prefix(msg_type)
    punctuation = "!" if msg_type in (
        "warning",
        "error",
    ) else "."
    clean_title = title.rstrip(".!") + punctuation

    if prefix:
        return f"{_emoji(msg_type)} **{prefix} {clean_title}**"
    return f"{_emoji(msg_type)} **{clean_title}**"

def _build_footer_text(
    footer            : str | None,
    *,
    contact_bot_owner : bool,
) -> str | None:
    if footer is None and not contact_bot_owner:
        return None

    base = footer or ""

    if contact_bot_owner:
        if base:
            return f"{base.rstrip('. ')}. Contact <@{BOT_OWNER_ID}>."
        return f"Contact <@{BOT_OWNER_ID}>."
    return f"{base.rstrip('. ')}."

async def _send(
    target       : CtxOrInteraction,
    view         : LayoutView,
    *,
    ephemeral    : bool                   = True,
    delete_after : float           | None = None,
    message      : discord.Message | None = None,
    edit         : bool                   = False,
) -> discord.Message | None:
    if isinstance(
        target,
        Interaction,
    ):
        if edit:
            return await target.edit_original_response(view = view)
        if target.response.is_done():
            return await target.followup.send(
                view      = view,
                ephemeral = ephemeral,
            )
        _ = await target.response.send_message(
            view      = view,
            ephemeral = ephemeral,
        )
        return None
    else:
        if message is not None:
            return await message.edit(view = view)

        if delete_after is not None:
            return await target.send(
                view         = view,
                delete_after = delete_after,
            )

        return await target.send(view = view)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# send_custom_message Response
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

@overload
async def send_custom_message(
    target       : CtxOrInteraction,
    *,
    msg_type     : Literal[
        "success",
        "information",
    ],
    title        : str,
    subtitle     : str             | None = ...,
    footer       : str             | None = ...,
    override     : bool                   = ...,
    ephemeral    : bool                   = ...,
    delete_after : float           | None = ...,
    message      : discord.Message | None = ...,
    edit         : bool                   = ...,
) -> discord.Message | None: ...

@overload
async def send_custom_message(
    target            : CtxOrInteraction,
    *,
    msg_type          : Literal[
        "warning",
        "error"],
    title             : str,
    subtitle          : str             | None = ...,
    footer            : str             | None = ...,
    contact_bot_owner : bool                   = ...,
    override          : bool                   = ...,
    ephemeral         : bool                   = ...,
    delete_after      : float           | None = ...,
    message           : discord.Message | None = ...,
    edit              : bool                   = ...,
) -> discord.Message | None: ...

async def send_custom_message(
    target            : CtxOrInteraction,
    *,
    msg_type          : MessageType,
    title             : str,
    subtitle          : str             | None = None,
    footer            : str             | None = None,
    contact_bot_owner : bool                   = False,
    override          : bool                   = False,
    ephemeral         : bool                   = True,
    delete_after      : float           | None = None,
    message           : discord.Message | None = None,
    edit              : bool                   = False,
) -> discord.Message | None:
    allow_contact = contact_bot_owner if msg_type in (
        "warning",
        "error",
    ) else False

    lines : list[str] = [
        _build_header(
            msg_type,
            title,
            override = override,
        ),
    ]
    if subtitle:
        lines.append(subtitle)
    footer_text = _build_footer_text(
        footer,
        contact_bot_owner = allow_contact,
    )
    if footer_text:
        lines.append(f"-# {footer_text}")

    content = "\n".join(lines)

    class _SingleView(LayoutView):
        text : TextDisplay[_SingleView] = TextDisplay(content = content)

    return await _send(
        target,
        _SingleView(),
        ephemeral    = ephemeral,
        delete_after = delete_after,
        message      = message,
        edit         = edit,
    )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# multi_custom_message Response
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class _MultiCustomMessage:
    def __init__(
        self,
        target : CtxOrInteraction,
    ) -> None:
        self._target       : CtxOrInteraction       = target
        self._fields       : list[_Field]           = []
        self._ephemeral    : bool                   = True
        self._delete_after : float | None           = None
        self._message      : discord.Message | None = None
        self._edit         : bool                   = False

    def set_ephemeral(
        self,
        *,
        value : bool = True,
    ) -> _MultiCustomMessage:
        self._ephemeral = value
        return self

    def set_delete_after(
        self,
        *,
        value : float | None,
    ) -> _MultiCustomMessage:
        self._delete_after = value
        return self

    def set_message(
        self,
        *,
        message : discord.Message,
    ) -> _MultiCustomMessage:
        self._message = message
        return self

    def set_edit(
        self,
        *,
        value : bool = True,
    ) -> _MultiCustomMessage:
        self._edit = value
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
        override  : bool = False,
    ) -> _MultiCustomMessage:
        self._fields.append(
            _Field(
                title     = title,
                msg_type  = msg_type,
                subfields = subfields,
                override  = override,
            ),
        )
        return self

    def _render_field_blocks(
        self,
        field : _Field,
    ) -> list[str]:
        def _build_block(
            index    : int,
            subfield : _Subfield,
        ) -> str:
            lines : list[str] = []

            if index == 0:
                lines.append(
                    _build_header(
                        cast(
                            "MessageType",
                            field.msg_type,
                        ),
                        field.title,
                        override = field.override,
                    ),
                )

            if subfield.subtitle:
                lines.append(subfield.subtitle)

            footer_text = _build_footer_text(
                subfield.footer,
                contact_bot_owner = subfield.contact_bot_owner,
            )
            if footer_text:
                lines.append(f"-# {footer_text}")

            return "\n".join(lines)

        return [
            _build_block(
                i,
                sf,
            ) for i, sf in enumerate(field.subfields)
        ]

    def has_errors(self) -> bool:
        return len(self._fields) > 0

    async def send(self) -> discord.Message | None:
        if not self.has_errors():
            return None

        all_components : list[TextDisplay[LayoutView] | Separator[LayoutView]] = []

        for field_index, field in enumerate(self._fields):
            if field_index > 0:
                all_components.append(
                    Separator[LayoutView](
                        spacing = SeparatorSpacing.small,
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

        return await _send(
            self._target,
            view,
            ephemeral    = self._ephemeral,
            delete_after = self._delete_after,
            message      = self._message,
            edit         = self._edit,
        )

def multi_custom_message(target : CtxOrInteraction) -> _MultiCustomMessage:
    return _MultiCustomMessage(target)
