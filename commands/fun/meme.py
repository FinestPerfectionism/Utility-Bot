import discord
from discord.ext import commands
from discord import app_commands

from typing import Any

import random
import aiohttp
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
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.session: aiohttp.ClientSession | None = None
        self.seen_memes: deque[str] = deque(maxlen=50)

    async def cog_load(self) -> None:
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))

    async def cog_unload(self) -> None:
        if self.session:
            await self.session.close()

    async def fetch_meme(self) -> dict[str, Any]:
        if self.session is None:
            raise RuntimeError("HTTP session not initialized")

        last_error = None

        for _ in range(5):
            import secrets

            subreddit: str = secrets.choice(SUBREDDITS)
            url: str = f"https://meme-api.com/gimme/{subreddit}/5"

            try:
                async with self.session.get(url) as resp:
                    if resp.status != 200:
                        continue

                    payload: dict[str, Any] = await resp.json()
                    memes: list[dict[str, Any]] = payload.get("memes", [])
                    random.shuffle(memes)

                    for meme in memes:
                        if meme.get("nsfw"):
                            continue

                        post_link: str | None = meme.get("postLink")
                        image_url: str | None = meme.get("url")

                        if not image_url or not image_url.lower().endswith(IMAGE_EXTENSIONS):
                            continue

                        if post_link in self.seen_memes:
                            continue

                        if post_link:
                            self.seen_memes.append(post_link)

                        return meme

            except (aiohttp.ClientError, TimeoutError) as e:
                last_error = e
                continue

        raise RuntimeError("Failed to fetch meme") from last_error

    @app_commands.command(
        name="meme", 
        description="Get a random meme."
    )
    @app_commands.checks.cooldown(1, 5.0)
    async def meme(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        try:
            data: dict[str, Any] = await self.fetch_meme()
        except Exception:
            await send_major_error(
                interaction,
                "Failed to fetch a meme. Try again later.",
                subtitle=f"Invalid operation. Contact @{BOT_OWNER_ID}"
            )
            return

        title: str = str(data.get("title", "Meme"))
        post_link: str | None = data.get("postLink")
        image_url: str = str(data.get("url", ""))
        subreddit: str = str(data.get("subreddit", "unknown"))
        ups: int = int(data.get("ups", 0))

        embed = discord.Embed(
            title=title,
            url=post_link,
            color=discord.Color.random(),
            timestamp=discord.utils.utcnow()
        )

        embed.set_image(url=image_url)

        embed.set_author(
            name=f"r/{subreddit}"
        )

        embed.set_footer(
            text=f"{ups}"
        )

        await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MemeCommands(bot))