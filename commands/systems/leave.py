import discord
from discord.ext import commands
from discord import app_commands

from typing import (
    Any,
    cast
)
import json
import os
import contextlib
import enum

from core.help import (
    RoleConfig,
    help_description,
    ArgumentInfo
)
from core.utils import (
    send_minor_error,
    send_major_error
)
from core.permissions import (
    is_director,
    is_staff,
)

from constants import (
    BOT_OWNER_ID,
    COLOR_RED,
    DENIED_EMOJI_ID,
    DIRECTORS_ROLE_ID,
    STAFF_ROLE_ID,
    PERSONAL_LEAVE_ROLE_ID,
    SENIOR_MODERATORS_ROLE_ID,
    JUNIOR_MODERATORS_ROLE_ID,
    MODERATORS_ROLE_ID,
    STAFF_COMMITTEE_ROLE_ID,
    MODERATORS_AND_ADMINISTRATORS_ROLE_ID,
    SENIOR_ADMINISTRATORS_ROLE_ID,
    JUNIOR_ADMINISTRATORS_ROLE_ID,
    ADMINISTRATORS_ROLE_ID,
    SUPPORTING_DIRECTORS_ROLE_ID,
)

DATA_FILE = "leave_data.json"

ALL_STAFF_ROLE_IDS: list[int] = [
    STAFF_ROLE_ID,
    SENIOR_MODERATORS_ROLE_ID,
    JUNIOR_MODERATORS_ROLE_ID,
    MODERATORS_ROLE_ID,
    STAFF_COMMITTEE_ROLE_ID,
    MODERATORS_AND_ADMINISTRATORS_ROLE_ID,
    SENIOR_ADMINISTRATORS_ROLE_ID,
    JUNIOR_ADMINISTRATORS_ROLE_ID,
    ADMINISTRATORS_ROLE_ID,
    DIRECTORS_ROLE_ID,
    SUPPORTING_DIRECTORS_ROLE_ID,
]


class LeaveType(enum.Enum):
    none       = "none"
    soft_clean = "soft_clean"
    hard_clean = "hard_clean"


def load_data() -> dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE) as f:
        return json.load(f)


def save_data(data: dict[str, Any]) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def extract_name(nickname: str) -> str:
    if nickname and "|" in nickname:
        return nickname.split("|")[-1].strip()
    return nickname


def can_manage_leave(invocator: discord.Member, target: discord.Member) -> bool:
    if not is_staff(invocator):
        return False
    modifying_other = target.id != invocator.id
    if modifying_other:
        return is_director(invocator)
    return True


def normalize_entry(raw: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, str):
        return {
            "original_nick": raw,
            "leave_type": LeaveType.none.value,
            "removed_roles": [],
        }
    return raw

