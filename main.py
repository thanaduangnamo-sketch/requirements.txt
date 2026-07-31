import nextcord
from nextcord.ext import commands
import requests
import os
from flask import Flask
from threading import Thread
import time
from collections import defaultdict
import random

# --- ระบบเปิดเว็บจำลองสำหรับ Render (แก้ปัญหา Port scan timeout) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# -----------------------------------------------------------------

token = os.environ.get("DISCORD_TOKEN")
ownerid = [1532607357962420229]
image = "https://cdn.discordapp.com/attachments/1355010685108490410/1355532067768766515/ed40c25e-1eaf-4cc0-b8b0-5198d79dae76.png"

bot = commands.Bot(command_prefix="!", intents=nextcord.Intents.all())

# ตัวแปรสถานะระบบป้องกัน
anti_link_status = {}
anti_mention_status = {}
anti_spam_status = {}
anti_nuke_status = {}

# ตัวแปรเก็บข้อมูลนับสถิติเพื่อลงโทษ (Anti-Spam / Anti-Mass Ping)
user_message_counts = defaultdict(list)
user_everyone_counts = defaultdict(list)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    bot.add_view(TokenCheckView())
    bot.add_view(VerifyView())
    bot.add_view(RoleSelectView())


# ==========================================
# ฟังก์ชันลงโทษขั้นเด็ดขาด (แบน + ยึด/ลบยศออกทั้งหมด)
# ==========================================
async def punish_user(member: nextcord.member.Member, reason: str):
    if member.bot or member.id in ownerid:
        return
    try:
        # 1. ยึด/ถอดยศทั้งหมดออก
        roles_to_remove = [r for r in member.roles if r != member.guild.default_role and r.is_assignable()]
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove, reason=f"Anti-Security: {reason}")
    except Exception:
        pass

    try:
        # 2. แบนออกจากเซิร์ฟเวอร์ทันที
        await member.ban(reason=f"Anti-Security Protection: {reason}")
    except Exception:
        pass


# ==========================================
# 1. ระบบป้องกันเซิร์ฟเวอร์อัจฉริยะ (Advanced Protection)
# ==========================================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    guild_id = message.guild.id
    current_time = time.time()
    author = message.author

    # เช็คสิทธิ์ข้ามแอดมินหลัก (แต่ถ้าทำผิดกฏหนักๆ ด้านล่างจะจัดการหมด)
    is_admin = author.guild_permissions.administrator

    # 1. กันลิงก์
    if anti_link_status.get(guild_id, False) and not is_admin:
        if any(domain in message.content for domain in ["http://", "https://", "discord.gg/", "www."]):
            try:
                await message.delete()
                await message.channel.send(f"🚫 `{author.name}` ตรวจพบการส่งลิงก์ ระบบบล็อกทันที", delete_after=4)
                return
            except Exception:
                pass

    # 2. ระบบกันแท็กทุกคน / แท็กซ้ำหลายครั้ง (แบน + ยึดยศ)
    if anti_mention_status.get(guild_id, False) and not is_admin:
        # ตรวจสอบการแท็ก @everyone หรือ @here หรือแท็กยศ/คนรัวๆ
        has_everyone = message.mention_everyone or "@everyone" in message.content or "@here" in message.content
        
        if has_everyone:
            user_everyone_counts[author.id] = [t for t in user_everyone_counts[author.id] if current_time - t < 10]
            user_everyone_counts[author.id].append(current_time)

            # ถ้าแท็กทุกคนเกิน 2 ครั้งใน 10 วิ -> จัดการขั้นเด็ดขาด
            if len(user_everyone_counts[author.id]) >= 2:
                try:
                    await message.delete()
                except:
                    pass
                await punish_user(author, "Mass Everyone Ping Spam")
                return

        if len(message.mentions) > 3 or len(message.role_mentions) > 2:
            try:
                await message.delete()
                await punish_user(author, "Mass Mention Spam")
                return
            except Exception:
                pass

    # 3. ระบบกันสแปม (สแปมรัวๆ แบน + ยึดยศ)
    if anti_spam_status.get(guild_id, False) and not is_admin:
        author_id = author.id
        user_message_counts[author_id] = [t for t in user_message_counts[author_id] if current_time - t < 5]
        user_message_counts[author_id].append(current_time)

        if len(user_message_counts[author_id]) > 6: # ส่งเกิน 6 ข้อความใน 5 วิ
            try:
                await message.delete()
            except:
                pass
            await punish_user(author, "Message Spam Flood")
            return

    await bot.process_commands(message)


