import os
import threading
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask

# ---------------------------------------------------------
# 1. ส่วนของ Web Server (Flask) สำหรับรันบน Render 24/7
# ---------------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Voice Bot & Ticket System is running 24/7!"

# ---------------------------------------------------------
# 2. ส่วนของ Discord Bot
# ---------------------------------------------------------
intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
intents.message_content = True

class VoiceBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("🚀 Slash commands synced successfully.")

bot = VoiceBot()

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user.name} (ID: {bot.user.id})')
    
    # กำหนดจุดสีสถานะของบอทให้เป็นสีเหลือง (Idle) ค้างไว้ตลอดเวลา
    await bot.change_presence(
        status=discord.Status.idle, 
        activity=discord.Game(name="🎧 ระบบออนช่องเสียง & Ticket 24 ชม.")
    )
    print("🟡 Bot status set to Idle (Yellow Dot).")

    # ระบบเข้าห้องเสียงอัตโนมัติ (ดึง ID จาก Environment Variable: VOICE_CHANNEL_ID)
    channel_id_str = os.environ.get("VOICE_CHANNEL_ID")
    if channel_id_str:
        try:
            channel_id = int(channel_id_str)
            channel = bot.get_channel(channel_id)
            if channel and isinstance(channel, discord.VoiceChannel):
                if not channel.guild.voice_client:
                    await channel.connect()
                    print(f"🔊 Auto-connected to voice channel: {channel.name}")
        except Exception as e:
            print(f"❌ Failed to auto-connect to voice channel: {e}")

# ---------------------------------------------------------
# 3. คำสั่ง Slash Commands (เลือกห้องเสียง & ออกจากห้อง)
# ---------------------------------------------------------
@bot.tree.command(name="join", description="🔊 เลือกช่องเสียงเพื่อให้บอทเข้าไปสิง")
@app_commands.describe(channel="เลือกห้องเสียงที่ต้องการให้บอทเข้าไป")
async def join(interaction: discord.Interaction, channel: discord.VoiceChannel):
    voice_client = interaction.guild.voice_client
    try:
        if voice_client:
            await voice_client.move_to(channel)
        else:
            await channel.connect()
        await interaction.response.send_message(f'🎧 บอทเข้ามาที่ห้องเสียง **{channel.name}** เรียบร้อยแล้ว!', ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f'❌ เกิดข้อผิดพลาด: {e}', ephemeral=True)

@bot.tree.command(name="leave", description="👋 สั่งให้บอทออกจากช่องเสียงปัจจุบัน")
async def leave(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client:
        await voice_client.disconnect()
        await interaction.response.send_message('👋 บอทออกจากห้องเสียงเรียบร้อยแล้ว', ephemeral=False)
    else:
        await interaction.response.send_message('⚠️ บอทยังไม่ได้อยู่ในห้องเสียงไหนเลย', ephemeral=True)

# ---------------------------------------------------------
# 4. คำสั่งระบบ Ticket (สร้างห้องส่วนตัว + แท็กแอดมิน)
# ---------------------------------------------------------
@bot.tree.command(name="ticket", description="🎫 สร้างปุ่มสำหรับเปิดตั๋วติดต่อทีมงานแบบห้องส่วนตัว")
async def ticket(interaction: discord.Interaction):
    view = discord.ui.View()
    
    async def button_callback(button_interaction: discord.Interaction):
        guild = button_interaction.guild
        user = button_interaction.user

        # ค้นหา Category สำหรับเก็บห้อง Ticket (ถ้าไม่อยากแยกหมวด สามารถข้ามได้)
        # ตั้งชื่อห้องส่วนตัวตามชื่อผู้ใช้ เช่น ticket-ชื่อผู้ใช้
        channel_name = f"ticket-{user.name}"

        # ตั้งค่าสิทธิ์การมองเห็นห้อง (เห็นเฉพาะตัวผู้ใช้, แอดมิน, และบอท)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False), # คนทั่วไปมองไม่เห็น
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True), # ผู้ใช้เห็น
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True) # บอทจัดการได้
        }

        # ค้นหาบทบาท (Role) แอดมินในเซิร์ฟเวอร์ (สามารถเปลี่ยนชื่อ "Admin" เป็นชื่อยศแอดมินของคุณจริง ๆ ได้)
        admin_role = discord.utils.get(guild.roles, name="Admin") 
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        try:
            # สร้างห้องข้อความใหม่แบบส่วนตัว
            ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)
            
            # ตอบกลับผู้ใช้แบบเห็นคนเดียวว่าสร้างห้องสำเร็จแล้ว พร้อมส่งลิงก์ห้อง
            await button_interaction.response.send_message(
                f'🔒 สร้างห้องส่วนตัวให้คุณเรียบร้อยแล้วครับ! ไปพูดคุยต่อได้ที่: {ticket_channel.mention}', 
                ephemeral=True
            )

            # ส่งข้อความต้อนรับและแท็กแอดมินในห้องส่วนตัวที่เพิ่งสร้าง
            ping_text = admin_role.mention if admin_role else "@here"
            await ticket_channel.send(
                f"👋 สวัสดีครับ {user.mention}\n"
                f"นี่คือห้องตั๋วส่วนตัวของคุณ มีปัญหาอะไรแจ้งไว้ได้เลยครับ!\n"
                f"🔔 แจ้งเตือนทีมงาน: {ping_text}"
            )
        except Exception as e:
            await button_interaction.response.send_message(f'❌ เกิดข้อผิดพลาดในการสร้างห้อง: {e}', ephemeral=True)

    button = discord.ui.Button(label="🎫 กดเพื่อเปิดห้อง Ticket ส่วนตัว", style=discord.ButtonStyle.green)
    button.callback = button_callback
    view.add_item(button)

    await interaction.response.send_message(
        "✨ **ระบบเปิดตั๋วติดต่อทีมงาน (Ticket System)**\n"
        "คลิกปุ่มด้านล่างนี้ ระบบจะสร้างห้องแชทส่วนตัวให้คุณและแท็กแอดมินให้อัตโนมัติครับ:", 
        view=view, 
        ephemeral=True
    )

# ---------------------------------------------------------
# 5. ฟังก์ชันรันบอทคู่กับ Web Server (Background Thread)
# ---------------------------------------------------------
def run_bot():
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ Error: Please set DISCORD_TOKEN in environment variables.")

if __name__ == "__main__":
    if not hasattr(app, "bot_started"):
        app.bot_started = True
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
