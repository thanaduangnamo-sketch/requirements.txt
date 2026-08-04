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
# 🌐 ระบบจำลองเว็บพอร์ต ป้องกัน Render ตัดการเชื่อมต่อ
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

ROLE_ID = 1326066039481565225        # ไอดี ยศที่จะให้หลังยืนยันสำเร็จ
LOG_CHANNEL_ID = None               # ไอดี ห้องส่ง Log แจ้งเตือน

TOKEN = os.environ.get("DISCORD_TOKEN", "ใส่ Token ของบอทในนี้")


@bot.event
async def on_ready():
    print(f"BOT LOGIN: {bot.user}")
    try:
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
        
        await interaction.response.defer(ephemeral=True)
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
    await interaction.followup.send(embed=embed, file=file, view=view, ephemeral=True)


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
# 💾 แผงควบคุมระบบ SaveRoles System
# ==========================================
class SaveRolesView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="เซฟยศ", emoji="✅", style=discord.ButtonStyle.primary, custom_id="saveroles_save", row=1)
    async def save_roles(self, button: Button, interaction: discord.Interaction):
        await interaction.response.send_message("✅ บันทึกข้อมูล (เซฟยศ) ของคุณเรียบร้อยแล้ว!", ephemeral=True)

    @discord.ui.button(label="รับยศคืน", emoji="🔄", style=discord.ButtonStyle.success, custom_id="saveroles_restore", row=1)
    async def restore_roles(self, button: Button, interaction: discord.Interaction):
        await interaction.response.send_message("🔄 ดึงข้อมูลและทำการคืนยศให้คุณเรียบร้อยแล้ว!", ephemeral=True)

    @discord.ui.button(label="ดูข้อมูลผู้ใช้", emoji="👤", style=discord.ButtonStyle.secondary, custom_id="saveroles_info", row=1)
    async def user_info(self, button: Button, interaction: discord.Interaction):
        embed = discord.Embed(
            title="👤 ข้อมูลการเซฟยศของคุณ",
            description=f">>> **ผู้ใช้งาน:** {interaction.user.mention}\n- สถานะ: ปกติ\n- ยศที่บันทึกไว้: (ยังไม่มีข้อมูล)",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="รีวิว", emoji="⭐", style=discord.ButtonStyle.danger, custom_id="saveroles_review", row=1)
    async def review_system(self, button: Button, interaction: discord.Interaction):
        await interaction.response.send_message("⭐ ขอบคุณที่สนใจรีวิวระบบของเรา! สามารถพิมพ์ข้อความรีวิวได้เลยครับ", ephemeral=True)


# ==========================================
# 💬 คำสั่ง Slash Command และ Prefix Command: /saveroles และ !saveroles
# ==========================================
@bot.tree.command(name="saveroles", description="ส่งแผงควบคุมระบบ SaveRoles System (เซฟยศ/คืนยศ)")
async def saveroles_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="SaveRoles System",
        description=(
            "### 🗄️ บอทเซฟยศอัตโนมัติ กันหลุดดิส\n\n"
            "🟢 **คนยังไม่เคยเซฟ** 🟢\n"
            "```asciidoc\n"
            "+ ให้กดปุ่ม ( เซฟยศ ) เพื่อทำการเก็บข้อมูล\n"
            "```\n"
            "🟢 **คนมาเอายศคืน** 🟢\n"
            "```asciidoc\n"
            "+ ให้กดปุ่ม ( รับยศคืน ) เพื่อรับยศคืน\n"
            "+ ในกรณีดิสบิน เผลอออกดิส หรือดิสหลุด หรืออยากออกเข้าใหม่\n"
            "```\n\n"
            "⚠️ **ข้อความจากแอดมิน** ⚠️\n"
            "```diff\n"
            "- ❗ : บอทมีปัญหาโปรดแจ้งแอดมินโดยทันที\n"
            "```"
        ),
        color=discord.Color.from_rgb(40, 42, 54)
    )
    # ใส่ลิงก์ GIF ตามที่คุณต้องการ
    embed.set_image(url="https://media.discordapp.net/attachments/1168490971990851645/1168892040562610278/standard.gif?ex=6a72864b&is=6a7134cb&hm=d305063fd143d3c83dda97b9ada40666a7a91df4e1d99193b474fb132d2d1d5b&")
    
    await interaction.response.send_message(embed=embed, view=SaveRolesView())


@bot.command(name="saveroles")
@commands.has_permissions(administrator=True)
async def saveroles_prefix(ctx):
    embed = discord.Embed(
        title="SaveRoles System",
        description=(
            "### 🗄️ บอทเซฟยศอัตโนมัติ กันหลุดดิส\n\n"
            "🟢 **คนยังไม่เคยเซฟ** 🟢\n"
            "```asciidoc\n"
            "+ ให้กดปุ่ม ( เซฟยศ ) เพื่อทำการเก็บข้อมูล\n"
            "```\n"
            "🟢 **คนมาเอายศคืน** 🟢\n"
            "```asciidoc\n"
            "+ ให้กดปุ่ม ( รับยศคืน ) เพื่อรับยศคืน\n"
            "+ ในกรณีดิสบิน เผลอออกดิส หรือดิสหลุด หรืออยากออกเข้าใหม่\n"
            "```\n\n"
            "⚠️ **ข้อความจากแอดมิน** ⚠️\n"
            "```diff\n"
            "- ❗ : บอทมีปัญหาโปรดแจ้งแอดมินโดยทันที\n"
            "```"
        ),
        color=discord.Color.from_rgb(40, 42, 54)
    )
    embed.set_image(url="https://media.discordapp.net/attachments/1168490971990851645/1168892040562610278/standard.gif?ex=6a72864b&is=6a7134cb&hm=d305063fd143d3c83dda97b9ada40666a7a91df4e1d99193b474fb132d2d1d5b&")
    
    await ctx.message.delete()
    await ctx.send(embed=embed, view=SaveRolesView())


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
