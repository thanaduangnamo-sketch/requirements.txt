import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import aiohttp
from flask import Flask
from threading import Thread
import asyncio
import time

# --- ระบบเปิดเว็บจำลองสำหรับ Render (ดึง Port อัตโนมัติ) ---
app = Flask('')

@app.route('/')
def home():
    return "Aegis Bot & Shop is running!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ------------------------------------

# --- ดึง Token จาก Environment Variable อย่างปลอดภัย ---
token = os.environ.get("DISCORD_TOKEN")

if not token:
    print("❌ ERROR: ไม่พบ DISCORD_TOKEN กรุณาตั้งค่า Token ใน Environment Variables")
    exit()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.moderation = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ==========================================
# ⚡ AEGIS — CONTROL PANEL (สำหรับเล่นขำๆ)
# ==========================================
ddos_cooldowns = {}
ddos_current_user = None

class DdosModal(discord.ui.Modal, title="⚡ AEGIS — กรอกเป้าหมาย"):
    def __init__(self, duration: int, mode: str):
        super().__init__()
        self.duration = duration
        self.mode = mode

        self.url_input = discord.ui.TextInput(
            label="กรอก URL เป้าหมายที่ต้องการทดสอบ",
            style=discord.TextStyle.short,
            placeholder="https://example.com",
            required=True,
            max_length=200
        )
        self.add_item(self.url_input)

    async def on_submit(self, interaction: discord.Interaction):
        global ddos_current_user
        target_url = self.url_input.value.strip()

        embed = discord.Embed(
            title="⚡ กำลังเริ่มกระบวนการ Aegis...",
            description=(
                f"🎯 **เป้าหมาย:** `{target_url}`\n"
                f"⏱️ **ระยะเวลา:** `{self.duration} วินาที`\n"
                f"⚙️ **โหมด:** `{self.mode}`\n"
                f"🔄 **สถานะ:** กำลังส่งคำขอ (Requests)..."
            ),
            color=0xf1c40f
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        for remaining in range(self.duration, 0, -5 if self.duration >= 10 else -1):
            await asyncio.sleep(min(5, remaining))

        ddos_current_user = None

        success_embed = discord.Embed(
            title="✅ AEGIS — สำเร็จ!",
            description=(
                f"🎉 การทดสอบจำลองเสร็จสิ้นเรียบร้อย!\n\n"
                f"🎯 **เป้าหมาย:** `{target_url}`\n"
                f"⏱️ **เวลาที่ใช้:** `{self.duration} วินาที`\n"
                f"⚙️ **โหมด:** `{self.mode}` (ผ่านพร็อกซี่ 2,841 ตัว)\n"
                f"📊 **สถานะผลลัพธ์:** จำลองการส่งข้อมูลสำเร็จ (Aegis Shop)"
            ),
            color=0x2ecc71
        )
        await interaction.followup.send(embed=success_embed, ephemeral=True)


class DdosSelect(discord.ui.Select):
    def __init__(self, is_vip: bool):
        self.is_vip = is_vip
        max_time = 500 if is_vip else 50
        
        options = [
            discord.SelectOption(label="⏱️ 10 วินาที (ทดสอบสั้นๆ)", value="10", description="โหมดรวดเร็ว เหมาะสำหรับการเทสระบบ"),
            discord.SelectOption(label="⏱️ 30 วินาที (มาตรฐาน)", value="30", description="ความเร็วกำลังดี"),
            discord.SelectOption(label=f"⏱️ {max_time} วินาที (สูงสุดของระดับคุณ)", value=str(max_time), description=f"จัดเต็มเวลาสูงสุดสำหรับ {'VIP' if is_vip else 'Member ปกติ'}"),
        ]
        super().__init__(placeholder="👉 เลือกระยะเวลา (Duration) ที่นี่...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        global ddos_current_user
        user = interaction.user
        current_time = time.time()

        if ddos_current_user and ddos_current_user != user.id:
            return await interaction.response.send_message("❌ ระบบกำลังใช้งานโดยผู้อื่นอยู่ กรุณารอสักครู่ (ใช้ได้ 1 คนต่อครั้ง)", ephemeral=True)

        cooldown_time = 900 if self.is_vip else 3600
        if user.id in ddos_cooldowns:
            remaining_cd = ddos_cooldowns[user.id] - current_time
            if remaining_cd > 0:
                mins = int(remaining_cd // 60)
                secs = int(remaining_cd % 60)
                return await interaction.response.send_message(f"⏳ คุณติดคูลดาวน์อยู่! กรุณารออีก `{mins} นาที {secs} วินาที` ก่อนใช้งานอีกครั้ง", ephemeral=True)

        ddos_current_user = user.id
        ddos_cooldowns[user.id] = current_time + cooldown_time

        selected_duration = int(self.values[0])

        view = DdosModeView(selected_duration)
        await interaction.response.send_message(
            f"⏱️ คุณเลือกเวลา **{selected_duration} วินาที** เรียบร้อย!\n👉 ขั้นตอนถัดไป: เลือกโหมดการโจมตีด้านล่างครับ",
            view=view,
            ephemeral=True
        )


class DdosModeView(discord.ui.View):
    def __init__(self, duration: int):
        super().__init__(timeout=60)
        self.duration = duration

    @discord.ui.button(label="🚀 โหมด Direct (เร็ว)", style=discord.ButtonStyle.danger, emoji="⚡")
    async def direct_mode(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DdosModal(self.duration, "Direct (รวดเร็ว)"))

    @discord.ui.button(label="🛡️ โหมด Proxy (ซ่อนตัว)", style=discord.ButtonStyle.primary, emoji="🌐")
    async def proxy_mode(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DdosModal(self.duration, "Proxy (2,841 ตัว)"))


class DdosControlPanelView(discord.ui.View):
    def __init__(self, is_vip: bool):
        super().__init__(timeout=None)
        self.add_item(DdosSelect(is_vip))


@bot.tree.command(name="aegis_panel", description="เปิดแผงควบคุมระบบ Aegis Bot / Shop")
async def aegis_panel_command(interaction: discord.Interaction):
    is_vip = any("vip" in role.name.lower() for role in interaction.user.roles)
    
    role_name = "⭐ VIP" if is_vip else "● MEMBER ปกติ"
    max_sec = "500 วิ" if is_vip else "50 วิ"
    cd_time = "15 นาที" if is_vip else "1 ชม."
    time_options = "10 ~ 500 วิ" if is_vip else "10 ~ 50 วิ"

    embed = discord.Embed(
        title="⚡ AEGIS BOT / SHOP — CONTROL PANEL ⚡",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"ยินดีต้อนรับ {interaction.user.mention} สู่ระบบ Aegis Bot / Shop\n"
            "เลือกระยะเวลาจาก Dropdown ด้านล่าง\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"**ระดับของคุณ:**\n`{role_name}`\n\n"
            "**ตารางเปรียบเทียบสิทธิ์:**\n"
            "```text\n"
            "╔══════════════╦══════════╦══════════╗\n"
            "║   สิทธิ์     ║  ⭐ VIP  ║  👤 ปกติ ║\n"
            "╠══════════════╬══════════╬══════════╣\n"
            "║ ⏱ ยิงสูงสุด ║  500 วิ  ║  50 วิ   ║\n"
            "║ ⏳ คูลดาวน์  ║  15 นาที ║  1 ชม.   ║\n"
            "║ ⚡ ลำดับคิว  ║  สูง     ║  ปกติ    ║\n"
            "╚══════════════╩══════════╩══════════╝\n"
            "```\n"
            "📌 **สิทธิ์ของคุณปัจจุบัน:**\n"
            f"• [ยิงสูงสุด]     = `{max_sec}`\n"
            f"• [คูลดาวน์]      = `{cd_time}`\n"
            f"• [ตัวเลือกเวลา]  = `{time_options}`\n"
            "• [Concurrent]    = `50 req`\n\n"
            "🌐 **ระบบพร็อกซี่:**\n"
            "• [สถานะ]    = `พร้อม`\n"
            "• [จำนวน]    = `2,841 ตัว`\n"
            "• [แหล่งที่มา] = `4 แหล่ง`\n"
            "• [Cache]    = `5 นาที`\n\n"
            "🟢 **สถานะระบบ:** ว่าง — พร้อมใช้งาน | คูลดาวน์: พร้อมใช้งาน\n\n"
            "┌──────────────────────────────────────┐\n"
            "│  📌 กฎการใช้งาน Aegis Bot / Shop     │\n"
            "├──────────────────────────────────────┤\n"
            "│ 1. ใช้ได้ 1 คนต่อครั้งเท่านั้น      │\n"
            "│ 2. ห้ามยิงซ้ำก่อนหมดคูลดาวน์        │\n"
            "│ 3. เลือกเวลา → เลือกโหมด → กรอก URL │\n"
            "│ 4. โหมด Direct = เร็ว / Proxy = ซ่อน │\n"
            "│ 5. ผลลัพธ์จะแสดงเมื่อยิงเสร็จ       │\n"
            "└──────────────────────────────────────┘"
        ),
        color=0xe74c3c
    )
    embed.set_footer(text="Aegis Bot / Shop V6 — สำหรับทดสอบและเล่นสนุกเท่านั้น")

    view = DdosControlPanelView(is_vip)
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ เปิดแผงควบคุม Aegis สำเร็จ!", ephemeral=True)


# ==========================================
# 🟩 ระบบรับยศทั่วไป (เลือกยศผ่านคำสั่ง /setup_roles)
# ==========================================
class GeneralRoleView(discord.ui.View):
    def __init__(self, role_id: int):
        super().__init__(timeout=None)
        self.role_id = role_id

    @discord.ui.button(label="【 ☁️ กดเพื่อรับ/คืนยศ 】", style=discord.ButtonStyle.success, emoji="🟢", custom_id="general_role_button:dynamic")
    async def toggle_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(self.role_id)
        
        if not role:
            return await interaction.response.send_message("❌ ไม่พบยศนี้ในระบบเซิร์ฟเวอร์ กรุณาติดต่อแอดมิน", ephemeral=True)

        user = interaction.user

        if role in user.roles:
            await user.remove_roles(role)
            await interaction.response.send_message(f"🗑️ ทำการคืนยศ **{role.name}** เรียบร้อยแล้วครับ", ephemeral=True)
        else:
            await user.add_roles(role)
            await interaction.response.send_message(f"✅ คุณได้รับยศ **{role.name}** เรียบร้อยแล้วครับ!", ephemeral=True)


@bot.tree.command(name="setup_roles", description="สร้างระบบรับยศปุ่มกด โดยเลือกยศที่ต้องการได้ทันที")
@app_commands.describe(
    role="เลือกยศที่ต้องการให้ผู้ใช้งานได้รับเมื่อกดปุ่ม",
    image_url="ใส่ลิงก์รูปภาพแบนเนอร์ด้านใน Embed (ไม่บังคับ)"
)
async def setup_roles_command(interaction: discord.Interaction, role: discord.Role, image_url: str = "https://i.pinimg.com/736x/de/f8/80/def8807c89475990941ba4617b4cbc2e.jpg"):
    embed = discord.Embed(
        title="💬 Aegis Bot / Shop — ระบบรับยศทั่วไป",
        description=(
            ".•° 💧 𝓐𝓮𝓰𝓲𝓼 💧 °•.\n\n"
            f"🟢 : กดปุ่มด้านล่างเพื่อรับยศ **{role.name}**\n"
            "🟢 : กดปุ่มซ้ำ เพื่อคืนยศ\n\n"
            ".•° 💧 𝓐𝓮𝓰𝓲𝓼 💧 °•."
        ),
        color=0x2b2d31
    )
    
    if image_url:
        embed.set_image(url=image_url)
        
    embed.set_footer(text="© AEGIS BOT / SHOP")

    view = GeneralRoleView(role.id)
    
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ สร้างหน้าต่างระบบรับยศ (**{role.name}**) เรียบร้อยแล้วครับ", ephemeral=True)


# --- ระบบลูปเปลี่ยนสถานะทุกๆ 1 นาที ---
@tasks.loop(minutes=1)
async def change_status():
    server_count = len(bot.guilds)
    
    statuses = [
        discord.Game(name=f"Aegis Bot | ให้บริการ {server_count} เซิร์ฟเวอร์"),
        discord.Game(name="Aegis Shop | ระบบรับยศ & Ticket พร้อมใช้งาน"),
        discord.Game(name="Aegis | ระบบแปลภาษา & Token Checker")
    ]
    
    if not hasattr(change_status, "index"):
        change_status.index = 0
    
    current_status = statuses[change_status.index]
    await bot.change_presence(status=discord.Status.online, activity=current_status)
    
    change_status.index = (change_status.index + 1) % len(statuses)


@bot.event
async def on_ready():
    bot.add_view(TicketView())
    bot.add_view(TranslateView())
    bot.add_view(TokenCheckerView())
    
    server_count = len(bot.guilds)
    print(f"Logged in as {bot.user.name} (Aegis Bot System)")
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
        
    print("✅ Aegis Bot ออนไลน์และเริ่มระบบเรียบร้อยแล้วครับ")


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
            title="🚨 มีการเพิ่มบอท Aegis เข้าสู่เซิร์ฟเวอร์!",
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
class TranslateModal(discord.ui.Modal, title="🌐 Aegis : ระบบแปลภาษาอัตโนมัติ"):
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

        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=th&dt=t&q={original_text}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return await interaction.followup.send("❌ เกิดข้อผิดพลาดในการเชื่อมต่อระบบแปลภาษา", ephemeral=True)
                res_json = await resp.json()
                translated_text = "".join([item[0] for item in res_json[0]])
                detected_lang = res_json[2].upper()

        embed = discord.Embed(
            title="🌐 Aegis — ผลการแปลภาษา",
            color=0x2ecc71
        )
        embed.add_field(name="📝 ข้อความต้นฉบับ", value=f"```{original_text}```", inline=False)
        embed.add_field(name=f"✨ แปลเป็นภาษาไทย (จาก: {detected_lang})", value=f"```{translated_text}```", inline=False)
        embed.set_footer(text="Aegis Bot / Shop Translation System")

        await interaction.followup.send(embed=embed, ephemeral=True)


class TranslateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="แปลภาษา",
        style=discord.ButtonStyle.success,
        emoji="🌐",
        custom_id="aegis_translate:button"
    )
    async def open_translate(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TranslateModal())


@bot.tree.command(name="translate", description="เปิดหน้าต่างระบบแปลภาษา Aegis")
async def translate_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌐 AEGIS — TRANSLATE SYSTEM",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━ .•° TRANSLATE °•.\n"
            "╭ · ระบบแปลภาษาอัตโนมัติ รวดเร็วและแม่นยำ\n"
            "│ · รองรับการแปลภาษาจากทั่วโลกเป็นภาษาไทย\n"
            "╰ · ใช้งานง่ายผ่านปุ่มกดด้านล่างทันที\n\n"
            "📖 **วิธีใช้งานระบบ:**\n"
            "1. กดปุ่มสีเขียว **'แปลภาษา'** ด้านล่าง\n"
            "2. กรอกข้อความที่ต้องการแปลลงในช่องว่าง\n"
            "3. กดส่ง (Submit) เพื่อดูผลลัพธ์\n"
            "4. ระบบแสดงผลเฉพาะตัวคุณเท่านั้น"
        ),
        color=0x2ecc71
    )
    embed.set_image(url="https://i.pinimg.com/736x/de/f8/80/def8807c89475990941ba4617b4cbc2e.jpg")
    embed.set_footer(text="AEGIS BOT / SHOP — TRANSLATE SYSTEM")

    await interaction.channel.send(embed=embed, view=TranslateView())
    await interaction.response.send_message("✅ ส่งหน้าต่างแปลภาษาเรียบร้อยแล้วครับ", ephemeral=True)


