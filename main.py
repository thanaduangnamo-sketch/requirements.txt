import nextcord
from nextcord.ext import commands
import requests
import os
from flask import Flask
from threading import Thread
import random

# --- ระบบเปิดเว็บจำลองสำหรับ Render (แก้ปัญหา Port scan timeout) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# -----------------------------------------------------------------

token = os.environ.get("DISCORD_TOKEN")
ownerid = [1532607357962420229]
image = "https://cdn.discordapp.com/attachments/1355010685108490410/1355532067768766515/ed40c25e-1eaf-4cc0-b8b0-5198d79dae76.png"

bot = commands.Bot(command_prefix="!", intents=nextcord.Intents.all())

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    bot.add_view(TokenCheckView())
    bot.add_view(VerifyView()) # โหลด View ยืนยันตัวตนให้ค้างไว้ตลอด

# --- ระบบยืนยันตัวตนแบบเท่ๆ (Verification System) ---
class VerifyModal(nextcord.ui.Modal):
    def __init__(self, correct_code: str):
        super().__init__(title="🛡️ ระบบยืนยันตัวตนความปลอดภัยสูง")
        self.correct_code = correct_code
        
        self.code_input = nextcord.ui.TextInput(
            label=f"กรุณากรอกรหัสยืนยัน: [{correct_code}]",
            placeholder="พิมพ์ตัวเลขตามด้านบนให้ถูกต้อง",
            style=nextcord.TextInputStyle.short,
            required=True,
            max_length=6
        )
        self.add_item(self.code_input)

    async def callback(self, interaction: nextcord.Interaction):
        user_answer = str(self.code_input.value).strip()
        
        if user_answer == self.correct_code:
            # กำหนดไอดีของยศ (Role) ที่ต้องการให้หลังยืนยันตัวตนสำเร็จ (เปลี่ยนเลขใน string ด้านล่างเป็น ID ยศในเซิร์ฟเวอร์ของคุณ)
            role_id = 000000000000000000  # <-- เปลี่ยนเป็น ID ยศสมาชิก
            role = interaction.guild.get_role(role_id)
            
            if role:
                try:
                    await interaction.user.add_roles(role)
                except Exception:
                    pass

            await interaction.response.send_message(
                embed=nextcord.Embed(
                    description="### ✅ ยืนยันตัวตนสำเร็จ!\nยินดีต้อนรับเข้าสู่เซิร์ฟเวอร์ คุณได้รับยศเรียบร้อยแล้ว",
                    color=nextcord.Color.green()
                ),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=nextcord.Embed(
                    description="### ❌ รหัสยืนยันไม่ถูกต้อง!\nกรุณากดปุ่มยืนยันตัวตนใหม่อีกครั้ง",
                    color=nextcord.Color.red()
                ),
                ephemeral=True
            )

class VerifyView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="คลิกเพื่อยืนยันตัวตน", style=nextcord.ButtonStyle.green, custom_id="verify_button_main", emoji="✅")
    async def verify_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # สุ่มเลข 4 หลักเพื่อความปลอดภัยเท่ๆ
        random_code = str(random.randint(1000, 9999))
        await interaction.response.send_modal(VerifyModal(correct_code=random_code))