class HardCleanConfirmView(discord.ui.LayoutView):
    def __init__(
        self,
        invocator_id: int,
        target: discord.Member,
        roles_to_remove: list[discord.Role],
    ) -> None:
        super().__init__(timeout=60)
        self.invocator_id    = invocator_id
        self.target          = target
        self.roles_to_remove = roles_to_remove
        self.message: discord.WebhookMessage | None = None

    container: discord.ui.Container[discord.ui.LayoutView] = discord.ui.Container(accent_colour=COLOR_RED)

    def _disable_buttons(self) -> None:
        for item in self.container.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    @container.button(label="Accept", style=discord.ButtonStyle.danger)  # type: ignore[attr-defined]
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.LayoutView]) -> None:
        if interaction.user.id != self.invocator_id:
            await send_minor_error(interaction, "This confirmation is not for you.", subtitle="Invalid operation.")
            return

        self.stop()

        try:
            await self.target.remove_roles(*self.roles_to_remove, reason=f"Hard Clean leave by {interaction.user.display_name}")
        except discord.Forbidden:
            await send_major_error(
                interaction,
                title="Error!",
                texts=f"I lack the permissions to remove roles from {self.target.mention}.",
                subtitle="Invalid configuration. Contact the owner."
            )
            return
        except discord.HTTPException:
            await send_major_error(
                interaction,
                title="Error!",
                texts="A Discord API error occurred. Please try again later.",
                subtitle=f"Invalid operation. Contact <@{BOT_OWNER_ID}>."
            )
            return

        self._disable_buttons()
        await interaction.response.edit_message(
            content=f"{self.target.mention} has been hard cleaned —— {len(self.roles_to_remove)} staff role(s) removed.",
            view=self
        )

    @container.button(label="Cancel", style=discord.ButtonStyle.primary)  # type: ignore[attr-defined]
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.LayoutView]) -> None:
        if interaction.user.id != self.invocator_id:
            await send_minor_error(interaction, "This confirmation is not for you.", subtitle="Invalid operation.")
            return

        self._disable_buttons()
        self.stop()

        await interaction.response.edit_message(
            content="Hard clean cancelled —— no changes were made.",
            view=self
        )

    async def on_timeout(self) -> None:
        self._disable_buttons()
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(content="Hard clean timed out —— no changes were made.", view=self)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Leave Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class LeaveCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot  = bot
        self.data = load_data()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /leave Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    leave_group = app_commands.Group(
        name="leave",
        description="Staff only —— Leave commands."
    )

    @leave_group.command(name="add", description="Add personal leave to yourself or another user.")
    @help_description(
        desc        = (
            f"The leave add command supports three leave types.\n\n"
            f"**None:** Adds the <@&{PERSONAL_LEAVE_ROLE_ID}> role and updates the nickname. No roles removed. Reversible with `/leave remove`.\n\n"
            f"**Soft Clean:** Removes all staff roles, adds <@&{PERSONAL_LEAVE_ROLE_ID}>, and updates the nickname. Reversible with `/leave remove`.\n\n"
            f"**Hard Clean:** Removes all staff roles only. No nickname change or leave role added. **Irreversible** via `/leave remove`. Cannot target self or Directors. Requires confirmation."
        ),
        prefix      = False,
        slash       = True,
        run_roles   = [RoleConfig(role_id=DIRECTORS_ROLE_ID)],
        has_inverse = "/leave remove",
        arguments   = {
            "leave_type": ArgumentInfo(
                roles       = [DIRECTORS_ROLE_ID],
                required    = True,
                description = "The type of leave to apply."
            ),
            "target": ArgumentInfo(
                roles       = [DIRECTORS_ROLE_ID],
                required    = False,
                description = "The user to add personal leave to."
            ),
        },
    )
    @app_commands.describe(
        leave_type = "The type of leave to apply.",
        target     = "The user to add personal leave to. Defaults to yourself."
    )
    async def leave_add(
        self,
        interaction: discord.Interaction,
        leave_type: LeaveType,
        target: discord.Member | None = None,
    ) -> None:
        if not interaction.guild:
            await send_minor_error(
                interaction,
                "This command can only be used in a server.",
                subtitle="Bad command environment."
            )
            return

        await interaction.response.defer(ephemeral=True)

        invocator = interaction.user
        if not isinstance(invocator, discord.Member):
            return

        target_member = target or invocator

        if target_member.bot:
            await send_minor_error(interaction, "Bots cannot go on personal leave.")
            return

        if leave_type == LeaveType.hard_clean:
            if target_member.id == invocator.id:
                await send_minor_error(interaction, "You cannot hard clean yourself.")
                return
            if is_director(target_member):
                await send_minor_error(interaction, "You cannot hard clean a Director.")
                return

        if not is_staff(invocator):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to run this command.",
                subtitle="Invalid permissions."
            )
            return

        if leave_type != LeaveType.hard_clean and not is_staff(target_member):
            await send_minor_error(interaction, "Target must exist within the Goobers Staff Team.")
            return

        if not can_manage_leave(invocator, target_member):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to add personal leave to other Staff Members.",
                subtitle="Invalid permissions."
            )
            return

        if leave_type != LeaveType.hard_clean and str(target_member.id) in self.data:
            await send_minor_error(interaction, "User is already on personal leave.")
            return

        roles_to_remove: list[discord.Role] = []
        if leave_type in (LeaveType.soft_clean, LeaveType.hard_clean):
            roles_to_remove = [
                r for r in target_member.roles
                if r.id in ALL_STAFF_ROLE_IDS
            ]

        if leave_type == LeaveType.hard_clean:
            if not roles_to_remove:
                await send_minor_error(interaction, "Target has no staff roles to remove.")
                return

            view      = HardCleanConfirmView(
                invocator_id    = invocator.id,
                target          = target_member,
                roles_to_remove = roles_to_remove,
            )
            role_list = ", ".join(r.mention for r in roles_to_remove)
            msg       = await interaction.followup.send(
                content=(
                    f"### {DENIED_EMOJI_ID} Warning,\n"
                    f"This will remove all **{len(roles_to_remove)}** staff role(s) from {target_member.mention} and **cannot be undone** via `/leave remove`.\n\n"
                    f"**Roles to remove:** {role_list}\n\n"
                ),
                view=cast("discord.ui.View", view),
                ephemeral=True,
            )
            view.message = msg
            return

        personal_leave_role = interaction.guild.get_role(PERSONAL_LEAVE_ROLE_ID)
        if personal_leave_role is None:
            await send_major_error(
                interaction,
                title="Error!",
                texts="I could not fetch the Personal Leave role.",
                subtitle=f"Invalid Configuration. Contact an administrator and <@{BOT_OWNER_ID}>."
            )
            return

        if personal_leave_role in target_member.roles:
            await send_minor_error(interaction, "User already has the Personal Leave role.")
            return

        original_full_nick = target_member.nick or target_member.name
        actual_name        = extract_name(original_full_nick)
        new_nick           = f"P. Leave | {actual_name}"

        if len(new_nick) > 32:
            await send_minor_error(
                interaction,
                title="Error!",
                texts="The resulting nickname exceeds Discord's 32 character limit.",
                subtitle="Invalid operation."
            )
            return

        roles_removed = False
        role_added    = False
        nick_changed  = False

        try:
            if roles_to_remove:
                await target_member.remove_roles(*roles_to_remove)
                roles_removed = True

            await target_member.add_roles(personal_leave_role)
            role_added = True

            await target_member.edit(nick=new_nick)
            nick_changed = True

            self.data[str(target_member.id)] = {
                "original_nick": original_full_nick,
                "leave_type":    leave_type.value,
                "removed_roles": [r.id for r in roles_to_remove],
            }
            save_data(self.data)

            if target_member.id == interaction.user.id:
                await interaction.followup.send("You have been placed on personal leave.", ephemeral=True)
            else:
                await interaction.followup.send(
                    f"{target_member.mention} has been placed on personal leave.",
                    ephemeral=True
                )

        except discord.Forbidden:
            if roles_removed and not role_added:
                with contextlib.suppress(discord.HTTPException):
                    await target_member.add_roles(*roles_to_remove)
            elif role_added and not nick_changed:
                with contextlib.suppress(discord.HTTPException):
                    await target_member.remove_roles(personal_leave_role)
                if roles_removed:
                    with contextlib.suppress(discord.HTTPException):
                        await target_member.add_roles(*roles_to_remove)

            if not role_added and not roles_removed:
                await send_major_error(
                    interaction,
                    title="Error!",
                    texts="I lack the necessary permissions to modify this user's roles.",
                    subtitle="Invalid configuration. Contact the owner."
                )
            elif not role_added:
                await send_major_error(
                    interaction,
                    title="Error!",
                    texts="I lack the necessary permissions to assign the Personal Leave role.",
                    subtitle="Invalid configuration. Contact the owner."
                )
            elif not nick_changed:
                if target_member.id == interaction.guild.owner_id:
                    await send_minor_error(
                        interaction,
                        title="Error!",
                        texts="The roles were updated, but I cannot change the server owner's nickname. Please change it manually.",
                    )
                else:
                    await send_major_error(
                        interaction,
                        title="Error!",
                        texts="I lack the necessary permissions to change this user's nickname.",
                        subtitle="Invalid configuration. Contact the owner."
                    )
            return

        except discord.HTTPException:
            if roles_removed and not role_added:
                with contextlib.suppress(discord.HTTPException):
                    await target_member.add_roles(*roles_to_remove)
            elif role_added and not nick_changed:
                with contextlib.suppress(discord.HTTPException):
                    await target_member.remove_roles(personal_leave_role)
                if roles_removed:
                    with contextlib.suppress(discord.HTTPException):
                        await target_member.add_roles(*roles_to_remove)

            await send_major_error(
                interaction,
                title="Error!",
                texts="A Discord API error occurred. Please try again later.",
                subtitle=f"Invalid operation. Contact <@{BOT_OWNER_ID}> if this persists."
            )
            return

    @leave_group.command(name="remove", description="Remove personal leave from yourself or another user.")
    @app_commands.describe(target="The user to remove personal leave from.")
    @help_description(
        desc        = (
            f"The leave remove command removes the <@&{PERSONAL_LEAVE_ROLE_ID}> role from a staff member and restores their nickname. "
            f"For **Soft Clean** leaves, their original staff roles are also restored. "
            f"This command cannot undo a **Hard Clean**."
        ),
        prefix      = False,
        slash       = True,
        run_roles   = [RoleConfig(role_id=STAFF_ROLE_ID)],
        has_inverse = "/leave add",
        arguments   = {
            "target": ArgumentInfo(
                roles       = [DIRECTORS_ROLE_ID],
                required    = False,
                description = "The user to remove leave from."
            ),
        },
    )
    async def leave_remove(
        self,
        interaction: discord.Interaction,
        target:      discord.Member | None = None
    ) -> None:
        if not interaction.guild:
            await send_minor_error(
                interaction,
                "This command can only be used in a server.",
                subtitle="Bad command environment."
            )
            return

        await interaction.response.defer(ephemeral=True)

        invocator = interaction.user
        if not isinstance(invocator, discord.Member):
            return

        target_member = target or invocator

        if target_member.bot:
            await send_minor_error(interaction, "Bots cannot go on personal leave.")
            return

        if not is_staff(invocator):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to run this command.",
                subtitle="Invalid permissions."
            )
            return

        if not is_staff(target_member):
            await send_minor_error(interaction, "Target must exist within the Goobers Staff Team.")
            return

        if not can_manage_leave(invocator, target_member):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to remove personal leave from other Staff Members.",
                subtitle="Invalid permissions."
            )
            return

        raw_entry = self.data.get(str(target_member.id))
        if not raw_entry:
            await send_minor_error(interaction, "User is not on personal leave.")
            return

        entry            = normalize_entry(raw_entry)
        stored_name: str = entry["original_nick"]
        leave_type_str   = entry.get("leave_type", LeaveType.none.value)
        stored_role_ids: list[int] = entry.get("removed_roles", [])

        personal_leave_role = interaction.guild.get_role(PERSONAL_LEAVE_ROLE_ID)
        if personal_leave_role is None:
            await send_major_error(
                interaction,
                title="Error!",
                texts="I could not fetch the Personal Leave role.",
                subtitle=f"Invalid configuration. Contact an administrator and <@{BOT_OWNER_ID}>."
            )
            return

        if personal_leave_role not in target_member.roles:
            self.data.pop(str(target_member.id), None)
            save_data(self.data)
            await send_minor_error(interaction, "User does not have the Personal Leave role.")
            return

        roles_to_restore: list[discord.Role] = []
        if leave_type_str == LeaveType.soft_clean.value:
            for role_id in stored_role_ids:
                restored_role = interaction.guild.get_role(role_id)
                if restored_role is not None:
                    roles_to_restore.append(restored_role)

        nickname_error:      str | None = None
        roles_restore_error: str | None = None

        try:
            await target_member.remove_roles(personal_leave_role)

            current_nick  = target_member.nick or target_member.name
            expected_nick = f"P. Leave | {extract_name(stored_name)}"

            if current_nick == expected_nick:
                try:
                    await target_member.edit(nick=stored_name)
                except discord.Forbidden:
                    nickname_error = "forbidden"
                except discord.HTTPException:
                    nickname_error = "http"

            if roles_to_restore:
                try:
                    await target_member.add_roles(*roles_to_restore)
                except discord.Forbidden:
                    roles_restore_error = "forbidden"
                except discord.HTTPException:
                    roles_restore_error = "http"

            self.data.pop(str(target_member.id), None)
            save_data(self.data)

        except discord.Forbidden:
            await send_major_error(
                interaction,
                title="Error!",
                texts="I lack the necessary permissions to remove the Personal Leave role.",
                subtitle="Invalid configuration. Contact the owner."
            )
            return

        except discord.HTTPException:
            await send_major_error(
                interaction,
                title="Error!",
                texts="A Discord API error occurred while removing the role. Please try again later.",
                subtitle=f"Invalid operation. Contact <@{BOT_OWNER_ID}>."
            )
            return

        if nickname_error == "forbidden":
            if target_member.id == interaction.guild.owner_id:
                await send_minor_error(
                    interaction,
                    title="Error!",
                    texts="The role was removed, but I cannot change the server owner's nickname. Please change it back manually.",
                )
            else:
                await send_major_error(
                    interaction,
                    title="Error!",
                    texts="The role was removed, but I lack the necessary permissions to restore the nickname. Please change it back manually.",
                    subtitle="Invalid configuration. Contact the owner."
                )
        elif nickname_error == "http":
            await send_minor_error(
                interaction,
                title="Error!",
                texts="The role was removed, but a Discord API error prevented the nickname from being restored.",
                subtitle=f"Invalid operation. Contact <@{BOT_OWNER_ID}>."
            )
        elif roles_restore_error == "forbidden":
            await send_major_error(
                interaction,
                title="Error!",
                texts="Personal leave was removed and the nickname restored, but I lack the permissions to re-add the original staff roles. Please restore them manually.",
                subtitle="Invalid configuration. Contact the owner."
            )
        elif roles_restore_error == "http":
            await send_minor_error(
                interaction,
                title="Error!",
                texts="Personal leave was removed and the nickname restored, but a Discord API error prevented the original staff roles from being re-added.",
                subtitle=f"Invalid operation. Contact <@{BOT_OWNER_ID}>."
            )
        else:
            if target_member.id == interaction.user.id:
                await interaction.followup.send("You have been removed from personal leave.", ephemeral=True)
            else:
                await interaction.followup.send(
                    f"{target_member.mention} has been removed from personal leave.",
                    ephemeral=True
                )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LeaveCommands(bot))