import discord
from discord.ext import commands
from discord import app_commands
from discord import Interaction

import aiosqlite
import time
from datetime import timezone

from core.permissions import (
    mod_only,
    main_guild_only
)
from core.utils import (
    send_major_error,
    send_minor_error
)

from events.systems.automod import (
    DB_PATH,
    TIME_LIMIT,
    WARNING_TIME
)

from constants import (
    CONTESTED_EMOJI_ID,
    GUILD_ID,
    GOOBERS_ROLE_ID,
    VERIFICATION_CHANNEL_ID
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Auto-Moderation Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class AutoModeration(
    commands.GroupCog,
    name="auto-mod",
    description="Moderators only -- Auto-moderation commands."):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /timed-members Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="timed-members",
        description="List all members currently on the verification timer."
    )
    @mod_only()
    async def timedmembers(self, interaction: Interaction):
        guild = self.bot.get_guild(GUILD_ID)
        if guild is None:
            await send_minor_error(interaction, "Guild not found.")
            return

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT user_id, joined_at, warned FROM pending_verification"
            ) as cursor:
                rows = await cursor.fetchall()

        if not rows:
            await interaction.response.send_message(
                "No members are currently on the verification timer.",
                ephemeral=True
            )
            return

        now = int(time.time())
        lines = []
        for user_id, joined_at, warned in rows:
            member = guild.get_member(user_id)
            if member is None:
                continue
            elapsed_hours = (now - joined_at) // 3600
            status = "Warned" if warned else "Not Warned"
            lines.append(
                f"- {member.mention} ({member.id}) — {elapsed_hours}h elapsed — {status}"
            )

        message = "\n".join(lines)
        if len(message) > 4000:
            message = message[:3990] + "\n…"

        await interaction.response.send_message(
            f"**Members on verification timer:**\n{message}",
            ephemeral=True
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /timed-member-sync Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="timed-member-sync",
        description="Sync a member into the verification timer."
    )
    @main_guild_only()
    @mod_only()
    @app_commands.describe(member="Member to sync into verification system.")
    async def timedmembersync(
        self,
        interaction: discord.Interaction,
        member: discord.Member
    ):
        await interaction.response.defer(
            ephemeral=True
        )

        guild = interaction.guild
        if guild is None:
            await send_minor_error(interaction, "Command must be run in a guild.", subtitle="Wrong command environment.")
            return

        verified_role = guild.get_role(GOOBERS_ROLE_ID)
        if verified_role is None:
            await send_major_error(interaction, "Verified role not found.")
            return

        if verified_role in member.roles:
            await send_minor_error(interaction, "User is already verified.")
            return

        if member.joined_at is None:
            await send_major_error(interaction, "Could not determine join time.")
            return

        now = int(time.time())
        joined_at = int(member.joined_at.replace(tzinfo=timezone.utc).timestamp())
        elapsed = now - joined_at
        elapsed_hours = elapsed // 3600

        if elapsed >= TIME_LIMIT:
            await member.kick(reason="Failure to verify within 72 hours.")
            await interaction.followup.send(
                "User exceeded 72-hour verification window and was kicked.",
                ephemeral=True
            )
            return

        warned = 0
        warning_message_id = None

        if elapsed >= WARNING_TIME:
            warned = 1
            try:
                await member.send(
                    f"**{CONTESTED_EMOJI_ID} Please verify within 24 hours!**\n"
                    "You joined this server recently but have not completed verification.\n"
                    "If you do not verify within the next 24 hours, you will be removed automatically."
                )
            except discord.Forbidden:
                channel = guild.get_channel(VERIFICATION_CHANNEL_ID)
                if isinstance(channel, discord.TextChannel):
                    msg = await channel.send(
                        f"{member.mention} **{CONTESTED_EMOJI_ID} Please verify within 24 hours!**"
                    )
                    warning_message_id = msg.id

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO pending_verification
                (user_id, joined_at, warned, warning_message_id)
                VALUES (?, ?, ?, ?)
                """,
                (member.id, joined_at, warned, warning_message_id)
            )
            await db.commit()

        if warned:
            await interaction.followup.send(
                f"User warned and synced to timer.\nElapsed time: **{elapsed_hours} hours**.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"User synced to timer.\nElapsed time: **{elapsed_hours} hours**.",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    cog = AutoModeration(bot)
    await bot.add_cog(cog)

    assert cog.app_command is not None