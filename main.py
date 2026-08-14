import os
import discord
from discord import app_commands
from discord.ext import commands
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# --- 1. ระบบเว็บเซิร์ฟเวอร์จำลองสำหรับ Render ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

# --- 2. ตั้งค่าบอท Discord ---
intents = discord.Intents.default()
intents.members = True

class VerifyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # ซิงค์ Slash Commands กับ Discord ทั่วโลก (หรือเซิร์ฟเวอร์หลัก)
        await self.tree.sync()
        print("🔄 ซิงค์ Slash Commands เรียบร้อยแล้ว!")

client = VerifyBot()

# ⚙️ ตั้งค่า ID ยศ และลิงก์รูปภาพของคุณที่นี่
VERIFY_ROLE_ID = 123456789012345678  # ใส่ ID ยศที่จะให้หลังยืนยัน
BANNER_IMAGE = "https://i.pinimg.com/736x/d1/50/12/d15012026d745a4302fd5bccffc437a2.jpg"

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="ยืนยันตัวตน", 
        style=discord.ButtonStyle.green, 
        custom_id="modern_verify_button_v2", 
        emoji="✨"
    )
    async def verify_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        
        if not role:
            await interaction.response.send_message("❌ เกิดข้อผิดพลาด: ไม่พบยศที่ตั้งค่าไว้ในระบบ", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.response.send_message("⚠️ คุณได้ทำการยืนยันตัวตนไปเรียบร้อยแล้วครับ!", ephemeral=True)
        else:
            try:
                await interaction.user.add_roles(role)
                await interaction.response.send_message("🎉 **ยืนยันตัวตนสำเร็จ!** ยินดีต้อนรับเข้าสู่เซิร์ฟเวอร์ของเราครับ", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message("❌ บอทไม่มีสิทธิ์จัดการยศนี้ (กรุณาเลื่อนยศบอทให้อยู่เหนือยศยืนยัน)", ephemeral=True)

@client.event
async def on_ready():
    client.add_view(VerifyView())
    print(f"🚀 บอทออนไลน์และพร้อมใช้งานในชื่อ: {client.user}")

# --- 3. คำสั่ง Slash Command (/setup) ---
@client.tree.command(name="setup", description="ส่งหน้าต่างระบบยืนยันตัวตนประจำเซิร์ฟเวอร์")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ **VERIFICATION SYSTEM**",
        description="กรุณากดปุ่ม **\"ยืนยันตัวตน\"** ด้านล่างนี้เพื่อปลดล็อกห้องแชทและเข้าถึงเนื้อหาทั้งหมดภายในเซิร์ฟเวอร์",
        color=discord.Color.from_rgb(88, 101, 242)
    )
    embed.set_image(url=BANNER_IMAGE)
    embed.set_footer(text="ระบบรักษาความปลอดภัยอัตโนมัติ", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

    # ตอบกลับคำสั่งแบบซ่อนข้อความชั่วคราวแล้วส่ง Embed ไปยังห้องนั้น
    await interaction.response.send_message("✅ สร้างระบบยืนยันตัวตนเรียบร้อยแล้ว!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=VerifyView())

# จัดการกรณีผู้ใช้ไม่มีสิทธิ์ใช้คำสั่งแอดมิน
@setup.error
async def setup_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้ (ต้องเป็น Administrator เท่านั้น)", ephemeral=True)
    else:
        await interaction.response.send_message("❌ เกิดข้อผิดพลาดบางประการ", ephemeral=True)

# ดึง Token จาก Environment Variables ของ Render
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ Error: ไม่พบ DISCORD_TOKEN ใน Environment Variables บน Render!")
else:
    client.run(TOKEN)
