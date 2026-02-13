import discord
from discord.ext import commands
from discord import app_commands

import json
import os

from core.utils import send_minor_error

DIRECTORS_ROLE_ID = 123456789012345678
PERSONAL_LEAVE_ROLE_ID = 123456789012345678
STAFF_ROLE_IDS = {
    111111111111111111,
    222222222222222222,
    333333333333333333
}

DATA_FILE = "leave_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def is_staff(member: discord.Member):
    return any(role.id in STAFF_ROLE_IDS for role in member.roles)

def is_director(member: discord.Member):
    return any(role.id == DIRECTORS_ROLE_ID for role in member.roles)

def extract_name(nickname: str):
    if nickname and "|" in nickname:
        return nickname.split("|")[-1].strip()
    return nickname

class UtilityCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_data()

    @app_commands.command(name="leave", description="Add or remove personal leave.")
    @app_commands.describe(choice="Add or Remove", target="target user")
    async def leave(
        self,
        interaction: discord.Interaction,
        choice: str,
        target: discord.Member | None = None
    ):
        invocator = interaction.user

        if not isinstance(invocator, discord.Member):
            return

        if choice not in ["add", "remove"]:
            return

        target_member = target or invocator

        if not is_staff(invocator) or not is_staff(target_member):
            return

        if choice == "add":
            if target and not is_director(invocator):
                return
            if not target and not is_director(invocator):
                return

            base_name = extract_name(target_member.nick or target_member.name)

            self.data[str(target_member.id)] = base_name
            save_data(self.data)

            if not interaction.guild:
                await send_minor_error(
                    interaction,
                    "This command can only be used in a server.",
                    subtitle="Bad command environment."
                )
            else:
                await target_member.add_roles(
                    interaction.guild.get_role(PERSONAL_LEAVE_ROLE_ID)
                )

            new_nick = f"P. Leave | {base_name}"

            try:
                await target_member.edit(nick=new_nick)
            except():
                alt_nick = f"PL | {base_name}"
                try:
                    await target_member.edit(nick=alt_nick)
                except():
                    await interaction.response.send_message(
                        "Unable to update nickname due to length constraints.",
                        ephemeral=True
                    )
                    return

            await interaction.response.defer(ephemeral=True)

        elif choice == "remove":
            if target and not is_director(invocator):
                return

            stored_name = self.data.get(str(target_member.id))
            if not stored_name:
                return

            if not interaction.guild:
                await send_minor_error(
                    interaction,
                    "This command can only be used in a server.",
                    subtitle="Bad command environment."
                )
            else:
                await target_member.remove_roles(
                    interaction.guild.get_role(PERSONAL_LEAVE_ROLE_ID)
                )

            try:
                await target_member.edit(nick=stored_name)
            except():
                return

            self.data.pop(str(target_member.id), None)
            save_data(self.data)

            await interaction.response.defer(ephemeral=True)


async def setup(bot):
    await bot.add_cog(UtilityCommands(bot))