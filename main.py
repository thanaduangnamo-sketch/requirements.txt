import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import aiohttp
from flask import Flask
from threading import Thread
from datetime import datetime

# --- ระบบเปิดเว็บจำลองสำหรับ Render (ดึง Port อัตโนมัติ) ---
app = Flask('')

@app.route('/')
def home():
    return "Multi-System Bot is running!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ------------------------------------

token = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.moderation = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- ระบบลูปเปลี่ยนสถานะทุกๆ 1 นาที ---
@tasks.loop(minutes=1)
async def change_status():
    server_count = len(bot.guilds)
    
    statuses = [
        discord.Game(name=f"ให้บริการอยู่ {server_count} เซิร์ฟเวอร์"),
        discord.Game(name="ระบบยืนยันตัวตน & Ticket พร้อมใช้งาน"),
        discord.Game(name="ระบบแปลภาษา & Token Checker พร้อมใช้งาน")
    ]
    
    if not hasattr(change_status, "index"):
        change_status.index = 0
    
    current_status = statuses[change_status.index]
    await bot.change_presence(status=discord.Status.online, activity=current_status)
    
    change_status.index = (change_status.index + 1) % len(statuses)


@bot.event
async def on_ready():
    bot.add_view(PersistentVerifyView())
    bot.add_view(TicketView())
    bot.add_view(TranslateView())
    
    server_count = len(bot.guilds)
    print(f"Logged in as {bot.user.name} (Auto Status Mode)")
    print(f"🌐 บอทกำลังให้บริการอยู่ทั้งหมด {server_count} เซิร์ฟเวอร์:")
    for guild in bot.guilds:
        print(f" - ชื่อเซิร์ฟเวอร์: {guild.name} | ID: {guild.id}")
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    if not change_status.is_running():
        change_status.start()
        
    print("✅ บอทออนไลน์และเริ่มระบบเปลี่ยนสถานะเรียบร้อยแล้วครับ")


# ==========================================
# 🛡️ ระบบแจ้งเตือนเมื่อมีคนดึงบอทเข้าเซิร์ฟเวอร์
# ==========================================
@bot.event
async def on_member_join(member: discord.Member):
    if member.bot:
        guild = member.guild
        target_channel_id = 1533086872471994489
        target_channel = guild.get_channel(target_channel_id)

        if not target_channel:
            return

        inviter = "ไม่ทราบ (อาจใช้ลิงก์ OAuth2 ลับ หรือดึงตรง)"
        try:
            async for entry in guild.audit_logs(action=discord.AuditLogAction.bot_add, limit=1):
                if entry.target.id == member.id:
                    inviter = entry.user.mention
                    break
        except Exception as e:
            print(f"ไม่สามารถดึง Audit Log ได้: {e}")

        embed = discord.Embed(
            title="🚨 มีการเพิ่มบอทตัวใหม่เข้าสู่เซิร์ฟเวอร์!",
            description=(
                f"🤖 **ชื่อบอท:** {member.mention} (`{member.name}`)\n"
                f"🆔 **Bot ID:** `{member.id}`\n"
                f"👤 **ผู้ที่ดึงเข้าเซิร์ฟ:** {inviter}\n\n"
                f"📅 **เวลา:** <t:{int(member.joined_at.timestamp())}:F>"
            ),
            color=0xe74c3c
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"เซิร์ฟเวอร์: {guild.name}", icon_url=guild.icon.url if guild.icon else None)

        await target_channel.send(embed=embed)


# ==========================================
# 🌐 ระบบแปลภาษา (Translate System)
# ==========================================
class TranslateModal(discord.ui.Modal, title="🌐 ระบบแปลภาษาอัตโนมัติ"):
    text_input = discord.ui.TextInput(
        label="ข้อความที่ต้องการแปล",
        style=discord.TextStyle.paragraph,
        placeholder="พิมพ์ข้อความที่ต้องการแปลภาษาลงที่นี่...",
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        original_text = self.text_input.value.strip()

        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=th&dt=t&q=" + discord.utils.parse_ratelimit(original_text) if hasattr(discord.utils, 'parse_ratelimit') else f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=th&dt=t&q={original_text}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return await interaction.followup.send("❌ เกิดข้อผิดพลาดในการเชื่อมต่อระบบแปลภาษา", ephemeral=True)
                res_json = await resp.json()
                translated_text = "".join([item[0] for item in res_json[0]])
                detected_lang = res_json[2].upper()

        embed = discord.Embed(
            title="🌐 ผลการแปลภาษา (Translation Result)",
            color=0x2ecc71
        )
        embed.add_field(name="📝 ข้อความต้นฉบับ", value=f"```{original_text}```", inline=False)
        embed.add_field(name=f"✨ แปลเป็นภาษาไทย (จาก: {detected_lang})", value=f"```{translated_text}```", inline=False)
        embed.set_footer(text="Translation System Powered by Bot")

        await interaction.followup.send(embed=embed, ephemeral=True)


class TranslateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="แปลภาษา",
        style=discord.ButtonStyle.success,
        emoji="🌐",
        custom_id="icewen_translate:button"
    )
    async def open_translate(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TranslateModal())


