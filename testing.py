import re
from collections.abc import Sequence
from typing import TypeAlias

from discord import (
    AllowedMentions,
    ButtonStyle,
    Member,
    Emoji,
    PartialEmoji,
)
from discord.ui import (
    ActionRow,
    Button,
    Checkbox,
    FileUpload,
    Label,
    Modal,
    Separator,
    TextDisplay,
    TextInput,
    UserSelect,
    View,
    select,
)
from discord.ui import (
    Container,
    LayoutView,
    Section,
)
import discord
from typing_extensions import override

from core.responses import send_custom_message

from constants import ACCEPTED_EMOJI

StateEntry : TypeAlias = dict[str, str | bool | None]
StateMap   : TypeAlias = dict[int, StateEntry]

def build_member_label(member : Member, state : StateEntry | None) -> str:
    label = member.mention
    if not state:
        return label
    label += f"\n**Reason:** \"{state['r']}\""
    if state.get("t"):
        label += f"\n**Timer:** `{state['t']}`"
    label += f"\n**Appealable:** `{state.get('a', False)}`"
    label += f"\n**DM:** `{state.get('d', False)}`"
    if state.get("f"):
        label += f"\n**File:** `{state['f']}`"
    return label

def resolve_state(
    member       : Member,
    state_map    : StateMap,
    global_state : StateEntry | None,
) -> StateEntry | None:
    return state_map.get(member.id) or global_state

class ActionButton(Button[LayoutView]):
    def __init__(
        self,
        target    : Member | None,
        editor    : "EditorView",
        *,
        style     : ButtonStyle                          = discord.ButtonStyle.grey,
        label     : str    | None                        = None,
        disabled  : bool                                 = False,
        custom_id : str    | None                        = None,
        url       : str    | None                        = None,
        emoji     : str    | Emoji | PartialEmoji | None = None,
        row       : int    | None                        = None,
        sku_id    : int    | None                        = None,
    ) -> None:
        super().__init__(
            style     = style,
            label     = label,
            disabled  = disabled,
            custom_id = custom_id,
            url       = url,
            emoji     = emoji,
            row       = row,
            sku_id    = sku_id,
        )
        self.target : Member | None = target
        self.editor : "EditorView"  = editor

    @override
    async def callback(self, interaction : discord.Interaction) -> None:
        try:
            _ = await interaction.response.send_modal(ReasonModal(self.target, self.editor))
        except Exception as e:
            _ = await send_custom_message(interaction, msg_type = "error", title = "do something", subtitle = f"{e}")

class ReasonModal(Modal):
    def __init__(self, target : Member | None, editor : "EditorView") -> None:
        title = f"Reason: {target.name}" if target else "Global Action"
        super().__init__(title = title)
        self.target : Member | None = target
        self.editor : "EditorView"  = editor

        existing : StateEntry = editor.state_map.get(
            target.id if target else 0,
            editor.state_map.get(0, {}),
        )

        self.reason_input : TextInput[Modal] = TextInput[Modal](
            label       = "Reason",
            placeholder = "ex: \"nsfw spam\"",
            default     = str(existing.get("r", "")),
            required    = True,
        )
        self.timer_input  : TextInput[Modal] = TextInput[Modal](
            label       = "Timer",
            placeholder = "ex: \"30m, 2d\"",
            default     = str(existing.get("t", "")),
            required    = False,
        )
        self.appealable_box : Checkbox[Modal]   = Checkbox(default = bool(existing.get("a", False)))
        self.dm_box         : Checkbox[Modal]   = Checkbox(default = bool(existing.get("d", False)))
        self.file_upload    : FileUpload[Modal] = FileUpload(required = False, max_values = 1)

        for item in [
            self.reason_input,
            self.timer_input,
            Label(text = "Appealable", component = self.appealable_box),
            Label(text = "DM User",    component = self.dm_box),
            Label(text = "Upload",     component = self.file_upload),
        ]:
            _ = self.add_item(item)

    @override
    async def on_submit(self, interaction : discord.Interaction) -> None:
        timer_value = self.timer_input.value.strip().lower()
        if timer_value and not re.match(r"^(\d+[hmds])+$", timer_value):
            _ = await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "compile window",
                subtitle = f"The time signature `{self.timer_input.value}` is not valid. Use formats like 10m, 2h, 1d.",
            )
            return

        uid = self.target.id if self.target else 0
        if uid == 0:
            self.editor.state_map.clear()

        filename : str | None = (
            self.file_upload.values[0].filename
            if self.file_upload.values
            else None
        )
        self.editor.state_map[uid] = {
            "r" : self.reason_input.value,
            "t" : self.timer_input.value,
            "a" : self.appealable_box.value,
            "d" : self.dm_box.value,
            "f" : filename,
        }
        await self.editor.refresh(interaction)

