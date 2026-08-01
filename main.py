import discord
from discord import app_commands
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# --- ระบบเปิดเว็บจำลองสำหรับ Render ---
app = Flask('')

@app.route('/')
def home():
    return "Multi-System Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ------------------------------------

token = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    # ลงทะเบียน Persistent Views ให้ปุ่มยังใช้งานได้หลังบอทรีสตาร์ท
    bot.add_view(PersistentVerifyView())
    bot.add_view(TicketView())
    
    print(f"Logged in as {bot.user.name} (Verify & Ticket Persistent Mode)")
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    streaming_activity = discord.Streaming(
        name="ระบบยืนยันตัวตนและ Ticket พร้อมใช้งานครับ",
        url="https://www.twitch.tv/discord"
    )
    await bot.change_presence(status=discord.Status.online, activity=streaming_activity)
    print("✅ บอทออนไลน์ในสถานะสตรีมมิ่ง (เม็ดม่วง) เรียบร้อยแล้วครับ")


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
        # ค้นหายศในเซิร์ฟเวอร์จากชื่อยศมาตรฐาน หรือจะตั้งค่าตามต้องการ
        role = discord.utils.get(interaction.guild.roles, name="Verified") or discord.utils.get(interaction.guild.roles, name="Member")
        
        if not role:
            # หากหาไม่เจอ ให้หายศแรกสุดที่เป็นยศแจก หรือแจ้งเตือนให้แอดมินตั้งชื่อยศให้ตรงกัน
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
            "\u001b[32m┌─────────────────────────────┐\n"
            "  ✨ Welcome to our Server ✨\n"
            "└─────────────────────────────┘\n"
            "\u001b[0m```\n"
            "☘️ เพื่อรับสิทธิ์ในการใช้งานและพูดคุย\n"
            "🍀 กรุณากดปุ่มด้านล่างเพื่อ **ยืนยันตัวตน**\n\n"
            f"» ยศที่คุณจะได้รับคือ: {role.mention}\n\n"
            "```ansi\n"
            "\u001b[32m┌─────────── •°·.•°- ───────────┐\n"
            "  🍀 กดเลย แล้วเจอกันข้างใน! 🦋\n"
            "└─────────── •°·.•°- ───────────┘\n"
            "\u001b[0m"
        ),
        color=0x2b2d31
    )

    target_image = image.url if image else (image_url if image_url else None)
    if target_image:
        embed.set_image(url=target_image)

    # ส่งข้อความพร้อมติด View แบบ Persistent
    await interaction.channel.send(
        embed=embed,
        view=PersistentVerifyView()
    )

    await interaction.response.send_message(
        "✅ สร้างหน้าต่างยืนยันตัวตนเรียบร้อยครับ",
        ephemeral=True
    )


# ==========================================
# 2. ระบบ Ticket ติดต่อแอดมิน (Persistent View)
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

        existing_channel = discord.utils.get(guild.text_channels, name=f"ticket-{user.name.lower()}")
        if existing_channel:
            return await interaction.response.send_message(
                f"❌ คุณมีห้องติดต่อแอดมินเปิดอยู่แล้วครับ: {existing_channel.mention}",
                ephemeral=True
            )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            overwrites=overwrites,
            topic=f"Ticket ของคุณ {user.name} (ID: {user.id})"
        )

        embed = discord.Embed(
            title="📩 เปิด Ticket สำเร็จ",
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

keep_alive()
bot.run(token)