@bot.tree.command(name="translate", description="เปิดหน้าต่างระบบแปลภาษาพร้อมวิธีใช้งานแบบละเอียด")
async def translate_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌐 TRANSLATE SYSTEM | ระบบแปลภาษา",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━ .•° TRANSLATE °•.\n"
            "╭ · ระบบแปลภาษาอัตโนมัติ รวดเร็วและแม่นยำ\n"
            "│ · รองรับการแปลภาษาจากทั่วโลกเป็นภาษาไทย\n"
            "╰ · ใช้งานง่ายผ่านปุ่มกดด้านล่างทันที\n\n"
            "📖 **วิธีใช้งานระบบ:**\n"
            "1. กดปุ่มสีเขียว **'แปลภาษา'** ด้านล่าง\n"
            "2. กรอกข้อความที่ต้องการแปลลงในช่องว่างที่ปรากฏขึ้น\n"
            "3. กดปุ่มส่ง (Submit) เพื่อดูผลลัพธ์การแปลภาษา\n"
            "4. ระบบจะแสดงผลลัพธ์แบบเฉพาะตัวคุณ (ไม่รบกวนผู้อื่น)"
        ),
        color=0x2ecc71
    )
    embed.set_image(url="https://i.pinimg.com/736x/de/f8/80/def8807c89475990941ba4617b4cbc2e.jpg")
    embed.set_footer(text="ICEWEN_2 : TRANSLATE SYSTEM")

    await interaction.channel.send(embed=embed, view=TranslateView())
    await interaction.response.send_message("✅ ส่งหน้าต่างแปลภาษาเรียบร้อยแล้วครับ", ephemeral=True)


