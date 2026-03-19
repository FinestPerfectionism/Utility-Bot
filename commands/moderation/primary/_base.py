import discord
from discord.ext import commands

import contextlib
import json
import os
from datetime import (
    datetime,
    timedelta
)
from typing import (
    TYPE_CHECKING,
    Any
)

from core.cases import (
    CaseType,
    CasesManager,
)

if TYPE_CHECKING:
    from bot import UtilityBot

from core.permissions import (
    has_role,
    is_director,
    is_administrator,
    is_moderator,
    is_senior_moderator,
)

from constants import (
    QUARANTINE_ROLE_ID,
    DIRECTORS_ROLE_ID,
    MODERATORS_ROLE_ID,
    ADMINISTRATORS_ROLE_ID,
    STAFF_ROLE_ID,
    JUNIOR_ADMINISTRATORS_ROLE_ID,
    SENIOR_ADMINISTRATORS_ROLE_ID,
    MODERATORS_AND_ADMINISTRATORS_ROLE_ID,
    JUNIOR_MODERATORS_ROLE_ID,
    SENIOR_MODERATORS_ROLE_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Flag Converters
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class BaseModFlags(commands.FlagConverter, prefix="/", delimiter=" "):
    r: str = commands.flag(
        name    = "r",
        aliases = ["reason"]
    )
    s: bool = commands.flag(
        name     = "s",
        aliases  = ["silent", "suppress", "shush"],
        default  = False,
        max_args = 0
    )

class BanFlags(BaseModFlags):
    d: int = commands.flag(name="d", aliases=["delete", "days"], default=7)

class UnbanFlags(BaseModFlags):
    pass

class QuarantineFlags(BaseModFlags):
    pass

class UnquarantineFlags(BaseModFlags):
    pass

class KickFlags(BaseModFlags):
    pass

class TimeoutFlags(BaseModFlags):
    d: str | None = commands.flag(name="d", aliases=["duration"], default=None)

class UntimeoutFlags(BaseModFlags):
    pass

class PurgeFlags(BaseModFlags):
    u: discord.Member | None = commands.flag(name="u", aliases=["user"], default=None)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Moderation Base
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ModerationBase(commands.Cog):
    def __init__(self, bot: "UtilityBot") -> None:
        self.bot = bot

        if not hasattr(bot, "mod_data"):
            bot.mod_data = self._load_data()

        self.QUARANTINE_ROLE_ID        = QUARANTINE_ROLE_ID
        self.DIRECTORS_ROLE_ID         = DIRECTORS_ROLE_ID
        self.SENIOR_MODERATORS_ROLE_ID = SENIOR_MODERATORS_ROLE_ID
        self.MODERATORS_ROLE_ID        = MODERATORS_ROLE_ID
        self.ADMINISTRATORS_ROLE_ID    = ADMINISTRATORS_ROLE_ID

        self.PROTECTED_ROLE_IDS = [
            STAFF_ROLE_ID,
            ADMINISTRATORS_ROLE_ID,
            JUNIOR_ADMINISTRATORS_ROLE_ID,
            SENIOR_ADMINISTRATORS_ROLE_ID,
            MODERATORS_AND_ADMINISTRATORS_ROLE_ID,
            MODERATORS_ROLE_ID,
            JUNIOR_MODERATORS_ROLE_ID,
            SENIOR_MODERATORS_ROLE_ID,
            DIRECTORS_ROLE_ID,
        ]

        self.BAN_HOURLY_LIMIT        = 2
        self.BAN_DAILY_LIMIT         = 4
        self.KICK_HOURLY_LIMIT       = 3
        self.KICK_DAILY_LIMIT        = 6
        self.QUARANTINE_HOURLY_LIMIT = 5
        self.QUARANTINE_DAILY_LIMIT  = 20
        self.SEVERE_HOURLY_LIMIT     = 4
        self.SEVERE_DAILY_LIMIT      = 8

    @property
    def data(self) -> dict[str, Any]:
        return self.bot.mod_data

    @property
    def cases_manager(self) -> CasesManager:
        return self.bot.cases_manager

    def _load_data(self) -> dict[str, Any]:
        if os.path.exists("moderation_data.json"):
            with contextlib.suppress(json.JSONDecodeError), open("moderation_data.json") as f:
                return json.load(f)
        return self._get_default_data()

    def _get_default_data(self) -> dict[str, Any]:
        return {
            "bans":        {},
            "timeouts":    {},
            "kicks":       {},
            "rate_limits": {},
            "quarantined": {}
        }

    def save_data(self) -> None:
        with open("moderation_data.json", "w") as f:
            json.dump(self.data, f, indent=4)

    def parse_duration(self, duration_str: str) -> int | None:
        duration_str = duration_str.lower().strip()
        try:
            if duration_str.endswith("s"):
                return int(duration_str[:-1])
            if duration_str.endswith("m"):
                return int(duration_str[:-1]) * 60
            if duration_str.endswith("h"):
                return int(duration_str[:-1]) * 3600
            if duration_str.endswith("d"):
                return int(duration_str[:-1]) * 86400
            if duration_str.endswith("w"):
                return int(duration_str[:-1]) * 604800
            return int(duration_str) * 60
        except ValueError:
            return None

    def _ensure_rate_limit_entry(self, user_id: str) -> None:
        if "rate_limits" not in self.data:
            self.data["rate_limits"] = {}

        rate_limits: dict[str, dict[str, list[str]]] = self.data["rate_limits"]

        if user_id not in rate_limits:
            rate_limits[user_id] = {}

        rl: dict[str, list[str]] = rate_limits[user_id]
        for key in (
            "ban_hourly", "ban_daily",
            "kick_hourly", "kick_daily",
            "quarantine_hourly", "quarantine_daily",
            "severe_hourly", "severe_daily",
        ):
            if key not in rl:
                rl[key] = []

    def clean_old_rate_limits(self, user_id: str) -> None:
        now = datetime.now()
        self._ensure_rate_limit_entry(user_id)

        rate_limits: dict[str, dict[str, list[str]]] = self.data["rate_limits"]
        rl: dict[str, list[str]] = rate_limits[user_id]

        for key in ("ban_hourly", "kick_hourly", "quarantine_hourly", "severe_hourly"):
            rl[key] = [ts for ts in rl[key] if datetime.fromisoformat(ts) > now - timedelta(hours=1)]
        for key in ("ban_daily", "kick_daily", "quarantine_daily", "severe_daily"):
            rl[key] = [ts for ts in rl[key] if datetime.fromisoformat(ts) > now - timedelta(days=1)]

    def check_rate_limit(self, user_id: str, action: str) -> tuple[bool, str]:
        self.clean_old_rate_limits(user_id)

        rate_limits: dict[str, dict[str, list[str]]] = self.data["rate_limits"]
        rl: dict[str, list[str]] = rate_limits[user_id]

        if len(rl["severe_hourly"]) >= self.SEVERE_HOURLY_LIMIT:
            return False, f"Severe action hourly limit exceeded ({self.SEVERE_HOURLY_LIMIT} bans/kicks/quarantines per hour)"
        if len(rl["severe_daily"]) >= self.SEVERE_DAILY_LIMIT:
            return False, f"Severe action daily limit exceeded ({self.SEVERE_DAILY_LIMIT} bans/kicks/quarantines per day)"

        if action == "ban":
            if len(rl["ban_hourly"]) >= self.BAN_HOURLY_LIMIT:
                return False, f"Ban hourly limit exceeded ({self.BAN_HOURLY_LIMIT} bans per hour)"
            if len(rl["ban_daily"]) >= self.BAN_DAILY_LIMIT:
                return False, f"Ban daily limit exceeded ({self.BAN_DAILY_LIMIT} bans per day)"
        elif action == "kick":
            if len(rl["kick_hourly"]) >= self.KICK_HOURLY_LIMIT:
                return False, f"Kick hourly limit exceeded ({self.KICK_HOURLY_LIMIT} kicks per hour)"
            if len(rl["kick_daily"]) >= self.KICK_DAILY_LIMIT:
                return False, f"Kick daily limit exceeded ({self.KICK_DAILY_LIMIT} kicks per day)"
        elif action == "quarantine":
            if len(rl["quarantine_hourly"]) >= self.QUARANTINE_HOURLY_LIMIT:
                return False, f"Quarantine hourly limit exceeded ({self.QUARANTINE_HOURLY_LIMIT} quarantines per hour)"
            if len(rl["quarantine_daily"]) >= self.QUARANTINE_DAILY_LIMIT:
                return False, f"Quarantine daily limit exceeded ({self.QUARANTINE_DAILY_LIMIT} quarantines per day)"

        return True, ""

    def add_rate_limit_entry(self, user_id: str, action: str) -> None:
        now = datetime.now().isoformat()
        self._ensure_rate_limit_entry(user_id)

        rate_limits: dict[str, dict[str, list[str]]] = self.data["rate_limits"]
        rl: dict[str, list[str]] = rate_limits[user_id]

        if action in ("ban", "kick", "quarantine"):
            rl["severe_hourly"].append(now)
            rl["severe_daily"].append(now)

        if action == "ban":
            rl["ban_hourly"].append(now)
            rl["ban_daily"].append(now)
        elif action == "kick":
            rl["kick_hourly"].append(now)
            rl["kick_daily"].append(now)
        elif action == "quarantine":
            rl["quarantine_hourly"].append(now)
            rl["quarantine_daily"].append(now)

        self.save_data()

    def has_protected_role(self, member: discord.Member) -> bool:
        return any(has_role(member, role_id) for role_id in self.PROTECTED_ROLE_IDS)

    def can_view(self, member: discord.Member) -> bool:
        return (
            is_director(member) or
            is_senior_moderator(member) or
            is_administrator(member) or
            is_moderator(member)
        )

    def can_moderate(self, member: discord.Member) -> bool:
        return is_senior_moderator(member)

    def can_unban_untimeout(self, member: discord.Member) -> bool:
        return is_director(member)

    def can_quarantine(self, member: discord.Member) -> bool:
        return is_senior_moderator(member)

    def check_hierarchy(self, moderator: discord.Member, target: discord.Member) -> bool:
        if target.id == moderator.guild.owner_id:
            return False
        if moderator.id == moderator.guild.owner_id:
            return True
        if is_director(moderator) and has_role(target, self.QUARANTINE_ROLE_ID):
            return True

        target_roles = [role for role in target.roles if role.id != self.QUARANTINE_ROLE_ID]
        if not target_roles:
            return True

        highest_target_role = max(target_roles, key=lambda r: r.position)
        return moderator.top_role.position > highest_target_role.position

    def check_can_moderate_target(self, moderator: discord.Member, target: discord.Member) -> tuple[bool, str]:
        if self.has_protected_role(target):
            if self.can_quarantine(moderator):
                return False, "You cannot ban/kick/mute staff members. Use `/quarantine add` instead."
            return False, "You cannot ban/kick/mute staff members."

        if not self.check_hierarchy(moderator, target):
            if self.can_quarantine(moderator):
                return False, "Target user is greater than or equal to your highest role. Use `/quarantine add` instead."
            return False, "Target user is greater than or equal to your highest role."

        return True, ""

    async def auto_quarantine_moderator(self, moderator: discord.Member, guild: discord.Guild) -> None:
        if not guild or not self.bot.user:
            return

        quarantine_role = guild.get_role(self.QUARANTINE_ROLE_ID)
        if not quarantine_role:
            return

        saved_roles = [role.id for role in moderator.roles if role.id != guild.id]

        if "quarantined" not in self.data:
            self.data["quarantined"] = {}

        self.data["quarantined"][str(moderator.id)] = {
            "roles":          saved_roles,
            "quarantined_at": datetime.now().isoformat(),
            "quarantined_by": self.bot.user.id,
            "reason":         "UB Anti-Nuke: exceeded moderation rate limits"
        }
        self.save_data()

        try:
            roles_to_remove = [role for role in moderator.roles if role.id != guild.default_role.id]
            await moderator.remove_roles(*roles_to_remove, reason="UB Anti-Nuke: Exceeded rate limits")
            await moderator.add_roles(quarantine_role, reason="UB Anti-Nuke: Exceeded rate limits")

            bot_member = guild.get_member(self.bot.user.id)
            if bot_member:
                await self.cases_manager.log_case(
                    guild       = guild,
                    case_type   = CaseType.QUARANTINE_ADD,
                    moderator   = bot_member,
                    reason      = "Exceeded moderation rate limits (auto-quarantine)",
                    target_user = moderator,
                    metadata    = {"roles_saved": len(saved_roles), "auto_quarantine": True}
                )
        except discord.Forbidden:
            pass