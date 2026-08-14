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

# --- 2. ตั้งค่าบอท ---
intents = discord.Intents.default()
intents.members = True

class VerifyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("🔄 ซิงค์ Slash Commands เรียบร้อยแล้ว!")

client = VerifyBot()

# ⚙️ ตั้งค่า ID ยศของคุณที่นี่
VERIFY_ROLE_ID = 1537840114380709998

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # ให้ปุ่มกดได้ตลอดเวลา

    @discord.ui.button(
        label="ยืนยันตัวตน", 
        style=discord.ButtonStyle.green, 
        custom_id="verify_button_no_image", 
        emoji="✅"
    )
    async def verify_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        
        if not role:
            await interaction.response.send_message("❌ เกิดข้อผิดพลาด: ไม่พบยศนี้ในระบบเซิร์ฟเวอร์", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.response.send_message("⚠️ คุณได้ทำการยืนยันตัวตนไปเรียบร้อยแล้วครับ!", ephemeral=True)
        else:
            try:
                await interaction.user.add_roles(role)
                await interaction.response.send_message("🎉 **ยืนยันตัวตนสำเร็จ!** ยินดีต้อนรับเข้าสู่เซิร์ฟเวอร์ของเราครับ", ephemeral=True)
            except Exception:
                await interaction.response.send_message("❌ บอทไม่มีสิทธิ์ให้ยศ (กรุณาเลื่อนยศบอทไว้บนสุดในหน้าตั้งค่า Role)", ephemeral=True)

@client.event
async def on_ready():
    client.add_view(VerifyView())
    print(f"🚀 บอทออนไลน์ในชื่อ: {client.user}")

# --- 3. คำสั่ง /setup (แบบไม่มีรูปภาพ) ---
@client.tree.command(name="setup", description="ส่งระบบยืนยันตัวตนแบบข้อความสะอาด ไม่มีรูปภาพ")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ **VERIFICATION SYSTEM**",
        description="กรุณากดปุ่ม **\"✅ ยืนยันตัวตน\"** ด้านล่างนี้เพื่อปลดล็อกห้องแชทและเข้าถึงเนื้อหาทั้งหมดภายในเซิร์ฟเวอร์ครับ",
        color=discord.Color.from_rgb(88, 101, 242)
    )
    embed.set_footer(text="ระบบรักษาความปลอดภัยอัตโนมัติ")

    await interaction.response.send_message("✅ สร้างหน้าต่างยืนยันตัวตนเรียบร้อยแล้ว!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=VerifyView())

# ดึง Token จาก Environment Variables
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    client.run(TOKEN)
