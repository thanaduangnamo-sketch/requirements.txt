import os
import threading
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask

# 1. ส่วนของเว็บเซิร์ฟเวอร์ Flask เพื่อเปิดพอร์ตให้ Render ตรวจพบ
app = Flask('')

@app.route('/')
def home():
    return "Voice Bot & Ticket System is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 2. ส่วนของบอท Discord
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
    
    # กำหนดจุดสีสถานะของบอทให้เป็นสีเทา (Invisible) ค้างไว้ตลอดเวลา
    await bot.change_presence(
        status=discord.Status.invisible, 
        activity=discord.Game(name="🎧 ระบบออนช่องเสียง & Ticket 24 ชม.")
    )
    print("⚪ Bot status set to Invisible (Gray Dot).")

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
# คำสั่งที่ 1: /join (ดึงบอทเข้าห้องเสียง)
# ---------------------------------------------------------
@bot.tree.command(name="join", description="🔊 สั่งให้บอทเข้ามาในช่องเสียงที่คุณอยู่")
async def join(interaction: discord.Interaction):
    if interaction.user.voice and interaction.user.voice.channel:
        channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client
        try:
            if voice_client:
                await voice_client.move_to(channel)
            else:
                await channel.connect()
            await interaction.response.send_message(f'🎧 ดึงบอทเข้าห้อง **{channel.name}** สำเร็จ!', ephemeral=False)
        except Exception as e:
            await interaction.response.send_message(f'❌ เกิดข้อผิดพลาด: {e}', ephemeral=True)
    else:
        await interaction.response.send_message('⚠️ กรุณาเข้าห้องเสียงก่อนใช้คำสั่งนี้!', ephemeral=True)

# ---------------------------------------------------------
# คำสั่งที่ 2: /leave (ให้บอทออกจากห้องเสียง)
# ---------------------------------------------------------
@bot.tree.command(name="leave", description="👋 สั่งให้บอทออกจากช่องเสียงปัจจุบัน")
async def leave(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client:
        await voice_client.disconnect()
        await interaction.response.send_message('👋 บอทออกจากห้องเสียงเรียบร้อยแล้ว', ephemeral=False)
    else:
        await interaction.response.send_message('⚠️ บอทยังไม่ได้อยู่ในห้องเสียงไหนเลย', ephemeral=True)

# ---------------------------------------------------------
# คำสั่งที่ 3: /ticket (ส่งข้อความปุ่มเปิดตั๋ว + รูป Pinterest)
# ---------------------------------------------------------
@bot.tree.command(name="ticket", description="🎫 ส่งข้อความระบบเปิดตั๋ว Ticket สำหรับสมาชิกทุกคน")
async def ticket(interaction: discord.Interaction):
    async def button_callback(button_interaction: discord.Interaction):
        guild = button_interaction.guild
        user = button_interaction.user
        channel_name = f"ticket-{user.name}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        admin_role = discord.utils.get(guild.roles, name="Admin") 
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        try:
            ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)
            
            await button_interaction.response.send_message(
                f'🔒 สร้างห้องส่วนตัวให้คุณเรียบร้อยแล้ว! ไปพูดคุยต่อได้ที่: {ticket_channel.mention}', 
                ephemeral=True
            )

            ping_text = admin_role.mention if admin_role else "@here"
            await ticket_channel.send(
                f"👋 สวัสดีครับ {user.mention}\n"
                f"นี่คือห้องตั๋วส่วนตัวของคุณ มีปัญหาอะไรแจ้งไว้ได้เลยครับ!\n"
                f"🔔 แจ้งเตือนทีมงาน: {ping_text}"
            )
        except Exception as e:
            await button_interaction.response.send_message(f'❌ เกิดข้อผิดพลาดในการสร้างห้อง: {e}', ephemeral=True)

    button = discord.ui.Button(label="OPEN TICKET", emoji="🎫", style=discord.ButtonStyle.blurple)
    button.callback = button_callback
    view = discord.ui.View()
    view.add_item(button)

    pinterest_image_url = "https://i.pinimg.com/736x/99/30/e8/9930e86245884b97783ae63e9d5162fc.jpg"
    
    embed = discord.Embed(
        title="Help & Support\nTicket System",
        description=(
            "🎟️ สั่งซื้อสินค้า ติดต่อแอดมิน ติดต่องาน แจ้งปัญหา "
            "ติดต่อสอบถาม ได้ที่ **Ticket Support 24 Hour**\n\n"
            "⏰\n"
            "Admin สต๊าฟรอ มีแอดมินบริการ ตรวจสอบทุกๆครั้ง "
            "ไม่ต้องเป็นห่วงเรื่องความปลอดภัย เพราะปลอดภัยแน่นอน "
            "ไม่มีหลุด ข้อมูลส่วนตัวของลูกค้าปลอดภัยหายห่วง💯!!"
        ),
        color=0xFEE75C
    )
    embed.set_thumbnail(url=pinterest_image_url)
    embed.set_image(url=pinterest_image_url)
    embed.set_footer(text="Powered by Ticket System", icon_url=bot.user.avatar.url if bot.user.avatar else None)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

# 3. รันเว็บและบอทพร้อมกัน
if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.start()
    
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ Error: Please set DISCORD_TOKEN in environment variables.")