# ==========================================
# 2. ระบบกันยิงดิส / กันลบห้อง / กันลบยศรัวๆ (Anti-Nuke)
# ==========================================
@bot.event
async def on_guild_channel_delete(channel):
    guild_id = channel.guild.id
    if anti_nuke_status.get(guild_id, False):
        try:
            # สร้างห้องคืนอัตโนมัติ
            new_ch = await channel.guild.create_text_channel(name=channel.name, category=channel.category)
            # พยายามหาคนที่ลบห้องผ่าน Audit Logs เพื่อแบนและยึดสิทธิ์
            async for entry in channel.guild.audit_logs(limit=1, action=nextcord.AuditLogAction.channel_delete):
                if entry.user and not entry.user.bot:
                    await punish_user(entry.user, "Nuke: Deleted Channels")
        except Exception:
            pass

@bot.event
async def on_guild_role_delete(role):
    guild_id = role.guild.id
    if anti_nuke_status.get(guild_id, False):
        try:
            async for entry in role.guild.audit_logs(limit=1, action=nextcord.AuditLogAction.role_delete):
                if entry.user and not entry.user.bot:
                    await punish_user(entry.user, "Nuke: Deleted Roles")
        except Exception:
            pass


# ==========================================
# 3. ระบบปุ่มเดิมทั้งหมด (Token, Verify, Roles)
# ==========================================

class TokenModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(title="🔐 ตรวจสอบ Discord Token")
        self.token_input = nextcord.ui.TextInput(
            label="กรอก Discord Token ของคุณ",
            placeholder="วาง Token ที่นี่ (ข้อมูลไม่ถูกบันทึก)",
            style=nextcord.TextInputStyle.paragraph,
            required=True
        )
        self.add_item(self.token_input)

    async def callback(self, interaction: nextcord.Interaction):
        await interaction.response.defer(ephemeral=True)
        raw_token = str(self.token_input.value).strip()
        headers = {"Authorization": raw_token if not raw_token.lower().startswith("bot ") else raw_token, "Content-Type": "application/json"}

        try:
            response = requests.get("https://discord.com/api/v9/users/@me", headers=headers, timeout=10)
            if response.status_code != 200:
                return await interaction.followup.send(embed=nextcord.Embed(description="### ❌ Tokenไม่ถูกต้อง", color=nextcord.Color.red()), ephemeral=True)

            data = response.json()
            dm_embed = nextcord.Embed(title="**🛡️ ผลการตรวจสอบ Token**", color=nextcord.Color.blurple())
            dm_embed.add_field(name="👤 ชื่อ", value=f"`{data.get('username')}`", inline=True)
            dm_embed.add_field(name="🆔 ไอดี", value=f"`{data.get('id')}`", inline=True)
            await interaction.user.send(embed=dm_embed)
            await interaction.followup.send(embed=nextcord.Embed(description="### ✅ ส่งผลลัพธ์ไปที่ DM แล้ว", color=nextcord.Color.green()), ephemeral=True)
        except Exception as e:
            await interaction.followup.send(embed=nextcord.Embed(description=f"### ❌ ผิดพลาด: `{e}`", color=nextcord.Color.red()), ephemeral=True)

class TokenCheckView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @nextcord.ui.button(label="เช็ค Token", style=nextcord.ButtonStyle.red, custom_id="check_token_btn", emoji="🔍")
    async def check_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(TokenModal())

