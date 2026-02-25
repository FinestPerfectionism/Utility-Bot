import discord
from discord.ext import commands
from discord import app_commands

from core import state

from constants import (
    DIRECTORS_ROLE_ID,
    STAFF_COMMITTEE_ROLE_ID,
    MODERATORS_AND_ADMINISTRATORS_ROLE_ID,
    ADMINISTRATORS_ROLE_ID,
    MODERATORS_ROLE_ID,
    STAFF_ROLE_ID,

    GUILD_ID,

    BOT_OWNER_ID
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Permissions Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Wrong Guild Check
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class WrongGuild(app_commands.CheckFailure):
    pass

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Permissions Denied Check
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class PermissionDenied(app_commands.CheckFailure):
    pass

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Main Guild Only Check
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

def main_guild_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None or interaction.guild.id != GUILD_ID:
            raise WrongGuild()
        return True

    return app_commands.check(predicate)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Require Role Check
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

def require_role(role_id: int):
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id == BOT_OWNER_ID and state.OWNER_PRIVILEGE_ENABLED:
            return True

        if not isinstance(interaction.user, discord.Member):
            raise PermissionDenied()

        if not any(role.id == role_id for role in interaction.user.roles):
            raise PermissionDenied()

        return True

    return app_commands.check(predicate)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Role Application Checks
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

def directors_only():
    return require_role(DIRECTORS_ROLE_ID)

def mod_and_admin_only():
    return require_role(MODERATORS_AND_ADMINISTRATORS_ROLE_ID)

def mod_only():
    return require_role(MODERATORS_ROLE_ID)

def admin_only():
    return require_role(ADMINISTRATORS_ROLE_ID)

def staff_only():
    return require_role(STAFF_ROLE_ID)

def committee_only():
    return require_role(STAFF_COMMITTEE_ROLE_ID)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Role Prefix Checks
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


def has_director_role():
    async def predicate(ctx: commands.Context) -> bool:
        if not isinstance(ctx.author, discord.Member):
            return False
        return any(role.id == DIRECTORS_ROLE_ID for role in ctx.author.roles)
    return commands.check(predicate)