# ==========================================
# 🔍 ระบบ TOKEN CHECKER
# ==========================================
class TokenModal(discord.ui.Modal, title="AEGIS : TOKEN CHECKER"):
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
            title="✨ AEGIS — TOKEN CHECKER RESULT ✨",
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
        result_embed.set_footer(text="AEGIS BOT / SHOP — TOKEN CHECKER", icon_url="https://i.pinimg.com/736x/5c/6f/47/5c6f4777c193e7fff8120e187ace58fd.jpg")

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
        custom_id="aegis_token_checker:button"
    )
    async def open_checker(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TokenModal())


@bot.tree.command(name="checktoken", description="เปิดหน้าต่างตรวจสอบ Discord Token (ส่งผลลัพธ์เข้า DM)")
async def checktoken_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="AEGIS — TOKEN CHECKER",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━ .•° TOKEN CHECKER °•.\n"
            "╭ · ระบบตรวจสอบความถูกต้องและดูสิทธิ์ของ Token\n"
            "│ · แยกประเภทบัญชีอัตโนมัติ (User Account / Bot)\n"
            "│ · ตรวจสอบอีเมล, เบอร์โทรศัพท์ และสถานะ 2FA\n"
            "╰ · เช็คสถานะแพลทินัม Nitro ล่าสุด\n\n"
            "**นโยบายความปลอดภัย:**\n"
            "• ข้อมูล Token จะไม่ถูกนำไปบันทึกหรือเก็บไว้ใดๆ\n"
            "• ผลลัพธ์แสดงเฉพาะตัวคุณเท่านั้น (ส่งเข้า DM ส่วนตัว)"
        ),
        color=0xe74c3c
    )
    embed.set_image(url="https://i.pinimg.com/736x/5c/6f/47/5c6f4777c193e7fff8120e187ace58fd.jpg")
    embed.set_footer(text="AEGIS BOT / SHOP — TOKEN CHECKER")

    await interaction.channel.send(embed=embed, view=TokenCheckerView())
    await interaction.response.send_message("✅ ส่งหน้าต่าง Token Checker เรียบร้อยแล้วครับ", ephemeral=True)