# --- ระบบเช็ค Token เดิมของคุณ ---
class TokenModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(title="🔐 ตรวจสอบ Discord Token")
        self.token_input = nextcord.ui.TextInput(
            label="กรอก Discord Token ของคุณ",
            placeholder="วาง Token ที่นี่ (ข้อมูลไม่ถูกบันทึก)",
            style=nextcord.TextInputStyle.paragraph,
            required=True
        )
        self.add_item(self.token_input)

    async def callback(self, interaction: nextcord.Interaction):
        await interaction.response.defer(ephemeral=True)
        raw_token = str(self.token_input.value).strip()

        headers = {
            "Authorization": raw_token if not raw_token.lower().startswith("bot ") else raw_token,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            response = requests.get("https://discord.com/api/v9/users/@me", headers=headers, timeout=10)

            if response.status_code != 200:
                return await interaction.followup.send(
                    embed=nextcord.Embed(
                        description="### ❌ Token ไม่ถูกต้อง หรือบัญชีถูกระงับ/ยืนยันตัวตน",
                        color=nextcord.Color.red()
                    ),
                    ephemeral=True
                )

            data = response.json()
            username = f"{data.get('username')}#{data.get('discriminator', '0')}"
            if data.get('discriminator') == '0':
                username = data.get('username')
            
            user_id = data.get('id')
            email = data.get('email', 'ไม่พบข้อมูล')
            phone = data.get('phone', 'ไม่พบข้อมูล')
            mfa = "เปิดใช้งาน ✅" if data.get('mfa_enabled') else "ปิดใช้งาน ❌"
            
            nitro_type = "ไม่มี Nitro ❌"
            premium_type = data.get('premium_type', 0)
            if premium_type == 1:
                nitro_type = "Nitro Classic 💎"
            elif premium_type == 2:
                nitro_type = "Nitro Boost 🚀"
            elif premium_type == 3:
                nitro_type = "Nitro Basic 🌟"

            dm_embed = nextcord.Embed(
                title="**🛡️ ผลการตรวจสอบ Token (ส่วนตัว)**",
                description="ระบบได้ทำการตรวจสอบข้อมูลเบื้องต้นเรียบร้อยแล้ว",
                color=nextcord.Color.blurple()
            )
            dm_embed.add_field(name="👤 ชื่อผู้ใช้", value=f"`{username}`", inline=True)
            dm_embed.add_field(name="🆔 ไอดีผู้ใช้", value=f"`{user_id}`", inline=True)
            dm_embed.add_field(name="🏷️ ประเภทบัญชี", value="`Bot Account`" if raw_token.startswith("Bot ") else "`User Account`", inline=True)
            dm_embed.add_field(name="📧 อีเมล", value=f"`{email}`", inline=True)
            dm_embed.add_field(name="📱 เบอร์โทรศัพท์", value=f"`{phone}`", inline=True)
            dm_embed.add_field(name="🔒 สถานะ 2FA", value=f"`{mfa}`", inline=True)
            dm_embed.add_field(name="💎 สถานะ Nitro", value=f"`{nitro_type}`", inline=False)
            dm_embed.set_footer(text="ข้อมูลความปลอดภัย: Token ของคุณจะไม่ถูกบันทึกใดๆ ทั้งสิ้น")

            avatar_hash = data.get('avatar')
            if avatar_hash:
                is_animated = avatar_hash.startswith("a_")
                ext = "gif" if is_animated else "png"
                dm_embed.set_thumbnail(url=f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{ext}?size=256")

            try:
                await interaction.user.send(embed=dm_embed)
                await interaction.followup.send(
                    embed=nextcord.Embed(
                        description="### ✅ ตรวจสอบสำเร็จ! ระบบได้ส่งผลลัพธ์ไปที่ **DM (ข้อความส่วนตัว)** ของคุณแล้ว",
                        color=nextcord.Color.green()
                    ),
                    ephemeral=True
                )
            except nextcord.Forbidden:
                await interaction.followup.send(
                    embed=nextcord.Embed(
                        description="### ⚠️ ไม่สามารถส่ง DM ได้ กรุณาเปิดรับข้อความส่วนตัวจากสมาชิกในเซิร์ฟเวอร์",
                        color=nextcord.Color.orange()
                    ),
                    ephemeral=True
                )

        except Exception as e:
            await interaction.followup.send(
                embed=nextcord.Embed(
                    description=f"### ❌ เกิดข้อผิดพลาดในการเชื่อมต่อ: `{e}`",
                    color=nextcord.Color.red()
                ),
                ephemeral=True
            )

class TokenCheckView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="เช็ค Token", style=nextcord.ButtonStyle.red, custom_id="check_token_btn", emoji="🔍")
    async def check_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(TokenModal())

# คำสั่งติดตั้งปุ่ม Token Checker
@bot.slash_command(name="setup-token-checker", description="🤖 ติดตั้งระบบ Token Checker")
async def setup(interaction: nextcord.Interaction):
    if interaction.user.id in ownerid:
        embed = nextcord.Embed(
            title="**TOKEN CHECKER | ตรวจสอบ Discord Token**",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━ .•° **TOKEN CHECKER** °•.\n"
                "╭ ·  **ระบบตรวจสอบความถูกต้องและดูสิทธิ์ของ Token**\n"
                "| ·  **แยกประเภทบัญชีอัตโนมัติ (User Account / Bot)**\n"
                "| ·  **ตรวจสอบอีเมล, เบอร์โทรศัพท์ และสถานะ 2FA**\n"
                "╰ ·  **เช็คสถานะแพลทินัม Nitro ล่าสุด นโยบายความปลอดภัย:**\n\n"
                "• **ข้อมูล Token จะไม่ถูกนำไปบันทึกหรือบันทึกในฐานข้อมูลใดๆ**\n"
                "• **ผลลัพธ์แสดงเฉพาะตัวคุณเท่านั้น (ส่งเข้า DM ส่วนตัว)**"
            ),
            color=nextcord.Color.red()
        )
        embed.set_image(url=image)
        embed.set_footer(text="ICEWEN_2 : TOKEN CHECKER SYSTEM")

        await interaction.channel.send(embed=embed, view=TokenCheckView())
        await interaction.response.send_message("### ✅ ติดตั้งระบบ Token Checker สำเร็จ", ephemeral=True)
    else:
        await interaction.response.send_message("### ❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)

# คำสั่งติดตั้งระบบยืนยันตัวตน (/setup-verify)
@bot.slash_command(name="setup-verify", description="🛡️ ติดตั้งระบบปุ่มยืนยันตัวตนสำหรับสมาชิกใหม่")
async def setup_verify(interaction: nextcord.Interaction):
    if interaction.user.id in ownerid:
        embed = nextcord.Embed(
            title="**VERIFICATION | ยืนยันตัวตนเพื่อเข้าสู่เซิร์ฟเวอร์**",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━ .•° **VERIFY SYSTEM** °•.\n\n"
                "🛡️ **กรุณากดปุ่มด้านล่างเพื่อทำการยืนยันตัวตน**\n"
                "• ป้องกันบอทและไอดีสแปมเข้าสู่เซิร์ฟเวอร์\n"
                "• กดปุ่มแล้วกรอกรหัสตัวเลขตามที่ระบบกำหนดเพื่อรับยศอัตโนมัติ"
            ),
            color=nextcord.Color.blurple()
        )
        embed.set_footer(text="SECURITY SYSTEM : ICEWEN_2")

        await interaction.channel.send(embed=embed, view=VerifyView())
        await interaction.response.send_message("### ✅ ติดตั้งระบบยืนยันตัวตนสำเร็จ", ephemeral=True)
    else:
        await interaction.response.send_message("### ❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)

# เริ่มรันระบบเว็บจำลองควบคู่ไปกับบอท
keep_alive()
bot.run(token)