# ==========================================
# 🔍 ระบบ TOKEN CHECKER (ความลับสูงสุด ส่งตรง DM)
# ==========================================
class TokenModal(discord.ui.Modal, title="ICEWEN_2 : TOKEN CHECKER"):
    token_input = discord.ui.TextInput(
        label="กรอก Discord Token ที่ต้องการตรวจสอบ",
        style=discord.TextStyle.paragraph,
        placeholder="วาง Token ของคุณลงที่นี่...",
        required=True,
        max_length=200
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        raw_token = self.token_input.value.strip()

        headers = {
            "Authorization": raw_token,
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get("https://discord.com/api/v9/users/@me", headers=headers) as resp:
                if resp.status != 200:
                    return await interaction.followup.send(
                        "❌ **Token ไม่ถูกต้องหรือหมดอายุแล้ว!** กรุณาตรวจสอบความถูกต้องอีกครั้ง",
                        ephemeral=True
                    )
                user_data = await resp.json()

        username = user_data.get("username", "Unknown")
        discriminator = user_data.get("discriminator", "0")
        full_name = f"{username}#{discriminator}" if discriminator != "0" else username
        user_id = user_data.get("id", "Unknown")
        email = user_data.get("email", "ไม่มีข้อมูล / ซ่อนอยู่")
        phone = user_data.get("phone", "ไม่มีข้อมูล / ซ่อนอยู่")
        mfa_enabled = "เปิดใช้งาน (2FA)" if user_data.get("mfa_enabled") else "ปิดใช้งาน"
        verified = "ยืนยันแล้ว" if user_data.get("verified") else "ยังไม่ยืนยัน"
        
        is_bot = user_data.get("bot", False)
        acc_type = "🤖 Bot Account" if is_bot else "👤 User Account"

        nitro_type = user_data.get("premium_type", 0)
        nitro_map = {0: "ไม่มี Nitro", 1: "Nitro Classic", 2: "Nitro Boost", 3: "Nitro Basic"}
        nitro_status = nitro_map.get(nitro_type, "ไม่ทราบสถานะ")

        avatar_id = user_data.get("avatar")
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_id}.png" if avatar_id else "https://cdn.discordapp.com/embed/avatars/0.png"

        result_embed = discord.Embed(
            title="✨ TOKEN CHECKER RESULT ✨",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "• **ข้อมูล Token จะไม่ถูกนำไปบันทึกในฐานข้อมูลใดๆ**\n"
                "• ผลลัพธ์แสดงเฉพาะตัวคุณเท่านั้น (ส่งเข้า DM ส่วนตัว)\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=0xe74c3c
        )
        result_embed.set_thumbnail(url=avatar_url)
        result_embed.add_field(name="🏷️ ชื่อผู้ใช้", value=f"`{full_name}`", inline=True)
        result_embed.add_field(name="🆔 บัญชี ID", value=f"`{user_id}`", inline=True)
        result_embed.add_field(name="📂 ประเภทบัญชี", value=acc_type, inline=True)
        result_embed.add_field(name="📧 อีเมล", value=f"`{email}`", inline=True)
        result_embed.add_field(name="📱 เบอร์โทรศัพท์", value=f"`{phone}`", inline=True)
        result_embed.add_field(name="🔒 ระบบความปลอดภัย (2FA)", value=mfa_enabled, inline=True)
        result_embed.add_field(name="✅ สถานะยืนยันอีเมล", value=verified, inline=True)
        result_embed.add_field(name="💎 สถานะ Nitro ล่าสุด", value=nitro_status, inline=True)
        result_embed.set_footer(text="ICEWEN_2 : TOKEN CHECKER SYSTEM", icon_url="https://i.pinimg.com/736x/5c/6f/47/5c6f4777c193e7fff8120e187ace58fd.jpg")

        try:
            await interaction.user.send(embed=result_embed)
            await interaction.followup.send(
                "✅ ตรวจสอบ Token สำเร็จ! ระบบได้จัดส่งผลลัพธ์ไปที่ **ข้อความส่วนตัว (DM)** เรียบร้อยแล้ว",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ ไม่สามารถส่งข้อความหาคุณได้ กรุณาเปิดรับข้อความส่วนตัว (Direct Messages) ก่อนใช้งานครับ",
                ephemeral=True
            )


class TokenCheckerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="TOKEN CHECKER",
        style=discord.ButtonStyle.danger,
        emoji="🔍",
        custom_id="icewen_token_checker:button"
    )
    async def open_checker(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TokenModal())


@bot.tree.command(name="checktoken", description="เปิดหน้าต่างตรวจสอบ Discord Token (ส่งผลลัพธ์เข้า DM)")
async def checktoken_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="TOKEN CHECKER | ตรวจสอบ Discord Token",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━ .•° TOKEN CHECKER °•.\n"
            "╭ · ระบบตรวจสอบความถูกต้องและดูสิทธิ์ของ Token\n"
            "│ · แยกประเภทบัญชีอัตโนมัติ (User Account / Bot)\n"
            "│ · ตรวจสอบอีเมล, เบอร์โทรศัพท์ และสถานะ 2FA\n"
            "╰ · เช็คสถานะแพลทินัม Nitro ล่าสุด\n\n"
            "**นโยบายความปลอดภัย:**\n"
            "• ข้อมูล Token จะไม่ถูกนำไปบันทึกหรือบันทึกในฐานข้อมูลใดๆ\n"
            "• ผลลัพธ์แสดงเฉพาะตัวคุณเท่านั้น (ส่งเข้า DM ส่วนตัว)"
        ),
        color=0xe74c3c
    )
    embed.set_image(url="https://i.pinimg.com/736x/5c/6f/47/5c6f4777c193e7fff8120e187ace58fd.jpg")
    embed.set_footer(text="ICEWEN_2 : TOKEN CHECKER SYSTEM")

    await interaction.channel.send(embed=embed, view=TokenCheckerView())
    await interaction.response.send_message("✅ ส่งหน้าต่าง Token Checker เรียบร้อยแล้วครับ", ephemeral=True)


