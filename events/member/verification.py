import discord
from discord.ext import (
    commands,
    tasks
)

import asyncio
import logging
from typing import Any
import secrets
import json
import os
import random
import string
import contextlib
from datetime import (
    datetime,
    timedelta
)
from io import BytesIO
from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    ImageFilter
)
import numpy as np

from constants import(
    BOT_OWNER_ID,
    COLOR_BLURPLE,

    COLOR_GREEN,
    COLOR_RED,

    ACCEPTED_EMOJI_ID,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,

    VERIFICATION_CHANNEL_ID,
    MODERATORS_CHANNEL_ID,

    GOOBERS_ROLE_ID
)
from core.utils import send_major_error

logger = logging.getLogger("Utility Bot")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Verification System
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class CaptchaModal(discord.ui.Modal, title="Enter CAPTCHA Code"):
    code_input: discord.ui.TextInput[discord.ui.Modal] = discord.ui.TextInput(
        label="CAPTCHA Code",
        placeholder="Enter the code from the image.",
        required=True,
        max_length=6,
        min_length=6
    )

    def __init__(self, correct_code: str, cog: "VerificationHandler") -> None:
        super().__init__(timeout=300)
        self.correct_code: str = correct_code
        self.cog: VerificationHandler = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        session = self.cog.active_captchas.get(interaction.user.id)

        if not session:
            await interaction.response.send_message(
                f"{DENIED_EMOJI_ID} **Verification expired!**\n"
                "Verification session expired. Please restart.",
                ephemeral=True
            )
            return

        if datetime.now() > session["expires_at"]:
            del self.cog.active_captchas[interaction.user.id]
            await interaction.response.send_message(
                f"{DENIED_EMOJI_ID} **Verification expired!**\n"
                "Verification session expired. Please restart.",
                ephemeral=True
            )
            return

        entered_code: str = self.code_input.value.strip().upper()

        session["attempts"] += 1

        if entered_code == session["code"]:
            del self.cog.active_captchas[interaction.user.id]
            await self.cog.verify_user(interaction)
            return

        if session["attempts"] >= 3:
            del self.cog.active_captchas[interaction.user.id]
            await interaction.response.send_message(
                f"{DENIED_EMOJI_ID} **Verification expired!**\n"
                "Verification session expired due to too many failed attempts. Please restart.",
                ephemeral=True
            )
            return

        remaining = 3 - session["attempts"]

        await interaction.response.send_message(
            f"{DENIED_EMOJI_ID} **Incorrect code!**\n"
            f"Please re-enter the code and try again. Attempts remaining: {remaining}",
            ephemeral=True
        )

class VerificationButton(discord.ui.Button[discord.ui.View]):
    def __init__(self, cog: "VerificationHandler") -> None:
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Verify",
            custom_id="persistent_verification_button"
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction) -> None:
        try:  
            await self.cog.start_verification(interaction)
        except Exception as e:
            await send_major_error(
                interaction,
                texts="An error occurred while starting verification.",
                subtitle=f"Invalid operation. Contact the <@{BOT_OWNER_ID}>."
            )
            logger.exception(f"Error in verification: {e}")

