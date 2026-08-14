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

# ตั้งค่า ID ยศ
VERIFY_ROLE_ID = 1537840114380709998

# 💡 เปลี่ยนมาใช้ลิงก์ภาพที่รองรับการแสดงผลบน Discord แน่นอน (หรือใช้วิธีอัปโหลดรูปเข้า Discord แล้วก๊อปปี้ลิงก์มาวางแทนที่ตรงนี้)
BANNER_IMAGE = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1000&auto=format&fit=crop"

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="ยืนยันตัวตน", style=discord.ButtonStyle.green, custom_id="verify_button_final_v4", emoji="✨")
    async def verify_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if not role:
            await interaction.response.send_message("❌ ไม่พบยศนี้ในเซิร์ฟเวอร์", ephemeral=True)
            return
        if role in interaction.user.roles:
            await interaction.response.send_message("⚠️ คุณยืนยันตัวตนไปแล้วครับ", ephemeral=True)
        else:
            try:
                await interaction.user.add_roles(role)
                await interaction.response.send_message("🎉 ยืนยันตัวตนสำเร็จแล้ว!", ephemeral=True)
            except:
                await interaction.response.send_message("❌ บอทไม่มีสิทธิ์ให้ยศ (เลื่อนยศบอทไว้บนสุดครับ)", ephemeral=True)

@client.event
async def on_ready():
    client.add_view(VerifyView())
    print(f"🚀 บอทออนไลน์ในชื่อ: {client.user}")

# --- 3. คำสั่ง /setup ---
@client.tree.command(name="setup", description="ส่งระบบยืนยันตัวตนพร้อมรูปภาพ")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ VERIFICATION SYSTEM",
        description="กรุณากดปุ่มด้านล่างเพื่อเข้าถึงเซิร์ฟเวอร์",
        color=0x5865F2
    )
    embed.set_image(url=BANNER_IMAGE)
    
    await interaction.response.send_message("✅ ส่งเรียบร้อยแล้ว", ephemeral=True)
    await interaction.channel.send(embed=embed, view=VerifyView())

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    client.run(TOKEN)
