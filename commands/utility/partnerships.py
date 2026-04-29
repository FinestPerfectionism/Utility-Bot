from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

import core.responses as cr
from constants import DIRECTORS_ROLE_ID, PARTNERSHIPS_CHANNEL_ID
from core.help import ArgumentInfo, RoleConfig, help_description
from core.permissions import directors_only
from core.responses import send_custom_message
from core.state.partnership_state import (
    IMAGE_DIR,
    PartnershipEntry,
    load_partnership_data,
    save_partnership_data,
)
from guild_info.partnerships import rebuild_partnership_layout

log = logging.getLogger("Utility Bot")

_INVITE_RE = re.compile(
    r"^(https?://)?(www\.)?(discord\.gg|discord\.com/invite)/[A-Za-z0-9-]+$",
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Partnership Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class PartnershipCommands(commands.Cog):
    def __init__(self, bot : commands.Bot) -> None:
        self.bot = bot

    partnership = app_commands.Group(
        name        = "partnership",
        description = "Directors only —— Manage server partnerships.",
    )

    async def _get_channel(
        self,
        interaction : discord.Interaction,
    ) -> discord.TextChannel | None:
        channel = self.bot.get_channel(PARTNERSHIPS_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            await send_custom_message(
                interaction,
                msg_type          = cr.error,
                title             =  "update",
                subtitle          =  "The partnerships channel ID is missing or points to the wrong channel type.",
                footer            = "Invalid IDs",
                contact_bot_owner = True,
            )
            return None
        return channel

    async def _server_name_autocomplete(
        self,
        _interaction : discord.Interaction,
        current      : str,
    ) -> list[app_commands.Choice[str]]:
        data = load_partnership_data()
        return [
            app_commands.Choice(name = p["server_name"], value = p["server_name"])
            for p in data["partnerships"]
            if current.lower() in p["server_name"].lower()
        ][:25]

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /partnership add
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @partnership.command(name = "add", description = "Add a server partnership.")
    @app_commands.describe(
        server_picture     = "The server's picture.",
        server_name        = "The server's name.",
        server_description = "The server's description.",
        server_owner       = "The server's owner.",
        server_link        = "The server's invite link. Must be a valid Discord invite of the form `https://discord.gg/example`.",
    )
    @help_description(
        desc      = "Directors only —— Adds a partnership entry and rebuilds the partnerships channel layout.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id = DIRECTORS_ROLE_ID)],
        arguments = {
            "server_picture"     : ArgumentInfo(description = "Image attachment shown for the partner server."),
            "server_name"        : ArgumentInfo(description = "Partner server name."),
            "server_description" : ArgumentInfo(description = "Partner server description."),
            "server_owner"       : ArgumentInfo(description = "Discord user who owns the partner server."),
            "server_link"        : ArgumentInfo(description = "Discord invite URL for the partner server."),
        },
    )
    @directors_only()
    async def partnership_add(
        self,
        interaction        : discord.Interaction,
        server_picture     : discord.Attachment,
        server_name        : str,
        server_description : str,
        server_owner       : discord.User,
        server_link        : str,
    ) -> None:
        if not _INVITE_RE.match(server_link):
            await send_custom_message(
                interaction,
                msg_type = cr.warning,
                title    = "update",
                subtitle = "The server link must be a valid Discord invite.",
                footer   = "Bad argument",
            )
            return

        _ = await interaction.response.defer(ephemeral = True)

        channel = await self._get_channel(interaction)
        if channel is None:
            return

        IMAGE_DIR.mkdir(parents=True, exist_ok=True)

        suffix     = Path(server_picture.filename).suffix or ".png"
        filename   = f"{uuid.uuid4()}{suffix}"
        image_path = IMAGE_DIR / filename

        try:
            image_bytes = await server_picture.read()
            _ = image_path.write_bytes(image_bytes)
        except discord.HTTPException:
            log.exception("Failed to download partnership attachment")
            await send_custom_message(
                interaction,
                msg_type          = cr.error,
                title             = "download the server picture",
                subtitle          = "Discord returned an error while fetching the attachment.",
                footer            = "Bad operation",
                contact_bot_owner = True,
            )
            return
        except OSError:
            log.exception("Failed to save partnership image to disk")
            await send_custom_message(
                interaction,
                msg_type          = cr.error,
                title             = "save the server picture",
                subtitle          = "The image was downloaded but could not be written to disk.",
                footer            = "Bad operation",
                contact_bot_owner = True,
            )
            return

        data        = load_partnership_data()
        description = server_description.replace("\\n", "\n")

        entry: PartnershipEntry = {
            "server_name"        : server_name,
            "server_description" : description,
            "server_owner_id"    : server_owner.id,
            "server_link"        : server_link,
            "image_filename"     : filename,
        }
        data["partnerships"].append(entry)

        _ = await interaction.followup.send(
            f"Partnership with **{server_name}** has been added successfully. Updating the channel...",
            ephemeral = True,
        )

        try:
            await rebuild_partnership_layout(channel, data)
        except discord.HTTPException:
            log.exception("Failed to rebuild partnership layout after add")
            _ = data["partnerships"].pop()
            image_path.unlink(missing_ok=True)
            await send_custom_message(
                interaction,
                msg_type          = cr.error,
                title             =  "update the partnerships channel",
                subtitle          = f"**{server_name}** was added to the data but the channel failed to rebuild. The entry has been rolled back.",
                footer            =  "Bad operation.",
                contact_bot_owner = True,
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /partnership remove
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @partnership.command(name = "remove", description = "Remove a server partnership.")
    @app_commands.describe(server_name = "The name of the server to remove.")
    @help_description(
        desc      = "Directors only —— Removes a partnership entry and rebuilds the partnerships channel layout.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id = DIRECTORS_ROLE_ID)],
        arguments = {"server_name" : ArgumentInfo(description = "Exact partner server name to remove.")},
    )
    @directors_only()
    async def partnership_remove(
        self,
        interaction : discord.Interaction,
        server_name : str,
    ) -> None:
        _ = await interaction.response.defer(ephemeral = True)

        channel = await self._get_channel(interaction)
        if channel is None:
            return

        data    = load_partnership_data()
        matches = [p for p in data["partnerships"] if p["server_name"] == server_name]

        if not matches:
            await send_custom_message(
                interaction,
                msg_type = cr.warning,
                title    = f'find partnership "{server_name}"',
                subtitle =  "No partnership exists with that name. Check the spelling or use the autocomplete.",
                footer   =  "Bad argument",
            )
            return

        removed  = matches[0]
        original = list(data["partnerships"])
        data["partnerships"] = [p for p in data["partnerships"] if p["server_name"] != server_name]

        _ = await interaction.followup.send(
            f"Partnership with **{server_name}** has been removed. Updating the channel...",
            ephemeral = True,
        )

        try:
            await rebuild_partnership_layout(channel, data)
        except discord.HTTPException:
            log.exception("Failed to rebuild partnership layout after remove")
            data["partnerships"] = original
            save_partnership_data(data)
            await send_custom_message(
                interaction,
                msg_type = cr.error,
                title             =  "update the partnerships channel",
                subtitle          = f"**{server_name}** was removed from the data but the channel failed to rebuild. The entry has been restored.",
                footer            = "Bad operation",
                contact_bot_owner = True,
            )
            return

        (IMAGE_DIR / removed["image_filename"]).unlink(missing_ok=True)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /partnership update
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @partnership.command(name = "update", description = "Update an existing server partnership.")
    @app_commands.describe(
        server_name        = "The name of the server to update.",
        server_picture     = "The server's new picture.",
        new_server_name    = "The server's new name.",
        server_description = "The server's new description.",
        server_owner       = "The server's new owner.",
        server_link        = "The server's new invite link. Must be a valid Discord invite of the form `https://discord.gg/example`.",
    )
    @app_commands.autocomplete(server_name = _server_name_autocomplete)
    @help_description(
        desc      = "Directors only —— Updates an existing partnership entry and rebuilds the partnerships channel layout.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id = DIRECTORS_ROLE_ID)],
        arguments = {
            "server_name"        : ArgumentInfo(description = "Existing partner server name to update."),
            "server_picture"     : ArgumentInfo(required = False, description = "Optional replacement image attachment."),
            "new_server_name"    : ArgumentInfo(required = False, description = "Optional replacement server name."),
            "server_description" : ArgumentInfo(required = False, description = "Optional replacement description."),
            "server_owner"       : ArgumentInfo(required = False, description = "Optional replacement server owner."),
            "server_link"        : ArgumentInfo(required = False, description = "Optional replacement Discord invite URL."),
        },
    )
    @directors_only()
    async def partnership_update(
        self,
        interaction        : discord.Interaction,
        server_name        : str,
        server_picture     : discord.Attachment | None = None,
        new_server_name    : str                | None = None,
        server_description : str                | None = None,
        server_owner       : discord.User       | None = None,
        server_link        : str                | None = None,
    ) -> None:
        if server_link is not None and not _INVITE_RE.match(server_link):
            await send_custom_message(
                interaction,
                msg_type = cr.warning,
                title    = "update partnership",
                subtitle = "The new server link must be a valid Discord invite.",
                footer   = "Bad argument",
            )
            return

        _ = await interaction.response.defer(ephemeral = True)

        channel = await self._get_channel(interaction)
        if channel is None:
            return

        data    = load_partnership_data()
        matches = [p for p in data["partnerships"] if p["server_name"] == server_name]

        if not matches:
            await send_custom_message(
                interaction,
                msg_type = cr.warning,
                title    = f'find partnership "{server_name}"',
                subtitle = "No partnership exists with that name. Check the spelling or use the autocomplete.",
                footer   = "Bad argument",
            )
            return

        entry               = matches[0]
        old_image_filename  : str | None = None

        if server_picture is not None:
            IMAGE_DIR.mkdir(parents=True, exist_ok=True)
            suffix         = Path(server_picture.filename).suffix or ".png"
            new_filename   = f"{uuid.uuid4()}{suffix}"
            new_image_path = IMAGE_DIR / new_filename
            try:
                image_bytes = await server_picture.read()
                _ = new_image_path.write_bytes(image_bytes)
                old_image_filename    = entry["image_filename"]
                entry["image_filename"] = new_filename
            except discord.HTTPException:
                log.exception("Failed to download updated partnership attachment")
                await send_custom_message(
                    interaction,
                    msg_type = cr.error,
                    title    = "download the new server picture",
                    subtitle = "Discord returned an error while fetching the attachment. No changes were saved.",
                    footer   = "Bad operation",
                    contact_bot_owner = True,
                )
                return
            except OSError:
                log.exception("Failed to save updated partnership image to disk")
                await send_custom_message(
                    interaction,
                    msg_type = cr.error,
                    title    = "save the new server picture",
                    subtitle = "The image was downloaded but could not be written to disk. No changes were saved.",
                    footer   = "Bad operation",
                    contact_bot_owner = True,
                )
                return

        if new_server_name is not None:
            entry["server_name"] = new_server_name
        if server_description is not None:
            entry["server_description"] = server_description.replace("\\n", "\n")
        if server_owner is not None:
            entry["server_owner_id"] = server_owner.id
        if server_link is not None:
            entry["server_link"] = server_link

        display_name = entry["server_name"]

        _ = await interaction.followup.send(
            f"Partnership with **{display_name}** has been updated. Updating the channel...",
            ephemeral = True,
        )

        try:
            await rebuild_partnership_layout(channel, data)
        except discord.HTTPException:
            log.exception("Failed to rebuild partnership layout after update")
            await send_custom_message(
                interaction,
                msg_type          = cr.error,
                title             =  "update the partnerships channel",
                subtitle          = f"**{display_name}** was edited in the data but the channel failed to rebuild.",
                footer            =  "Bad operation",
                contact_bot_owner = True,
            )
            return

        if old_image_filename is not None:
            (IMAGE_DIR / old_image_filename).unlink(missing_ok=True)


async def setup(bot : commands.Bot) -> None:
    await bot.add_cog(PartnershipCommands(bot))