class HelpButton(discord.ui.Button[discord.ui.View]):
    def __init__(self, cog: "VerificationHandler") -> None:
        super().__init__(
            style=discord.ButtonStyle.red,
            label="Help!",
            custom_id="persistent_help_button"
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.cog.start_help(interaction)

class VerificationComponents(discord.ui.LayoutView):
    def __init__(self, cog: "VerificationHandler") -> None:
        super().__init__(timeout=None)
        self.cog = cog

        container = discord.ui.Container( # type: ignore
            discord.ui.TextDisplay( # type: ignore
                content=(
                    "# Verification\n"
                    "This verification system ensures that spammers get harshly limited and bots get completely blocked. "
                    "Humans, though, should be able to pass the verification, so let's see, are you human? :]\n\n"
                    "1. **First,** click the **Verify** button,\n"
                    "2. **Secondly,** you'll receive a CAPTCHA image,\n"
                    "3. **Then,** enter the code you see in the image,\n"
                    "4. **Finally,** get verified and gain access to the server!\n\n"
                    "**Note:** Failure to verify within 72 hours will result in the bot removing you from the guild. "
                    "You will be warned at 48 hours. This is __not__ a ban and you can rejoin and start the process again!"
                )
            ),
            discord.ui.Separator( # type: ignore
                visible=True,
                spacing=discord.SeparatorSpacing.large
            ),
            discord.ui.TextDisplay( # type: ignore
                content=(
                    "Welcome to the server! We look forward to meeting you,\n"
                    "-# The Goobers community."
                )
            ),
            discord.ui.Separator( # type: ignore
                visible=True,
                spacing=discord.SeparatorSpacing.large
            ),
            discord.ui.ActionRow( # type: ignore
                VerificationButton(cog),
                HelpButton(cog),
            ),
            accent_color=COLOR_GREEN,
        )

        self.add_item(container) # type: ignore

class VerificationHandler(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.data_file = "verification_data.json"
        self.data = self.load_data()

        self.VERIFICATION_CHANNEL_ID = VERIFICATION_CHANNEL_ID
        self.GOOBERS_ROLE_ID = GOOBERS_ROLE_ID

        self.verification_message_id = None
        self.active_captchas: dict[int, dict[str, Any]] = {}

    async def cog_load(self) -> None:
        self.check_unverified_users.start()

    async def cog_unload(self) -> None:
        self.check_unverified_users.cancel()

    def load_data(self) -> dict[str, Any]:
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self.get_default_data()
        return self.get_default_data()

    def get_default_data(self) -> dict[str, Any]:
        return {
            "unverified": {},
            "verification_message_id": None
        }

    def save_data(self) -> None:
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=4)

    @staticmethod
    def generate_captcha() -> tuple[str, BytesIO]:
        code: str = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))

        def sine_distort(img: Image.Image) -> Image.Image:
            w, h = img.size
            amplitude: int = random.SystemRandom().randint(3, 6)
            period: float = 40 + (secrets.randbelow(310) / 10.0)

            src: np.ndarray[Any, Any] = np.array(img)
            dst: np.ndarray[Any, Any] = np.zeros_like(src)

            for x in range(w):
                offset: int = int(
                    amplitude * np.sin(2 * np.pi * x / period)
                    + random.SystemRandom().randint(-2, 2)
                )

                if offset > 0:
                    dst[offset:h, x] = src[0:h - offset, x]
                elif offset < 0:
                    dst[0:h + offset, x] = src[-offset:h, x]
                else:
                    dst[:, x] = src[:, x]

            return Image.fromarray(dst, "RGBA")

        width: int = 320
        height: int = 120

        background: Image.Image = Image.new("RGB", (width, height))
        bg_draw: ImageDraw.ImageDraw = ImageDraw.Draw(background)

        for y in range(height):
            r: int = 230 - int((y / height) * 20)
            g: int = 230 - int((y / height) * 20)
            b: int = 255
            bg_draw.line([(0, y), (width, y)], fill=(r, g, b))

        background = background.filter(ImageFilter.GaussianBlur(1))

        noise_layer: Image.Image = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        noise_draw: ImageDraw.ImageDraw = ImageDraw.Draw(noise_layer)

        text_layer: Image.Image = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        text_draw: ImageDraw.ImageDraw = ImageDraw.Draw(text_layer)

        font: Any
        small_font: Any

        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48
            )
            small_font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18
            )
        except Exception:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        char_images: list[Image.Image] = []
        for char in code:
            char_img: Image.Image = Image.new("RGBA", (70, 80), (255, 255, 255, 0))
            char_draw: ImageDraw.ImageDraw = ImageDraw.Draw(char_img)
            c_base: int = random.SystemRandom().randint(70, 120)
            color: tuple[int, int, int, int] = (
                c_base + random.SystemRandom().randint(-20, 20),
                c_base + random.SystemRandom().randint(-20, 20),
                c_base + random.SystemRandom().randint(-20, 20),
                random.SystemRandom().randint(160, 210)
            )
            char_draw.text((10, 10), char, fill=color, font=font)
            angle: int = random.SystemRandom().randint(-30, 30)
            char_img = char_img.rotate(angle, expand=True)
            char_img = sine_distort(char_img)
            char_images.append(char_img)

        section_width: int = width // len(code)
        baseline_points: list[tuple[int, int]] = []
        for i, char_img in enumerate(char_images):
            section_center: int = (i * section_width) + (section_width // 2)
            x_pos: int = section_center - (char_img.size[0] // 2) + random.SystemRandom().randint(-5, 5)
            y_offset: int = random.SystemRandom().randint(25, 45)
            x_pos = max(5, min(x_pos, width - char_img.size[0] - 5))
            text_layer.paste(char_img, (x_pos, y_offset), char_img)
            baseline_points.append(
                (
                    x_pos + char_img.size[0] // 2,
                    y_offset + char_img.size[1] // 2
                )
            )

        if len(baseline_points) >= 2:
            text_draw.line(
                baseline_points,
                fill=(40, 40, 40, 180),
                width=3,
                joint="curve"
            )

        for _ in range(25):
            fake_char: str = secrets.choice(string.ascii_uppercase + string.digits)
            fx: int = random.SystemRandom().randint(0, width - 40)
            fy: int = random.SystemRandom().randint(0, height - 40)
            n_base: int = random.SystemRandom().randint(80, 150)
            fake_color: tuple[int, int, int, int] = (
                n_base + random.SystemRandom().randint(-20, 20),
                n_base + random.SystemRandom().randint(-20, 20),
                n_base + random.SystemRandom().randint(-20, 20),
                random.SystemRandom().randint(160, 220)
            )
            fake_img: Image.Image = Image.new("RGBA", (50, 50), (255, 255, 255, 0))
            fake_draw: ImageDraw.ImageDraw = ImageDraw.Draw(fake_img)
            fake_draw.text((10, 5), fake_char, font=small_font, fill=fake_color)
            fake_img = fake_img.rotate(random.SystemRandom().randint(-45, 45), expand=True)
            fake_img = sine_distort(fake_img)
            noise_layer.paste(fake_img, (fx, fy), fake_img)

        for _ in range(5):
            x1: int = random.SystemRandom().randint(0, width)
            y1: int = random.SystemRandom().randint(0, height)
            x2: int = x1 + random.SystemRandom().randint(30, 80)
            y2: int = y1 + random.SystemRandom().randint(15, 50)
            noise_draw.ellipse(
                (x1, y1, x2, y2),
                fill=(
                    random.SystemRandom().randint(150, 255),
                    random.SystemRandom().randint(150, 255),
                    random.SystemRandom().randint(150, 255),
                    40,
                ),
            )

        text_layer = sine_distort(text_layer)
        text_layer = text_layer.filter(ImageFilter.GaussianBlur(0.4))

        canvas: Image.Image = Image.alpha_composite(background.convert("RGBA"), noise_layer)
        final_image: Image.Image = Image.alpha_composite(canvas, text_layer)

        final_draw: ImageDraw.ImageDraw = ImageDraw.Draw(final_image)
        for _ in range(150):
            px: int = random.SystemRandom().randint(0, width - 1)
            py: int = random.SystemRandom().randint(0, height - 1)
            final_draw.point(
                (px, py),
                fill=(
                    random.SystemRandom().randint(0, 255),
                    random.SystemRandom().randint(0, 255),
                    random.SystemRandom().randint(0, 255),
                    random.SystemRandom().randint(50, 150),
                ),
            )

        grain: np.ndarray[Any, Any] = np.random.normal(0, 10, (height, width, 3)).astype(np.int16)
        img_np: np.ndarray[Any, Any] = np.array(final_image.convert("RGB")).astype(np.int16)
        img_np = np.clip(img_np + grain, 0, 255).astype(np.uint8)
        final_image = Image.fromarray(img_np, "RGB")

        buffer: BytesIO = BytesIO()
        final_image.save(buffer, format="PNG")
        buffer.seek(0)

        return code, buffer

    class HelpComponents(discord.ui.LayoutView):
        def __init__(self, cog: commands.Cog) -> None:
            super().__init__(timeout=None)
            self.cog = cog

            container = discord.ui.Container( # type: ignore
                discord.ui.TextDisplay( # type: ignore
                    content=(
                        "# Stuck?\n"
                        "Ocasionally, the CAPTCHA system may be difficult to pass. Here are some tips:\n\n"
                        "- **Swap out letters:** For example, try switching out `0` and `O`, or `2` and `Z`.\n"
                        "- **Restart the verification process:** You'll receive a new CAPTCHA image.\n"
                        "## Still stuck?\n"
                        "Please contact a staff member (moderator, administrator, or director) for assistance. They will run manual verification, as long as you __provide the captcha image__ that was difficult for you to read. The bot developer will be notified of the issue."
                    ),
                ),
                accent_color=COLOR_RED,
            )

            self.add_item(container) # type: ignore

    async def start_help(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            view=self.HelpComponents(self),
            ephemeral=True,
        )

    async def start_verification(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        user = interaction.user
        guild = interaction.guild

        if not guild or not isinstance(user, discord.Member):
            return

        goobers_role = guild.get_role(self.GOOBERS_ROLE_ID)
        if goobers_role and goobers_role in user.roles:
            await interaction.followup.send(
                f"**{CONTESTED_EMOJI_ID} Failed to open verification session!**\n"
                "You are already verified!"
            )
            return

        code, image_buffer = await asyncio.to_thread(self.generate_captcha)

        self.active_captchas[user.id] = {
            "code": code,
            "expires_at": datetime.now() + timedelta(minutes=5),
            "attempts": 0
        }

        verification_cog = self

        class SubmitButton(discord.ui.Button[discord.ui.View]):
            def __init__(self) -> None:
                super().__init__(
                    label="Submit Code",
                    style=discord.ButtonStyle.green
                )

            async def callback(self, interaction: discord.Interaction) -> None:
                session = verification_cog.active_captchas.get(interaction.user.id)

                if not session:
                    await interaction.response.send_message(
                        f"{DENIED_EMOJI_ID} **Verification expired!**\n"
                        "Verification session expired. Please restart.",
                        ephemeral=True
                    )
                    return

                await interaction.response.send_modal(
                    CaptchaModal(session["code"], verification_cog)
                )

        file = discord.File(image_buffer, filename="captcha.png")

        layout = discord.ui.LayoutView()

        container = discord.ui.Container( # type: ignore
            discord.ui.TextDisplay( # type: ignore
                content=(
                    "## CAPTCHA Verification\n"
                    "Enter the code shown in the image below.\n"
                    "- Code is **case-insensitive.**\n"
                    "- You have **5 minutes**."
                )
            ),
            discord.ui.Separator( # type: ignore
                visible=True,
                spacing=discord.SeparatorSpacing.large
            ),
            discord.ui.MediaGallery( # type: ignore
                discord.MediaGalleryItem(
                    media="attachment://captcha.png"
                ),
            ),
            discord.ui.Separator( # type: ignore
                visible=True,
                spacing=discord.SeparatorSpacing.large
            ),
            discord.ui.ActionRow(SubmitButton()), # type: ignore
            accent_color=COLOR_BLURPLE,
        )

        layout.add_item(container) # type: ignore

        await interaction.response.send_message(
            view=layout,
            files=[file],
        )

    async def verify_user(self, interaction: discord.Interaction) -> None:
        user = interaction.user
        guild = interaction.guild

        if not guild or not isinstance(user, discord.Member):
            return

        goobers_role = guild.get_role(self.GOOBERS_ROLE_ID)
        if not goobers_role:
            await send_major_error(
                interaction,
                "Verification role not found.",
                subtitle=f"Invalid configuration. Contact <@{BOT_OWNER_ID}>."
            )
            return

        try:
            await user.add_roles(goobers_role, reason="UB Verification: passed verification")

            if str(user.id) in self.data["unverified"]:
                user_data = self.data["unverified"][str(user.id)]
                if user_data.get("warning_message_id"):
                    channel = guild.get_channel(self.VERIFICATION_CHANNEL_ID)
                    if channel and isinstance(channel, discord.TextChannel):
                        msg = await channel.fetch_message(user_data["warning_message_id"])
                        await msg.delete()

                del self.data["unverified"][str(user.id)]
                self.save_data()

            await interaction.response.send_message(
                f"{ACCEPTED_EMOJI_ID} **Successfully verified!\n**"
                "Welcome to the server!",
                ephemeral=True
            )

        except discord.Forbidden:
            await send_major_error(
                interaction,
                "I lack the necessary permissions to assign roles.",
                subtitle="Invalid configuration. Contact the owner."
            )

    async def _send_mod_notification(self, guild: discord.Guild, lines: list[str]) -> None:
        if not lines:
            return
        mod_channel = guild.get_channel(MODERATORS_CHANNEL_ID)
        if not isinstance(mod_channel, discord.TextChannel):
            return
        with contextlib.suppress(discord.Forbidden, discord.HTTPException):
            await mod_channel.send("\n".join(lines))

    @tasks.loop(minutes=30)
    async def check_unverified_users(self) -> None:
        now: datetime = datetime.now()
        to_remove: list[str] = []

        kicked_log: list[str] = []
        warned_log: list[str] = []

        for user_id_raw, data in list(self.data["unverified"].items()):
            user_id: str = str(user_id_raw)
            joined_at: datetime = datetime.fromisoformat(data["joined_at"])
            time_since_join: timedelta = now - joined_at
            member: discord.Member | None = None
            user_id_int: int = int(user_id)

            for guild in self.bot.guilds:
                member = guild.get_member(user_id_int)
                if not member:
                    try:
                        member = await guild.fetch_member(user_id_int)
                    except (discord.NotFound, discord.HTTPException):
                        continue
                if member:
                    break

            if not member:
                to_remove.append(user_id)
                continue

            goobers_role: discord.Role | None = member.guild.get_role(self.GOOBERS_ROLE_ID)
            if goobers_role and goobers_role in member.roles:
                to_remove.append(user_id)
                continue

            is_overdue: bool = time_since_join >= timedelta(days=3)

            if is_overdue:
                msg_id: int | None = data.get("warning_message_id")
                if msg_id:
                    with contextlib.suppress(discord.NotFound, discord.Forbidden, discord.HTTPException):
                        channel: discord.abc.GuildChannel | discord.Thread | None = member.guild.get_channel(self.VERIFICATION_CHANNEL_ID)
                        if isinstance(channel, discord.TextChannel):
                            msg: discord.Message = await channel.fetch_message(msg_id)
                            await msg.delete()

                with contextlib.suppress(discord.Forbidden, discord.HTTPException):
                    await member.send(
                        f"{DENIED_EMOJI_ID} **Guild removal!**\n"
                        "You joined \"The Goobers\" recently and did not complete verification in time. You were automatically removed from the guild.\n"
                        "-# **Note:** This is __not__ a ban and you can rejoin and start the process again."
                    )

                try:
                    await member.kick(reason="UB Verification: failure to verify within 72 hours")
                    to_remove.append(user_id)
                    kicked_log.append(f"{DENIED_EMOJI_ID} **{discord.utils.escape_markdown(str(member))}** (`{member.id}`) was kicked for failing to verify within 72 hours.")
                except discord.Forbidden:
                    pass

            elif time_since_join >= timedelta(days=2) and not data.get("warned"):
                warned: bool = False
                warning_message_id: int | None = None
                where: str = ""

                try:
                    await member.send(
                        f"{CONTESTED_EMOJI_ID} **Verification required!**\n"
                        "You joined \"The Goobers\" recently but have not completed verification! In 24 hours you will automatically be removed from the guild.\n"
                        "-# **Note:** This is __not__ a ban and you can rejoin and start the process again."
                    )
                    warned = True
                    where = "DM"
                except (discord.Forbidden, discord.HTTPException):
                    try:
                        warn_channel: discord.abc.GuildChannel | discord.Thread | None = member.guild.get_channel(self.VERIFICATION_CHANNEL_ID)
                        if isinstance(warn_channel, discord.TextChannel):
                            warn_msg: discord.Message = await warn_channel.send(
                                f"{member.mention}\n\n"
                                f"{CONTESTED_EMOJI_ID} **Verification required!**\n"
                                "You joined \"The Goobers\" recently but have not completed verification! In 24 hours you will automatically be removed from the guild.\n"
                                "-# **Note:** This is __not__ a ban and you can rejoin and start the process again."
                            )
                            warning_message_id = warn_msg.id
                            warned = True
                            where = "verification channel"
                    except (discord.Forbidden, discord.HTTPException):
                        pass

                if warned:
                    self.data["unverified"][user_id]["warned"] = True
                    self.data["unverified"][user_id]["warning_message_id"] = warning_message_id
                    self.save_data()
                    warned_log.append(f"{CONTESTED_EMOJI_ID} **{discord.utils.escape_markdown(str(member))}** (`{member.id}`) was warned via {where}.")

        for user_id_to_del in to_remove:
            if user_id_to_del in self.data["unverified"]:
                del self.data["unverified"][user_id_to_del]
        if to_remove:
            self.save_data()

        notification_lines: list[str] = warned_log + kicked_log
        if notification_lines:
            for guild in self.bot.guilds:
                await self._send_mod_notification(guild, notification_lines)

    @check_unverified_users.before_loop
    async def before_check_unverified_users(self) -> None:
        await self.bot.wait_until_ready()

    def get_verification_message_id(self) -> None:
        return self.data.get("verification_message_id")

    def set_verification_message_id(self, message_id: int) -> None:
        self.data["verification_message_id"] = message_id
        self.save_data()

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VerificationHandler(bot))