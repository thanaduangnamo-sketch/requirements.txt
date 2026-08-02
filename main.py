import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import aiohttp
from flask import Flask
from threading import Thread
import asyncio

# ==========================================
# 🌐 ระบบเปิดเว็บจำลอง (Keep-Alive) สำหรับรัน 24 ชม.
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Aegis Bot System is running!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==========================================
# ⚙️ ตั้งค่าพื้นฐานของบอท
# ==========================================
token = os.environ.get("DISCORD_TOKEN") # ดึง Token จาก Environment Variables

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.moderation = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ตัวแปรจำลองสำหรับเก็บยศ (User ID -> List of Role IDs)
user_saved_roles = {}


# ==========================================
# 🛡️ 1. ระบบเซฟและคืนยศ (Save & Restore Roles)
# ==========================================
class SaveRestoreRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="เซฟยศของฉัน", style=discord.ButtonStyle.primary, emoji="🛡️", custom_id="aegis_save_role:button")
    async def save_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        guild = interaction.guild
        roles_to_save = [role.id for role in user.roles if role != guild.default_role and guild.me.top_role > role]
        user_saved_roles[user.id] = roles_to_save
        
        embed = discord.Embed(
            title="🛡️ สำเร็จ — บันทึกยศเรียบร้อย",
            description=f"✅ ทำการเซฟยศทั้งหมดของคุณจำนวน **{len(roles_to_save)} ยศ** เรียบร้อยแล้วครับ!",
            color=0xf1c40f
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="คืนยศของฉัน", style=discord.ButtonStyle.danger, emoji="🛠️", custom_id="aegis_restore_role:button")
    async def restore_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        guild = interaction.guild

        if user.id not in user_saved_roles or not user_saved_roles[user.id]:
            return await interaction.response.send_message("❌ ไม่พบข้อมูลการเซฟยศของคุณในระบบ กรุณากด 'เซฟยศของฉัน' ก่อนครับ", ephemeral=True)

        saved_role_ids = user_saved_roles[user.id]
        roles_to_add = [guild.get_role(r_id) for r_id in saved_role_ids if guild.get_role(r_id) and guild.me.top_role > guild.get_role(r_id)]

        try:
            await user.add_roles(*roles_to_add)
            embed = discord.Embed(
                title="🛠️ สำเร็จ — คืนยศเรียบร้อย",
                description=f"✅ ทำการคืนยศให้คุณสำเร็จจำนวน **{len(roles_to_add)} ยศ** เรียบร้อยแล้วครับ!",
                color=0xf1c40f
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ เกิดข้อผิดพลาดในการคืนยศ: {e}", ephemeral=True)

    @discord.ui.button(label="โปรไฟล์ของฉัน", style=discord.ButtonStyle.secondary, emoji="👤", custom_id="aegis_profile_role:button")
    async def profile_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        guild = interaction.guild
        saved_ids = user_saved_roles.get(user.id, [])
        saved_role_names = [guild.get_role(r_id).name for r_id in saved_ids if guild.get_role(r_id)]
        current_roles = [r.name for r in user.roles if r != guild.default_role]

        embed = discord.Embed(
            title=f"👤 โปรไฟล์ข้อมูลยศของ: {user.name}",
            description=(
                f"🛡️ **ยศที่เซฟไว้ในระบบ:** `{len(saved_ids)} ยศ`\n"
                f"📋 รายชื่อยศที่เซฟ: {', '.join(saved_role_names) if saved_role_names else 'ยังไม่มีการเซฟ'}\n\n"
                f"🏷️ **ยศปัจจุบันที่มี:** `{len(current_roles)} ยศ`\n"
                f"📋 รายชื่อยศปัจจุบัน: {', '.join(current_roles) if current_roles else 'ไม่มี'}"
            ),
            color=0xf1c40f
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="เซฟยศ", description="สร้างระบบปุ่มกดเซฟและคืนยศอัตโนมัติ")
@app_commands.describe(ลิงก์รูปภาพ="ใส่ลิงก์รูปภาพแบนเนอร์ (ไม่บังคับ)")
async def setup_saveroles_command(interaction: discord.Interaction, ลิงก์รูปภาพ: str = "https://i.pinimg.com/736x/14/68/59/146859926bd33323535af3b8697b024d.jpg"):
    embed = discord.Embed(
        title="🛡️ ระบบเซฟและคืนยศ",
        description="กดปุ่มด้านล่างเพื่อจัดการยศของคุณได้เลย!\n\n> 🛡️ **เซฟยศ** — บันทึกยศทั้งหมด\n> 🛠️ **คืนยศ** — กู้คืนยศที่เคยเซฟไว้\n> 👤 **โปรไฟล์** — ตรวจสอบข้อมูลยศ",
        color=0xf1c40f
    )
    embed.set_image(url=ลิงก์รูปภาพ)
    await interaction.channel.send(embed=embed, view=SaveRestoreRoleView())
    await interaction.response.send_message("✅ สร้างหน้าต่างระบบเซฟและคืนยศเรียบร้อย", ephemeral=True)


# ==========================================
# 🟩 2. ระบบรับยศทั่วไป
# ==========================================
class GeneralRoleView(discord.ui.View):
    def __init__(self, role_id: int):
        super().__init__(timeout=None)
        self.role_id = role_id

    @discord.ui.button(label="【 ☁️ กดเพื่อรับ/คืนยศ 】", style=discord.ButtonStyle.primary, emoji="🔵", custom_id="general_role_button:dynamic")
    async def toggle_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(self.role_id)
        if not role: return await interaction.response.send_message("❌ ไม่พบยศนี้", ephemeral=True)
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"🗑️ คืนยศ **{role.name}** เรียบร้อย", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"✅ ได้รับยศ **{role.name}** เรียบร้อย", ephemeral=True)