class VerifyModal(nextcord.ui.Modal):
    def __init__(self, correct_code: str):
        super().__init__(title="🛡️ ยืนยันตัวตน")
        self.correct_code = correct_code
        self.code_input = nextcord.ui.TextInput(label=f"กรอกรหัส: [{correct_code}]", style=nextcord.TextInputStyle.short, required=True, max_length=6)
        self.add_item(self.code_input)

    async def callback(self, interaction: nextcord.Interaction):
        if str(self.code_input.value).strip() == self.correct_code:
            role_id = 000000000000000000  # <-- เปลี่ยน ID ยศสมาชิก
            role = interaction.guild.get_role(role_id)
            if role:
                try: await interaction.user.add_roles(role)
                except: pass
            await interaction.response.send_message(embed=nextcord.Embed(description="### ✅ ยืนยันสำเร็จ!", color=nextcord.Color.green()), ephemeral=True)
        else:
            await interaction.response.send_message(embed=nextcord.Embed(description="### ❌ รหัสไม่ถูกต้อง!", color=nextcord.Color.red()), ephemeral=True)

class VerifyView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @nextcord.ui.button(label="คลิกเพื่อยืนยันตัวตน", style=nextcord.ButtonStyle.green, custom_id="verify_button_main", emoji="✅")
    async def verify_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(VerifyModal(correct_code=str(random.randint(1000, 9999))))

class RoleSelectDropdown(nextcord.ui.Select):
    def __init__(self):
        options = [
            nextcord.SelectOption(label="Notification Ping", emoji="🔔", value="111111111111111111"),
            nextcord.SelectOption(label="Announcement", emoji="📢", value="222222222222222222"),
        ]
        super().__init__(placeholder="📌 เลือกยศ...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: nextcord.Interaction):
        role = interaction.guild.get_role(int(self.values[0]))
        if not role: return await interaction.response.send_message("❌ ไม่พบยศ", ephemeral=True)
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"🗑️ ถอดยศ `{role.name}` แล้ว", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"✨ เพิ่มยศ `{role.name}` แล้ว", ephemeral=True)

class RoleSelectView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleSelectDropdown())


# ==========================================
# 4. ระบบคำสั่งทั้งหมด (Slash Commands & Help)
# ==========================================

def security_embed(title, status_type, desc):
    color = nextcord.Color.blurple() if status_type == "on" else nextcord.Color.dark_gray()
    state = "เปิดใช้งาน" if status_type == "on" else "ปิดการใช้งาน"
    embed = nextcord.Embed(title=f"🔒 {title}", description=f"**สถานะ:** `{state}`\n\n{desc}", color=color)
    embed.set_footer(text="• ระบบรักษาความปลอดภัยอัตโนมัติ (Anti-Nuke / Anti-Spam / Ban & Strip)")
    return embed

