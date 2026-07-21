import os
import json
import random
import re
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import discord
from discord.ext import commands
from discord import app_commands

MAIN_GUILD_ID = 1522224772258332792

class AliveServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("Bot is running!".encode("utf-8"))

def run_alive_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("", port), AliveServer)
    server.serve_forever()

threading.Thread(target=run_alive_server, daemon=True).start()

SETTINGS_FILE = "guild_settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

URL_REGEX = r"(https?://[^\s]+|discord\.gg/[^\s]+|discord\.com/invite/[^\s]+|www\.[^\s]+|[a-zA-Z0-0]+\.(com|net|org|gg|xyz|co|th|io|me))"

# ==========================================
# 🧩 Modal สำหรับโหมดกรอกรหัสสุ่ม 4 หลัก
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
        user_code = self.code_input.value.strip()

        if user_code == self.correct_code:
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
                description="กรุณากดปุ่มเพื่อรับรหัสผ่านใหม่แล้วลองอีกครั้ง",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

# ==========================================
# 🔘 View ปุ่มกดรองรับทั้ง 2 โหมด (Persistent)
# ==========================================
class PersistentVerifyView(discord.ui.View):
    def __init__(self, mode: str = "code", role_id: int = None):
        super().__init__(timeout=None)
        self.mode = mode
        self.role_id = role_id

    @discord.ui.button(label="กดเพื่อยืนยันตัวตน", style=discord.ButtonStyle.success, emoji="🛡️", custom_id="persistent_verify_btn")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ดึง Role ID และ Mode จาก Footer/Embed ข้อความหากถูกตั้งไว้
        role_id_to_use = self.role_id
        current_mode = self.mode

        if not role_id_to_use and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            if embed.footer and embed.footer.text:
                if "ROLE:" in embed.footer.text:
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

        # โหมดที่ 1: แบบกดปุ่มแล้วได้ยศทันที
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

        # โหมดที่ 2: แบบเด้ง Modal ให้กรอกรหัสสุ่ม 4 หลัก
        else:
            generated_code = str(random.randint(1000, 9999))
            modal = VerifyCodeModal(correct_code=generated_code, role_id=role_id_to_use)
            await interaction.response.send_modal(modal)

@bot.event
async def on_ready():
    print(f"✅ Online: {bot.user.name}")
    bot.add_view(PersistentVerifyView())
    try:
        synced = await bot.tree.sync()
        print(f"✨ Synced {len(synced)} commands")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    settings = load_settings()
    anti_link_enabled = settings.get("anti_link_enabled", True)

    if anti_link_enabled:
        if re.search(URL_REGEX, message.content, re.IGNORECASE):
            author = message.author
            is_admin = author.guild_permissions.administrator or author.guild_permissions.manage_messages
            user_roles_count = len([r for r in author.roles if not r.is_default()])

            if not is_admin and user_roles_count < 5:
                try:
                    await message.delete()
                    warn_msg = await message.channel.send(
                        f"⚠️ {author.mention} ห้ามส่งลิงก์! (ต้องมียศอย่างน้อย 5 ยศขึ้นไปจึงจะส่งลิงก์ได้)"
                    )
                    await asyncio.sleep(5)
                    await warn_msg.delete()
                except Exception:
                    pass
                return

    await bot.process_commands(message)

@bot.event
async def on_guild_join(guild: discord.Guild):
    settings = load_settings()
    log_channel_id = settings.get("bot_join_log_channel")

    if log_channel_id:
        log_channel = bot.get_channel(int(log_channel_id))
        if log_channel:
            owner_text = f"{guild.owner.name} ({guild.owner.mention})" if guild.owner else "ไม่พบข้อมูล"
            embed = discord.Embed(
                title="🎉 แจ้งเตือน: บอทเข้าเซิร์ฟเวอร์ใหม่",
                color=0x5865F2
            )
            embed.add_field(name="🏰 เซิร์ฟเวอร์", value=f"**{guild.name}**", inline=True)
            embed.add_field(name="🆔 Guild ID", value=f"`{guild.id}`", inline=True)
            embed.add_field(name="👑 เจ้าของ", value=owner_text, inline=False)
            embed.add_field(name="👥 สมาชิก", value=f"`{guild.member_count:,}` คน", inline=True)
            
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            embed.set_footer(text=f"🌐 รวมทั้งหมด: {len(bot.guilds)} เซิร์ฟเวอร์")
            
            try:
                await log_channel.send(embed=embed)
            except Exception:
                pass

