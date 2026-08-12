import asyncio, os, discord
from threading import Thread
from discord import app_commands
from discord.ext import commands
from flask import Flask

# 1. ระบบ Keep-Alive (กัน Render ปิดบอท)
app = Flask("")
@app.route("/")
def home(): return "Bot is Online!"
def run_web(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
Thread(target=run_web).start()

# 2. ตั้งค่า Intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ บอท {bot.user} พร้อมใช้งาน!")

# 3. ระบบต้อนรับ (Welcome)
@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="welcome")
    if channel: await channel.send(f"ยินดีต้อนรับ {member.mention} เข้าสู่เซิร์ฟเวอร์!")

# 4. ระบบ Verify (ปุ่มกดรับยศ)
class VerifyView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="✅ ยืนยันตัวตน", style=discord.ButtonStyle.green, custom_id="verify")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="Member")
        await interaction.user.add_roles(role)
        await interaction.response.send_message("คุณได้รับยศแล้ว!", ephemeral=True)

# 5. ระบบ Ticket (สร้างห้องแจ้งปัญหา)
class TicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🎫 แจ้งปัญหา", style=discord.ButtonStyle.blurple, custom_id="ticket")
    async def ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await interaction.guild.create_text_channel(f"ticket-{interaction.user.name}")
        await interaction.response.send_message(f"สร้างห้องแล้ว: {channel.mention}", ephemeral=True)

# 6. ระบบป้องกันคำหยาบ (Anti-Swear)
@bot.event
async def on_message(message):
    bad_words = ["ควย", "เหี้ย", "สัส"] # เพิ่มคำที่นี่
    if any(word in message.content for word in bad_words):
        await message.delete()
        await message.channel.send(f"{message.author.mention} ห้ามใช้คำหยาบครับ!")
    await bot.process_commands(message)

# 7. ระบบสถานะเซิร์ฟเวอร์ (Stats/Status)
@bot.tree.command(name="stats", description="ดูสถานะเซิร์ฟเวอร์")
async def stats(interaction: discord.Interaction):
    await interaction.response.send_message(f"สมาชิกทั้งหมด: {interaction.guild.member_count} คน")

# 8. ระบบจัดการแอดมิน (Admin Panel)
@bot.tree.command(name="announce", description="ประกาศข่าวสาร")
async def announce(interaction: discord.Interaction, text: str):
    await interaction.channel.send(f"📢 ประกาศ: {text}")
    await interaction.response.send_message("ส่งแล้ว", ephemeral=True)

# 9. ระบบปุ่มเปิดเมนู (Main Control Panel)
@bot.tree.command(name="setup", description="เปิดเมนูตั้งค่าหลัก")
async def setup(interaction: discord.Interaction):
    view = discord.ui.View()
    # ปุ่มในเมนูหลัก
    btn_verify = discord.ui.Button(label="ระบบยืนยันตัวตน", style=discord.ButtonStyle.green, custom_id="v")
    btn_ticket = discord.ui.Button(label="ระบบแจ้งปัญหา", style=discord.ButtonStyle.blurple, custom_id="t")
    view.add_item(btn_verify); view.add_item(btn_ticket)
    await interaction.response.send_message("เลือกเมนูที่ต้องการ:", view=view)

bot.run(os.environ.get("DISCORD_TOKEN"))
