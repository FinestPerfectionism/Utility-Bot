import discord
from discord.ext import (
    commands,
    tasks
)
import asyncio
from typing_extensions import override

from constants import (
    DIRECTORSHIP_CATEGORY_ID,
    CHANGE_LOG_CHANNEL_ID
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Queue
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

_SEND_INTERVAL = 1.0

class AuditQueue(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._queue: asyncio.Queue[tuple[discord.abc.Messageable, discord.Embed]] = asyncio.Queue()
        _ = self._queue_worker.start()

    @override
    async def cog_unload(self) -> None:
        self._queue_worker.cancel()

    @tasks.loop(seconds=_SEND_INTERVAL)
    async def _queue_worker(self) -> None:
        if self._queue.empty():
            return

        channel, embed = await self._queue.get()
        try:
            _ = await channel.send(embed=embed)
        except discord.RateLimited as e:
            await asyncio.sleep(e.retry_after)
            await self._queue.put((channel, embed))
        except discord.HTTPException as e:
            print(f"Failed to send log embed: {e}")
        finally:
            self._queue.task_done()

    @_queue_worker.before_loop
    async def _before_queue_worker(self) -> None:
        await self.bot.wait_until_ready()

    async def enqueue(self, channel: discord.abc.Messageable, embed: discord.Embed) -> None:
        await self._queue.put((channel, embed))


# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Base Cog
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class AuditCog(commands.Cog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        self.bot = bot
        self.log_channel_id = CHANGE_LOG_CHANNEL_ID
        self._queue = queue

    async def _enqueue(self, channel: discord.abc.Messageable, embed: discord.Embed) -> None:
        await self._queue.enqueue(channel, embed)

    async def get_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        channel = guild.get_channel(self.log_channel_id)
        if not isinstance(channel, discord.TextChannel):
            print(f"Warning: Logging channel {self.log_channel_id} not found in {guild.name}")
            return None
        return channel

    def is_directorship_channel(self, channel: discord.abc.GuildChannel) -> bool:
        return (
            (hasattr(channel, 'category_id') and channel.category_id == DIRECTORSHIP_CATEGORY_ID) or
            (hasattr(channel, 'category') and channel.category is not None and channel.category.id == DIRECTORSHIP_CATEGORY_ID)
        )

    async def get_executor(
        self,
        guild: discord.Guild,
        action_type: discord.AuditLogAction,
        target_id: int | None = None
    ) -> discord.Member | None:
        try:
            await asyncio.sleep(0.5)
            async for entry in guild.audit_logs(limit=10, action=action_type):
                if (target_id is None or (entry.target is not None and entry.target.id == target_id)) and isinstance(entry.user, discord.Member):
                    return entry.user
        except discord.HTTPException as e:
            print(f"Error fetching audit log: {e}")
        return None

    from collections.abc import Iterable
    def format_permissions(self, permissions: discord.Permissions | Iterable[tuple[str, bool | None]]) -> str:
        if not permissions:
            return "None"

        perms: list[str] = []
        for perm, value in permissions:
            if value is not None:
                status = "Allow" if value else "Deny"
                perm_name = perm.replace('_', ' ').title()
                perms.append(f"{perm_name}: {status}")

        return "\n".join(perms) if perms else "None"

    def get_overwrite_changes(
        self, 
        before_overwrites: dict[discord.Role | discord.Member | discord.Object, discord.PermissionOverwrite], 
        after_overwrites: dict[discord.Role | discord.Member | discord.Object, discord.PermissionOverwrite]
    ) -> list[str]:
        changes: list[str] = []
        all_targets = set(before_overwrites.keys()) | set(after_overwrites.keys())

        for target in all_targets:
            before_ow = before_overwrites.get(target)
            after_ow = after_overwrites.get(target)

            target_type = "Role" if isinstance(target, discord.Role) else "Member"
            target_name = getattr(target, 'name', str(target))
            target_id = target.id if hasattr(target, 'id') else "Unknown"

            if before_ow is None and after_ow is not None:
                perms: list[str] = []
                for perm, value in after_ow:
                    if value is not None:
                        status = "Allow" if value else "Deny"
                        perms.append(f"{perm.replace('_', ' ').title()}: {status}")
                if perms:
                    changes.append(
                        f"**Added {target_type}** `{target_name}`\n`{target_id}`\n" + "\n".join(perms)
                    )

            elif after_ow is None:
                changes.append(f"**Removed {target_type}** `{target_name}`\n`{target_id}`")

            else:
                before_perms: dict[str, bool | None] = dict(before_ow) if before_ow is not None else {}
                after_perms: dict[str, bool | None] = dict(after_ow)

                modified_perms: list[str] = []
                for perm in set(before_perms.keys()) | set(after_perms.keys()):
                    before_val = before_perms.get(perm)
                    after_val = after_perms.get(perm)

                    if before_val != after_val:
                        perm_name = perm.replace('_', ' ').title()
                        before_status = "Allow" if before_val else ("Deny" if before_val is False else "Neutral")
                        after_status = "Allow" if after_val else ("Deny" if after_val is False else "Neutral")
                        modified_perms.append(f"{perm_name}: {before_status} → {after_status}")

                if modified_perms:
                    changes.append(
                        f"**Modified {target_type}** `{target_name}`\n`{target_id}`\n" + "\n".join(modified_perms)
                    )

        return changes