import os
import random
import threading
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask

# 1. ส่วนของเว็บเซิร์ฟเวอร์ Flask เพื่อเปิดพอร์ตให้ Render ตรวจพบ
app = Flask('')

@app.route('/')
def home():
    return "Voice Bot, Ticket, Verification, Rules & Invite System is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 2. ส่วนของบอท Discord
intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
intents.message_content = True

# --- ระบบ Modal สำหรับกรอกรหัสยืนยันตัวตน ---
class VerifyModal(discord.ui.Modal, title="ระบบยืนยันตัวตน"):
    code_input = discord.ui.TextInput(
        label="กรุณากรอกรหัส 6 หลักที่แสดงด้านล่าง",
        placeholder="เช่น 123456",
        max_length=6,
        min_length=6,
        required=True
    )

    def __init__(self, expected_code: str):
        super().__init__()
        self.expected_code = expected_code

    async def on_submit(self, interaction: discord.Interaction):
        if self.code_input.value.strip() == self.expected_code:
            guild = interaction.guild
            member = interaction.user
            
            role = discord.utils.get(guild.roles, name="Member")
            
            if role:
                try:
                    await member.add_roles(role)
                    await interaction.response.send_message("✅ ยืนยันตัวตนสำเร็จ! คุณได้รับยศ Member เรียบร้อยแล้วครับ 🎉", ephemeral=True)
                except Exception as e:
                    await interaction.response.send_message(f"❌ เกิดข้อผิดพลาดในการมอบยศ: {e}", ephemeral=True)
            else:
                await interaction.response.send_message("❌ ไม่พบยศ 'Member' ในเซิร์ฟเวอร์นี้ กรุณาแจ้งแอดมิน", ephemeral=True)
        else:
            await interaction.response.send_message("❌ รหัสยืนยันตัวตนไม่ถูกต้อง! กรุณาลองใหม่อีกครั้ง", ephemeral=True)

# --- ระบบ View ยืนยันตัวตนแบบ Persistent ---
class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="ยืนยันตัวตน", emoji="✅", style=discord.ButtonStyle.green, custom_id="persistent_verify_button_id")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        random_code = str(random.randint(100000, 999999))
        modal = VerifyModal(expected_code=random_code)
        modal.code_input.label = f"กรอกรหัส 6 หลักนี้: {random_code}"
        await interaction.response.send_modal(modal)

# --- ระบบ View สำหรับ Ticket แบบ Persistent ---
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="OPEN TICKET", emoji="🎫", style=discord.ButtonStyle.blurple, custom_id="persistent_ticket_button_id")
    async def ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
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
            
            await interaction.response.send_message(
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
            await interaction.response.send_message(f'❌ เกิดข้อผิดพลาดในการสร้างห้อง: {e}', ephemeral=True)

# --- ระบบ View สำหรับกฎประจำเซิร์ฟเวอร์แบบ Persistent ---
class RulesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="รับทราบและยอมรับกฎ", emoji="📜", style=discord.ButtonStyle.success, custom_id="persistent_rules_button_id")
    async def rules_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("✅ ขอบคุณที่อ่านและยอมรับกฎของเซิร์ฟเวอร์เราครับ ขอให้สนุก!", ephemeral=True)

class VoiceBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        self.add_view(TicketView())
        self.add_view(VerifyView())
        self.add_view(RulesView())
        await self.tree.sync()
        print("🚀 Slash commands synced and Persistent Views loaded successfully.")

bot = VoiceBot()

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user.name} (ID: {bot.user.id})')
    
    # ตั้งค่าสถานะจุดสีแดง (DND)
    await bot.change_presence(
        status=discord.Status.dnd, 
        activity=discord.Game(name="🎧 ระบบออนช่องเสียง & Invite 24 ชม.")
    )
    print("🔴 Bot status set to Do Not Disturb (Red Dot).")

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

# คำสั่ง /join
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

