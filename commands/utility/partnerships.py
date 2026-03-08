from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import uuid
import logging
from pathlib import Path

from core.partnership_state import (
    IMAGE_DIR,
    PartnershipEntry,
    load_partnership_data
)
from core.permissions import directors_only

from guild_info.partnerships import rebuild_partnership_layout

from constants import PARTNERSHIPS_CHANNEL_ID

log = logging.getLogger("Utility Bot")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Partnership Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class PartnershipCommand(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /partnership Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(name="partnership", description="Add a server partnership.")
    @directors_only()
    async def partnership(
        self,
        interaction: discord.Interaction,
        server_picture: discord.Attachment,
        server_name: str,
        server_description: str,
        server_owner: discord.User,
        server_link: str,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        channel = self.bot.get_channel(PARTNERSHIPS_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            await interaction.followup.send(
                "Partnership channel not configured.", ephemeral=True
            )
            return

        IMAGE_DIR.mkdir(parents=True, exist_ok=True)

        suffix = Path(server_picture.filename).suffix or ".png"
        filename = f"{uuid.uuid4()}{suffix}"
        image_path = IMAGE_DIR / filename

        try:
            image_bytes = await server_picture.read()
            image_path.write_bytes(image_bytes)
        except discord.HTTPException as e:
            log.exception("Failed to download partnership attachment: %s", e)
            await interaction.followup.send(
                "Failed to process the server picture.", ephemeral=True
            )
            return
        except OSError as e:
            log.exception("Failed to save partnership image to disk: %s", e)
            await interaction.followup.send(
                "Failed to save the server picture.", ephemeral=True
            )
            return

        data = load_partnership_data()

        entry: PartnershipEntry = {
            "server_name": server_name,
            "server_description": server_description,
            "server_owner_id": server_owner.id,
            "server_link": server_link,
            "image_filename": filename,
        }
        data["partnerships"].append(entry)

        try:
            await rebuild_partnership_layout(channel, data)
        except discord.HTTPException as e:
            log.exception("Failed to rebuild partnership layout: %s", e)
            data["partnerships"].pop()
            image_path.unlink(missing_ok=True)
            await interaction.followup.send(
                "Failed to update the partnership channel.", ephemeral=True
            )
            return

        await interaction.followup.send(
            f"Partnership with **{server_name}** has been added successfully.",
            ephemeral=True,
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PartnershipCommand(bot))