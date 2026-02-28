import discord
from discord.ext import commands
from discord import app_commands

import json
import os
from datetime import datetime
from typing import (
    Optional,
    Dict,
    List,
    cast
)

from commands.moderation.cases import CaseType

from core.utils import (
    send_major_error
)

from constants import (
    COLOR_GREEN,
    COLOR_ORANGE,
    COLOR_BLURPLE,

    DIRECTORS_ROLE_ID,
    SENIOR_MODERATORS_ROLE_ID,
    MODERATORS_ROLE_ID,
    ADMINISTRATORS_ROLE_ID,
)

from bot import UtilityBot

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Notes Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class NotesCommands(commands.Cog):
    def __init__(self, bot: "UtilityBot"):
        self.bot = bot
        self.data_file = "notes_data.json"
        self.data = self.load_data()

        self.DIRECTORS_ROLE_ID = DIRECTORS_ROLE_ID
        self.SENIOR_MODERATORS_ROLE_ID = SENIOR_MODERATORS_ROLE_ID
        self.MODERATORS_ROLE_ID = MODERATORS_ROLE_ID
        self.ADMINISTRATORS_ROLE_ID = ADMINISTRATORS_ROLE_ID

    @property
    def cases_manager(self):
        return cast(UtilityBot, self.bot).cases_manager

    def load_data(self) -> Dict:
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self.get_default_data()
        return self.get_default_data()

    def get_default_data(self) -> Dict:
        return {
            "notes": {},
            "next_note_id": 1
        }

    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=4)

    def get_next_note_id(self) -> int:
        note_id = self.data["next_note_id"]
        self.data["next_note_id"] += 1
        self.save_data()
        return note_id

    def has_role(self, member: discord.Member, role_id: int) -> bool:
        return any(role.id == role_id for role in member.roles)

    def is_director(self, member: discord.Member) -> bool:
        return self.has_role(member, self.DIRECTORS_ROLE_ID)

    def is_senior_moderator(self, member: discord.Member) -> bool:
        return self.has_role(member, self.SENIOR_MODERATORS_ROLE_ID)

    def is_administrator(self, member: discord.Member) -> bool:
        return self.has_role(member, self.ADMINISTRATORS_ROLE_ID)

    def is_moderator(self, member: discord.Member) -> bool:
        return self.has_role(member, self.MODERATORS_ROLE_ID)

    def can_manage_notes(self, member: discord.Member) -> bool:
        return (
            self.is_director(member) or
            self.is_senior_moderator(member) or
            self.is_administrator(member) or
            self.is_moderator(member)
        )

    def can_delete_notes(self, member: discord.Member) -> bool:
        return self.is_director(member) or self.is_senior_moderator(member)

    def get_note_by_id(self, note_id: int) -> Optional[Dict]:
        for user_notes in self.data["notes"].values():
            for note in user_notes:
                if note["note_id"] == note_id:
                    return note
        return None

    def get_notes_for_user(self, user_id: int) -> List[Dict]:
        return self.data["notes"].get(str(user_id), [])

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .note Command Group
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.group(name="note", aliases=["notes", "n"], invoke_without_command=True)
    async def note_group(self, ctx: commands.Context, user: Optional[discord.User] = None):
        actor = ctx.author
        if not isinstance(actor, discord.Member):
            return

        if not self.can_manage_notes(actor):
            return

        if user is None:
            return

        await self._send_notes_embed(ctx, user)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .note add Subcommand
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @note_group.command(name="add", aliases=["a", "create"])
    async def note_add(self, ctx: commands.Context, user: discord.User, *, content: str):
        actor = ctx.author
        if not isinstance(actor, discord.Member):
            return

        if not self.can_manage_notes(actor):
            return

        guild = ctx.guild
        if not guild:
            return

        note_id = self.get_next_note_id()
        user_key = str(user.id)

        if user_key not in self.data["notes"]:
            self.data["notes"][user_key] = []

        note = {
            "note_id": note_id,
            "content": content,
            "moderator_id": actor.id,
            "moderator_name": str(actor),
            "created_at": datetime.now().isoformat(),
            "edited_at": None
        }

        self.data["notes"][user_key].append(note)
        self.save_data()

        await self.cases_manager.log_case(
            guild=guild,
            case_type=CaseType.NOTE,
            moderator=actor,
            reason=content,
            target_user=user,
            metadata={"note_id": note_id, "action": "add"}
        )

        embed = discord.Embed(
            title="Note Added",
            color=COLOR_BLURPLE,
            timestamp=datetime.now()
        )
        embed.add_field(name="User", value=f"{user.mention} ({user.id})", inline=True)
        embed.add_field(name="Moderator", value=actor.mention, inline=True)
        embed.add_field(name="Note ID", value=f"`#{note_id}`", inline=True)
        embed.add_field(name="Content", value=content, inline=False)

        await ctx.send(embed=embed)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .note edit Subcommand
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @note_group.command(name="edit", aliases=["update"])
    async def note_edit(self, ctx: commands.Context, note_id: int, *, new_content: str):
        actor = ctx.author
        if not isinstance(actor, discord.Member):
            return

        if not self.can_manage_notes(actor):
            return

        guild = ctx.guild
        if not guild:
            return

        note = self.get_note_by_id(note_id)
        if not note:
            return

        if note["moderator_id"] != actor.id and not self.is_director(actor):
            return

        old_content = note["content"]
        note["content"] = new_content
        note["edited_at"] = datetime.now().isoformat()
        self.save_data()

        target_user: Optional[discord.User] = None
        for user_id, user_notes in self.data["notes"].items():
            if any(n["note_id"] == note_id for n in user_notes):
                try:
                    target_user = await self.bot.fetch_user(int(user_id))
                except discord.NotFound:
                    pass
                break

        await self.cases_manager.log_case(
            guild=guild,
            case_type=CaseType.NOTE,
            moderator=actor,
            reason=new_content,
            target_user=target_user,
            metadata={"note_id": note_id, "action": "edit", "old_content": old_content}
        )

        embed = discord.Embed(
            title="Note Edited",
            color=COLOR_ORANGE,
            timestamp=datetime.now()
        )
        embed.add_field(name="Note ID", value=f"`#{note_id}`", inline=True)
        embed.add_field(name="Moderator", value=actor.mention, inline=True)
        if target_user:
            embed.add_field(name="User", value=f"{target_user.mention} ({target_user.id})", inline=True)
        embed.add_field(name="Before", value=old_content, inline=False)
        embed.add_field(name="After", value=new_content, inline=False)

        await ctx.send(embed=embed)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .note delete Subcommand
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @note_group.command(name="remove", aliases=["rem"])
    async def note_delete(self, ctx: commands.Context, note_id: int):
        actor = ctx.author
        if not isinstance(actor, discord.Member):
            return

        if not self.can_delete_notes(actor):
            return

        guild = ctx.guild
        if not guild:
            return

        note = self.get_note_by_id(note_id)
        if not note:
            return

        if note["moderator_id"] != actor.id and not self.is_director(actor):
            return

        target_user: Optional[discord.User] = None
        for user_id, user_notes in self.data["notes"].items():
            if any(n["note_id"] == note_id for n in user_notes):
                try:
                    target_user = await self.bot.fetch_user(int(user_id))
                except discord.NotFound:
                    pass
                self.data["notes"][user_id] = [n for n in user_notes if n["note_id"] != note_id]
                if not self.data["notes"][user_id]:
                    del self.data["notes"][user_id]
                break

        self.save_data()

        await self.cases_manager.log_case(
            guild=guild,
            case_type=CaseType.NOTE,
            moderator=actor,
            reason=note["content"],
            target_user=target_user,
            metadata={"note_id": note_id, "action": "delete"}
        )

        embed = discord.Embed(
            title="Note Deleted",
            color=COLOR_GREEN,
            timestamp=datetime.now()
        )
        embed.add_field(name="Note ID", value=f"`#{note_id}`", inline=True)
        embed.add_field(name="Moderator", value=actor.mention, inline=True)
        if target_user:
            embed.add_field(name="User", value=f"{target_user.mention} ({target_user.id})", inline=True)
        embed.add_field(name="Deleted Content", value=note["content"], inline=False)

        await ctx.send(embed=embed)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .note view Subcommand
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @note_group.command(name="view", aliases=["v", "list", "ls"])
    async def note_view(self, ctx: commands.Context, user: discord.User):
        actor = ctx.author
        if not isinstance(actor, discord.Member):
            return

        if not self.can_manage_notes(actor):
            return

        await self._send_notes_embed(ctx, user)

    async def _send_notes_embed(self, ctx: commands.Context, user: discord.User):
        notes = self.get_notes_for_user(user.id)

        if not notes:
            embed = discord.Embed(
                description=f"No notes found for {user.mention}.",
                color=COLOR_GREEN
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title=f"Notes — {user} ({user.id})",
            color=COLOR_BLURPLE,
            timestamp=datetime.now()
        )

        for note in notes[:25]:
            created_at = datetime.fromisoformat(note["created_at"])
            timestamp_str = discord.utils.format_dt(created_at, 'R')

            header = f"#{note['note_id']} · {note['moderator_name']} · {timestamp_str}"
            if note["edited_at"]:
                edited_at = datetime.fromisoformat(note["edited_at"])
                header += f" (edited {discord.utils.format_dt(edited_at, 'R')})"

            embed.add_field(name=header, value=note["content"], inline=False)

        if len(notes) > 25:
            embed.set_footer(text=f"Showing 25 of {len(notes)} notes")

        await ctx.send(embed=embed)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /notes Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    notes_group = app_commands.Group(
        name="notes",
        description="Moderators only —— Notes management."
    )

    @notes_group.command(name="view", description="View notes for a user.")
    @app_commands.describe(user="The user whose notes to view.")
    async def notes_view_slash(self, interaction: discord.Interaction, user: discord.User):
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_manage_notes(actor):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to view notes.",
                subtitle="Invalid permissions."
            )
            return

        await interaction.response.defer(ephemeral=True)

        notes = self.get_notes_for_user(user.id)

        if not notes:
            embed = discord.Embed(
                description=f"No notes found for {user.mention}.",
                color=COLOR_GREEN
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Notes — {user} ({user.id})",
            color=COLOR_BLURPLE,
            timestamp=datetime.now()
        )

        for note in notes[:25]:
            created_at = datetime.fromisoformat(note["created_at"])
            timestamp_str = discord.utils.format_dt(created_at, 'R')

            header = f"#{note['note_id']} · {note['moderator_name']} · {timestamp_str}"
            if note["edited_at"]:
                edited_at = datetime.fromisoformat(note["edited_at"])
                header += f" (edited {discord.utils.format_dt(edited_at, 'R')})"

            embed.add_field(name=header, value=note["content"], inline=False)

        if len(notes) > 25:
            embed.set_footer(text=f"Showing 25 of {len(notes)} notes")

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(NotesCommands(cast(UtilityBot, bot)))