@bot.event
async def on_member_join(member: discord.Member):
    settings = load_settings()
    auto_kick_enabled = settings.get("auto_kick_unverified", False)
    verify_role_id = settings.get("verify_role_id")

    if auto_kick_enabled and verify_role_id:
        await asyncio.sleep(600)
        
        guild = member.guild
        current_member = guild.get_member(member.id)
        
        if current_member:
            role = guild.get_role(int(verify_role_id))
            if role and role not in current_member.roles:
                try:
                    await current_member.kick(reason="ไม่อยืนยันตัวตนภายใน 10 นาที")
                    print(f"👢 Kicked {current_member.name} (Unverified)")
                except Exception as e:
                    print(f"❌ Failed to kick {current_member.name}: {e}")

@bot.tree.command(name="set-logchannel", description="🔔 ตั้งค่าช่องแจ้งเตือนการดึงบอท")
@app_commands.describe(channel="เลือกช่องข้อความ")
@app_commands.default_permissions(administrator=True)
async def set_logchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    if interaction.guild_id != MAIN_GUILD_ID:
        return await interaction.response.send_message("❌ อนุญาตเฉพาะเซิร์ฟเวอร์หลักเท่านั้น", ephemeral=True)

    settings = load_settings()
    settings["bot_join_log_channel"] = str(channel.id)
    save_settings(settings)

    embed = discord.Embed(
        title="✅ บันทึกสำเร็จ",
        description=f"ตั้งค่าช่องแจ้งเตือนเป็น {channel.mention}",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="toggle-autokick", description="⏱️ เปิด/ปิด ระบบเตะคนไม่อยืนยันตัวตนภายใน 10 นาที")
@app_commands.describe(status="เลือกเปิดหรือปิดระบบ", verify_role="เลือกยศยืนยันตัวตนเพื่อตรวจสอบ")
@app_commands.default_permissions(administrator=True)
async def toggle_autokick(interaction: discord.Interaction, status: bool, verify_role: discord.Role = None):
    if interaction.guild_id != MAIN_GUILD_ID:
        return await interaction.response.send_message("❌ อนุญาตเฉพาะเซิร์ฟเวอร์หลักเท่านั้น", ephemeral=True)

    settings = load_settings()
    settings["auto_kick_unverified"] = status
    if verify_role:
        settings["verify_role_id"] = str(verify_role.id)
    save_settings(settings)

    status_str = "🟢 เปิดใช้งาน" if status else "🔴 ปิดใช้งาน"
    role_str = f"\n🎯 ยศที่ใช้เช็ค: {verify_role.mention}" if verify_role else ""

    embed = discord.Embed(
        title="⚙️ ตั้งค่าระบบเตะเลท 10 นาที",
        description=f"สถานะปัจจุบัน: **{status_str}**{role_str}",
        color=discord.Color.green() if status else discord.Color.red()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="toggle-antilink", description="🚫 เปิด/ปิด ระบบป้องกันการส่งลิงก์")
