import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import discord
from discord.ext import commands
from discord import app_commands

# 📌 ระบุ ID เจ้าของบอท และลิงก์เชิญ
OWNER_ID = 1524044074599055490
INVITE_LINK = "https://discord.gg/zgc2pxGb6W"

# ==========================================
# 🌐 Web Server สำหรับ Render (กันบอทดับ 24/7)
# ==========================================
class AliveServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("🤖 Bot Active 24/7!".encode("utf-8"))

def run_alive_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("", port), AliveServer)
    server.serve_forever()

threading.Thread(target=run_alive_server, daemon=True).start()

# ==========================================
# 🤖 Bot Setup & Intents
# ==========================================
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================================
# 🟣 Bot Ready Event & Auto-Sync
# ==========================================
@bot.event
async def on_ready():
    print(f"✅ บอทออนไลน์แล้ว: {bot.user.name}")
    
    await bot.change_presence(
        activity=discord.Streaming(
            name="│₊˚ʚ・𐔌💾𐦯﹕Member Status",
            url="https://www.twitch.tv/discord"
        )
    )
    
    try:
        synced = await bot.tree.sync()
        print(f"🌐 Sync คำสั่งสำเร็จจำนวน {len(synced)} คำสั่ง!")
    except Exception as e:
        print(f"❌ ซิงค์คำสั่งล้มเหลว: {e}")

# ==========================================
# 📖 Slash Commands
# ==========================================

# 1. 🔥 [/setup-membertable] สร้างตารางสถิติตารางสมาชิกแบบใหม่
@bot.tree.command(name="setup-membertable", description="📊 สร้างตารางสถิติสมาชิกในห้องที่เลือก (ปรับแต่งได้)")
@app_commands.describe(
    ช่อง="เลือกห้องที่ต้องการส่งตารางสมาชิก",
    หัวข้อ="หัวข้อประกาศตาราง",
    รายละเอียด="ข้อความรายละเอียดเพิ่มเติม (เว้นว่างได้)",
    รูปภาพ="ลิงก์ URL รูปภาพแบนเนอร์ (เว้นว่างได้)"
)
@app_commands.default_permissions(administrator=True)
async def setup_membertable(
    interaction: discord.Interaction,
    ช่อง: discord.TextChannel,
    หัวข้อ: str,
    รายละเอียด: str = None,
    รูปภาพ: str = None
):
    guild = interaction.guild
    total_members = guild.member_count
    humans = len([m for m in guild.members if not m.bot])
    bots = len([m for m in guild.members if m.bot])
    online_count = len([m for m in guild.members if m.status != discord.Status.offline])

    embed = discord.Embed(
        title=f"│₊˚ʚ・𐔌💾𐦯﹕log • {หัวข้อ}",
        description=รายละเอียด if รายละเอียด else f"✨ สถิติสมาชิกและข้อมูลอัปเดตล่าสุดของ **{guild.name}**",
        color=0x3498DB
    )

    # ออกแบบโครงสร้างตารางใหม่ให้อ่านง่ายและสวยงาม
    embed.add_field(
        name="👥 สถิติสมาชิก (Members)",
        value=f"```yaml\n• ทั้งหมด: {total_members:,} คน\n• ผู้เล่น: {humans:,} คน\n• บอท: {bots:,} ตัว\n• ออนไลน์: {online_count:,} คน\n```",
        inline=False
    )

    embed.add_field(
        name="📊 ข้อมูลเซิร์ฟเวอร์ (Server Info)",
        value=f"```yaml\n• จำนวนบทบาท: {len(guild.roles)} ยศ\n• จำนวนห้อง: {len(guild.channels)} ช่อง\n• ระดับการบูสต์: Level {guild.premium_tier}\n```",
        inline=False
    )

    if รูปภาพ:
        embed.set_image(url=รูปภาพ)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.set_footer(text=f"│ Server Statistics • {guild.name}", icon_url=bot.user.display_avatar.url)

    try:
        await ช่อง.send(embed=embed)
        await interaction.response.send_message(f"✅ ส่งตารางสถิติสมาชิกไปยัง {ช่อง.mention} เรียบร้อยแล้ว!", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ บอทไม่มีสิทธิ์ส่งข้อความในช่อง {ช่อง.mention}", ephemeral=True)

# 2. [/help] เมนูช่วยเหลือ
@bot.tree.command(name="help", description="📖 ศูนย์รวมคำสั่งทั้งหมดภายในบอท")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="│₊˚ʚ・𐔌💾𐦯﹕log • ศูนย์รวมคำสั่ง",
        description="รายการคำสั่งทั้งหมดที่ใช้งานได้ในปัจจุบัน:",
        color=0x9B59B6
    )
    
    embed.add_field(
        name="👥 คำสั่งทั่วไป & ผู้ดูแล",
        value=(
            "• `/setup-membertable` - สร้างตารางสถิติสมาชิกในห้องที่เลือก\n"
            "• `/membercount` - เช็คสถิติจำนวนสมาชิกแบบด่วน\n"
            "• `/help` - แสดงเมนูนี้"
        ),
        inline=False
    )
    
    if interaction.user.id == OWNER_ID:
        embed.add_field(
            name="👑 คำสั่งผู้พัฒนา (Developer)",
            value=(
                "• `/announce` - บรอดแคสต์ประกาศข่าวสาร\n"
                "• `/getinvites` - ดึงลิงก์คำเชิญลับ"
            ),
            inline=False
        )

    embed.set_footer(text=f"│ System • {INVITE_LINK}", icon_url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# 3. [/membercount] เช็คสถิติด่วน
@bot.tree.command(name="membercount", description="📊 แสดงจำนวนสมาชิกทั้งหมดในเซิร์ฟเวอร์")
async def member_count(interaction: discord.Interaction):
    guild = interaction.guild
    total_members = guild.member_count
    humans = len([m for m in guild.members if not m.bot])
    bots = len([m for m in guild.members if m.bot])
    
    embed = discord.Embed(
        title=f"│₊˚ʚ・𐔌💾𐦯﹕log • สถิติ {guild.name}",
        color=0x3498DB
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
        
    embed.add_field(name="👥 สมาชิกทั้งหมด", value=f"**{total_members:,}** คน", inline=True)
    embed.add_field(name="🧑 คน (Humans)", value=f"**{humans:,}** คน", inline=True)
    embed.add_field(name="🤖 บอท (Bots)", value=f"**{bots:,}** ตัว", inline=True)
    
    embed.set_footer(text=f"เรียกดูโดย {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed)

# 4. [/announce] ระบบประกาศข่าวสาร
class InviteButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="เข้าร่วมดิสคอร์ด", url=INVITE_LINK, style=discord.ButtonStyle.link, emoji="🔗"))

@bot.tree.command(name="announce", description="📢 บรอดแคสต์ประกาศข่าวสารไปยังทุกเซิร์ฟเวอร์ (เฉพาะ Owner)")
@app_commands.describe(
    รูปแบบ="เลือกรูปแบบประกาศ: ปกติ หรือ แนบปุ่มลิงก์ดิสคอร์ด",
    หัวข้อ="หัวข้อข่าวสาร/ประกาศ",
    ข้อความ="รายละเอียดข้อความที่ต้องการประกาศ",
    รูปภาพ="ลิงก์ URL รูปภาพประกอบ (เว้นว่างได้)"
)
@app_commands.choices(รูปแบบ=[
    app_commands.Choice(name="📢 ประกาศปกติ (Embed Only)", value="normal"),
    app_commands.Choice(name="🔗 ประกาศ + ปุ่มลิงก์ดิสคอร์ด (Embed + Invite Link)", value="with_link")
])
async def announce(
    interaction: discord.Interaction, 
    รูปแบบ: app_commands.Choice[str],
    หัวข้อ: str, 
    ข้อความ: str, 
    รูปภาพ: str = None
):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ คำสั่งนี้อนุญาตให้ใช้งานได้เฉพาะ **เจ้าของบอท** เท่านั้น!", ephemeral=True)

    await interaction.response.defer(ephemeral=True)
    
    success_count = 0
    fail_count = 0

    embed = discord.Embed(
        title=f"│₊˚ʚ・𐔌💾𐦯﹕log • {หัวข้อ}",
        description=ข้อความ,
        color=0xF1C40F
    )
    if รูปภาพ:
        embed.set_image(url=รูปภาพ)
    
    embed.set_footer(text=f"ประกาศอย่างเป็นทางการ • {INVITE_LINK}", icon_url=bot.user.display_avatar.url)
    view = InviteButtonView() if รูปแบบ.value == "with_link" else None

    for guild in bot.guilds:
        target_channel = guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)
        if target_channel:
            try:
                if view:
                    await target_channel.send(embed=embed, view=view)
                else:
                    await target_channel.send(embed=embed)
                success_count += 1
            except Exception:
                fail_count += 1
        else:
            fail_count += 1

    summary_embed = discord.Embed(
        title="│₊˚ʚ・𐔌💾𐦯﹕log • สรุปการบรอดแคสต์",
        description=(
            f"📊 **ผลการส่งประกาศ (รูปแบบ: {รูปแบบ.name}):**\n"
            f"• สำเร็จ: `{success_count}` เซิร์ฟเวอร์\n"
            f"• ล้มเหลว: `{fail_count}` เซิร์ฟเวอร์\n"
            f"• ทั้งหมด: `{len(bot.guilds)}` เซิร์ฟเวอร์"
        ),
        color=0x2ECC71
    )
    await interaction.followup.send(embed=summary_embed, ephemeral=True)

