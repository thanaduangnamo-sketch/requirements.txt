import discord
from discord.ext import commands
from discord.ui import View, Button
from captcha.image import ImageCaptcha
import random
import io
import asyncio
import os
from flask import Flask
from threading import Thread

# ==========================================
# 🌐 ระบบจำลองเว็บพอร์ต ป้องกัน Render ตัดการเชื่อมต่อ (Timeout)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()


# ==========================================
# 🤖 ตั้งค่าบอท Discord
# ==========================================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ⚙️ ตั้งค่า ID ยศและห้อง Log ตรงนี้ได้เลย
ROLE_ID = 1326066039481565225        # ไอดี ยศที่จะให้หลังยืนยันสำเร็จ (จำเป็น)
LOG_CHANNEL_ID = None               # ไอดี ห้องส่ง Log แจ้งเตือน (ใส่ตัวเลข หรือปล่อยเป็น None ถ้าไม่ใช้)

TOKEN = os.environ.get("DISCORD_TOKEN", "ใส่ Token ของบอทในนี้")


@bot.event
async def on_ready():
    print(f"BOT LOGIN: {bot.user}")
    try:
        # ซิงค์ Slash Command ให้แสดงผลบน Discord ทันที
        await bot.tree.sync()
        print("Slash commands synced successfully.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


# ==========================================
# 🛡️ แผงปุ่มกดหลักสำหรับเรียกหน้าต่าง Captcha
# ==========================================
class VerifyButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="ยืนยันตัวตน", emoji="<:kb_members:1222593151449960549>", style=discord.ButtonStyle.secondary, custom_id="verify_start_new", row=1)
    async def verify(self, button: Button, interaction: discord.Interaction):
        role = interaction.guild.get_role(ROLE_ID)
        if role and role in interaction.user.roles:
            return await interaction.response.send_message("ℹ️ คุณได้ทำการยืนยันตัวตนไปแล้วเรียบร้อยครับ", ephemeral=True)
        
        await generate_captcha(interaction)
        
    @discord.ui.button(label="👨‍💻 Terms of dev", style=discord.ButtonStyle.secondary, custom_id="verify_dev_new", row=3)
    async def show_dev_info(self, button: Button, interaction: discord.Interaction):
        embed = discord.Embed(
            title="👨‍💻 คนทำระบบ",
            description=">>> **📌 ผู้พัฒนา:**\n"
                        "- 👤 **[icewen_2]**\n"
                        "- 🛠 **เครื่องมือ:** `discord.py`, `captcha.image`\n"
                        "- 📅 **วันพัฒนา:** [14/02/2025]\n"
                        "- 🌐 **ติดต่อ:** [IG: icesus_22]"
        )
        embed.set_footer(text="ขอบคุณที่ใช้ระบบ Aegis & icewen_2 ❤️")
        await interaction.response.send_message(embed=embed, ephemeral=True)  

    @discord.ui.button(label="วิธียืนยันตัวตน", emoji="<:kb_information:1217043424054874213>", style=discord.ButtonStyle.secondary, custom_id="verify_help_new", row=1)
    async def how_to_verify(self, button: Button, interaction: discord.Interaction):
        embed = discord.Embed(
            title="# ❓ วิธีการยืนยันตัวตน",
            description=(
                ">>> 1️⃣ กดปุ่ม **✅ ยืนยันตัวตน**\n"
                "2️⃣ บอทจะส่งรูป **Captcha ตัวเลข 4 หลัก**\n"
                "3️⃣ กดปุ่มตัวเลขให้ **ตรงกับตัวเลขในภาพ** ตามลำดับ\n"
                "4️⃣ ระบบจะทำการนับถอยหลังและตรวจสอบความถูกต้อง\n"
                "5️⃣ หากถูกต้อง บอทจะเพิ่มยศให้และส่งข้อความแจ้งเตือนทาง DM ทันที! ✅\n"
                "❌ ถ้ากรอกผิด ต้องเริ่มใหม่อีกครั้งกั้บผมม"
            )
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)  


# ==========================================
# 🖼️ ฟังก์ชันสร้างรูปภาพ Captcha
# ==========================================
async def generate_captcha(interaction: discord.Interaction):
    captcha_text = "".join(str(random.randint(0, 9)) for _ in range(4))

    image = ImageCaptcha(width=180, height=80)
    image_data = image.generate(captcha_text)
    image_bytes = io.BytesIO(image_data.read())

    embed = discord.Embed(
        title="**🔒 ยืนยันตัวตน (Captcha)**", 
        description="> กดปุ่มตัวเลขให้ตรงกับรูปภาพด้านล่างนี้"
    )
    file = discord.File(fp=image_bytes, filename="captcha.png")
    embed.set_image(url="attachment://captcha.png")

    view = CaptchaButtons(captcha_text)
    await interaction.response.send_message(embed=embed, file=file, view=view, ephemeral=True)


