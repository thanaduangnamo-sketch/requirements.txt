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
# ⚙️ ตั้งค่าพื้นฐานของบอทและ Intents
# ==========================================
token = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

user_saved_roles = {}
verify_config = {}


# ==========================================
# 🛡️ 1. ระบบยืนยันตัวตน (Verification System)
# ==========================================
class VerifyModal(discord.ui.Modal, title="✨ ระบบยืนยันตัวตน"):
    answer = discord.ui.TextInput(
        label="กรอกรหัสผ่าน / ชื่อเล่น หรือข้อมูลยืนยัน",
        style=discord.TextStyle.short,
        placeholder="กรอกข้อมูลที่นี่...",
        required=True,
        min_length=1,
        max_length=100,
    )

    def __init__(self, guild_id: int):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        config = verify_config.get(self.guild_id)
        if not config:
            return await interaction.edit_original_response(content="❌ เกิดข้อผิดพลาด: ระบบยืนยันตัวตนยังไม่ได้ตั้งค่าในเซิร์ฟเวอร์นี้ กรุณาให้แอดมินใช้คำสั่ง /Aegis_verify อีกครั้ง")

        role_id = config.get("role_id")
        log_channel_id = config.get("log_channel_id")

        member = interaction.user
        guild = interaction.guild
        role = guild.get_role(role_id)

        if not role:
            return await interaction.edit_original_response(content="❌ เกิดข้อผิดพลาด: ไม่พบยศที่ตั้งค่าไว้ กรุณาแจ้งแอดมิน")

        try:
            await member.add_roles(role)
            success_embed = discord.Embed(
                title="✅ ยืนยันตัวตนสำเร็จ!",
                description=f"ยินดีด้วยครับคุณได้รับยศ **{role.name}** เรียบร้อยแล้ว! 🎉",
                color=0x2ecc71
            )
            await interaction.edit_original_response(embed=success_embed)
        except Exception as e:
            return await interaction.edit_original_response(content=f"❌ เกิดข้อผิดพลาดในการให้ยศ: {e}")

        if log_channel_id:
            log_channel = guild.get_channel(log_channel_id)
            if log_channel:
                log_embed = discord.Embed(
                    title="🛡️ มีผู้ยืนยันตัวตนสำเร็จ",
                    color=0x2ecc71,
                    timestamp=discord.utils.utcnow()
                )
                log_embed.add_field(name="👤 ผู้ใช้งาน", value=f"{member.mention} (`{member.name}`)", inline=False)
                log_embed.add_field(name="🆔 User ID", value=f"`{member.id}`", inline=False)
                log_embed.add_field(name="📝 ข้อมูลที่กรอก", value=f"```{self.answer.value}```", inline=False)
                log_embed.set_thumbnail(url=member.display_avatar.url)
                await log_channel.send(embed=log_embed)

class VerifyView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    @discord.ui.button(label="ยืนยันตัวตน", style=discord.ButtonStyle.success, emoji="🌲", custom_id="verify_button_main:persistent")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = verify_config.get(interaction.guild.id)
        if config:
            role_id = config.get("role_id")
            already_role = interaction.guild.get_role(role_id)
            if already_role and already_role in interaction.user.roles:
                return await interaction.response.send_message("ℹ️ คุณได้ทำการยืนยันตัวตนไปแล้วเรียบร้อยครับ", ephemeral=True)

        await interaction.response.send_modal(VerifyModal(interaction.guild.id))

    @discord.ui.button(label="คู่มือการยืนยันตัวตน", style=discord.ButtonStyle.secondary, emoji="🎄", custom_id="manual_button_link:persistent")
    async def manual_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("📖 สามารถอ่านคู่มือการใช้งานได้ภายในเซิร์ฟเวอร์ครับ", ephemeral=True)

    @discord.ui.button(label="why?", style=discord.ButtonStyle.secondary, emoji="🎄", custom_id="why_button_info:persistent")
    async def why_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        why_embed = discord.Embed(
            title="🎄 ทำไมต้องยืนยันตัวตน?",
            description="ระบบนี้มีไว้เพื่อป้องกันบอทสแปม และคัดกรองสมาชิกเพื่อความปลอดภัยภายในเซิร์ฟเวอร์ครับ",
            color=0x99aab5
        )
        await interaction.response.send_message(embed=why_embed, ephemeral=True)