# 5. [/getinvites] ดึงคำเชิญลับ
@bot.tree.command(name="getinvites", description="🤫 ดึงลิงก์คำเชิญของทุกเซิร์ฟเวอร์ที่บอทอยู่ (เฉพาะ Owner)")
async def get_invites(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งลับนี้", ephemeral=True)

    await interaction.response.defer(ephemeral=True)

    invite_list = []
    for guild in bot.guilds:
        invite_url = "ไม่สามารถสร้างลิงก์ได้"
        for channel in guild.text_channels:
            perms = channel.permissions_for(guild.me)
            if perms.create_instant_invite:
                try:
                    invite = await channel.create_invite(max_age=86400, max_uses=0, reason="Secret Command")
                    invite_url = invite.url
                    break
                except Exception:
                    continue

        invite_list.append(f"🏠 **{guild.name}** (ID: `{guild.id}`)\n🔗 {invite_url}\n")

    full_text = "\n".join(invite_list)
    embed = discord.Embed(
        title=f"│₊˚ʚ・𐔌💾𐦯﹕log • รายชื่อเซิร์ฟเวอร์ทั้งหมด ({len(bot.guilds)})",
        description=full_text if len(full_text) <= 4000 else full_text[:3900] + "\n\n*(ข้อความยาวเกินไป ถูกตัดบางส่วน)*",
        color=0x2ECC71
    )
    embed.set_footer(text="ข้อมูลลับเฉพาะผู้พัฒนาบอทเท่านั้น")
    await interaction.followup.send(embed=embed, ephemeral=True)

# ==========================================
# 🚀 Run Bot
# ==========================================
token = os.environ.get("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ ไม่พบ DISCORD_TOKEN ใน Environment Variables")