# ==========================================
# 1. ระบบยืนยันตัวตน (Persistent View แบบใหม่)
# ==========================================
class PersistentVerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # ปุ่มที่ 1: ยืนยันตัวตน (ให้ยศและแสดงหน้าต่างสำเร็จ)
    @discord.ui.button(
        label="ยืนยันตัวตน",
        style=discord.ButtonStyle.success,
        emoji="🌳",
        custom_id="persistent_verify:button"
    )
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="Verified") or discord.utils.get(interaction.guild.roles, name="Member")
        
        if not role:
            return await interaction.response.send_message(
                "❌ ไม่พบยศสำหรับยืนยันตัวตนในระบบ (กรุณาตั้งชื่อยศว่า 'Verified' หรือ 'Member' ในเซิร์ฟเวอร์)",
                ephemeral=True
            )

        if role in interaction.user.roles:
            return await interaction.response.send_message(
                "❌ คุณได้ทำการยืนยันตัวตนไปแล้ว",
                ephemeral=True
            )

        await interaction.user.add_roles(role)
        
        # สร้าง Embed หน้าต่างสำเร็จ (VERIFY SUCCEEDED)
        success_embed = discord.Embed(
            title="✅ VERIFY SUCCEEDED",
            color=0x2ecc71,
            timestamp=datetime.utcnow()
        )
        success_embed.add_field(name="⭐ USER", value=f"{interaction.user.mention}", inline=False)
        success_embed.add_field(name="🥟 USERID", value=f"`{interaction.user.id}`", inline=False)
        success_embed.add_field(name="🚀 ROLE", value=f"{role.mention}", inline=False)
        success_embed.set_footer(text="ICEWEN_2 : VERIFY SYSTEM")

        await interaction.response.send_message(embed=success_embed, ephemeral=True)

    # ปุ่มที่ 2: คู่มือการยืนยันตัวตน
    @discord.ui.button(
        label="คู่มือการยืนยันตัวตน",
        style=discord.ButtonStyle.secondary,
        emoji="🎄",
        custom_id="persistent_verify:guide"
    )
    async def guide_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guide_embed = discord.Embed(
            title="📖 | คู่มือการยืนยันตัวตน",
            description="> 1. กดปุ่ม **'ยืนยันตัวตน'** สีเขียว\n> 2. ระบบจะทำการมอบยศให้อัตโนมัติทันที\n> 3. หากมีปัญหาติดต่อแอดมิน",
            color=0x2b2d31
        )
        await interaction.response.send_message(embed=guide_embed, ephemeral=True)


@bot.tree.command(name="ยืนยันตัวตน", description="สร้างระบบยืนยันตัวตนแบบใหม่ดีไซน์ Cinnamoroll")
@app_commands.describe(
    role="เลือกยศที่ต้องการให้ผู้ใช้งานได้รับ",
    image="อัปโหลดรูปภาพประกอบ (ไม่บังคับ)",
    image_url="หรือใส่ลิงก์รูปภาพ URL (ไม่บังคับ)",
    url_link="ใส่ลิงก์เว็บไซต์สำหรับปุ่ม why? (ไม่บังคับ)"
)
async def verify_command(
    interaction: discord.Interaction, 
    role: discord.Role, 
    image: discord.Attachment = None,
    image_url: str = None,
    url_link: str = "https://your-link-here.com"
):
    embed = discord.Embed(
        description=(
            "+  . ✦ 🐈‍⬛ ' **ระบบยืนยันตัวตน**\n\n"
            "+  . ✦ 🐉 ' ยืนยันตน ✨ <u>ง่ายๆ</u> ✨ ระบบคุณภาพ\n"
            f"+  . ✦ 🐑 ' ยืนยันแล้วจะได้รับบทบาท 👑 {role.mention} 👑\n"
            "+  . ✦ 🐉 ' ยืนยันไม่กี่ ⚡ <u>ขั้นตอน</u> ⚡ ก็ได้รับบทบาท\n"
            "+  . ✦ 🐰 ' มีคู่มือการใช้งานระบบแบบ 📚 <u>ละเอียด</u> 📚"
        ),
        color=0x2b2d31
    )

    # กำหนดรูปภาพแบนเนอร์ (ถ้าไม่ได้เลือกไฟล์หรือใส่ลิงก์มา จะใช้รูปค่าเริ่มต้น Cinnamoroll ทันที)
    target_image = image.url if image else (image_url if image_url else "https://i.ibb.co/QcHHS4H/Discord.png")
    if target_image:
        embed.set_image(url=target_image)

    # สร้าง View และเพิ่มปุ่มลิงก์ภายนอก why? ตามที่คุณต้องการ
    view = PersistentVerifyView()
    url_button = discord.ui.Button(
        label="why?", 
        emoji="🌲", 
        style=discord.ButtonStyle.link, 
        url=url_link
    )
    view.add_item(url_button)

    await interaction.channel.send(
        embed=embed,
        view=view
    )

    await interaction.response.send_message(
        "✅ สร้างหน้าต่างยืนยันตัวตนเรียบร้อยครับ",
        ephemeral=True
    )