@bot.tree.command(name="aegis_verify", description="[ ✨ ] ส่งหน้าต่างระบบยืนยันตัวตนอัตโนมัติพร้อมเลือกยศและห้อง Log")
@app_commands.describe(
    เลือกยศ="เลือกยศที่จะให้หลังจากยืนยันตัวตนสำเร็จ",
    ห้องแจ้งเตือน="เลือกห้องที่จะให้บอทส่ง Log แจ้งเตือน (ไม่บังคับ)",
    ลิงก์รูปภาพ="ลิงก์รูปภาพแบนเนอร์ GIF (ไม่บังคับ)"
)
@app_commands.default_permissions(administrator=True)
async def aegis_verify(interaction: discord.Interaction, เลือกยศ: discord.Role, ห้องแจ้งเตือน: discord.TextChannel = None, ลิงก์รูปภาพ: str = "https://i.pinimg.com/originals/29/49/e0/2949e0262e42def248f1c77c571bf9ab.gif"):
    verify_config[interaction.guild.id] = {
        "role_id": เลือกยศ.id,
        "log_channel_id": ห้องแจ้งเตือน.id if ห้องแจ้งเตือน else None
    }

    embed = discord.Embed(
        description=(
            "✨ ・ ✨ 🇹‌🇭‌🇦‌🇮‌🇱‌🇦‌🇳‌🇩‌ ✨ ・ ✨\n"
            f"⁺ ✦  *   🐈 **ระบบยืนยันตัวตน**\n"
            "•   ยืนยันตนง่ายๆ ระบบคุณภาพ\n"
            f"•   ยืนยันแล้วจะได้รับบทบาท **{เลือกยศ.mention}**\n"
            "•   ยืนยันไม่กี่ขั้นตอนก็ได้รับบทบาท\n"
            "•   มีคู่มือการใช้งานระบบแบบละเอียด"
        ),
        color=0x2b2d31,
    )
    embed.set_image(url=ลิงก์รูปภาพ)
    embed.set_footer(text="© ระบบยืนยันตัวตนอัตโนมัติ")

    await interaction.channel.send(embed=embed, view=VerifyView(interaction.guild.id))
    log_text = f", ห้อง Log: {ห้องแจ้งเตือน.mention}" if ห้องแจ้งเตือน else ", ห้อง Log: (ไม่ได้ตั้งค่า)"
    await interaction.response.send_message(f"✅ ตั้งค่าและส่งแผงระบบยืนยันตัวตนเรียบร้อย! (ยศ: {เลือกยศ.mention}{log_text})", ephemeral=True)


# ==========================================
# 🎫 2. ระบบ Ticket (ติดต่อแอดมิน)
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
                return await interaction.response.send_message(f"❌ คุณมีห้องติดต่อเปิดอยู่แล้วครับ: {channel.mention}", ephemeral=True)

        category = discord.utils.get(guild.categories, name="🎫 AEGIS TICKETS") or await guild.create_category("🎫 AEGIS TICKETS")
        existing_tickets = [int(c.name.split("-")[1]) for c in guild.text_channels if c.name.startswith("ticket-") and c.name.split("-")[1].isdigit()]
        next_number = max(existing_tickets) + 1 if existing_tickets else 1

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }
        ticket_channel = await guild.create_text_channel(name=f"ticket-{next_number}", category=category, overwrites=overwrites, topic=f"ID: {user.id}")
        
        embed = discord.Embed(title=f"📩 เปิด Ticket #{next_number} สำเร็จ", description=f"{user.mention} แจ้งรายละเอียดปัญหาหรือเรื่องที่ต้องการติดต่อแอดมินไว้ได้เลยครับ!", color=0x2b2d31)
        await ticket_channel.send(content=f"{user.mention}", embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ สร้างห้องติดต่อแอดมินให้แล้ว: {ticket_channel.mention}", ephemeral=True)

@bot.tree.command(name="aegis_ticket", description="[ ✨ ] สร้างระบบ Ticket สำหรับติดต่อแอดมินดีไซน์หรูหรา")
@app_commands.describe(รูปภาพ="อัปโหลดรูปภาพแบนเนอร์", ลิงก์รูปภาพ="ลิงก์ URL รูปภาพ")
async def aegis_ticket(interaction: discord.Interaction, รูปภาพ: discord.Attachment = None, ลิงก์รูปภาพ: str = None):
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
# 🛡️ 3. ระบบเซฟและคืนยศ (Save & Restore Roles)
# ==========================================
class SaveRestoreRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="เซฟยศของฉัน", style=discord.ButtonStyle.primary, emoji="🛡️", custom_id="aegis_save_role:button")
    async def save_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        user, guild = interaction.user, interaction.guild
        roles_to_save = [role.id for role in user.roles if role != guild.default_role and guild.me.top_role > role]
        user_saved_roles[user.id] = roles_to_save
        
        embed = discord.Embed(title="🛡️ สำเร็จ — บันทึกยศเรียบร้อย", description=f"✅ ทำการเซฟยศทั้งหมดของคุณจำนวน **{len(roles_to_save)} ยศ** เรียบร้อยแล้ว!", color=0xf1c40f)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="คืนยศของฉัน", style=discord.ButtonStyle.danger, emoji="🛠️", custom_id="aegis_restore_role:button")
    async def restore_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        user, guild = interaction.user, interaction.guild
        if user.id not in user_saved_roles or not user_saved_roles[user.id]:
            return await interaction.response.send_message("❌ ไม่พบข้อมูลการเซฟยศของคุณ กรุณากด 'เซฟยศของฉัน' ก่อนครับ", ephemeral=True)

        saved_role_ids = user_saved_roles[user.id]
        roles_to_add = [guild.get_role(r_id) for r_id in saved_role_ids if guild.get_role(r_id) and guild.me.top_role > guild.get_role(r_id)]

        try:
            await user.add_roles(*roles_to_add)
            embed = discord.Embed(title="🛠️ สำเร็จ — คืนยศเรียบร้อย", description=f"✅ คืนยศให้คุณสำเร็จจำนวน **{len(roles_to_add)} ยศ** แล้วครับ!", color=0xf1c40f)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)