@bot.slash_command(name="help", description="📖 แสดงคู่มือการใช้งานคำสั่งทั้งหมด")
async def help_command(interaction: nextcord.Interaction):
    embed = nextcord.Embed(title="🤖 BOT COMMANDS PANEL", description="รายการคำสั่งทั้งหมดในระบบ:", color=nextcord.Color.gold())
    embed.add_field(name="🛡️ ระบบป้องกันความปลอดภัย (Auto-Ban & Strip Roles)", value="`/anti-link` | `/anti-mention` | `/anti-spam` | `/anti-nuke`", inline=False)
    embed.add_field(name="⚙️ ระบบติดตั้งปุ่ม", value="`/setup-token-checker` | `/setup-verify` | `/setup-roles`", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.slash_command(name="anti-link", description="[ 🎃 ระบบกันลิ้ง ]")
async def anti_link(interaction: nextcord.Interaction, status: str = nextcord.SlashOption(choices={"เปิด": "on", "ปิด": "off"})):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ เฉพาะแอดมิน", ephemeral=True)
    anti_link_status[interaction.guild.id] = (status == "on")
    await interaction.response.send_message(embed=security_embed("ANTI-LINK", status, "บล็อกและลบลิงก์อัตโนมัติ"), ephemeral=True)

@bot.slash_command(name="anti-mention", description="[ 🎃 ระบบกันแท็ก ] (แท็กทุกคนรัวๆ แบน+ยึดยศ)")
async def anti_mention(interaction: nextcord.Interaction, status: str = nextcord.SlashOption(choices={"เปิด": "on", "ปิด": "off"})):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ เฉพาะแอดมิน", ephemeral=True)
    anti_mention_status[interaction.guild.id] = (status == "on")
    await interaction.response.send_message(embed=security_embed("ANTI-MENTION / @EVERYONE", status, "ตรวจจับการแท็กทุกคนซ้ำๆ ทำการแบนและยึดยศทันที"), ephemeral=True)

@bot.slash_command(name="anti-spam", description="[ 🎃 ระบบกันสแปม ] (สแปมข้อความ แบน+ยึดยศ)")
async def anti_spam(interaction: nextcord.Interaction, status: str = nextcord.SlashOption(choices={"เปิด": "on", "ปิด": "off"})):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ เฉพาะแอดมิน", ephemeral=True)
    anti_spam_status[interaction.guild.id] = (status == "on")
    await interaction.response.send_message(embed=security_embed("ANTI-SPAM", status, "จำกัดความเร็วข้อความ สแปมโดนแบนและยึดยศทันที"), ephemeral=True)

@bot.slash_command(name="anti-nuke", description="[ 🎃 ระบบกันยิงดิส ] (ลบห้อง/ลบยศ แบน+ยึดแอดมิน)")
async def anti_nuke(interaction: nextcord.Interaction, status: str = nextcord.SlashOption(choices={"เปิด": "on", "ปิด": "off"})):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ เฉพาะแอดมิน", ephemeral=True)
    anti_nuke_status[interaction.guild.id] = (status == "on")
    await interaction.response.send_message(embed=security_embed("ANTI-NUKE SYSTEM", status, "ป้องกันการทำลายเซิร์ฟเวอร์ ลบห้องหรือลบยศจะถูกแบนและยึดสิทธิ์ทันที"), ephemeral=True)

@bot.slash_command(name="setup-token-checker", description="🤖 ติดตั้งปุ่ม Token Checker")
async def setup_token(interaction: nextcord.Interaction):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ ไม่มีสิทธิ์", ephemeral=True)
    embed = nextcord.Embed(title="**TOKEN CHECKER**", color=nextcord.Color.red())
    embed.set_image(url=image)
    await interaction.channel.send(embed=embed, view=TokenCheckView())
    await interaction.response.send_message("✅ สำเร็จ", ephemeral=True)

@bot.slash_command(name="setup-verify", description="🛡️ ติดตั้งปุ่มยืนยันตัวตน")
async def setup_verify(interaction: nextcord.Interaction):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ ไม่มีสิทธิ์", ephemeral=True)
    embed = nextcord.Embed(title="**VERIFICATION SYSTEM**", description="กดปุ่มเพื่อยืนยันตัวตน", color=nextcord.Color.blurple())
    await interaction.channel.send(embed=embed, view=VerifyView())
    await interaction.response.send_message("✅ สำเร็จ", ephemeral=True)

@bot.slash_command(name="setup-roles", description="🎯 ติดตั้งเมนูเลือกยศ")
async def setup_roles(interaction: nextcord.Interaction):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ ไม่มีสิทธิ์", ephemeral=True)
    embed = nextcord.Embed(title="**SELF-ASSIGNABLE ROLES**", description="📌 เลือกยศจากเมนูด้านล่าง", color=nextcord.Color.gold())
    await interaction.channel.send(embed=embed, view=RoleSelectView())
    await interaction.response.send_message("✅ สำเร็จ", ephemeral=True)

keep_alive()
bot.run(token)