@app_commands.describe(status="เลือกเปิดหรือปิดระบบห้ามส่งลิงก์")
@app_commands.default_permissions(administrator=True)
async def toggle_antilink(interaction: discord.Interaction, status: bool):
    if interaction.guild_id != MAIN_GUILD_ID:
        return await interaction.response.send_message("❌ อนุญาตเฉพาะเซิร์ฟเวอร์หลักเท่านั้น", ephemeral=True)

    settings = load_settings()
    settings["anti_link_enabled"] = status
    save_settings(settings)

    status_str = "🟢 เปิดใช้งาน (ห้ามส่งลิงก์ถ้ามีต่ำกว่า 5 ยศ)" if status else "🔴 ปิดใช้งาน (อนุญาตให้ส่งลิงก์ได้ทุกคน)"

    embed = discord.Embed(
        title="⚙️ ตั้งค่าระบบป้องกันลิงก์",
        description=f"สถานะปัจจุบัน: **{status_str}**",
        color=discord.Color.green() if status else discord.Color.red()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setup-military-roles", description="🎖️ สร้างบทบาท/ยศทหารเรียงตามลำดับชั้นอัตโนมัติ")
@app_commands.default_permissions(administrator=True)
async def setup_military_roles(interaction: discord.Interaction):
    if interaction.guild_id != MAIN_GUILD_ID:
        return await interaction.response.send_message("❌ อนุญาตเฉพาะเซิร์ฟเวอร์หลักเท่านั้น", ephemeral=True)

    await interaction.response.defer(ephemeral=True)

    military_roles = [
        ("🎖️ จอมพล (Field Marshal)", discord.Color.from_rgb(180, 0, 0)),
        ("⭐ พลเอก (General)", discord.Color.from_rgb(220, 20, 60)),
        ("⭐⭐ พลโท (Lieutenant General)", discord.Color.from_rgb(255, 69, 0)),
        ("⭐⭐⭐ พลตรี (Major General)", discord.Color.from_rgb(255, 140, 0)),
        ("🦅 พันเอก (Colonel)", discord.Color.from_rgb(218, 165, 32)),
        ("🦅 พันโท (Lieutenant Colonel)", discord.Color.from_rgb(184, 134, 11)),
        ("🦅 พันตรี (Major)", discord.Color.from_rgb(204, 204, 0)),
        ("⚔️ ร้อยเอก (Captain)", discord.Color.from_rgb(60, 179, 113)),
        ("⚔️ ร้อยโท (First Lieutenant)", discord.Color.from_rgb(46, 139, 87)),
        ("⚔️ ร้อยตรี (Second Lieutenant)", discord.Color.from_rgb(32, 178, 170)),
        ("🛡️ จ่าสิบเอก (Master Sergeant)", discord.Color.from_rgb(70, 130, 180)),
        ("🛡️ สิบเอก (Sergeant)", discord.Color.from_rgb(100, 149, 237)),
        ("🪖 พลทหาร (Private)", discord.Color.from_rgb(128, 128, 128))
    ]

    created_roles = []
    guild = interaction.guild

    for name, color in reversed(military_roles):
        existing_role = discord.utils.get(guild.roles, name=name)
        if not existing_role:
            try:
                role = await guild.create_role(
                    name=name,
                    color=color,
                    hoist=True,
                    mentionable=True,
                    reason="สร้างยศทหารอัตโนมัติ"
                )
                created_roles.append(role.name)
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"❌ Failed to create role {name}: {e}")

    embed = discord.Embed(
        title="🎖️ สร้างยศทหารเรียบร้อยแล้ว",
        description=f"สร้างยศทั้งหมด **{len(created_roles)}** ยศเรียงตามลำดับชั้นเรียบร้อยครับ",
        color=discord.Color.gold()
    )
    await interaction.followup.send(embed=embed, ephemeral=True)

# ==========================================
# 🛡️ คำสั่ง /setup-verify (เลือกโหมดได้)
# ==========================================
@bot.tree.command(name="setup-verify", description="🛡️ สร้างระบบยืนยันตัวตน (เลือกโหมดปุ่มกด หรือ กรอกรหัสสุ่มได้)")
@app_commands.describe(
    mode="เลือกโหมด: button (กดปุ่มได้ยศเลย) หรือ code (กดแล้วกรอกรหัสสุ่ม 4 หลัก)",
    role="เลือกยศที่จะแจกเมื่อยืนยันสำเร็จ",
    title="หัวข้อประกาศ",
    description="รายละเอียดข้อความ (เว้นไว้ได้)",
    image_url="ลิงก์รูปภาพประกอบ (เว้นไว้ได้)"
)
@app_commands.choices(mode=[
    app_commands.Choice(name="🔘 ปุ่มกดได้ยศเลย (Button)", value="button"),
    app_commands.Choice(name="🔐 กรอกรหัสสุ่ม 4 หลัก (Random Code)", value="code")
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
        color=0x2b2d31
    )
    
    if image_url:
        embed.set_image(url=image_url)

    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
        
    embed.set_footer(text=f"Verification System | MODE:{mode.value} | ROLE:{role.id}", icon_url=bot.user.display_avatar.url)

    view = PersistentVerifyView(mode=mode.value, role_id=role.id)
    
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ สร้างระบบยืนยันตัวตนแบบ **{mode.name}** เรียบร้อยแล้ว!", ephemeral=True)

@bot.tree.command(name="clear", description="🧹 ลบข้อความ")
@app_commands.describe(amount="จำนวนข้อความ 1-100")
@app_commands.default_permissions(manage_messages=True)
async def clear_messages(interaction: discord.Interaction, amount: int):
    if amount < 1 or amount > 100:
        return await interaction.response.send_message("❌ ระบุ 1-100 เท่านั้น", ephemeral=True)

    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    
    embed = discord.Embed(
        title="🧹 ลบเรียบร้อย",
        description=f"ลบไปทั้งหมด **{len(deleted)}** ข้อความ",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=embed, ephemeral=True)

token = os.environ.get("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ ไม่พบ DISCORD_TOKEN")