# ==========================================
# 2. ระบบ Ticket รันเลขเริ่มต้นจาก 1 พร้อมหมวดหมู่ (Persistent View)
# ==========================================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="สอบถาม/แจ้งปัญหา",
        style=discord.ButtonStyle.success,
        emoji="📩",
        custom_id="persistent_ticket:button"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        for channel in guild.text_channels:
            if channel.topic and f"ID: {user.id}" in channel.topic:
                return await interaction.response.send_message(
                    f"❌ คุณมีห้องติดต่อแอดมินเปิดอยู่แล้วครับ: {channel.mention}",
                    ephemeral=True
                )

        category_name = "🎫 TICKETS"
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)

        existing_tickets = [c for c in guild.text_channels if c.name.startswith("ticket-")]
        ticket_numbers = []
        for c in existing_tickets:
            parts = c.name.split("-")
            if len(parts) > 1 and parts[1].isdigit():
                ticket_numbers.append(int(parts[1]))

        next_number = 1 if not ticket_numbers else max(ticket_numbers) + 1

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{next_number}",
            category=category,
            overwrites=overwrites,
            topic=f"Ticket #{next_number} ของคุณ {user.name} (ID: {user.id})"
        )

        embed = discord.Embed(
            title=f"📩 เปิด Ticket #{next_number} สำเร็จ",
            description=f"สวัสดีครับคุณ {user.mention} แจ้งรายละเอียดปัญหาหรือเรื่องที่ต้องการติดต่อแอดมินไว้ได้เลยครับ ทีมงานจะรีบเข้ามาช่วยเหลือโดยเร็วที่สุด!",
            color=0x2b2d31
        )
        
        close_view = CloseTicketView()
        await ticket_channel.send(content=f"{user.mention}", embed=embed, view=close_view)

        await interaction.response.send_message(
            f"✅ สร้างห้องติดต่อแอดมินให้แล้วครับ: {ticket_channel.mention}",
            ephemeral=True
        )


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="ปิด Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="persistent_close_ticket:button"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 กำลังปิดห้องนี้ใน 3 วินาที...", ephemeral=True)
        import asyncio
        await asyncio.sleep(3)
        await interaction.channel.delete()


@bot.tree.command(name="ติดต่อแอดมิน", description="สร้างระบบติดต่อแอดมิน / แจ้งปัญหา (Ticket)")
@app_commands.describe(
    image="อัปโหลดรูปภาพประกอบ (ไม่บังคับ)",
    image_url="หรือใส่ลิงก์รูปภาพ URL (ไม่บังคับ)"
)
async def ticket_command(
    interaction: discord.Interaction,
    image: discord.Attachment = None,
    image_url: str = None
):
    embed = discord.Embed(
        title="ติดต่อแอดมิน/แจ้งปัญหาได้ที่นี่",
        description=(
            "🎟️ **Support Ticket**\n"
            "หากคุณมีเรื่องจะติดต่อ\n"
            "กดปุ่มด้านล่างเพื่อเปิดตั๋วได้ทันที\n\n"
            "```ansi\n"
            "\u001b[30;1m┌─────────────────────────────────────────┐\n"
            "  🟩 โปรดอธิบายรายละเอียดให้ครบถ้วน\n"
            "  ⏳ แอดมินจะรีบเข้ามาตอบโดยเร็วที่สุด\n"
            "  ⚠️ การเปิดตั๋วเล่น ๆ หรือไม่เหมาะสม อาจส่งผลต่อสิทธิ์การใช้งาน\n"
            "└─────────────────────────────────────────┘\n"
            "\u001b[0m"
        ),
        color=0xf1c40f
    )

    target_image = image.url if image else (image_url if image_url else None)
    if target_image:
        embed.set_image(url=target_image)

    embed.set_footer(text="Powered by Custom Bot")

    await interaction.channel.send(
        embed=embed,
        view=TicketView()
    )

    await interaction.response.send_message(
        "✅ ส่งหน้าต่างติดต่อแอดมินเรียบร้อยครับ",
        ephemeral=True
    )

# เปิดใช้งาน Web Server และรันบอท
keep_alive()
bot.run(token)