# คำสั่ง /leave
@bot.tree.command(name="leave", description="👋 สั่งให้บอทออกจากช่องเสียงปัจจุบัน")
async def leave(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client:
        await voice_client.disconnect()
        await interaction.response.send_message('👋 บอทออกจากห้องเสียงเรียบร้อยแล้ว', ephemeral=False)
    else:
        await interaction.response.send_message('⚠️ บอทยังไม่ได้อยู่ในห้องเสียงไหนเลย', ephemeral=True)

# คำสั่ง /ticket
@bot.tree.command(name="ticket", description="🎫 ส่งข้อความระบบเปิดตั๋ว Ticket สำหรับสมาชิกทุกคน")
async def ticket(interaction: discord.Interaction):
    view = TicketView()
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

# คำสั่ง /verify
@bot.tree.command(name="verify", description="🛡️ ส่งข้อความระบบยืนยันตัวตน (Verify)")
async def verify(interaction: discord.Interaction):
    view = VerifyView()
    
    embed = discord.Embed(
        title="</> ระบบยืนยันตัวตน",
        description=(
            "> 🔑 กดปุ่มด้านล่างเพื่อเริ่มยืนยันตัวตน\n"
            "> {/} ระบบจะส่งรหัส 6 หลัก ให้คุณกรอก\n"
            "> 🟩 กรอกรหัสถูกต้อง $\\rightarrow$ ได้รับ `@ · Member` ทันที\n"
            "> 🩵 พร้อมให้บริการตลอด 24 ชั่วโมง"
        ),
        color=0x5865F2
    )

    await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

# คำสั่ง /rules
@bot.tree.command(name="rules", description="📜 ส่งข้อความกฎระเบียบประจำเซิร์ฟเวอร์")
async def rules(interaction: discord.Interaction):
    view = RulesView()
    
    embed = discord.Embed(
        title="📜 กฎระเบียบประจำเซิร์ฟเวอร์ (Server Rules)",
        description=(
            "**1. ให้เกียรติซึ่งกันและกัน**\n"
            "> ห้ามเหยียดหยาม ดูหมิ่น หรือใช้คำพูดรุนแรงต่อสมาชิกท่านอื่น\n\n"
            "**2. ห้ามสแปมข้อความหรือรูปภาพ**\n"
            "> ห้ามส่งข้อความซ้ำๆ รัวๆ หรือส่งภาพที่ไม่เหมาะสมในช่องแชททั่วไป\n\n"
            "**3. ห้ามโปรโมทหรือโฆษณาโดยไม่ได้รับอนุญาต**\n"
            "> ห้ามโพสต์ลิงก์กลุ่ม ลิงก์ดิสอื่น หรือชวนโปรโมทสินค้าในแชทส่วนรวม\n\n"
            "**4. ปฏิบัติตามคำสั่งของทีมงาน (Admin / Staff)**\n"
            "> การตัดสินใจของแอดมินถือเป็นที่สิ้นสุดในทุกกรณี\n\n"
            "⚠️ *หากฝ่าฝืนกฎ มีโทษตั้งแต่ตักเตือนจนถึงแบนออกจากเซิร์ฟเวอร์*"
        ),
        color=0xE74C3C
    )
    embed.set_footer(text="กรุณาอ่านและปฏิบัติตามอย่างเคร่งครัด", icon_url=bot.user.avatar.url if bot.user.avatar else None)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

# คำสั่ง /invite (สร้างลิงค์เชิญถาวร ไม่มีวันหมดอายุ)
@bot.tree.command(name="invite", description="🔗 สร้างและส่งลิงค์เชิญเข้าเซิร์ฟเวอร์แบบถาวร (ไม่มีวันหมดอายุ)")
async def invite(interaction: discord.Interaction):
    try:
        # เช็คว่าห้องแชทปัจจุบันอนุญาตให้สร้างลิงค์ไหม หรือดึงจากช่องแรกที่บอทมีสิทธิ์
        target_channel = interaction.channel
        if not hasattr(target_channel, "create_invite"):
            # ถ้าห้องปัจจุบันสร้างไม่ได้ ให้หาช่องแชทตัวหนังสือช่องแรกในกิลด์
            for c in interaction.guild.text_channels:
                if c.permissions_for(interaction.guild.me).create_instant_invite:
                    target_channel = c
                    break

        # สร้างลิงค์เชิญ: max_age=0 (ไม่มีวันหมดอายุ), max_uses=0 (ไม่จำกัดจำนวนครั้ง)
        invite_link = await target_channel.create_invite(max_age=0, max_uses=0, unique=True)

        embed = discord.Embed(
            title="🔗 ลิงค์เชิญเข้าสู่เซิร์ฟเวอร์ถาวร",
            description=(
                f"คุณสามารถคัดลอกลิงค์ด้านล่างนี้ไปชวนเพื่อนๆ เข้าเซิร์ฟเวอร์ได้เลยครับ!\n\n"
                f"👉 **{invite_link.url}**\n\n"
                f"📌 *ลิงค์นี้ไม่มีวันหมดอายุและใช้งานได้ไม่จำกัดจำนวนครั้ง*"
            ),
            color=0x2ECC71
        )
        embed.set_footer(text=f"สร้างโดย {interaction.user.name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)

        await interaction.response.send_message(embed=embed, ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"❌ เกิดข้อผิดพลาดในการสร้างลิงค์เชิญ: ขอสิทธิ์ 'สร้างคำเชิญ (Create Invite)' ให้บอทก่อนใช้งานครับ", ephemeral=True)

# 3. รันเว็บและบอทพร้อมกัน
if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.start()
    
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ Error: Please set DISORD_TOKEN in environment variables.")
