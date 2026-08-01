import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import aiohttp
import asyncio
from flask import Flask
from threading import Thread

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
        discord.Game(name="ระบบแปลภาษา & Webhook Spammer พร้อมใช้งาน")
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
    bot.add_view(WebhookSpamView())
    
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
# 🚀 ระบบส่งข้อความผ่าน Webhook (จำกัดถึง 100 ข้อความ + แจ้งเตือน DM)
# ==========================================
class WebhookSpamModal(discord.ui.Modal, title="🚀 ระบบส่ง Webhook จำนวนมาก"):
    webhook_url = discord.ui.TextInput(
        label="ลิงก์ Webhook (Discord Webhook URL)",
        style=discord.TextStyle.short,
        placeholder="https://discord.com/api/webhooks/...",
        required=True
    )
    message_content = discord.ui.TextInput(
        label="ข้อความที่ต้องการส่ง",
        style=discord.TextStyle.paragraph,
        placeholder="พิมพ์ข้อความที่ต้องการส่งซ้ำๆ...",
        required=True,
        max_length=1000
    )
    count_input = discord.ui.TextInput(
        label="จำนวนครั้งที่ต้องการส่ง (สูงสุด 100)",
        style=discord.TextStyle.short,
        placeholder="ใส่ตัวเลข 1 ถึง 100",
        required=True,
        max_length=3
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        url = self.webhook_url.value.strip()
        text = self.message_content.value.strip()
        raw_count = self.count_input.value.strip()

        if not url.startswith("https://discord.com/api/webhooks/") and not url.startswith("https://discordapp.com/api/webhooks/"):
            return await interaction.followup.send("❌ **ลิงก์ Webhook ไม่ถูกต้อง!** กรุณาตรวจสอบลิงก์ใหม่อีกครั้ง", ephemeral=True)

        if not raw_count.isdigit():
            return await interaction.followup.send("❌ **จำนวนครั้งไม่ถูกต้อง!** กรุณาใส่เป็นตัวเลขเท่านั้น", ephemeral=True)
        
        count = int(raw_count)
        if count < 1 or count > 100:
            return await interaction.followup.send("❌ **จำกัดจำนวนครั้งระหว่าง 1 ถึง 100 เท่านั้นครับ!**", ephemeral=True)

        await interaction.followup.send(f"⏳ กำลังดำเนินการส่งข้อความผ่าน Webhook จำนวน `{count}` ครั้ง... โปรดรอสักครู่ ระบบจะแจ้งเตือนไปที่ DM เมื่อเสร็จสิ้น", ephemeral=True)

        success_count = 0
        failed_count = 0

        async with aiohttp.ClientSession() as session:
            for i in range(count):
                payload = {"content": text}
                try:
                    async with session.post(url, json=payload) as resp:
                        if resp.status in [200, 204]:
                            success_count += 1
                        else:
                            failed_count += 1
                except Exception:
                    failed_count += 1
                
                await asyncio.sleep(0.5)

        dm_embed = discord.Embed(
            title="📊 สรุปผลการส่งข้อความ Webhook",
            description=(
                f"✅ **ส่งสำเร็จ:** `{success_count}` ครั้ง\n"
                f"❌ **ส่งไม่สำเร็จ:** `{failed_count}` ครั้ง\n"
                f"📌 **จำนวนที่ตั้งไว้:** `{count}` ครั้ง\n\n"
                f"📝 **ข้อความที่ส่ง:**\n```{text}```"
            ),
            color=0x3498db
        )
        dm_embed.set_footer(text="ICEWEN_2 : Webhook Spammer System")

        try:
            user = interaction.user
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            print(f"ไม่สามารถส่ง DM หา {interaction.user.name} ได้เนื่องจากปิดรับข้อความส่วนตัว")


class WebhookSpamView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="ส่ง Webhook (สูงสุด 100)",
        style=discord.ButtonStyle.primary,
        emoji="🚀",
        custom_id="icewen_webhook_spam:button"
    )
    async def open_webhook_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(WebhookSpamModal())


@bot.tree.command(name="webhook", description="เปิดหน้าต่างส่งข้อความผ่าน Webhook (จำกัดสูงสุด 100 ครั้ง แจ้งเตือนเข้า DM)")
async def webhook_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🚀 WEBHOOK SPAMMER | ระบบส่งข้อความผ่านเว็บฮุค",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━ .•° WEBHOOK °•.\n"
            "╭ · ระบบส่งข้อความอัตโนมัติผ่าน Discord Webhook\n"
            "│ · กำหนดข้อความและจำนวนครั้งได้ตามต้องการ\n"
            "│ · รองรับการส่งสูงสุดถึง **100 ข้อความ** ต่อครั้ง\n"
            "╰ · ระบบจะทำการ **แจ้งเตือนสรุปผลเข้า DM** ทันทีที่ทำงานเสร็จ!\n\n"
            "📖 **วิธีใช้งานระบบ:**\n"
            "1. กดปุ่มสีฟ้า **'ส่ง Webhook (สูงสุด 100)'** ด้านล่าง\n"
            "2. กรอกลิงก์ Webhook URL ของคุณ\n"
            "3. ใส่ข้อความที่ต้องการส่ง\n"
            "4. ใส่จำนวนครั้ง (1 - 100) แล้วกด Submit ได้เลย!"
        ),
        color=0x3498db
    )
    # อัปเดตรูปภาพใหม่ตามที่คุณให้มา
    embed.set_image(url="https://i.pinimg.com/736x/ba/39/4d/ba394dfe32869d5078c3d94a69dff0ce.jpg")
    embed.set_footer(text="ICEWEN_2 : WEBHOOK SYSTEM")

    await interaction.channel.send(embed=embed, view=WebhookSpamView())
    await interaction.response.send_message("✅ ส่งหน้าต่าง Webhook Spammer เรียบร้อยแล้วครับ", ephemeral=True)


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

        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=th&dt=t&q={original_text}"
        
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
# 1. ระบบยืนยันตัวตน (Persistent View)
# ==========================================
class PersistentVerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="ยืนยันตัวตน",
        style=discord.ButtonStyle.success,
        emoji="🍀",
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
        await interaction.response.send_message(
            f"✅ รับยศ {role.mention} เรียบร้อยแล้ว",
            ephemeral=True
        )


@bot.tree.command(name="ยืนยันตัวตน", description="สร้างระบบยืนยันตัวตนสไตล์เท่ๆ")
@app_commands.describe(
    role="เลือกยศที่ต้องการให้ผู้ใช้งานได้รับ",
    image="อัปโหลดรูปภาพประกอบ (ไม่บังคับ)",
    image_url="หรือใส่ลิงก์รูปภาพ URL (ไม่บังคับ)"
)
async def verify_command(
    interaction: discord.Interaction, 
    role: discord.Role, 
    image: discord.Attachment = None,
    image_url: str = None
):
    embed = discord.Embed(
        title="🧸 ระบบยืนยันตัวตน",
        description=(
            "```ansi\n"