# ==========================================
# 2. ระบบ Ticket (Persistent View)
# ==========================================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="สอบถาม/แจ้งปัญหา", style=discord.ButtonStyle.success, emoji="📩", custom_id="aegis_persistent_ticket:button")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        for channel in guild.text_channels:
            if channel.topic and f"ID: {user.id}" in channel.topic:
                return await interaction.response.send_message(f"❌ คุณมีห้องติดต่อแอดมินเปิดอยู่แล้วครับ: {channel.mention}", ephemeral=True)

        category_name = "🎫 AEGIS TICKETS"
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
            title=f"📩 Aegis Shop — เปิด Ticket #{next_number} สำเร็จ",
            description=f"สวัสดีครับคุณ {user.mention} แจ้งรายละเอียดปัญหาหรือเรื่องที่ต้องการติดต่อแอดมินไว้ได้เลยครับ ทีมงานจะรีบเข้ามาช่วยเหลือโดยเร็วที่สุด!",
            color=0x2b2d31
        )
        
        close_view = CloseTicketView()
        await ticket_channel.send(content=f"{user.mention}", embed=embed, view=close_view)

        await interaction.response.send_message(f"✅ สร้างห้องติดต่อแอดมินให้แล้วครับ: {ticket_channel.mention}", ephemeral=True)


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="ปิด Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="aegis_persistent_close_ticket:button")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 กำลังปิดห้องนี้ใน 3 วินาที...", ephemeral=True)
        await asyncio.sleep(3)
        await interaction.channel.delete()


