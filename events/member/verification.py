import discord
from discord.ext import commands, tasks

import json
import os
import random
import string
from datetime import datetime, timedelta
from typing import Dict
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from constants import(
    BOT_OWNER_ID,

    ACCEPTED_EMOJI_ID,
    COLOR_GREEN,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,

    VERIFICATION_CHANNEL_ID,
    GOOBERS_ROLE_ID,
)
from core.utils import send_major_error, send_minor_error

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
        entered_code = self.code_input.value.strip().upper()

        if entered_code == self.correct_code:
            await self.cog.verify_user(interaction)
        else:
            await interaction.response.send_message(
                f"{DENIED_EMOJI_ID} **Incorrect code!**\n"
                "Please try again.",
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
            VerificationButton(cog),
            accent_color=COLOR_GREEN,
        )

        self.add_item(container)

class VerificationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data_file = "verification_data.json"
        self.data = self.load_data()

        self.VERIFICATION_CHANNEL_ID = VERIFICATION_CHANNEL_ID
        self.GOOBERS_ROLE_ID = GOOBERS_ROLE_ID

        self.verification_message_id = None

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

    def generate_captcha(self) -> tuple[str, BytesIO]:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        width, height = 300, 100
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        except():
            font = ImageFont.load_default()

        for _ in range(5):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(0, height)
            draw.line([(x1, y1), (x2, y2)], fill=(200, 200, 200), width=2)

        x_offset = 20
        for char in code:
            color = (
                random.randint(0, 100),
                random.randint(0, 100),
                random.randint(0, 100)
            )

            char_img = Image.new('RGBA', (60, 60), (255, 255, 255, 0))
            char_draw = ImageDraw.Draw(char_img)
            char_draw.text((5, 5), char, fill=color, font=font)

            angle = random.randint(-30, 30)
            char_img = char_img.rotate(angle, expand=True, fillcolor=(255, 255, 255, 0))

            y_offset = random.randint(10, 30)
            image.paste(char_img, (x_offset, y_offset), char_img)
            x_offset += 45

        for _ in range(100):
            x = random.randint(0, width)
            y = random.randint(0, height)
            draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))

        image = image.filter(ImageFilter.SMOOTH)

        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)

        return code, buffer

    async def start_verification(self, interaction: discord.Interaction):
        user = interaction.user
        guild = interaction.guild

        if not guild or not isinstance(user, discord.Member):
            return

        goobers_role = guild.get_role(self.GOOBERS_ROLE_ID)
        if goobers_role and goobers_role in user.roles:
            await send_minor_error(
                interaction,
                "You are already verified!",
                subtitle="Invalid operation."
            )
            return

        code, image_buffer = self.generate_captcha()
        file = discord.File(image_buffer, filename="captcha.png")

        verification_cog = self

        class SubmitButton(discord.ui.Button):
            def __init__(self):
                super().__init__(
                    label="Submit Code",
                    style=discord.ButtonStyle.green
                )

            async def callback(self, interaction: discord.Interaction):
                await interaction.response.send_modal(
                    CaptchaModal(code, verification_cog)
                )


        layout = discord.ui.LayoutView()
        container = discord.ui.Container(
            accent_colour=discord.Colour.blurple()
        )
        container.add_item(discord.ui.TextDisplay(
            content=(
                "## CAPTCHA Verification\n"
                "Enter the code shown in the image above.\n"
                "- Code is **case-insensitive.**\n"
                "- You have **5 minutes**."
            )
        ))
        container.add_item(SubmitButton())
        layout.add_item(container)

        await interaction.response.send_message(
            files=[file],
            view=layout,
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
            await user.add_roles(goobers_role, reason="Passed verification")

            if str(user.id) in self.data["unverified"]:
                user_data = self.data["unverified"][str(user.id)]
                if user_data.get("warning_message_id"):
                    try:
                        channel = guild.get_channel(self.VERIFICATION_CHANNEL_ID)
                        if channel and isinstance(channel, discord.TextChannel):
                            msg = await channel.fetch_message(user_data["warning_message_id"])
                            await msg.delete()
                    except():
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

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        goobers_role = member.guild.get_role(self.GOOBERS_ROLE_ID)
        if goobers_role and goobers_role in member.roles:
            return

        self.data["unverified"][str(member.id)] = {
            "joined_at": datetime.now().isoformat(),
            "warned": False,
            "warning_message_id": None
        }
        self.save_data()

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
                        except():
                            pass

                    try:
                        await member.send(
                            f"{DENIED_EMOJI_ID} **Guild removal!**\n"
                            "You joined \"The Goobers\" recently and did not complete verification in time. You were automatically removed from the guild.\n"
                            "-# **Note:** This is __not__ a ban and you can rejoin and start the process again."
                        )
                    except():
                        pass

                    await member.kick(reason="Failure to verify within 72 hours.")
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
                    except():
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
    await bot.add_cog(VerificationCog(bot))