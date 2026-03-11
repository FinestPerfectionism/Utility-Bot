import discord
from discord.ext import commands
from discord import app_commands

from ._base import (
    LeaveType,
    leave_group,
    load_data,
    save_data,
    extract_name,
    can_manage_leave,
    normalize_entry,
    entry_has_automation,
    describe_automation,
    InterferenceConfirmView,
)
from core.help import (
    RoleConfig,
    help_description,
    ArgumentInfo
)
from core.utils import (
    send_minor_error,
    send_major_error
)
from core.permissions import is_staff
from constants import (
    BOT_OWNER_ID,
    DENIED_EMOJI_ID,
    DIRECTORS_ROLE_ID,
    STAFF_ROLE_ID,
    PERSONAL_LEAVE_ROLE_ID,
)


class LeaveRemove(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot  = bot
        self.data = load_data()

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
        target:      discord.Member | None = None,
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

        is_self_removal  = target_member.id == invocator.id
        is_self_on_leave = str(invocator.id) in self.data

        if not (is_self_removal and is_self_on_leave):
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

        entry = normalize_entry(raw_entry)

        if entry_has_automation(entry):
            automation_desc = describe_automation(entry)
            warning_text = (
                f"### {DENIED_EMOJI_ID} Automation Conflict,\n"
                f"{target_member.mention} currently has an active automation entry ({automation_desc}).\n\n"
                "Running `/leave remove` now will override and clear that automation. Proceed?"
            )
            view = InterferenceConfirmView(
                invocator_id=invocator.id,
                warning_text=warning_text,
            )
            msg          = await interaction.followup.send(view=view, ephemeral=True)
            view.message = msg
            await view.wait()

            if not view.confirmed:
                return

        stored_name:     str       = entry["original_nick"]
        leave_type_str:  str       = entry.get("leave_type", LeaveType.none.value)
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
        if leave_type_str in (LeaveType.soft_clean.value, "soft_clean"):
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
                    "The role was removed, but I cannot change the server owner's nickname. Please change it back manually.",
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
                "The role was removed, but a Discord API error prevented the nickname from being restored.",
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
                "Personal leave was removed and the nickname restored, but a Discord API error prevented the original staff roles from being re-added.",
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
    await bot.add_cog(LeaveRemove(bot))