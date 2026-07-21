import os
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import discord
from discord.ext import commands
from discord import app_commands

# ==========================================
# 🟢 1. Web Server หลอกพอร์ตสำหรับ Render Free
# ==========================================
class AliveServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Verification Bot is Online!")

def run_alive_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("", port), AliveServer)
    server.serve_forever()

threading.Thread(target=run_alive_server, daemon=True).start()

# ==========================================
# 🤖 2. ตั้งค่าระบบ Discord Bot
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------------------------------
# 🧩 Modal (หน้าต่าง Pop-up กรอกตัวเลข 4 หลัก)
# ------------------------------------------
class VerifyModal(discord.ui.Modal, title="🔒 กรอกรหัสเพื่อยืนยันตัวตน"):
    def __init__(self, correct_code: str, role_id: int):
        super().__init__()
        self.correct_code = correct_code
        self.role_id = role_id

        self.code_input = discord.ui.TextInput(
            label=f"กรอกรหัส 4 หลักนี้: [{correct_code}]",
            placeholder="พิมพ์ตัวเลข 4 หลักที่เห็นให้ถูกต้อง...",
            min_length=4,
            max_length=4,
            required=True
        )
        self.add_item(self.code_input)

    async def on_submit(self, interaction: discord.Interaction):
        user_code = self.code_input.value.strip()

        if user_code == self.correct_code:
            role = interaction.guild.get_role(self.role_id)
            if role:
                try:
                    await interaction.user.add_roles(role)
                    embed = discord.Embed(
                        title="🎉 ยืนยันตัวตนสำเร็จ!",
                        description=f"คุณ {interaction.user.mention} ได้รับยศ **{role.name}** เรียบร้อยแล้ว",
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except discord.Forbidden:
                    await interaction.response.send_message("❌ บอทไม่มียศสูงพอที่จะแจกยศนี้ได้ (ย้ายยศบอทให้อยู่เหนือยศที่จะแจก)", ephemeral=True)
            else:
                await interaction.response.send_message("❌ ไม่พบยศนี้ในระบบ", ephemeral=True)
        else:
            embed = discord.Embed(
                title="❌ รหัสไม่ถูกต้อง",
                description="กรุณากดปุ่มแล้วลองใหม่อีกครั้งครับ",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

# ------------------------------------------
# 🔘 View (ปุ่มกด Verify)
# ------------------------------------------
class VerifyView(discord.ui.View):
    def __init__(self, role_id: int):
        super().__init__(timeout=None)
        self.role_id = role_id

    @discord.ui.button(label="ยืนยันตัวตน (Verify)", style=discord.ButtonStyle.success, emoji="🛡️", custom_id="verify_btn_custom")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        generated_code = str(random.randint(1000, 9999))
        modal = VerifyModal(correct_code=generated_code, role_id=self.role_id)
        await interaction.response.send_modal(modal)

# ==========================================
# ⚙️ 3. Slash Commands
# ==========================================
@bot.event
async def on_ready():
    print(f"✅ บอทออนไลน์แล้ว: {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"✨ ซิงค์ Slash Commands สำเร็จ ({len(synced)} คำสั่ง)")
    except Exception as e:
        print(f"❌ ซิงค์คำสั่งไม่สำเร็จ: {e}")

# --- 1. คำสั่ง /setup-verify ---
@bot.tree.command(name="setup-verify", description="สร้างกล่องยืนยันตัวตนแบบกำหนดเอง")
@app_commands.describe(
    role="เลือกยศที่จะแจก (บังคับ)",
    title="หัวข้อของกล่องข้อความ (บังคับ)",
    description="รายละเอียดคำอธิบาย (ไม่บังคับ)",
    image_url="ลิงก์รูปภาพประกอบ Embed (ไม่บังคับ)"
)
@app_commands.default_permissions(administrator=True)
async def setup_verify(
    interaction: discord.Interaction, 
    role: discord.Role, 
    title: str, 
    description: str = None, 
    image_url: str = None
):
    if not description:
        description = (
            "กรุณากดปุ่มด้านล่างเพื่อรับรหัสผ่าน 4 หลัก\n"
            "แล้วกรอกให้ถูกต้องภายใน **3 นาที** เพื่อรับยศเข้าใช้งานห้องต่างๆ"
        )

    embed = discord.Embed(
        title=title,
        description=f"{description}\n\n🎁 **ยศที่จะได้รับ:** {role.mention}",
        color=0x2b2d31
    )
    
    if image_url:
        embed.set_image(url=image_url)

    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
        
    embed.set_footer(text="Security System • ระบบยืนยันตัวตนอัตโนมัติ", icon_url=bot.user.display_avatar.url)

    view = VerifyView(role_id=role.id)
    
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ สร้างกล่องยืนยันตัวตนเรียบร้อยแล้ว!", ephemeral=True)


# --- 2. คำสั่ง /clear (ลบข้อความ) ---
@bot.tree.command(name="clear", description="ลบข้อความในช่องปัจจุบันตามจำนวนที่กำหนด")
@app_commands.describe(amount="จำนวนข้อความที่ต้องการลบ (เช่น 1-100)")
@app_commands.default_permissions(manage_messages=True)
async def clear_messages(interaction: discord.Interaction, amount: int):
    if amount < 1 or amount > 100:
        return await interaction.response.send_message("❌ กรุณาระบุจำนวนข้อความระหว่าง 1 ถึง 100 ข้อความครับ", ephemeral=True)

    # ส่งการตอบรับเบื้องหลังก่อนเพื่อป้องกันเวลาลบเกิน 3 วินาทีแล้วขึ้น Error
    await interaction.response.defer(ephemeral=True)
    
    deleted = await interaction.channel.purge(limit=amount)
    
    embed = discord.Embed(
        title="🧹 ลบข้อความเรียบร้อยแล้ว",
        description=f"ลบข้อความในช่องนี้ไปทั้งหมด **{len(deleted)}** ข้อความ",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=embed, ephemeral=True)

# ==========================================
# 🚀 4. เริ่มต้นรันบอท
# ==========================================
token = os.environ.get("DISCORD_TOKEN")

if token:
    bot.run(token)
else:
    print("❌ ไม่พบ DISCORD_TOKEN")