# ==========================================
# 🎛️ ปุ่มกดเลือกตัวเลข Captcha
# ==========================================
class CaptchaButtons(View):
    def __init__(self, captcha_text):
        super().__init__(timeout=None)
        self.captcha_text = captcha_text
        self.user_input = ""

        for digit in captcha_text:
            self.add_item(NumberButton(digit, self))

class NumberButton(Button):
    def __init__(self, digit, parent_view):
        super().__init__(label=digit, style=discord.ButtonStyle.primary)
        self.digit = digit
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.user_input += self.digit

        embed = interaction.message.embeds[0]
        embed.description = f">>> **🔢 โค้ดที่คุณป้อน:** ```{self.parent_view.user_input}```\n\nกรุณากดตัวเลขให้ครบ 4 ตัว"

        if len(self.parent_view.user_input) >= 4:
            if self.parent_view.user_input == self.parent_view.captcha_text:
                embed.description = ">>> ⏳ **กำลังตรวจสอบคำตอบ...**\n**3...**"
                await interaction.response.edit_message(embed=embed, view=None)

                for i in [2, 1]:
                    await asyncio.sleep(1)
                    embed.description = f">>> ⏳ **กำลังตรวจสอบคำตอบ...**\n**{i}...**"
                    await interaction.edit_original_message(embed=embed)
                
                await asyncio.sleep(1)

                role = interaction.guild.get_role(ROLE_ID)
                if role:
                    try:
                        await interaction.user.add_roles(role)
                        
                        try:
                            dm_embed = discord.Embed(
                                title="🎉 ยืนยันตัวตนสำเร็จ!",
                                description=f"ยินดีด้วยครับ คุณได้ผ่านการยืนยันตัวตนในเซิร์ฟเวอร์ **{interaction.guild.name}** และได้รับยศ **{role.name}** เรียบร้อยแล้ว!",
                                color=discord.Color.green()
                            )
                            await interaction.user.send(embed=dm_embed)
                        except:
                            pass 

                        embed.description = ">>> ✅ **ยืนยันตัวตนสำเร็จ! ตรวจสอบผลลัพธ์ทาง DM ได้เลย**"
                        embed.color = discord.Color.green()
                        await interaction.edit_original_message(embed=embed)

                        if LOG_CHANNEL_ID is not None:
                            log_channel = bot.get_channel(LOG_CHANNEL_ID)
                            if log_channel:
                                log_embed = discord.Embed(
                                    title="[ ✨ ] 🛡️ มีผู้ยืนยันตัวตนสำเร็จ",
                                    description=f">>> **👤 ผู้ใช้:** {interaction.user.mention} (`{interaction.user.id}`)\n**🎭 บทบาทที่ได้รับ:** {role.mention}",
                                    color=discord.Color.green()
                                )
                                await log_channel.send(embed=log_embed)
                    except Exception as e:
                        embed.description = f">>> ❌ เกิดข้อผิดพลาดในการให้ยศ: {e}"
                        embed.color = discord.Color.red()
                        await interaction.edit_original_message(embed=embed)
            else:
                embed.description = "> ❌ **ตัวเลขไม่ถูกต้อง! โปรดกดปุ่มยืนยันตัวตนใหม่อีกครั้ง**"
                embed.color = discord.Color.red()
                self.parent_view.clear_items()
                await interaction.response.edit_message(embed=embed, view=self.parent_view)
                return

        if self.parent_view.user_input != self.parent_view.captcha_text:
            await interaction.response.edit_message(embed=embed, view=self.parent_view)


# ==========================================
# 💬 คำสั่ง Slash Command: /vfy
# ==========================================
@bot.tree.command(name="vfy", description="ส่งแผงควบคุมระบบยืนยันตัวตน (Captcha)")
async def vfy(interaction: discord.Interaction):
    embed = discord.Embed(
        title="**🎄 | Verifications System**", 
        description=">>> - กดปุ่ม **ยืนยันตัวตน** ด้านล่างเพื่อเริ่มทำ Captcha\n - สงสัยวิธีทำ กดปุ่ม **วิธียืนยันตัวตน**", 
        color=discord.Color.blue()
    )
    embed.set_image(url="https://i.pinimg.com/originals/29/49/e0/2949e0262e42def248f1c77c571bf9ab.gif")
    await interaction.response.send_message(embed=embed, view=VerifyButton())


# ==========================================
# 🚀 รันบอทและเว็บเซิร์ฟเวอร์
# ==========================================
if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
