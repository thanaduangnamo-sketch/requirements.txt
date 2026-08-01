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
    return "Ticket Bot is running!"

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
    print(f"Logged in as {bot.user.name} (Ticket System Mode)")
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    streaming_activity = discord.Streaming(
        name="ระบบติดต่อแอดมินพร้อมใช้งานครับ",
        url="https://www.twitch.tv/discord"
    )
    await bot.change_presence(status=discord.Status.online, activity=streaming_activity)
    print("✅ บอทออนไลน์ในสถานะสตรีมมิ่ง (เม็ดม่วง) เรียบร้อยแล้วครับ")


# --- View สำหรับปุ่มกดเปิด Ticket ---
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="สอบถาม/แจ้งปัญหา",
        style=discord.ButtonStyle.success,
        emoji="📩"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        # ป้องกันการสร้างห้องซ้ำสำหรับผู้ใช้คนเดิม (เช็คชื่อห้อง)
        existing_channel = discord.utils.get(guild.text_channels, name=f"ticket-{user.name.lower()}")
        if existing_channel:
            return await interaction.response.send_message(
                f"❌ คุณมีห้องติดต่อแอดมินเปิดอยู่แล้วครับ: {existing_channel.mention}",
                ephemeral=True
            )

        # ตั้งค่าสิทธิ์การมองเห็นห้อง (ให้เฉพาะแอดมินกับคนที่กดเห็นห้องนี้)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        # สร้างห้องในหมวดหมู่ หรือสร้างปกติ
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
        
        # ปุ่มสำหรับปิด Ticket
        close_view = CloseTicketView()
        await ticket_channel.send(content=f"{user.mention}", embed=embed, view=close_view)

        await interaction.response.send_message(
            f"✅ สร้างห้องติดต่อแอดมินให้แล้วครับ: {ticket_channel.mention}",
            ephemeral=True
        )


# --- View สำหรับปุ่มปิดห้อง Ticket ---
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="ปิด Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 กำลังปิดห้องนี้ใน 3 วินาที...", ephemeral=True)
        import asyncio
        await asyncio.sleep(3)
        await interaction.channel.delete()


# --- คำสั่ง Slash Command สำหรับเรียกหน้าต่างแจ้งปัญหา ---
@bot.tree.command(name="ติดต่อแอดมิน", description="สร้างระบบติดต่อแอดมิน / แจ้งปัญหา (Ticket)")
@app_commands.describe(
    image="อัปโหลดรูปภาพประกอบ Embed (ไม่บังคับ)",
    image_url="หรือใส่ลิงก์รูปภาพ (URL) แทนการอัปโหลด (ไม่บังคับ)"
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
            "  ⚠️ การเปิดตั๋วเล่น ๆ หรือไม่เหมาะสม อาจส่งผลชาติต่อสิทธิ์การใช้งาน\n"
            "└─────────────────────────────────────────┘\n"
            "\u001b[0m"
        ),
        color=0xf1c40f  # แถบสีเหลืองด้านข้างแบบในรูปตัวอย่าง
    )

    target_image = None
    if image:
        target_image = image.url
    elif image_url:
        target_image = image_url

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
