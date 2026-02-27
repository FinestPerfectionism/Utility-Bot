import discord
from discord.ext import (
    commands,
    tasks
)

import json
import os
import random
import string
from datetime import (
    datetime,
    timedelta
)
from typing import Dict
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

    GOOBERS_ROLE_ID
)
from core.utils import send_major_error

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Verification System
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class CaptchaModal(discord.ui.Modal, title="Enter CAPTCHA Code"):
    def __init__(self, correct_code: str, cog):
        super().__init__(timeout=300)
        self.correct_code = correct_code
        self.cog = cog

        self.code_input = discord.ui.TextInput(
            label="CAPTCHA Code",
            placeholder="Enter the code from the image.",
            required=True,
            max_length=6,
            min_length=6
        )
        self.add_item(self.code_input)

    async def on_submit(self, interaction: discord.Interaction):
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

        entered_code = self.code_input.value.strip().upper()

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

class VerificationButton(discord.ui.Button):
    def __init__(self, cog):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Verify",
            custom_id="persistent_verification_button"
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        await self.cog.start_verification(interaction)

class HelpButton(discord.ui.Button):
    def __init__(self, cog):
        super().__init__(
            style=discord.ButtonStyle.red,
            label="Help!",
            custom_id="persistent_help_button"
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        await self.cog.start_help(interaction)

class VerificationComponents(discord.ui.LayoutView):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

        container = discord.ui.Container(
            discord.ui.TextDisplay(
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
            discord.ui.Separator(
                visible=True,
                spacing=discord.SeparatorSpacing.large
            ),
            discord.ui.TextDisplay(
                content=(
                    "Welcome to the server! We look forward to meeting you,\n"
                    "-# The Goobers community."
                )
            ),
            discord.ui.Separator(
                visible=True,
                spacing=discord.SeparatorSpacing.large
            ),
            discord.ui.ActionRow(
                VerificationButton(cog),
                HelpButton(cog),
            ),
            accent_color=COLOR_GREEN,
        )

        self.add_item(container)

class VerificationHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data_file = "verification_data.json"
        self.data = self.load_data()

        self.VERIFICATION_CHANNEL_ID = VERIFICATION_CHANNEL_ID
        self.GOOBERS_ROLE_ID = GOOBERS_ROLE_ID

        self.verification_message_id = None
        self.active_captchas: Dict[int, Dict] = {}

    async def cog_load(self):
        self.check_unverified_users.start()

    async def cog_unload(self):
        self.check_unverified_users.cancel()

    def load_data(self) -> Dict:
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self.get_default_data()
        return self.get_default_data()

    def get_default_data(self) -> Dict:
        return {
            "unverified": {},
            "verification_message_id": None
        }

    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=4)

    @staticmethod
    def generate_captcha() -> tuple[str, BytesIO]:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        def sine_distort(img: Image.Image) -> Image.Image:
            w, h = img.size
            amplitude = random.randint(3, 6)
            period = random.uniform(40, 70)

            src = np.array(img)
            dst = np.zeros_like(src)

            for x in range(w):
                offset = int(
                    amplitude * np.sin(2 * np.pi * x / period)
                    + random.randint(-2, 2)
                )

                if offset > 0:
                    dst[offset:h, x] = src[0:h - offset, x]
                elif offset < 0:
                    dst[0:h + offset, x] = src[-offset:h, x]
                else:
                    dst[:, x] = src[:, x]

            return Image.fromarray(dst, "RGBA")

        width, height = 320, 120

        background = Image.new("RGB", (width, height))
        bg_draw = ImageDraw.Draw(background)

        for y in range(height):
            r = 230 - int((y / height) * 20)
            g = 230 - int((y / height) * 20)
            b = 255
            bg_draw.line([(0, y), (width, y)], fill=(r, g, b))

        background = background.filter(ImageFilter.GaussianBlur(1))

        noise_layer = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        noise_draw = ImageDraw.Draw(noise_layer)

        text_layer = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        text_draw = ImageDraw.Draw(text_layer)

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

        char_images = []

        char_images = []
        for char in code:
            char_img = Image.new("RGBA", (70, 80), (255, 255, 255, 0))
            char_draw = ImageDraw.Draw(char_img)

            base = random.randint(70, 120)
            color = (
                base + random.randint(-20, 20),
                base + random.randint(-20, 20),
                base + random.randint(-20, 20),
                random.randint(160, 210)
            )

            char_draw.text((10, 10), char, fill=color, font=font)

            angle = random.randint(-30, 30)
            char_img = char_img.rotate(angle, expand=True)
            char_img = sine_distort(char_img)
            char_images.append(char_img)

        section_width = width // len(code)
        baseline_points = []

        for i, char_img in enumerate(char_images):
            section_center = (i * section_width) + (section_width // 2)

            x_pos = section_center - (char_img.size[0] // 2) + random.randint(-5, 5)
            y_offset = random.randint(25, 45)

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
            fake_char = random.choice(string.ascii_uppercase + string.digits)

            x = random.randint(0, width - 40)
            y = random.randint(0, height - 40)

            base = random.randint(80, 150)

            fake_color = (
                base + random.randint(-20, 20),
                base + random.randint(-20, 20),
                base + random.randint(-20, 20),
                random.randint(160, 220)
            )

            fake_img = Image.new("RGBA", (50, 50), (255, 255, 255, 0))
            fake_draw = ImageDraw.Draw(fake_img)

            fake_draw.text((10, 5), fake_char, font=small_font, fill=fake_color)

            fake_img = fake_img.rotate(random.randint(-45, 45), expand=True)
            fake_img = sine_distort(fake_img)

            noise_layer.paste(fake_img, (x, y), fake_img)

        for _ in range(5):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = x1 + random.randint(30, 80)
            y2 = y1 + random.randint(15, 50)

            noise_draw.ellipse(
                (x1, y1, x2, y2),
                fill=(
                    random.randint(150, 255),
                    random.randint(150, 255),
                    random.randint(150, 255),
                    40,
                ),
            )

        text_layer = sine_distort(text_layer)
        text_layer = text_layer.filter(ImageFilter.GaussianBlur(0.4))

        base = Image.alpha_composite(background.convert("RGBA"), noise_layer)
        final_image = Image.alpha_composite(base, text_layer)

        final_draw = ImageDraw.Draw(final_image)
        for _ in range(150):
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            final_draw.point(
                (x, y),
                fill=(
                    random.randint(0, 255),
                    random.randint(0, 255),
                    random.randint(0, 255),
                    random.randint(50, 150),
                ),
            )

        grain = np.random.normal(0, 10, (height, width, 3)).astype(np.int16)
        img_np = np.array(final_image.convert("RGB")).astype(np.int16)
        img_np = np.clip(img_np + grain, 0, 255).astype(np.uint8)
        final_image = Image.fromarray(img_np, "RGB")

        buffer = BytesIO()
        final_image.save(buffer, format="PNG")
        buffer.seek(0)

        return code, buffer

    class HelpComponents(discord.ui.LayoutView):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

            container = discord.ui.Container(
                discord.ui.TextDisplay(
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

            self.add_item(container)

    async def start_help(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            view=self.HelpComponents(self),
            ephemeral=True,
        )

    async def start_verification(self, interaction: discord.Interaction):
        user = interaction.user
        guild = interaction.guild

        if not guild or not isinstance(user, discord.Member):
            return

        goobers_role = guild.get_role(self.GOOBERS_ROLE_ID)
        if goobers_role and goobers_role in user.roles:
            await interaction.response.send_message(
                f"**{CONTESTED_EMOJI_ID} Failed to open verification session!**\n"
                "You are already verified!",
                ephemeral=True
            )
            return

        code, image_buffer = self.generate_captcha()

        self.active_captchas[user.id] = {
            "code": code,
            "expires_at": datetime.now() + timedelta(minutes=5),
            "attempts": 0
        }

        verification_cog = self

        class SubmitButton(discord.ui.Button):
            def __init__(self):
                super().__init__(
                    label="Submit Code",
                    style=discord.ButtonStyle.green
                )

            async def callback(self, interaction: discord.Interaction):
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

        container = discord.ui.Container(
            discord.ui.TextDisplay(
                content=(
                    "## CAPTCHA Verification\n"
                    "Enter the code shown in the image below.\n"
                    "- Code is **case-insensitive.**\n"
                    "- You have **5 minutes**."
                )
            ),
            discord.ui.Separator(
                visible=True,
                spacing=discord.SeparatorSpacing.large
            ),
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    media="attachment://captcha.png"
                ),
            ),
            discord.ui.Separator(
                visible=True,
                spacing=discord.SeparatorSpacing.large
            ),
            discord.ui.ActionRow(SubmitButton()),
            accent_color=COLOR_BLURPLE,
        )

        layout.add_item(container)

        await interaction.response.send_message(
            view=layout,
            files=[file],
            ephemeral=True
        )
    
    async def verify_user(self, interaction: discord.Interaction):
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
                    try:
                        channel = guild.get_channel(self.VERIFICATION_CHANNEL_ID)
                        if channel and isinstance(channel, discord.TextChannel):
                            msg = await channel.fetch_message(user_data["warning_message_id"])
                            await msg.delete()
                    except Exception:
                        pass

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

    @tasks.loop(minutes=30)
    async def check_unverified_users(self):
        now = datetime.now()
        to_remove = []

        for user_id, data in self.data["unverified"].items():
            joined_at = datetime.fromisoformat(data["joined_at"])
            time_since_join = now - joined_at

            member = None
            for guild in self.bot.guilds:
                member = guild.get_member(int(user_id))
                if member:
                    break

            if not member:
                to_remove.append(user_id)
                continue

            goobers_role = member.guild.get_role(self.GOOBERS_ROLE_ID)
            if goobers_role and goobers_role in member.roles:
                to_remove.append(user_id)
                continue

            if time_since_join >= timedelta(days=3):
                try:
                    if data.get("warning_message_id"):
                        try:
                            channel = member.guild.get_channel(self.VERIFICATION_CHANNEL_ID)
                            if channel and isinstance(channel, discord.TextChannel):
                                msg = await channel.fetch_message(data["warning_message_id"])
                                await msg.delete()
                        except Exception:
                            pass

                    try:
                        await member.send(
                            f"{DENIED_EMOJI_ID} **Guild removal!**\n"
                            "You joined \"The Goobers\" recently and did not complete verification in time. You were automatically removed from the guild.\n"
                            "-# **Note:** This is __not__ a ban and you can rejoin and start the process again."
                        )
                    except Exception:
                        pass

                    await member.kick(reason="UB Verification: failure to verify within 72 hours")
                    to_remove.append(user_id)

                except discord.Forbidden:
                    pass

            elif time_since_join >= timedelta(days=2) and not data.get("warned"):
                warned = False
                warning_message_id = None

                try:
                    await member.send(
                        f"{CONTESTED_EMOJI_ID} **Verification required!**\n"
                        "You joined \"The Goobers\" recently but have not completed verification! In 24 hours you will automatically be removed from the guild.\n"
                        "-# **Note:** This is __not__ a ban and you can rejoin and start the process again."
                    )
                    warned = True
                except discord.Forbidden:
                    try:
                        channel = member.guild.get_channel(self.VERIFICATION_CHANNEL_ID)
                        if channel and isinstance(channel, discord.TextChannel):
                            msg = await channel.send(
                                f"{CONTESTED_EMOJI_ID} **Verification required!**\n"
                                "You joined \"The Goobers\" recently but have not completed verification! In 24 hours you will automatically be removed from the guild.\n"
                                "-# **Note:** This is __not__ a ban and you can rejoin and start the process again."
                            )
                            warning_message_id = msg.id
                            warned = True
                    except Exception:
                        pass

                if warned:
                    self.data["unverified"][user_id]["warned"] = True
                    self.data["unverified"][user_id]["warning_message_id"] = warning_message_id
                    self.save_data()

        for user_id in to_remove:
            if user_id in self.data["unverified"]:
                del self.data["unverified"][user_id]

        if to_remove:
            self.save_data()

    @check_unverified_users.before_loop
    async def before_check_unverified_users(self):
        await self.bot.wait_until_ready()

    def get_verification_message_id(self):
        return self.data.get("verification_message_id")

    def set_verification_message_id(self, message_id: int):
        self.data["verification_message_id"] = message_id
        self.save_data()

async def setup(bot: commands.Bot):
    await bot.add_cog(VerificationHandler(bot))