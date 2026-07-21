import os
import json
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import discord
from discord.ext import commands
from discord import app_commands

# ==========================================
# ⚙️ ตั้งค่าไอดีเซิร์ฟเวอร์หลัก (ADMIN SERVER ID)
# ==========================================
MAIN_GUILD_ID = 1529136414715809893  # ล็อกสิทธิ์เฉพาะเซิร์ฟเวอร์หลักเท่านั้น

# ==========================================
# 🟢 1. Web Server หลอกพอร์ตสำหรับ Render Free
# ==========================================
class AliveServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("🤖 บอททำงานปกติพร้อมใช้งาน!".encode("utf-8"))

def run_alive_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("", port), AliveServer)
    server.serve_forever()

threading.Thread(target=run_alive_server, daemon=True).start()

# ==========================================
# 📁 2. ระบบบันทึกและโหลดข้อมูลการตั้งค่า (JSON Storage)
# ==========================================
SETTINGS_FILE = "guild_settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ โหลดข้อมูลการตั้งค่าไม่สำเร็จ: {e}")
            return {}
    return {}

def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ บันทึกข้อมูลการตั้งค่าไม่สำเร็จ: {e}")

# ==========================================
# 🤖 3. ตั้งค่าระบบ Discord Bot
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------------------------------
# 🧩 Modal (หน้าต่าง Pop-up กรอกตัวเลข 4 หลัก)
# ------------------------------------------
class VerifyModal(discord.ui.Modal, title="🔐 ยืนยันตัวตนความปลอดภัย"):
    def __init__(self, correct_code: str, role_id: int):
        super().__init__()
        self.correct_code = correct_code
        self.role_id = role_id

        self.code_input = discord.ui.TextInput(
            label=f"🔢 รหัสผ่านของคุณคือ: {correct_code}",
            placeholder="โปรดพิมพ์ตัวเลข 4 หลักด้านบนให้ถูกต้อง...",
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
                        description=f"ยินดีต้อนรับคุณ {interaction.user.mention} ✨\nคุณได้รับยศ **{role.name}** เรียบร้อยแล้วครับ!",
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except discord.Forbidden:
                    await interaction.response.send_message("❌ บอทมียศต่ำกว่ายศที่ต้องการแจก โปรดย้ายยศของบอทให้อยู่สูงกว่ายศนี้ครับ", ephemeral=True)
            else:
                await interaction.response.send_message("❌ ไม่พบยศนี้ในเซิร์ฟเวอร์", ephemeral=True)
        else:
            embed = discord.Embed(
                title="❌ รหัสผ่านไม่ถูกต้อง!",
                description="กรุณากดปุ่มเพื่อรับรหัสผ่านใหม่แล้วลองใหม่อีกครั้งครับ 🔄",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

# ------------------------------------------
# 🔘 View แบบถาวร (Persistent View)
# ------------------------------------------
class PersistentVerifyView(discord.ui.View):
    def __init__(self, role_id: int = None):
        super().__init__(timeout=None)
        self.role_id = role_id

    @discord.ui.button(label="กดเพื่อยืนยันตัวตน", style=discord.ButtonStyle.success, emoji="🛡️", custom_id="persistent_verify_button")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_id_to_use = self.role_id
        
        if not role_id_to_use:
            try:
                embed_desc = interaction.message.embeds[0].description
                if "<@&" in embed_desc:
                    role_id_to_use = int(embed_desc.split("<@&")[1].split(">")[0])
            except Exception:
                role_id_to_use = None

        if not role_id_to_use:
            return await interaction.response.send_message("❌ เกิดข้อผิดพลาดในการค้นหาข้อมูลยศ กรุณาสร้างระบบ Verify ใหม่อีกครั้งครับ", ephemeral=True)

        generated_code = str(random.randint(1000, 9999))
        modal = VerifyModal(correct_code=generated_code, role_id=role_id_to_use)
        await interaction.response.send_modal(modal)

# ==========================================
# ⚙️ 4. Events & Slash Commands
# ==========================================
@bot.event
async def on_ready():
    print(f"✅ บอท {bot.user.name} ออนไลน์และพร้อมทำงานแล้ว!")
    bot.add_view(PersistentVerifyView())
    try:
        synced = await bot.tree.sync()
        print(f"✨ ซิงค์คำสั่ง Slash Commands เรียบร้อยแล้ว ({len(synced)} คำสั่ง)")
    except Exception as e:
        print(f"❌ ซิงค์คำสั่งไม่สำเร็จ: {e}")

# --- 📢 ระบบแจ้งเตือนเมื่อบอทถูกดึงเข้าเซิร์ฟเวอร์ใหม่ ---
@bot.event
async def on_guild_join(guild: discord.Guild):
    settings = load_settings()
    log_channel_id = settings.get("bot_join_log_channel")

    if log_channel_id:
        log_channel = bot.get_channel(int(log_channel_id))
        if log_channel:
            owner_text = f"{guild.owner.name} ({guild.owner.mention})" if guild.owner else "ไม่พบข้อมูลเจ้าของ"
            
            embed = discord.Embed(
                title="🎉 แจ้งเตือน: มีการเชิญบอทเข้าเซิร์ฟเวอร์ใหม่!",
                color=0x5865F2
            )
            embed.add_field(name="🏰 ชื่อเซิร์ฟเวอร์", value=f"**{guild.name}**", inline=True)
            embed.add_field(name="🆔 ไอดีเซิร์ฟเวอร์", value=f"`{guild.id}`", inline=True)
            embed.add_field(name="👑 เจ้าของเซิร์ฟเวอร์", value=owner_text, inline=False)
            embed.add_field(name="👥 จำนวนสมาชิก", value=f"`{guild.member_count:,}` คน", inline=True)
            
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            
            embed.set_footer(text=f"🌐 เซิร์ฟเวอร์ทั้งหมดที่บอทอยู่ตอนนี้: {len(bot.guilds)} เซิร์ฟเวอร์")
            
            try:
                await log_channel.send(embed=embed)
            except Exception as e:
                print(f"⚠️ ไม่สามารถส่งข้อความแจ้งเตือน Log ได้: {e}")

# --- 1. คำสั่ง /ตั้งค่าห้องแจ้งเตือน (จำกัดเฉพาะเซิร์ฟเวอร์หลัก) ---
@bot.tree.command(name="set-logchannel", description="🔔 กำหนดช่องสำหรับรับแจ้งเตือนเมื่อบอทถูกดึงเข้าเซิร์ฟเวอร์ (เฉพาะผู้พัฒนา)")
@app_commands.describe(channel="เลือกช่องข้อความที่ต้องการให้บอทส่งการแจ้งเตือน")
@app_commands.default_permissions(administrator=True)
async def set_logchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    if interaction.guild_id != MAIN_GUILD_ID:
        return await interaction.response.send_message("❌ คำสั่งนี้อนุญาตให้ใช้งานได้เฉพาะเซิร์ฟเวอร์หลักเท่านั้นครับ 🔒", ephemeral=True)

    settings = load_settings()
    settings["bot_join_log_channel"] = str(channel.id)
    settings["main_guild_id"] = str(interaction.guild_id)
    save_settings(settings)

    embed = discord.Embed(
        title="✅ บันทึกการตั้งค่าสำเร็จ!",
        description=(
            f"📌 **เซิร์ฟเวอร์:** {interaction.guild.name} (`{interaction.guild_id}`)\n"
            f"📢 **ช่องแจ้งเตือน:** {channel.mention} (`{channel.id}`)\n\n"
            "💾 ระบบทำการบันทึกข้อมูลถาวรเรียบร้อยแล้ว แม้รีสตาร์ทบอทข้อมูลจะไม่หายครับ ✨"
        ),
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- 2. คำสั่ง /ตรวจสอบการตั้งค่า ---
@bot.tree.command(name="check-config", description="⚙️ ตรวจสอบช่องรับแจ้งเตือนบอทในปัจจุบัน")
@app_commands.default_permissions(administrator=True)
async def check_config(interaction: discord.Interaction):
    if interaction.guild_id != MAIN_GUILD_ID:
        return await interaction.response.send_message("❌ คำสั่งนี้อนุญาตให้ใช้งานได้เฉพาะเซิร์ฟเวอร์หลักเท่านั้นครับ 🔒", ephemeral=True)

    settings = load_settings()
    log_channel_id = settings.get("bot_join_log_channel")
    
    if log_channel_id:
        ch = bot.get_channel(int(log_channel_id))
        ch_text = ch.mention if ch else f"ID: `{log_channel_id}` (ไม่พบช่องข้อความ)"
        
        embed = discord.Embed(
            title="⚙️ ตรวจสอบการตั้งค่าระบบปัจจุบัน",
            description=f"📢 **ช่องรับแจ้งเตือน Log:** {ch_text}",
            color=discord.Color.blue()
        )
    else:
        embed = discord.Embed(
            title="⚙️ ตรวจสอบการตั้งค่าระบบปัจจุบัน",
            description="⚠️ ยังไม่ได้ตั้งค่าช่องรับแจ้งเตือน (สามารถตั้งค่าด้วยคำสั่ง `/set-logchannel`)",
            color=discord.Color.gold()
        )
        
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- 3. คำสั่ง /สร้างระบบยืนยันตัวตน ---
@bot.tree.command(name="setup-verify", description="🛡️ สร้างกล่องยืนยันตัวตนพร้อมปุ่มกด (บันทึกถาวร)")
@app_commands.describe(
    role="เลือกยศที่จะแจกเมื่อยืนยันตัวตนสำเร็จ (จำเป็น)",
    title="หัวข้อข้อความประกาศ (จำเป็น)",
    description="ข้อความอธิบายรายละเอียด (ไม่ใส่ใช้ค่าเริ่มต้น)",
    image_url="ลิงก์รูปภาพประกอบ Embed (ใส่หรือไม่ใส่ก็ได้)"
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
            "กรุณากดปุ่ม **ยืนยันตัวตน** ด้านล่างเพื่อรับรหัสผ่าน 4 หลัก\n"
            "จากนั้นนำรหัสมากรอกให้ถูกต้อง เพื่อเข้าใช้งานห้องต่างๆ ในเซิร์ฟเวอร์ครับ ✨"
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
        
    embed.set_footer(text="🛡️ Verification System • ระบบยืนยันตัวตนอัตโนมัติ", icon_url=bot.user.display_avatar.url)

    view = PersistentVerifyView(role_id=role.id)
    
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ สร้างกล่องยืนยันตัวตนเรียบร้อยแล้วครับ!", ephemeral=True)

# --- 4. คำสั่ง /ลบข้อความ ---
@bot.tree.command(name="clear", description="🧹 ลบข้อความในช่องปัจจุบันตามจำนวนที่กำหนด")
@app_commands.describe(amount="จำนวนข้อความที่ต้องการลบ (ระบุ 1-100)")
@app_commands.default_permissions(manage_messages=True)
async def clear_messages(interaction: discord.Interaction, amount: int):
    if amount < 1 or amount > 100:
        return await interaction.response.send_message("❌ กรุณาระบุจำนวนข้อความระหว่าง 1 ถึง 100 ข้อความครับ ⚠️", ephemeral=True)

    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    
    embed = discord.Embed(
        title="🧹 ลบข้อความเรียบร้อยแล้ว!",
        description=f"ลบข้อความในช่องนี้ไปทั้งหมด **{len(deleted)}** ข้อความ ✨",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=embed, ephemeral=True)

# ==========================================
# 🚀 5. เริ่มต้นรันบอท
# ==========================================
token = os.environ.get("DISCORD_TOKEN")

if token:
    bot.run(token)
else:
    print("❌ ไม่พบ DISCORD_TOKEN ใน Environment Variables")