class EditorView(LayoutView):
    def __init__(self, members : Sequence[Member] | None = None) -> None:
        super().__init__(timeout = None)
        self.members   : list[Member] = list(members) if members else []
        self.state_map : StateMap     = {}
        self._rebuild()

    def _rebuild(self) -> None:
        _ = self.clear_items()
        container : Container[LayoutView] = Container()
        global_state                      = self.state_map.get(0)

        for member in self.members:
            resolved = resolve_state(member, self.state_map, global_state)
            label    = build_member_label(member, resolved)

            if resolved:
                style = discord.ButtonStyle.green if (member.id in self.state_map or 0 in self.state_map) else discord.ButtonStyle.blurple
            else:
                style = discord.ButtonStyle.grey

            _ = container.add_item(
                Section(
                    label,
                    accessory = ActionButton(member, self, style = style, label = "Action"),
                )
            )

        _ = container.add_item(Separator(spacing = discord.SeparatorSpacing.large))

        async def handle_execute(interaction : discord.Interaction) -> None:
            errors : list[str] = []
            global_entry       = self.state_map.get(0)

            for member in self.members:
                entry               = resolve_state(member, self.state_map, global_entry)
                missing : list[str] = []
                if not entry or not entry.get("r"):
                    missing.append("reason")
                if not entry or not entry.get("t"):
                    missing.append("timer")
                if missing:
                    missing_string = " and ".join(missing) if len(missing) == 2 else missing[0]
                    errors.append(f"- {member.mention}: Missing {missing_string}")

            if errors:
                try:
                    _ = await send_custom_message(
                        interaction,
                        msg_type  = "warning",
                        title     = "moderate members",
                        subtitle  = (
                            "Fix the following assignments before executing:\n"
                            + "\n".join(errors)
                        ),
                    )
                    return
                except Exception as e:
                    _ = await send_custom_message(interaction, msg_type = "error", title = "do something", subtitle = f"{e}")

            try:
                summary_lines = [f"{ACCEPTED_EMOJI} **Successfully mass moderated all members.**\n"]

                for member in self.members:
                    entry = resolve_state(member, self.state_map, global_entry)
                    if entry:
                        reason     = entry.get("r", "N/A")
                        timer      = entry.get("t", "N/A")
                        appealable = "Yes" if entry.get("a") else "No"
                        dm_user    = "Yes" if entry.get("d") else "No"
                        file       = entry.get("f") or "None"

                        summary_lines.append(
                            (
                                f"{ACCEPTED_EMOJI} **Success for {member.mention}.**\n"
                                f"- **Reason:** {reason}\n"
                                f"- **Timer:** {timer}\n"
                                f"- **Appealable:** {appealable} | **DM Sent:** {dm_user}\n"
                                f"- ***Attachment:** {file}"
                            )
                        )
                        
                    else:
                        summary_lines.append(
                            (
                               f"{ACCEPTED_EMOJI} **Success for {member.mention}.**\n"
                                "-# Missing configuration data for this member."
                            )
                        )

                class FinalizedView(LayoutView):
                    text : TextDisplay[LayoutView] = TextDisplay(content = "\n".join(summary_lines))

                _ = await interaction.response.edit_message(view = FinalizedView())
            except Exception as e:
                _ = await send_custom_message(interaction, msg_type = "error", title = "do something", subtitle = f"{e}")

        execute_button : Button[LayoutView] =  Button(style = discord.ButtonStyle.red, label="Execute")
        execute_button.callback             = handle_execute

        _ = container.add_item(
            ActionRow(
                ActionButton(None, self, style = discord.ButtonStyle.blurple, label=  "Global"),
                execute_button,
            )
        )
        _ = self.add_item(container)

    async def refresh(self, interaction : discord.Interaction) -> None:
        self._rebuild()
        try:
            _ = await interaction.response.edit_message(
                view             = self,
                allowed_mentions = AllowedMentions.none(),
            )
        except Exception as e:
            _ = await send_custom_message(interaction, msg_type = "error", title = "do something", subtitle = f"{e}")

class MemberSelectView(View):
    def __init__(self) -> None:
        super().__init__(timeout = None)

    @select(cls = UserSelect, placeholder = "Choose members...", max_values = 6)
    async def member_select(
        self,
        interaction : discord.Interaction,
        select      : UserSelect[LayoutView],
    ) -> None:
        ineligible = [
            user.mention 
            for user in select.values
            if isinstance(user, Member) 
            and isinstance(interaction.user, Member) 
            and user.top_role >= interaction.user.top_role
        ]
        if ineligible:
            _ = await send_custom_message(
                interaction,
                msg_type  = "warning",
                title     = "compile window",
                subtitle  = f"The following users have an equal or higher role than you and cannot be chosen: {', '.join(ineligible)}"
            )
            return

        members = [user for user in select.values if isinstance(user, Member)]
        try:
            _ = await interaction.response.edit_message(view = EditorView(members = members))
        except Exception as e:
            _ = await send_custom_message(interaction, msg_type = "error", title = "do something", subtitle = f"{e}")