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
intents.message_content = True

class VerifyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("🔄 ซิงค์ Slash Commands เรียบร้อยแล้ว!")

client = VerifyBot()

# ⚙️ ID ยศยืนยันตัวตนของคุณ
VERIFY_ROLE_ID = 1537840114380709998

# --- 3. ระบบปุ่มยืนยันตัวตน ---
class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ ยืนยันตัวตน", style=discord.ButtonStyle.green, custom_id="verify_button_all_in_one")
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
                await interaction.response.send_message("❌ บอทไม่มีสิทธิ์ให้ยศ (กรุณาเลื่อนยศบอทไว้บนสุด)", ephemeral=True)

@client.event
async def on_ready():
    client.add_view(VerifyView())
    print(f"🚀 บอทออนไลน์ในชื่อ: {client.user}")

# --- 4. คำสั่ง Slash Commands ---

# คำสั่ง /setup (ส่งปุ่มยืนยันตัวตน)
@client.tree.command(name="setup", description="ส่งระบบยืนยันตัวตนแบบปุ่มกด")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ VERIFICATION SYSTEM",
        description="กรุณากดปุ่ม **\"✅ ยืนยันตัวตน\"** ด้านล่างนี้เพื่อปลดล็อกเซิร์ฟเวอร์",
        color=0x5865F2
    )
    embed.set_footer(text="ระบบรักษาความปลอดภัยอัตโนมัติ")
    
    await interaction.response.send_message("✅ สร้างระบบยืนยันตัวตนเรียบร้อยแล้ว", ephemeral=True)
    await interaction.channel.send(embed=embed, view=VerifyView())

# คำสั่ง /announce (ประกาศแท็กทุกคน)
@client.tree.command(name="announce", description="ประกาศข้อความและแท็กทุกคนในเซิร์ฟเวอร์")
@app_commands.describe(message="ข้อความที่ต้องการประกาศ")
@app_commands.checks.has_permissions(administrator=True)
async def announce(interaction: discord.Interaction, message: str):
    await interaction.response.send_message("📢 ประกาศเรียบร้อยแล้ว", ephemeral=True)
    await interaction.channel.send(f"@everyone \n\n📢 **ประกาศจากแอดมิน:**\n{message}")

# คำสั่ง /dm (ส่งข้อความส่วนตัวหาบุคคล)
@client.tree.command(name="dm", description="ส่งข้อความส่วนตัวหาผู้ใช้ที่ระบุ")
@app_commands.describe(member="เลือกสมาชิกที่ต้องการส่ง", message="ข้อความที่ต้องการส่ง")
@app_commands.checks.has_permissions(administrator=True)
async def dm(interaction: discord.Interaction, member: discord.Member, message: str):
    try:
        await member.send(f"📢 **ข้อความส่วนตัวจากแอดมิน:**\n{message}")
        await interaction.response.send_message(f"✅ ส่งข้อความส่วนตัวหา {member.mention} เรียบร้อยแล้ว", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ ไม่สามารถส่งข้อความหา {member.name} ได้ (ผู้ใช้ปิดรับ DM)", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)

# ดึง Token จาก Environment Variables บน Render
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    client.run(TOKEN)