@bot.tree.command(name="รับยศ", description="สร้างระบบรับยศปุ่มกด")
async def setup_roles_command(interaction: discord.Interaction, เลือกยศ: discord.Role):
    embed = discord.Embed(
        title="💬 Aegis Bot — ระบบรับยศทั่วไป",
        description=f"🔵 : กดปุ่มด้านล่างเพื่อรับ/คืนยศ **{เลือกยศ.name}**",
        color=0x2b2d31
    )
    await interaction.channel.send(embed=embed, view=GeneralRoleView(เลือกยศ.id))
    await interaction.response.send_message(f"✅ สร้างปุ่มรับยศ **{เลือกยศ.name}** เรียบร้อย", ephemeral=True)


# ==========================================
# 🌐 3. ระบบแปลภาษา (Translate)
# ==========================================
class TranslateModal(discord.ui.Modal, title="🌐 ระบบแปลภาษาอัตโนมัติ"):
    text_input = discord.ui.TextInput(label="ข้อความที่ต้องการแปล", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        original_text = self.text_input.value.strip()
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=th&dt=t&q={original_text}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                res_json = await resp.json()
                translated_text = "".join([item[0] for item in res_json[0]])
                detected_lang = res_json[2].upper()
        embed = discord.Embed(title="🌐 ผลการแปลภาษา", color=0x2ecc71)
        embed.add_field(name="📝 ต้นฉบับ", value=f"```{original_text}```", inline=False)
        embed.add_field(name=f"✨ ภาษาไทย (จาก: {detected_lang})", value=f"```{translated_text}```", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

class TranslateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="แปลภาษา", style=discord.ButtonStyle.success, emoji="🌐", custom_id="aegis_translate:button")
    async def open_translate(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TranslateModal())

@bot.tree.command(name="แปลภาษา", description="เปิดหน้าต่างระบบแปลภาษา")
async def translate_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🌐 TRANSLATE SYSTEM", description="กดปุ่มด้านล่างเพื่อแปลภาษาใดก็ได้เป็นภาษาไทย", color=0x2ecc71)
    await interaction.channel.send(embed=embed, view=TranslateView())
    await interaction.response.send_message("✅ ส่งหน้าต่างแปลภาษาเรียบร้อย", ephemeral=True)


# ==========================================
# 🔍 4. ระบบ TOKEN CHECKER
# ==========================================
class TokenModal(discord.ui.Modal, title="TOKEN CHECKER"):
    token_input = discord.ui.TextInput(label="กรอก Discord Token", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        headers = {"Authorization": self.token_input.value.strip(), "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.get("https://discord.com/api/v9/users/@me", headers=headers) as resp:
                if resp.status != 200:
                    return await interaction.followup.send("❌ Token ไม่ถูกต้องหรือหมดอายุ", ephemeral=True)
                data = await resp.json()
        
        embed = discord.Embed(title="✨ TOKEN CHECKER RESULT ✨", description="ส่งผลลัพธ์ให้คุณเท่านั้น (DM)", color=0xe74c3c)
        embed.add_field(name="🏷️ ผู้ใช้", value=f"`{data.get('username')}#{data.get('discriminator', '0')}`", inline=True)
        embed.add_field(name="📧 อีเมล", value=f"`{data.get('email', 'ซ่อนอยู่')}`", inline=True)
        try:
            await interaction.user.send(embed=embed)
            await interaction.followup.send("✅ ส่งผลลัพธ์ไปที่ DM ของคุณแล้ว!", ephemeral=True)
        except:
            await interaction.followup.send("❌ ไม่สามารถส่ง DM ได้ กรุณาเปิดรับข้อความส่วนตัว", ephemeral=True)

class TokenCheckerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="TOKEN CHECKER", style=discord.ButtonStyle.danger, emoji="🔍", custom_id="aegis_token_checker:button")
    async def open_checker(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TokenModal())

@bot.tree.command(name="เช็คโทเค็น", description="ตรวจสอบ Discord Token (ส่งเข้า DM)")
async def checktoken_command(interaction: discord.Interaction):
    embed = discord.Embed(title="AEGIS — TOKEN CHECKER", description="ตรวจสอบข้อมูล Token ปลอดภัย 100% ไม่มีการบันทึกข้อมูล", color=0xe74c3c)
    await interaction.channel.send(embed=embed, view=TokenCheckerView())
    await interaction.response.send_message("✅ ส่งหน้าต่าง Token Checker เรียบร้อย", ephemeral=True)


# ==========================================
# 🎫 5. ระบบ Ticket (ติดต่อแอดมิน - ดีไซน์ใหม่)
# ==========================================
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="ปิด Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="aegis_persistent_close_ticket:button")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 กำลังปิดห้องนี้ใน 3 วินาที...", ephemeral=True)
        await asyncio.sleep(3)
        await interaction.channel.delete()

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="สร้าง Ticket", style=discord.ButtonStyle.secondary, emoji="🎟️", custom_id="aegis_persistent_ticket:button")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild, user = interaction.guild, interaction.user
        for channel in guild.text_channels:
            if channel.topic and f"ID: {user.id}" in channel.topic:
                return await interaction.response.send_message(f"❌ คุณมีห้องเปิดอยู่แล้ว: {channel.mention}", ephemeral=True)

        category = discord.utils.get(guild.categories, name="🎫 AEGIS TICKETS") or await guild.create_category("🎫 AEGIS TICKETS")
        existing_tickets = [int(c.name.split("-")[1]) for c in guild.text_channels if c.name.startswith("ticket-") and c.name.split("-")[1].isdigit()]
        next_number = max(existing_tickets) + 1 if existing_tickets else 1

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }
        ticket_channel = await guild.create_text_channel(name=f"ticket-{next_number}", category=category, overwrites=overwrites, topic=f"ID: {user.id}")
        
        embed = discord.Embed(title=f"📩 เปิด Ticket #{next_number} สำเร็จ", description=f"{user.mention} แจ้งรายละเอียดปัญหาไว้ได้เลยครับ", color=0x2b2d31)
        await ticket_channel.send(content=f"{user.mention}", embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ สร้างห้องติดต่อแอดมินให้แล้ว: {ticket_channel.mention}", ephemeral=True)

@bot.tree.command(name="ติดต่อแอดมิน", description="สร้างระบบติดต่อแอดมิน / แจ้งปัญหา (Ticket ดีไซน์ใหม่)")
@app_commands.describe(รูปภาพ="อัปโหลดรูปภาพแบนเนอร์", ลิงก์รูปภาพ="ลิงก์ URL รูปภาพ")
async def ticket_command(interaction: discord.Interaction, รูปภาพ: discord.Attachment = None, ลิงก์รูปภาพ: str = None):
    embed = discord.Embed(
        title="🎟️  ระบบ Ticket",
        description="━━━━━━━━━━━━━━━━━━━━━━\n> \"ทุกปัญหา มีทางออก\"\n> \"ทีมงานพร้อมช่วยเหลือคุณ\"\n━━━━━━━━━━━━━━━━━━━━━━\n\n**กดปุ่มด้านล่างเพื่อสร้าง Ticket**",
        color=0x2b2d31
    )
    if รูปภาพ: embed.set_image(url=รูปภาพ.url)
    elif ลิงก์รูปภาพ: embed.set_image(url=ลิงก์รูปภาพ)
    
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("✅ ส่งหน้าต่าง Ticket เรียบร้อย", ephemeral=True)


# ==========================================
# 🛡️ 6. ระบบยืนยันตัวตน (Verification)
# ==========================================
class VerifyModal(discord.ui.Modal, title="ระบบยืนยันตัวตน (Verification)"):
    verify_name = discord.ui.TextInput(label="กรอกชื่อเล่น / ชื่อในเกม", placeholder="เช่น John_Doe", style=discord.TextStyle.short, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # ⚠️ กำหนดตั้งค่าตรงนี้ ⚠️
        ROLE_ID_TO_GIVE = 123456789012345678  # ใส่ ID ยศที่ต้องการให้
        LOG_CHANNEL_ID = 123456789012345678   # ใส่ ID ช่องที่จะให้แจ้งเตือน
        
        role = interaction.guild.get_role(ROLE_ID_TO_GIVE)
        if role:
            try: await interaction.user.add_roles(role)
            except Exception as e: print(f"Error giving role: {e}")

        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(title="🛡️ มีผู้ทำการยืนยันตัวตนสำเร็จ", color=0x2ecc71)
            log_embed.add_field(name="👤 ผู้ใช้งาน", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
            log_embed.add_field(name="📝 ข้อมูลที่กรอก", value=f"`{self.verify_name.value}`", inline=False)
            await log_channel.send(embed=log_embed)

        await interaction.editReply(content="✅ **ยืนยันตัวตนสำเร็จ!** คุณได้รับยศเรียบร้อยครับ")

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="ยืนยันตัวตน", style=discord.ButtonStyle.success, emoji="✅", custom_id="verify_button:persistent")
    async def verify_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VerifyModal())

@bot.tree.command(name="ส่งปุ่มยืนยันตัวตน", description="ส่งหน้าต่างยืนยันตัวตน")
async def send_verify_command(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)
    embed = discord.Embed(title="🛡️ ระบบยืนยันตัวตน", description="กรุณากดปุ่ม **'ยืนยันตัวตน'** ด้านล่างนี้เพื่อรับยศเข้าเซิร์ฟเวอร์", color=0x3498db)
    await interaction.channel.send(embed=embed, view=VerifyView())
    await interaction.response.send_message("✅ ส่งปุ่มยืนยันตัวตนเรียบร้อย", ephemeral=True)


# ==========================================
# 🤖 7. Event & Status Loop (เปิดระบบทำงาน)
# ==========================================
@tasks.loop(minutes=1)
async def change_status():
    server_count = len(bot.guilds)
    statuses = [
        discord.Game(name=f"ให้บริการ {server_count} เซิร์ฟเวอร์"),
        discord.Game(name="ระบบรับยศ & Ticket พร้อมใช้งาน"),
        discord.Game(name="ระบบความปลอดภัย Aegis")
    ]
    if not hasattr(change_status, "index"): change_status.index = 0
    await bot.change_presence(status=discord.Status.online, activity=statuses[change_status.index])
    change_status.index = (change_status.index + 1) % len(statuses)

@bot.event
async def on_ready():
    # ลงทะเบียน Persistent Views (ให้ปุ่มกดได้ตลอดแม้บอทรีสตาร์ท)
    bot.add_view(TicketView())
    bot.add_view(CloseTicketView())
    bot.add_view(TranslateView())
    bot.add_view(TokenCheckerView())
    bot.add_view(SaveRestoreRoleView())
    bot.add_view(VerifyView())
    
    await bot.tree.sync()
    if not change_status.is_running(): change_status.start()
    print(f"✅ บอท {bot.user} ออนไลน์และโหลดทุกระบบสำเร็จแล้ว!")

@bot.event
async def on_member_remove(member: discord.Member):
    roles = [role.id for role in member.roles if role != member.guild.default_role and member.guild.me.top_role > role]
    if roles: user_saved_roles[member.id] = roles


# ==========================================
# 🚀 รันบอท
# ==========================================
if not token:
    print("❌ ERROR: ไม่พบ DISCORD_TOKEN กรุณาตั้งค่า Token ใน Environment Variables")
else:
    keep_alive() # เปิด Web Server
    bot.run(token)
