import nextcord
from nextcord import app_commands
from nextcord.ext import commands, tasks
from nextcord.ui import View, Button
from captcha.image import ImageCaptcha
import random
import io
import asyncio
import aiohttp
import os

# ==========================================
# ⚙️ ตั้งค่าพื้นฐานของบอทและ Intents
# ==========================================
intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ดึง Token จาก Render Environment Variables
TOKEN = os.environ.get("DISCORD_TOKEN", "ใส่ในนี้เลยครับบ")

verify_config = {}
user_saved_roles = {}

# ==========================================
# 🛡️ 1. ระบบยืนยันตัวตน (Captcha)
# ==========================================
class VerifyButton(View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    @nextcord.ui.button(label="ยืนยันตัวตน", emoji="<:kb_members:1222593151449960549>", style=nextcord.ButtonStyle.secondary, custom_id="verify_start_aegis", row=1)
    async def verify(self, button: Button, interaction: nextcord.Interaction):
        config = verify_config.get(interaction.guild.id)
        if not config:
            return await interaction.response.send_message("❌ เกิดข้อผิดพลาด: ระบบยืนยันตัวตนยังไม่ได้ตั้งค่า", ephemeral=True)
        await generate_captcha(interaction, self.guild_id)

    @nextcord.ui.button(label="👨‍💻 Terms of dev", style=nextcord.ButtonStyle.secondary, custom_id="verify_dev_aegis", row=3)
    async def show_dev_info(self, button: Button, interaction: nextcord.Interaction):
        embed = nextcord.Embed(title="👨‍💻 คนทำระบบ", description=">>> **📌 ผู้พัฒนา:** icewen_2")
        await interaction.response.send_message(embed=embed, ephemeral=True)  

    @nextcord.ui.button(label="วิธียืนยันตัวตน", emoji="<:kb_information:1217043424054874213>", style=nextcord.ButtonStyle.secondary, custom_id="verify_help_aegis", row=1)
    async def how_to_verify(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message("1. กดปุ่มยืนยันตัวตน\n2. กรอกตัวเลขให้ตรงรูปภาพ", ephemeral=True)  

async def generate_captcha(interaction: nextcord.Interaction, guild_id: int):
    captcha_text = "".join(str(random.randint(0, 9)) for _ in range(4))
    image = ImageCaptcha(width=180, height=80)
    image_data = image.generate(captcha_text)
    image_bytes = io.BytesIO(image_data.read())

    embed = nextcord.Embed(title="**🔒 ยืนยันตัวตน**", description="> กดตัวเลขให้ตรงกับ Captcha")
    file = nextcord.File(fp=image_bytes, filename="captcha.png")
    embed.set_image(url="attachment://captcha.png")
    await interaction.response.send_message(embed=embed, file=file, view=CaptchaButtons(captcha_text, guild_id), ephemeral=True)

class CaptchaButtons(View):
    def __init__(self, captcha_text, guild_id):
        super().__init__(timeout=None)
        self.captcha_text = captcha_text
        self.guild_id = guild_id
        self.user_input = ""
        for digit in captcha_text:
            self.add_item(NumberButton(digit, self))

class NumberButton(Button):
    def __init__(self, digit, parent_view):
        super().__init__(label=digit, style=nextcord.ButtonStyle.primary)
        self.digit = digit
        self.parent_view = parent_view

    async def callback(self, interaction: nextcord.Interaction):
        self.parent_view.user_input += self.digit
        if len(self.parent_view.user_input) >= 4:
            if self.parent_view.user_input == self.parent_view.captcha_text:
                config = verify_config.get(self.parent_view.guild_id)
                role = interaction.guild.get_role(config["role_id"])
                await interaction.user.add_roles(role)
                await interaction.response.edit_message(content="✅ ยืนยันตัวตนสำเร็จ!", embed=None, view=None)
            else:
                self.parent_view.user_input = ""
                await interaction.response.edit_message(content="❌ กรอกผิด ลองใหม่อีกครั้ง", view=self.parent_view)
        else:
            await interaction.response.edit_message(content=f"ป้อนแล้ว: {self.parent_view.user_input}", view=self.parent_view)

@bot.tree.command(name="aegis_verify", description="ส่งหน้าต่างยืนยันตัวตน")
@app_commands.default_permissions(administrator=True)
async def aegis_verify(interaction: nextcord.Interaction, เลือกยศ: nextcord.Role):
    verify_config[interaction.guild.id] = {"role_id": เลือกยศ.id}
    embed = nextcord.Embed(title="Verifications", description="กดปุ่มด้านล่างเพื่อยืนยันตัวตน")
    await interaction.channel.send(embed=embed, view=VerifyButton(interaction.guild.id))
    await interaction.response.send_message("✅ ส่งแผงยืนยันตัวตนแล้ว", ephemeral=True)

@bot.event
async def on_ready():
    print(f"BOT LOGIN: {bot.user}")
    await bot.tree.sync()

if __name__ == "__main__":
    bot.run(TOKEN)
