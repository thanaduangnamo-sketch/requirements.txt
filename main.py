import os
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import discord
from discord.ext import commands
from discord import app_commands

# 📌 ระบุ ID ของคุณ (เจ้าของบอท) และ ID เซิร์ฟเวอร์หลัก
OWNER_ID = 1524044074599055490
MAIN_GUILD_ID = 1522224772258332792
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
# 🛠️ ฟังก์ชันช่วยเหลือ
# ==========================================
async def send_welcome_dm(user: discord.User, guild: discord.Guild, role: discord.Role):
    embed = discord.Embed(
        title="│₊˚ʚ・𐔌💾𐦯﹕log • ยินดีต้อนรับ!",
        description=(
            f"สวัสดีครับคุณ {user.mention} 👋\n\n"
            f"คุณได้ทำการ **ยืนยันตัวตนสำเร็จ** ในเซิร์ฟเวอร์ **{guild.name}** เรียบร้อยแล้ว!\n"
            f"🎁 **ยศที่คุณได้รับ:** `{role.name}`\n\n"
            f"ขอให้สนุกกับการใช้งานเซิร์ฟเวอร์นะครับ ✨"
        ),
        color=0x9B59B6
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text=f"│ System Notice • {guild.name}")

    try:
        await user.send(embed=embed)
        return True
    except Exception:
        return False

