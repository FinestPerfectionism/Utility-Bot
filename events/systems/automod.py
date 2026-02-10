import discord
from discord.ext import (
    commands,
    tasks
)

import time
import aiosqlite
from typing import Optional

from constants import (
    CONTESTED_EMOJI_ID,

    GUILD_ID,

    GOOBERS_ROLE_ID,
    MODERATORS_CHANNEL_ID,

    VERIFICATION_CHANNEL_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Auto-Moderation Handling
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

DB_PATH = "verification.db"
TIME_LIMIT = 72 * 60 * 60
WARNING_TIME = 48 * 60 * 60

class AutoModerationEvent(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        await self.migrate_database()
        await self.start_verification_system()

    async def migrate_database(self):
        async with aiosqlite.connect(DB_PATH) as db:
            try:
                await db.execute(
                    "ALTER TABLE pending_verification "
                    "ADD COLUMN warning_message_id INTEGER DEFAULT NULL;"
                )
                await db.commit()
            except aiosqlite.OperationalError:
                pass

    async def start_verification_system(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_verification (
                    user_id INTEGER PRIMARY KEY,
                    joined_at INTEGER NOT NULL,
                    warned INTEGER NOT NULL DEFAULT 0,
                    warning_message_id INTEGER DEFAULT NULL
                )
                """
            )
            await db.commit()

        if not self.verification_check.is_running():
            self.verification_check.start()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Events
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO pending_verification
                (user_id, joined_at, warned)
                VALUES (?, ?, 0)
                """,
                (member.id, int(time.time())),
            )
            await db.commit()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Verification Loop
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @tasks.loop(minutes=1)
    async def verification_check(self):
        guild: Optional[discord.Guild] = self.bot.get_guild(GUILD_ID)
        if guild is None:
            return

        verified_role: Optional[discord.Role] = guild.get_role(GOOBERS_ROLE_ID)
        if verified_role is None:
            return

        now = int(time.time())

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT user_id, joined_at, warned, warning_message_id FROM pending_verification"
            ) as cursor:
                async for user_id, joined_at, warned, warning_message_id in cursor:
                    member = guild.get_member(user_id)

                    if member is None:
                        await self.cleanup_warning(guild, warning_message_id)
                        await db.execute(
                            "DELETE FROM pending_verification WHERE user_id = ?",
                            (user_id,),
                        )
                        continue

                    if verified_role in member.roles:
                        await self.cleanup_warning(guild, warning_message_id)
                        await db.execute(
                            "DELETE FROM pending_verification WHERE user_id = ?",
                            (user_id,),
                        )
                        continue

                    elapsed = now - joined_at

                    if elapsed >= WARNING_TIME and not warned:
                        new_warning_id, sent_location = await self.send_warning(
                            guild, member
                        )

                        await db.execute(
                            """
                            UPDATE pending_verification
                            SET warned = 1, warning_message_id = ?
                            WHERE user_id = ?
                            """,
                            (new_warning_id, user_id),
                        )

                        log_channel = guild.get_channel(MODERATORS_CHANNEL_ID)
                        if isinstance(log_channel, discord.TextChannel):
                            await log_channel.send(
                                f"**Sent @{member} a warning in {sent_location}.**"
                            )

                    if elapsed >= TIME_LIMIT:
                        await self.cleanup_warning(guild, warning_message_id)
                        await member.kick(
                            reason="Failure to verify within 72 hours."
                        )
                        await db.execute(
                            "DELETE FROM pending_verification WHERE user_id = ?",
                            (user_id,),
                        )

            await db.commit()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Helpers
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def cleanup_warning(
        self,
        guild: discord.Guild,
        warning_message_id: Optional[int],
    ):
        if not warning_message_id:
            return

        channel = guild.get_channel(VERIFICATION_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            return

        try:
            msg = await channel.fetch_message(warning_message_id)
            await msg.delete()
        except (discord.NotFound, discord.Forbidden):
            pass

    async def send_warning(
        self,
        guild: discord.Guild,
        member: discord.Member,
    ) -> tuple[Optional[int], str]:
        try:
            await member.send(
                f"**{CONTESTED_EMOJI_ID} Please verify within 24 hours!**\n"
                "You joined this server recently but have not completed verification.\n"
                "If you do not verify within the next 24 hours, you will be removed automatically."
            )
            return None, "DMs"
        except discord.Forbidden:
            channel = guild.get_channel(VERIFICATION_CHANNEL_ID)
            if isinstance(channel, discord.TextChannel):
                msg = await channel.send(
                    f"{member.mention} **{CONTESTED_EMOJI_ID} Please verify within 24 hours!**\n"
                    "You joined this server recently but have not completed verification.\n"
                    "If you do not verify within the next 24 hours, you will be removed automatically."
                )
                return msg.id, channel.mention

        return None, "Unknown"

    async def cog_unload(self) -> None:
        if self.verification_check.is_running():
            self.verification_check.cancel()

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoModerationEvent(bot))