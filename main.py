import os
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import discord
from discord.ext import commands
from discord import app_commands

# 📌 ระบุ ID เซิร์ฟเวอร์หลักของคุณที่นี่
MAIN_GUILD_ID = 1522224772258332792

# ==========================================
# 🌐 Web Server สำหรับ Render (กันบอทดับ)
# ==========================================
class AliveServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("🤖 Bot Active 24/7!".encode("utf-8"))

def run_alive_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("", port), AliveServer)
    server.serve_forever()

threading.Thread(target=run_alive_server, daemon=True).start()

# ==========================================
# 🤖 Bot Setup & Status เม็ดม่วง
# ==========================================
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================================
# 🔐 ระบบ Verification (Modal & View)
# ==========================================
class VerifyCodeModal(discord.ui.Modal, title="🔐 ยืนยันตัวตนด้วยรหัสผ่าน"):
    def __init__(self, correct_code: str, role_id: int):
        super().__init__()
        self.correct_code = correct_code
        self.role_id = role_id

        self.code_input = discord.ui.TextInput(
            label=f"🔢 พิมพ์รหัสผ่านนี้: {correct_code}",
            placeholder="กรอกตัวเลข 4 หลักตามที่เห็นข้างบน...",
            min_length=4,
            max_length=4,
            required=True
        )
        self.add_item(self.code_input)

    async def on_submit(self, interaction: discord.Interaction):
        if self.code_input.value.strip() == self.correct_code:
            role = interaction.guild.get_role(self.role_id)
            if role:
                try:
                    await interaction.user.add_roles(role)
                    embed = discord.Embed(
                        title="🎉 ยืนยันตัวตนสำเร็จ!",
                        description=f"ยินดีต้อนรับ {interaction.user.mention} ✨\nคุณได้รับยศ **{role.name}** เรียบร้อยแล้วครับ",
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except discord.Forbidden:
                    await interaction.response.send_message("❌ บอทมียศต่ำกว่ายศที่จะมอบ โปรดย้ายยศบอทขึ้นไปข้างบน", ephemeral=True)
            else:
                await interaction.response.send_message("❌ ไม่พบยศในระบบ", ephemeral=True)
        else:
            embed = discord.Embed(
                title="❌ รหัสผ่านไม่ถูกต้อง!",
                description="กรุณากดปุ่มเพื่อลองใหม่อีกครั้ง",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class PersistentVerifyView(discord.ui.View):
    def __init__(self, mode: str = "code", role_id: int = None):
        super().__init__(timeout=None)
        self.mode = mode
        self.role_id = role_id

    @discord.ui.button(label="กดเพื่อยืนยันตัวตน", style=discord.ButtonStyle.success, emoji="🛡️", custom_id="persistent_verify_btn")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_id_to_use = self.role_id
        current_mode = self.mode

        if not role_id_to_use and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            if embed.footer and embed.footer.text and "ROLE:" in embed.footer.text:
                try:
                    parts = embed.footer.text.split("|")
                    for p in parts:
                        if "ROLE:" in p:
                            role_id_to_use = int(p.replace("ROLE:", "").strip())
                        if "MODE:" in p:
                            current_mode = p.replace("MODE:", "").strip()
                except Exception:
                    pass

        if not role_id_to_use:
            return await interaction.response.send_message("❌ ไม่พบข้อมูลยศในการตั้งค่า", ephemeral=True)

        if current_mode == "button":
            role = interaction.guild.get_role(role_id_to_use)
            if role:
                if role in interaction.user.roles:
                    return await interaction.response.send_message("✨ คุณมียศนี้อยู่แล้วครับ!", ephemeral=True)
                try:
                    await interaction.user.add_roles(role)
                    embed = discord.Embed(
                        title="🎉 ยืนยันตัวตนสำเร็จ!",
                        description=f"ยินดีต้อนรับ {interaction.user.mention} ✨\nคุณได้รับยศ **{role.name}** เรียบร้อยแล้วครับ",
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except discord.Forbidden:
                    await interaction.response.send_message("❌ บอทมียศต่ำกว่ายศที่จะมอบ", ephemeral=True)
            else:
                await interaction.response.send_message("❌ ไม่พบยศในระบบ", ephemeral=True)
        else:
            generated_code = str(random.randint(1000, 9999))
            modal = VerifyCodeModal(correct_code=generated_code, role_id=role_id_to_use)
            await interaction.response.send_modal(modal)

# ==========================================
# 🟣 Bot Events (สถานะเม็ดม่วง)
# ==========================================
@bot.event
async def on_ready():
    print(f"✅ บอทออนไลน์แล้ว: {bot.user.name}")
    bot.add_view(PersistentVerifyView())
    
    # 🟣 ตั้งค่าสถานะเป็น "สตรีมมิ่ง" (เม็ดม่วง)
    await bot.change_presence(
        activity=discord.Streaming(
            name="🛡️ ระบบยืนยันตัวตนอัตโนมัติ 24/7",
            url="https://www.twitch.tv/discord"
        )
    )
    
    try:
        synced = await bot.tree.sync()
        print(f"✨ ซิงค์คำสั่งสำเร็จ: {len(synced)} คำสั่ง")
    except Exception as e:
        print(f"❌ ซิงค์คำสั่งล้มเหลว: {e}")

# ==========================================
# 📜 Command: ตั้งค่ายืนยันตัวตน
# ==========================================
@bot.tree.command(name="ตั้งค่า-ยืนยันตัวตน", description="🛡️ สร้างระบบยืนยันตัวตน (ปุ่มกดรับยศ หรือ สุ่มรหัส)")
@app_commands.describe(
    mode="รูปแบบ: button (กดรับยศทันที) หรือ code (กรอกรหัสสุ่ม 4 หลัก)",
    role="ยศที่จะมอบให้ผู้ใช้",
    title="หัวข้อข้อความประกาศ",
    description="เนื้อหาเพิ่มเติม (เว้นว่างได้)",
    image_url="รูปภาพประกอบ Embed (เว้นว่างได้)"
)
@app_commands.choices(mode=[
    app_commands.Choice(name="🔘 ปุ่มกดรับยศทันที (Button Mode)", value="button"),
    app_commands.Choice(name="🔐 กรอกรหัสสุ่ม 4 หลัก (Random Code Mode)", value="code")
])
@app_commands.default_permissions(administrator=True)
async def setup_verify(
    interaction: discord.Interaction, 
    mode: app_commands.Choice[str],
    role: discord.Role, 
    title: str, 
    description: str = None, 
    image_url: str = None
):
    if interaction.guild_id != MAIN_GUILD_ID:
        return await interaction.response.send_message("❌ อนุญาตเฉพาะเซิร์ฟเวอร์หลักเท่านั้น", ephemeral=True)

    if not description:
        if mode.value == "button":
            description = "กดปุ่ม **ยืนยันตัวตน** ด้านล่างเพื่อรับยศเข้าใช้งานเซิร์ฟเวอร์ได้ทันที ✨"
        else:
            description = "กดปุ่ม **ยืนยันตัวตน** ด้านล่างเพื่อรับรหัสผ่านสุ่ม 4 หลัก แล้วกรอกให้ถูกต้องเพื่อรับยศ ✨"

    embed = discord.Embed(
        title=title,
        description=f"{description}\n\n🎁 **ยศที่จะได้รับ:** {role.mention}",
        color=0x9B59B6
    )
    
    if image_url:
        embed.set_image(url=image_url)

    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
        
    embed.set_footer(text=f"Verification System | MODE:{mode.value} | ROLE:{role.id}", icon_url=bot.user.display_avatar.url)

    view = PersistentVerifyView(mode=mode.value, role_id=role.id)
    
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ สร้างระบบยืนยันตัวตนเรียบร้อยแล้ว!", ephemeral=True)

# ==========================================
# 🚀 Run Bot
# ==========================================
token = os.environ.get("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ ไม่พบ DISCORD_TOKEN ใน Environment Variables")