# ==========================================
# 🔐 ระบบ Verification Components
# ==========================================
class VerifyCodeModal(discord.ui.Modal, title="🔐 ยืนยันตัวตนด้วยรหัสผ่าน"):
    def __init__(self, correct_code: str, role_id: int):
        super().__init__()
        self.correct_code = correct_code
        self.role_id = role_id

        self.code_input = discord.ui.TextInput(
            label=f"🔢 พิมพ์รหัสผ่านนี้: {correct_code}",
            placeholder="กรอกตัวเลข 4 หลักตามที่เห็นข้างบน...",
            min_length=4,
            max_length=4,
            required=True
        )
        self.add_item(self.code_input)

    async def on_submit(self, interaction: discord.Interaction):
        if self.code_input.value.strip() == self.correct_code:
            role = interaction.guild.get_role(self.role_id)
            if role:
                try:
                    await interaction.user.add_roles(role)
                    dm_sent = await send_welcome_dm(interaction.user, interaction.guild, role)
                    dm_status = "\n📩 *ส่งข้อความแจ้งเตือนไปยัง DM ของคุณเรียบร้อยแล้ว*" if dm_sent else "\n⚠️ *(บอทไม่สามารถส่ง DM หาคุณได้ เนื่องจากคุณปิด DM)*"
                    
                    embed = discord.Embed(
                        title="│₊˚ʚ・𐔌💾𐦯﹕log • ยืนยันตัวตนสำเร็จ!",
                        description=f"ยินดีต้อนรับ {interaction.user.mention} ✨\nคุณได้รับยศ **{role.name}** เรียบร้อยแล้วครับ{dm_status}",
                        color=0x2ECC71
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except discord.Forbidden:
                    await interaction.response.send_message("❌ บอทมียศต่ำกว่ายศที่จะมอบ โปรดย้ายยศบอทขึ้นไปข้างบน", ephemeral=True)
            else:
                await interaction.response.send_message("❌ ไม่พบยศในระบบ", ephemeral=True)
        else:
            embed = discord.Embed(
                title="│₊˚ʚ・𐔌💾𐦯﹕log • รหัสผ่านไม่ถูกต้อง!",
                description="กรุณากดปุ่มเพื่อลองใหม่อีกครั้ง",
                color=0xE74C3C
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class PersistentVerifyView(discord.ui.View):
    def __init__(self, mode: str = "code", role_id: int = None):
        super().__init__(timeout=None)
        self.mode = mode
        self.role_id = role_id

    @discord.ui.button(label="กดเพื่อยืนยันตัวตน", style=discord.ButtonStyle.success, emoji="🛡️", custom_id="persistent_verify_btn")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_id_to_use = self.role_id
        current_mode = self.mode

        if not role_id_to_use and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            if embed.footer and embed.footer.text and "ROLE:" in embed.footer.text:
                try:
                    parts = embed.footer.text.split("|")
                    for p in parts:
                        if "ROLE:" in p:
                            role_id_to_use = int(p.replace("ROLE:", "").strip())
                        if "MODE:" in p:
                            current_mode = p.replace("MODE:", "").strip()
                except Exception:
                    pass

        if not role_id_to_use:
            return await interaction.response.send_message("❌ ไม่พบข้อมูลยศในการตั้งค่า", ephemeral=True)

        if current_mode == "button":
            role = interaction.guild.get_role(role_id_to_use)
            if role:
                if role in interaction.user.roles:
                    return await interaction.response.send_message("✨ คุณมียศนี้อยู่แล้วครับ!", ephemeral=True)
                try:
                    await interaction.user.add_roles(role)
                    dm_sent = await send_welcome_dm(interaction.user, interaction.guild, role)
                    dm_status = "\n📩 *ส่งข้อความแจ้งเตือนไปยัง DM ของคุณเรียบร้อยแล้ว*" if dm_sent else "\n⚠️ *(บอทไม่สามารถส่ง DM หาคุณได้ เนื่องจากคุณปิด DM)*"
                    
                    embed = discord.Embed(
                        title="│₊˚ʚ・𐔌💾𐦯﹕log • ยืนยันตัวตนสำเร็จ!",
                        description=f"ยินดีต้อนรับ {interaction.user.mention} ✨\nคุณได้รับยศ **{role.name}** เรียบร้อยแล้วครับ{dm_status}",
                        color=0x2ECC71
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except discord.Forbidden:
                    await interaction.response.send_message("❌ บอทมียศต่ำกว่ายศที่จะมอบ", ephemeral=True)
            else:
                await interaction.response.send_message("❌ ไม่พบยศในระบบ", ephemeral=True)
        else:
            generated_code = str(random.randint(1000, 9999))
            modal = VerifyCodeModal(correct_code=generated_code, role_id=role_id_to_use)
            await interaction.response.send_modal(modal)

# ==========================================
# 🟣 Bot Ready Event & Sync
# ==========================================
@bot.event
async def on_ready():
    print(f"✅ บอทออนไลน์แล้ว: {bot.user.name}")
    bot.add_view(PersistentVerifyView())
    
    await bot.change_presence(
        activity=discord.Streaming(
            name="│₊˚ʚ・𐔌💾𐦯﹕log Member System",
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

# 1. คำสั่งแสดงตารางสถิติตารางสมาชิกในห้องที่เลือก
@bot.tree.command(name="setup-membertable", description="📊 สร้างตารางแสดงสถิติสมาชิกในห้องที่เลือก (เฉพาะแอดมิน)")
@app_commands.describe(
    ช่อง="เลือกห้องที่ต้องการส่งตารางสมาชิก",
    หัวข้อ="หัวข้อตาราง (เช่น 📊 ตารางสถิติสมาชิกประจำเซิร์ฟเวอร์)",
    รายละเอียด="ข้อความต้อนรับหรือรายละเอียดเพิ่มเติม (เว้นว่างได้)",
    รูปภาพ="ลิงก์ URL รูปภาพประกอบ (เว้นว่างได้)"
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
    
    # ดึงรายชื่อบทบาทหลัก/ผู้ดูแล
    online_count = len([m for m in guild.members if m.status != discord.Status.offline])

    embed = discord.Embed(
        title=f"│₊˚ʚ・𐔌💾𐦯﹕log • {หัวข้อ}",
        description=รายละเอียด if รายละเอียด else f"ยินดีต้อนรับสู่ **{guild.name}** สถิติอัปเดตล่าสุดของเซิร์ฟเวอร์เรา!",
        color=0x3498DB
    )

    # จัดโครงสร้างตารางสมาชิก
    embed.add_field(name="👥 สมาชิกทั้งหมด", value=f"```\n{total_members:,} คน\n```", inline=True)
    embed.add_field(name="🧑 ผู้เล่น (Humans)", value=f"```\n{humans:,} คน\n```", inline=True)
    embed.add_field(name="🤖 บอท (Bots)", value=f"```\n{bots:,} ตัว\n```", inline=True)
    embed.add_field(name="🟢 สมาชิกออนไลน์", value=f"```\n{online_count:,} คน\n```", inline=True)
    embed.add_field(name="🛡️ จำนวนยศทั้งหมด", value=f"```\n{len(guild.roles)} ยศ\n```", inline=True)
    embed.add_field(name="📁 จำนวนห้องทั้งหมด", value=f"```\n{len(guild.channels)} ช่อง\n```", inline=True)

    if รูปภาพ:
        embed.set_image(url=รูปภาพ)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.set_footer(text=f"Server Statistics • {guild.name}", icon_url=bot.user.display_avatar.url)

    try:
        await ช่อง.send(embed=embed)
        await interaction.response.send_message(f"✅ สร้างตารางสมาชิกในห้อง {ช่อง.mention} เรียบร้อยแล้ว!", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ บอทไม่มีสิทธิ์ส่งข้อความในห้อง {ช่อง.mention}", ephemeral=True)

# 2. คำสั่ง Help
@bot.tree.command(name="help", description="📖 ศูนย์รวมคำสั่งทั้งหมดภายในบอท")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="│₊˚ʚ・𐔌💾𐦯﹕log • ศูนย์รวมคำสั่งทั้งหมด",
        description="รวบรวมคำสั่งสำหรับใช้งานบอท แยกตามหมวดหมู่ไว้ให้อย่างเป็นระเบียบครับ:",
        color=0x9B59B6
    )
    
    embed.add_field(
        name="👥 หมวดหมู่คำสั่งทั่วไป",
        value=(
            "• `/help` - แสดงเมนูช่วยเหลือและศูนย์รวมคำสั่ง\n"
            "• `/membercount` - ดูสถิติจำนวนสมาชิก สมาชิกที่เป็นคน และบอท"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚙️ หมวดหมู่คำสั่งผู้ดูแลระบบ (Admin)",
        value=(
            "• `/setup-membertable` - สร้างตารางสถิติสมาชิกในห้องที่เลือก\n"
            "• `/setup-verify` - ตั้งค่าสร้างกล่องข้อความยืนยันตัวตน (ปุ่ม/รหัสสุ่ม)"
        ),
        inline=False
    )
    
    if interaction.user.id == OWNER_ID:
        embed.add_field(
            name="👑 หมวดหมู่คำสั่งเฉพาะผู้พัฒนา (Developer)",
            value=(
                "• `/announce` - ส่งบรอดแคสต์ประกาศไปยังทุกเซิร์ฟเวอร์ที่บอทอยู่\n"
                "• `/getinvites` - ดึงลิงก์คำเชิญลับของทุกเซิร์ฟเวอร์"
            ),
            inline=False
        )

    embed.set_footer(text=f"│ System • {INVITE_LINK}", icon_url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# 3. คำสั่ง Membercount แบบส่งในแชทปกติ
@bot.tree.command(name="membercount", description="📊 แสดงจำนวนสมาชิกทั้งหมด ผู้ใช้งาน และบอทภายในเซิร์ฟเวอร์")
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

# 4. คำสั่งตั้งค่าระบบ Verify
@bot.tree.command(name="setup-verify", description="🛡️ สร้างกล่องข้อความยืนยันตัวตน (เฉพาะแอดมิน)")
@app_commands.describe(
    โหมด="เลือกรูปแบบ: ปุ่มกดรับยศทันที หรือ สุ่มรหัส 4 หลัก",
    ยศ="เลือกยศที่จะมอบให้ผู้ใช้งานหลังยืนยันสำเร็จ",
    หัวข้อ="ข้อความหัวข้อประกาศ (Title)",
    รายละเอียด="รายละเอียดเนื้อหาเพิ่มเติม (เว้นว่างไว้ได้)",
    รูปภาพ="ลิงก์ URL รูปภาพประกอบ Embed (เว้นว่างไว้ได้)"
)
@app_commands.choices(โหมด=[
    app_commands.Choice(name="🔘 ปุ่มกดรับยศทันที (Button Mode)", value="button"),
    app_commands.Choice(name="🔐 กรอกรหัสสุ่ม 4 หลัก (Random Code Mode)", value="code")
])
@app_commands.default_permissions(administrator=True)
async def setup_verify(
    interaction: discord.Interaction, 
    โหมด: app_commands.Choice[str],
    ยศ: discord.Role, 
    หัวข้อ: str, 
    รายละเอียด: str = None, 
    รูปภาพ: str = None
):
    if interaction.guild_id != MAIN_GUILD_ID:
        return await interaction.response.send_message("❌ อนุญาตให้ใช้เฉพาะในเซิร์ฟเวอร์หลักเท่านั้น", ephemeral=True)

    if not รายละเอียด:
        if โหมด.value == "button":
            รายละเอียด = "กดปุ่ม **ยืนยันตัวตน** ด้านล่างเพื่อรับยศเข้าใช้งานเซิร์ฟเวอร์ได้ทันที ✨"
        else:
            รายละเอียด = "กดปุ่ม **ยืนยันตัวตน** ด้านล่างเพื่อรับรหัสผ่านสุ่ม 4 หลัก แล้วกรอกให้ถูกต้องเพื่อรับยศ ✨"

    embed = discord.Embed(
        title=f"│₊˚ʚ・𐔌💾𐦯﹕log • {หัวข้อ}",
        description=f"{รายละเอียด}\n\n🎁 **ยศที่คุณจะได้รับ:** {ยศ.mention}",
        color=0x9B59B6
    )
    if รูปภาพ:
        embed.set_image(url=รูปภาพ)
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
        
    embed.set_footer(text=f"Verification System | MODE:{โหมด.value} | ROLE:{ยศ.id}", icon_url=bot.user.display_avatar.url)
    view = PersistentVerifyView(mode=โหมด.value, role_id=ยศ.id)
    
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ สร้างกล่องข้อความยืนยันตัวตนเรียบร้อยแล้ว!", ephemeral=True)

class InviteButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="เข้าร่วมดิสคอร์ด", url=INVITE_LINK, style=discord.ButtonStyle.link, emoji="🔗"))

# 5. คำสั่ง Announce
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
        target_channel = guild.system_channel or guild.text_channels[0] if guild.text_channels else None
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

# 6. คำสั่ง Getinvites
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
