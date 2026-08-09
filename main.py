import os
import discord
from discord import app_commands
from discord.ext import commands

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

    # ระบบเข้าห้องเสียงอัตโนมัติ
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
# ระบบ Slash Command: /ticket (ดีไซน์ตามรูปตัวอย่าง)
# ---------------------------------------------------------
@bot.tree.command(name="ticket", description="🎫 ส่งข้อความระบบเปิดตั๋ว Ticket สำหรับสมาชิกทุกคน")
async def ticket(interaction: discord.Interaction):
    # ฟังก์ชันเมื่อมีคนกดปุ่ม OPEN TICKET
    async def button_callback(button_interaction: discord.Interaction):
        guild = button_interaction.guild
        user = button_interaction.user
        channel_name = f"ticket-{user.name}"

        # ตั้งค่าสิทธิ์ (เห็นเฉพาะตัวผู้ใช้, แอดมิน, และบอท)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        # ค้นหายศแอดมิน (เปลี่ยนคำว่า "Admin" เป็นชื่อยศจริงในเซิร์ฟเวอร์ของคุณ)
        admin_role = discord.utils.get(guild.roles, name="Admin") 
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        try:
            # สร้างห้องแชทส่วนตัว
            ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)
            
            await button_interaction.response.send_message(
                f'🔒 สร้างห้องส่วนตัวให้คุณเรียบร้อยแล้ว! ไปพูดคุยต่อได้ที่: {ticket_channel.mention}', 
                ephemeral=True
            )

            # แท็กแอดมินในห้องส่วนตัว
            ping_text = admin_role.mention if admin_role else "@here"
            await ticket_channel.send(
                f"👋 สวัสดีครับ {user.mention}\n"
                f"นี่คือห้องตั๋วส่วนตัวของคุณ มีปัญหาอะไรแจ้งไว้ได้เลยครับ!\n"
                f"🔔 แจ้งเตือนทีมงาน: {ping_text}"
            )
        except Exception as e:
            await button_interaction.response.send_message(f'❌ เกิดข้อผิดพลาดในการสร้างห้อง: {e}', ephemeral=True)

    # สร้างปุ่ม OPEN TICKET สีม่วง (Blurple) พร้อมไอคอนตั๋ว 🎫
    button = discord.ui.Button(label="OPEN TICKET", emoji="🎫", style=discord.ButtonStyle.blurple)
    button.callback = button_callback
    
    view = discord.ui.View()
    view.add_item(button)

    # สร้าง Embed ดีไซน์ตามภาพตัวอย่าง
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
        color=0xFEE75C # สีเหลืองทองแถบข้างตามรูป
    )
    # ใส่รูปภาพขนาดเล็กมุมขวาบน (Thumbnail) และรูปภาพใหญ่ตรงกลาง (Image) ตามแบบในรูป
    embed.set_thumbnail(url="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=500") # รูปตัวอย่างมุมขวาบน
    embed.set_image(url="https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=500")    # รูปแบนเนอร์ตรงกลาง
    embed.set_footer(text="Powered by Ticket System", icon_url=bot.user.avatar.url if bot.user.avatar else None)

    # ส่งข้อความออกไปในห้องแชทให้ทุกคนเห็น
    await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ Error: Please set DISCORD_TOKEN in environment variables.")