@bot.tree.command(name="aegis_saveroles", description="[ ✨ ] สร้างระบบปุ่มกดเซฟและคืนยศอัตโนมัติสำหรับสมาชิก")
async def aegis_saveroles(interaction: discord.Interaction, ลิงก์รูปภาพ: str = "https://i.pinimg.com/736x/14/68/59/146859926bd33323535af3b8697b024d.jpg"):
    embed = discord.Embed(title="🛡️ ระบบเซฟและคืนยศ", description="กดปุ่มด้านล่างเพื่อจัดการยศของคุณได้เลย!", color=0xf1c40f)
    embed.set_image(url=ลิงก์รูปภาพ)
    await interaction.channel.send(embed=embed, view=SaveRestoreRoleView())
    await interaction.response.send_message("✅ สร้างหน้าต่างระบบเซฟและคืนยศเรียบร้อย", ephemeral=True)


# ==========================================
# 🌐 4. ระบบแปลภาษา
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

@bot.tree.command(name="aegis_translate", description="[ ✨ ] เปิดหน้าต่างระบบแปลภาษาข้อความสากลเป็นไทย")
async def aegis_translate(interaction: discord.Interaction):
    embed = discord.Embed(title="🌐 TRANSLATE SYSTEM", description="กดปุ่มด้านล่างเพื่อแปลภาษาเป็นไทย", color=0x2ecc71)
    await interaction.channel.send(embed=embed, view=TranslateView())
    await interaction.response.send_message("✅ ส่งหน้าต่างแปลภาษาเรียบร้อย", ephemeral=True)


# ==========================================
# 🔍 5. ระบบ TOKEN CHECKER
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
        
        embed = discord.Embed(title="✨ TOKEN CHECKER RESULT ✨", description="ส่งผลลัพธ์ให้คุณทาง DM", color=0xe74c3c)
        embed.add_field(name="🏷️ ผู้ใช้", value=f"`{data.get('username')}`", inline=True)
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

@bot.tree.command(name="aegis_tokencheck", description="[ ✨ ] ตรวจสอบความถูกต้องของ Discord Token และส่งข้อมูลเข้า DM")
async def aegis_tokencheck(interaction: discord.Interaction):
    embed = discord.Embed(title="AEGIS — TOKEN CHECKER", description="ตรวจสอบ Token ปลอดภัย 100%", color=0xe74c3c)
    await interaction.channel.send(embed=embed, view=TokenCheckerView())
    await interaction.response.send_message("✅ ส่งหน้าต่าง Token Checker เรียบร้อย", ephemeral=True)


# ==========================================
# 🤖 6. Event & Status Loop (เปิดระบบทำงาน)
# ==========================================
@tasks.loop(minutes=1)
async def change_status():
    server_count = len(bot.guilds)
    statuses = [
        discord.Game(name=f"ให้บริการ {server_count} เซิร์ฟเวอร์"),
        discord.Game(name="ระบบยืนยันตัวตน & Ticket พร้อมใช้งาน"),
        discord.Game(name="ระบบความปลอดภัย Aegis")
    ]
    if not hasattr(change_status, "index"): change_status.index = 0
    await bot.change_presence(status=discord.Status.online, activity=statuses[change_status.index])
    change_status.index = (change_status.index + 1) % len(statuses)

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    bot.add_view(CloseTicketView())
    bot.add_view(TranslateView())
    bot.add_view(TokenCheckerView())
    bot.add_view(SaveRestoreRoleView())
    
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
if __name__ == "__main__":
    BOT_TOKEN = token or "YOUR_BOT_TOKEN"
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN":
        print("❌ ERROR: กรุณาใส่ BOT_TOKEN ของคุณก่อนรันบอท")
    else:
        keep_alive()
        bot.run(BOT_TOKEN)
