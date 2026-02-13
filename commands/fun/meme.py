import discord
from discord.ext import commands
from discord import app_commands

import random
import aiohttp
import asyncio
from typing import Optional
from collections import deque

from core.utils import send_major_error

from constants import BOT_OWNER_ID

MEME_APIS = [
    "https://meme-api.com/gimme"
]

SUBREDDITS = [
    "memes",
    "dankmemes",
    "me_irl",
    "wholesomememes",
    "AdviceAnimals",
    "ProgrammerHumor",
]

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Meme Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class MemeCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None
        self.seen_memes = deque(maxlen=50)

    async def cog_load(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))

    async def cog_unload(self):
        if self.session:
            await self.session.close()

    async def fetch_meme(self) -> dict:
        if self.session is None:
            raise RuntimeError("HTTP session not initialized")

        last_error = None

        for _ in range(5):
            subreddit = random.choice(SUBREDDITS)
            url = f"https://meme-api.com/gimme/{subreddit}/5"

            try:
                async with self.session.get(url) as resp:
                    if resp.status != 200:
                        continue

                    payload = await resp.json()
                    memes = payload.get("memes", [])
                    random.shuffle(memes)

                    for meme in memes:
                        if meme.get("nsfw"):
                            continue

                        post_link = meme.get("postLink")
                        image_url = meme.get("url")

                        if not image_url or not image_url.lower().endswith(IMAGE_EXTENSIONS):
                            continue

                        if post_link in self.seen_memes:
                            continue

                        self.seen_memes.append(post_link)
                        return meme

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                continue

        raise RuntimeError("Failed to fetch meme") from last_error

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /meme Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name="meme", 
        description="Get a random meme."
    )
    @app_commands.checks.cooldown(1, 5.0)
    async def meme(self, interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            data = await self.fetch_meme()
        except Exception:
            await send_major_error(
                interaction,
                "Failed to fetch a meme. Try again later.",
                subtitle=f"Invalid operation. Contact @{BOT_OWNER_ID}"
            )
            return

        embed = discord.Embed(
            title=data.get("title", "Meme"),
            url=data.get("postLink"),
            color=discord.Color.random(),
            timestamp=discord.utils.utcnow()
        )

        embed.set_image(url=data["url"])

        embed.set_author(
            name=f"r/{data.get('subreddit', 'unknown')}"
        )

        embed.set_footer(
            text=f"{data.get('ups', 0)}"
        )

        await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(MemeCommands(bot))