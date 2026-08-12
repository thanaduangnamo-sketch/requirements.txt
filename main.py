import asyncio, os, discord
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

# --- 3. ฟังก์ชัน Sync คำสั่งอัตโนมัติ ---
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


# ==========================================
# 📌 รวมคำสั่ง Slash Commands ทั้งหมด (ครบ 9 คำสั่ง)
# ==========================================

# 1. ระบบ Verify
@bot.tree.command(name="setup_verify", description="1. สร้างปุ่มยืนยันตัวตน")
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

# 2. ระบบ Ticket
@bot.tree.command(name="setup_ticket", description="2. สร้างระบบ Ticket แจ้งปัญหา")
async def setup_ticket(interaction: discord.Interaction):
    class TicketView(discord.ui.View):
        def __init__(self): super().__init__(timeout=None)
        @discord.ui.button(label="🎫 แจ้งปัญหา", style=discord.ButtonStyle.blurple)
        async def btn(self, interaction: discord.Interaction, button: discord.ui.Button):
            channel = await interaction.guild.create_text_channel(f"ticket-{interaction.user.name}")
            await interaction.response.send_message(f"ห้องของคุณ: {channel.mention}", ephemeral=True)
    await interaction.channel.send("หากมีปัญหา กดปุ่มนี้:", view=TicketView())
    await interaction.response.send_message("สร้างระบบ Ticket แล้ว", ephemeral=True)

# 3. ระบบ Stats (ดูสถานะเซิร์ฟเวอร์)
@bot.tree.command(name="stats", description="3. ดูสถานะและข้อมูลเบื้องต้นของเซิร์ฟเวอร์")
async def stats(interaction: discord.Interaction):
    await interaction.response.send_message(f"👥 สมาชิกทั้งหมดในเซิร์ฟเวอร์: {interaction.guild.member_count} คน")

# 4. ระบบ Announce (ประกาศข้อความ)
@bot.tree.command(name="announce", description="4. ประกาศข่าวสารสำคัญในห้อง")
async def announce(interaction: discord.Interaction, text: str):
    await interaction.channel.send(f"📢 **ประกาศ:** {text}")
    await interaction.response.send_message("ประกาศเรียบร้อย", ephemeral=True)

# 5. ระบบ Kick (เตะสมาชิก)
@bot.tree.command(name="kick", description="5. เตะสมาชิกออกจากเซิร์ฟเวอร์")
@app_commands.describe(member="เลือกสมาชิกที่ต้องการเตะ", reason="เหตุผล")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "ไม่ระบุเหตุผล"):
    if not interaction.user.guild_permissions.kick_members:
        return await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้!", ephemeral=True)
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 เตะ {member.name} ออกจากเซิร์ฟเวอร์แล้ว เพราะ: {reason}")

# 6. ระบบ Ban (แบนสมาชิก)
@bot.tree.command(name="ban", description="6. แบนสมาชิกออกจากเซิร์ฟเวอร์")
@app_commands.describe(member="เลือกสมาชิกที่ต้องการแบน", reason="เหตุผล")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "ไม่ระบุเหตุผล"):
    if not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้!", ephemeral=True)
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 แบน {member.name} ออกจากเซิร์ฟเวอร์แล้ว เพราะ: {reason}")

# 7. ระบบ Clear (ลบข้อความ)
@bot.tree.command(name="clear", description="7. ลบข้อความในแชทจำนวนตามที่กำหนด")
@app_commands.describe(amount="จำนวนข้อความที่ต้องการลบ (1-100)")
async def clear(interaction: discord.Interaction, amount: int):
    if not interaction.user.guild_permissions.manage_messages:
        return await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้!", ephemeral=True)
    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"🗑️ ลบข้อความไปแล้ว {amount} ข้อความ", ephemeral=True)

# 8. ระบบ Userinfo (ดูข้อมูลสมาชิก)
@bot.tree.command(name="userinfo", description="8. ดูข้อมูลรายละเอียดของสมาชิกคนนั้นๆ")
@app_commands.describe(member="เลือกสมาชิกที่ต้องการดูข้อมูล")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    embed = discord.Embed(title=f"ข้อมูลของ: {target.name}", color=discord.Color.blue())
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="ID", value=target.id, inline=True)
    embed.add_field(name="เข้าร่วมเมื่อ", value=target.joined_at.strftime("%Y-%m-%d"), inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# 9. ระบบ Botinfo (ดูข้อมูลบอท)
@bot.tree.command(name="botinfo", description="9. ดูสถานะและข้อมูลของบอทตัวนี้")
async def botinfo(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 ข้อมูลบอท", description="บอทสารพัดประโยชน์ All-in-One", color=discord.Color.green())
    embed.add_field(name="ชื่อบอท", value=bot.user.name, inline=True)
    embed.add_field(name="ความหน่วง (Ping)", value=f"{round(bot.latency * 1000)} ms", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# รันบอท
bot.run(os.environ.get("DISCORD_TOKEN"))
