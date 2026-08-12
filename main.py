import discord, os, asyncio
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread

# --- 1. ระบบ Keep Alive (รันบน Render) ---
app = Flask("")
@app.route("/")
def home(): return "Bot is Alive!"
Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))).start()

# --- 2. การตั้งค่าบอท ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- 3. ฟังก์ชัน Sync คำสั่งอัตโนมัติ (แก้ปัญหา / ไม่ขึ้น) ---
@bot.event
async def on_ready():
    print(f"✅ บอท {bot.user} เชื่อมต่อแล้ว!")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 ซิงค์คำสั่งสำเร็จ: {len(synced)} คำสั่ง")
    except Exception as e:
        print(f"❌ ซิงค์พลาด: {e}")

# --- 4. ระบบกรองคำหยาบ (Anti-Swear) ---
@bot.event
async def on_message(message):
    if message.author == bot.user: return
    bad_words = ["ควย", "เหี้ย", "สัส", "อีเ_ี้ย"]
    if any(word in message.content for word in bad_words):
        await message.delete()
        await message.channel.send(f"⚠️ {message.author.mention} ห้ามใช้คำหยาบครับ!")
    await bot.process_commands(message)

# --- 5. ระบบต้อนรับ (Welcome) ---
@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="welcome")
    if channel: await channel.send(f"🎉 ยินดีต้อนรับ {member.mention} สู่เซิร์ฟเวอร์!")

# --- 6. ระบบ Verify (ปุ่มกด) ---
@bot.tree.command(name="setup_verify", description="สร้างปุ่มยืนยันตัวตน")
async def setup_verify(interaction: discord.Interaction):
    class VerifyView(discord.ui.View):
        def __init__(self): super().__init__(timeout=None)
        @discord.ui.button(label="✅ ยืนยันตัวตน", style=discord.ButtonStyle.green)
        async def btn(self, interaction: discord.Interaction, button: discord.ui.Button):
            role = discord.utils.get(interaction.guild.roles, name="Member")
            if role: await interaction.user.add_roles(role)
            await interaction.response.send_message("ยืนยันสำเร็จ!", ephemeral=True)
    await interaction.channel.send("กดปุ่มเพื่อรับยศ:", view=VerifyView())
    await interaction.response.send_message("สร้างระบบ Verify แล้ว", ephemeral=True)

# --- 7. ระบบ Ticket (สร้างห้องแจ้งปัญหา) ---
@bot.tree.command(name="setup_ticket", description="สร้างระบบ Ticket")
async def setup_ticket(interaction: discord.Interaction):
    class TicketView(discord.ui.View):
        def __init__(self): super().__init__(timeout=None)
        @discord.ui.button(label="🎫 แจ้งปัญหา", style=discord.ButtonStyle.blurple)
        async def btn(self, interaction: discord.Interaction, button: discord.ui.Button):
            channel = await interaction.guild.create_text_channel(f"ticket-{interaction.user.name}")
            await interaction.response.send_message(f"ห้องของคุณ: {channel.mention}", ephemeral=True)
    await interaction.channel.send("หากมีปัญหา กดปุ่มนี้:", view=TicketView())
    await interaction.response.send_message("สร้างระบบ Ticket แล้ว", ephemeral=True)

# --- 8. ระบบข้อมูลเซิร์ฟเวอร์ ---
@bot.tree.command(name="stats", description="ดูสถานะเซิร์ฟเวอร์")
async def stats(interaction: discord.Interaction):
    await interaction.response.send_message(f"👥 สมาชิก: {interaction.guild.member_count} คน")

# --- 9. ระบบประกาศ (Admin) ---
@bot.tree.command(name="announce", description="ประกาศข่าวสาร")
async def announce(interaction: discord.Interaction, text: str):
    await interaction.channel.send(f"📢 **ประกาศ:** {text}")
    await interaction.response.send_message("ประกาศแล้ว", ephemeral=True)

# รันบอท
bot.run(os.environ.get("DISCORD_TOKEN"))