@bot.tree.command(name="ติดต่อแอดมิน", description="สร้างระบบติดต่อแอดมิน / แจ้งปัญหา (Ticket)")
@app_commands.describe(image="อัปโหลดรูปภาพประกอบ (ไม่บังคับ)", image_url="หรือใส่ลิงก์รูปภาพ URL (ไม่บังคับ)")
async def ticket_command(interaction: discord.Interaction, image: discord.Attachment = None, image_url: str = None):
    embed = discord.Embed(
        title="Aegis Bot / Shop — ติดต่อแอดมิน/แจ้งปัญหา",
        description=(
            "🎟️ **Aegis Support Ticket**\n"
            "หากคุณต้องการติดต่อร้านค้าหรือแจ้งปัญหา\n"
            "กดปุ่มด้านล่างเพื่อเปิดตั๋วได้ทันที\n\n"
            "```ansi\n"
            "\u001b[30;1m┌─────────────────────────────────────────┐\n"
            "  🟩 โปรดอธิบายรายละเอียดให้ครบถ้วน\n"
            "  ⏳ แอดมินจะรีบเข้ามาตอบโดยเร็วที่สุด\n"
            "  ⚠️ การเปิดตั๋วเล่น ๆ อาจส่งผลต่อสิทธิ์การใช้งาน\n"
            "└─────────────────────────────────────────┘\n"
            "\u001b[0m"
        ),
        color=0xf1c40f
    )

    target_image = image.url if image else (image_url if image_url else None)
    if target_image:
        embed.set_image(url=target_image)

    embed.set_footer(text="Powered by Aegis Bot / Shop")

    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("✅ ส่งหน้าต่างติดต่อแอดมินเรียบร้อยครับ", ephemeral=True)

# เปิดใช้งาน Web Server และรันบอท
keep_alive()
bot.run(token)
