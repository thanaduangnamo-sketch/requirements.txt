import nextcord
from nextcord.ext import commands, tasks
import os
from flask import Flask
from threading import Thread
from groq import Groq
import time
from datetime import datetime, timezone

# --- ระบบเปิดเว็บจำลองสำหรับ Render (แก้ปัญหา Port scan timeout) ---
app = Flask('')

@app.route('/')
def home():
    return "Frost AI Bot (AI Modes + Verification + Dropdown Roles + Tickets + Auto-Kick + Clear + Log) is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# -----------------------------------------------------------------

token = os.environ.get("DISCORD_TOKEN")
groq_api_key = os.environ.get("GROQ_API_KEY")

intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

groq_client = Groq(api_key=groq_api_key)

# ตัวแปรเก็บข้อมูลการตั้งค่าต่างๆ ภายในเซิร์ฟเวอร์
allowed_ai_channels = {}
ai_modes = {} # เก็บโหมด AI ของแต่ละเซิร์ฟเวอร์ (ค่าเริ่มต้นเป็น 'polite' หรือ 'toxic')
log_channels = {}
user_cooldowns = {}
pending_verifications = {}
COOLDOWN_TIME = 3.0

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (Frost AI - Dual AI Mode)")
    
    if not check_unverified_users.is_running():
        check_unverified_users.start()

    activity = nextcord.Activity(type=nextcord.ActivityType.watching, name="ดูแลความปลอดภัยและระบบเลือกโหมด AI 🌸")
    await bot.change_presence(status=nextcord.Status.online, activity=activity)
    print("✅ ตั้งค่าสถานะบอทสำเร็จแล้วค่ะ!")


# ==========================================
# 1. ระบบดักจับสมาชิกใหม่เข้าเซิร์ฟเวอร์ (Auto-Kick 5 นาที)
# ==========================================
@bot.event
async def on_member_join(member):
    pending_verifications[member.id] = {
        "guild": member.guild,
        "join_time": datetime.now(timezone.utc)
    }

    guild_id = member.guild.id
    if guild_id in log_channels:
        log_channel = member.guild.get_channel(log_channels[guild_id])
        if log_channel:
            embed = nextcord.Embed(
                title="📥 สมาชิกใหม่เข้าสู่เซิร์ฟเวอร์",
                description=f"ยินดีต้อนรับคุณ {member.mention} (`{member.name}`)",
                color=nextcord.Color.green()
            )
            embed.set_footer(text=f"ID: {member.id}")
            await log_channel.send(embed=embed)


@bot.event
async def on_member_remove(member):
    guild_id = member.guild.id
    if guild_id in log_channels:
        log_channel = member.guild.get_channel(log_channels[guild_id])
        if log_channel:
            embed = nextcord.Embed(
                title="📤 สมาชิกออกจากเซิร์ฟเวอร์",
                description=f"คุณ {member.mention} (`{member.name}`) ได้ออกจากเซิร์ฟเวอร์ไปแล้ว",
                color=nextcord.Color.red()
            )
            embed.set_footer(text=f"ID: {member.id}")
            await log_channel.send(embed=embed)


@tasks.loop(seconds=30)
async def check_unverified_users():
    current_time = datetime.now(timezone.utc)
    to_remove = []

    for member_id, data in list(pending_verifications.items()):
        guild = data["guild"]
        join_time = data["join_time"]

        verified_role = nextcord.utils.get(guild.roles, name="Verified")
        if not verified_role:
            continue

        member = guild.get_member(member_id)
        if not member:
            to_remove.append(member_id)
            continue

        if verified_role in member.roles:
            to_remove.append(member_id)
            continue

        elapsed_seconds = (current_time - join_time).total_seconds()
        if elapsed_seconds >= 300:
            try:
                try:
                    await member.send(f"⚠️ สวัสดีค่ะคุณ {member.name} เนื่องจากคุณไม่ได้ทำการกด **'ยืนยันตัวตน'** ภายในเวลา 5 นาทีที่กำหนด ระบบจึงขออนุญาตเชิญคุณออกจากเซิร์ฟเวอร์ **{guild.name}** ก่อนนะคะ สามารถกดลิงก์เชิญกลับเข้ามาใหม่และยืนยันตัวตนได้เสมอนะคะ 🌸")
                except:
                    pass

                await guild.kick(member, reason="ไม่ยืนยันตัวตนภายในเวลา 5 นาที")
                print(f"👢 เตะสมาชิก {member.name} ออกจากเซิร์ฟเวอร์ {guild.name} เรียบร้อยแล้ว")
            except Exception as e:
                print(f"❌ เกิดข้อผิดพลาดในการเตะสมาชิก: {e}")
            
            to_remove.append(member_id)

    for member_id in to_remove:
        pending_verifications.pop(member_id, None)

@check_unverified_users.before_loop
async def before_check_unverified_users():
    await bot.wait_until_ready()


# ==========================================
# 2. ระบบ Log ข้อความที่ถูกลบ หรือแก้ไข
# ==========================================
@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild:
        return
    guild_id = message.guild.id
    if guild_id in log_channels:
        log_channel = message.guild.get_channel(log_channels[guild_id])
        if log_channel:
            embed = nextcord.Embed(
                title="🗑️ ข้อความถูกลบ",
                description=f"**ผู้ส่ง:** {message.author.mention}\n**ห้อง:** {message.channel.mention}\n**ข้อความ:**\n{message.content or '[ไม่มีข้อความ / รูปภาพ]'}",
                color=nextcord.Color.orange()
            )
            embed.set_footer(text=f"Author ID: {message.author.id}")
            await log_channel.send(embed=embed)


@bot.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild or before.content == after.content:
        return
    guild_id = before.guild.id
    if guild_id in log_channels:
        log_channel = before.guild.get_channel(log_channels[guild_id])
        if log_channel:
            embed = nextcord.Embed(
                title="✏️ ข้อความถูกแก้ไข",
                description=f"**ผู้ส่ง:** {before.author.mention}\n**ห้อง:** {before.channel.mention}\n\n**ก่อนแก้:** {before.content}\n**หลังแก้:** {after.content}",
                color=nextcord.Color.blue()
            )
            embed.set_footer(text=f"Author ID: {before.author.id}")
            await log_channel.send(embed=embed)


@bot.slash_command(name="set-log-channel", description="📊 กำหนดช่องสำหรับบันทึก Log กิจกรรมในเซิร์ฟเวอร์")
async def set_log_channel(interaction: nextcord.Interaction, channel: nextcord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.administrator:
        return await interaction.followup.send("❌ เฉพาะแอดมินเซิร์ฟเวอร์เท่านั้นถึงจะตั้งค่าได้ค่ะ", ephemeral=True)

    log_channels[interaction.guild.id] = channel.id
    embed = nextcord.Embed(
        title="📊 ตั้งค่าช่อง Log สำเร็จแล้วค่ะ",
        description=f"กิจกรรมทั้งหมดในเซิร์ฟเวอร์จะถูกบันทึกไว้ที่ห้อง {channel.mention} เรียบร้อยค่ะ!",
        color=nextcord.Color.pink()
    )
    await interaction.followup.send(embed=embed, ephemeral=True)


# ==========================================
# 3. คำสั่ง /clear (ลบข้อความ)
# ==========================================
@bot.slash_command(name="clear", description="🧹 ลบข้อความที่ไม่เหมาะสมหรือไม่จำเป็นในห้องแชท")
async def clear(interaction: nextcord.Interaction, amount: int = 10):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.manage_messages:
        return await interaction.followup.send("❌ คุณไม่มีสิทธิ์ในการจัดการข้อความ (Manage Messages) ค่ะ", ephemeral=True)

    if amount < 1 or amount > 100:
        return await interaction.followup.send("❌ กรุณาระบุจำนวนข้อความที่ต้องการลบระหว่าง **1 ถึง 100** ข้อความนะคะ", ephemeral=True)

    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 ทำการลบข้อความที่ไม่จำเป็นออก **{len(deleted)} ข้อความ** เรียบร้อยแล้วค่ะ!", ephemeral=True)


# ==========================================
# 4. ระบบปุ่มยืนยันตัวตน (Verification)
# ==========================================
class VerificationView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="✅ ยืนยันตัวตน", style=nextcord.ButtonStyle.green, custom_id="verify_button")
    async def verify(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer(ephemeral=True)
        role = nextcord.utils.get(interaction.guild.roles, name="Verified")
        
        if not role:
            return await interaction.followup.send("❌ ยังไม่ได้สร้างยศชื่อ `Verified` ในเซิร์ฟเวอร์นี้ค่ะ รบกวนให้แอดมินสร้างยศก่อนน้า!", ephemeral=True)

        if role in interaction.user.roles:
            await interaction.followup.send("✨ คุณได้ทำการยืนยันตัวตนไปเรียบร้อยแล้วนะคะ!", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            pending_verifications.pop(interaction.user.id, None)
            await interaction.followup.send("🎉 ยืนยันตัวตนสำเร็จแล้วค่ะ! ยินดีต้อนรับเข้าสู่เซิร์ฟเวอร์นะคะ 💖", ephemeral=True)


@bot.slash_command(name="setup-verification", description="🛡️ ส่งข้อความ, รูปภาพยืนยันตัวตน และปุ่มสำหรับสมาชิกใหม่")
async def setup_verification(interaction: nextcord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.administrator:
        return await interaction.followup.send("❌ เฉพาะแอดมินเซิร์ฟเวอร์เท่านั้นถึงจะใช้คำสั่งนี้ได้ค่ะ", ephemeral=True)

    embed = nextcord.Embed(
        title="🛡️ ยืนยันตัวตนเพื่อเข้าสู่เซิร์ฟเวอร์",
        description="กรุณากดปุ่ม **'✅ ยืนยันตัวตน'** ด้านล่างนี้ภายใน **5 นาที** เพื่อรับยศและป้องกันการถูกเตะออกจากเซิร์ฟเวอร์ค่ะ!",
        color=nextcord.Color.blurple()
    )
    embed.set_image(url="https://i.pinimg.com/1200x/19/b3/90/19b390db882386287fb4a5f4e7d4177e.jpg")
    embed.set_footer(text="ระบบยืนยันตัวตนแบบอัตโนมัติ 🌸")

    view = VerificationView()
    await interaction.channel.send(embed=embed, view=view)
    await interaction.followup.send("✅ สร้างระบบปุ่มยืนยันตัวตนและเปิดใช้งานระบบตรวจสอบ 5 นาทีเรียบร้อยแล้วค่ะ!", ephemeral=True)


# ==========================================
# 5. ระบบเลือกยศแบบดรอปดาวน์ (Role Dropdown)
# ==========================================
class RoleSelect(nextcord.ui.Select):
    def __init__(self):
        options = [
            nextcord.SelectOption(label="Gamer", description="สำหรับสายเล่นเกม", emoji="🎮", value="Gamer"),
            nextcord.SelectOption(label="Announce", description="สำหรับรับข่าวสารประกาศ", emoji="📢", value="Announce"),
            nextcord.SelectOption(label="Music Lover", description="สำหรับคนรักเสียงเพลง", emoji="🎵", value="Music Lover"),
        ]
        super().__init__(placeholder="📌 เลือกยศที่คุณต้องการที่นี่...", min_values=1, max_values=1, options=options, custom_id="role_select_menu")

    async def callback(self, interaction: nextcord.Interaction):
        await interaction.response.defer(ephemeral=True)
        selected_role_name = self.values[0]
        role = nextcord.utils.get(interaction.guild.roles, name=selected_role_name)

        if not role:
            return await interaction.followup.send(f"❌ ไม่พบยศชื่อ `{selected_role_name}` ในเซิร์ฟเวอร์นี้ รบกวนให้แอดมินสร้างยศนี้ก่อนนะคะ!", ephemeral=True)

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.followup.send(f"📤 ระบบได้ทำการถอดออกยศ **{selected_role_name}** ให้เรียบร้อยแล้วค่ะ", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.followup.send(f"📥 ระบบได้มอบยศ **{selected_role_name}** ให้เรียบร้อยแล้วค่ะ!", ephemeral=True)


class RoleSelectView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleSelect())


@bot.slash_command(name="setup-selfroles", description="🏷️ ส่งเมนูดรอปดาวน์เลือกยศพร้อมรูปภาพ")
async def setup_selfroles(interaction: nextcord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.administrator:
        return await interaction.followup.send("❌ เฉพาะแอดมินเซิร์ฟเวอร์เท่านั้นถึงจะใช้คำสั่งนี้ได้ค่ะ", ephemeral=True)

    embed = nextcord.Embed(
        title="🏷️ ระบบเลือกยศด้วยตนเอง (Self-Roles)",
        description="กดเลือกยศที่คุณสนใจจากเมนูดรอปดาวน์ด้านล่างนี้ได้เลยนะคะ!\n\n"
                    "• 🎮 **Gamer** - สำหรับสายเล่นเกม\n"
                    "• 📢 **Announce** - สำหรับรับข่าวสารประกาศ\n"
                    "• 🎵 **Music Lover** - สำหรับคนรักเสียงเพลง",
        color=nextcord.Color.purple()
    )
    embed.set_image(url="https://i.pinimg.com/736x/57/6b/75/576b75f28cd7812560fd2984e3af10c3.jpg")
    embed.set_footer(text="เลือกซ้ำเพื่อถอดออก หรือเลือกเพื่อรับยศ 🌸")

    view = RoleSelectView()
    await interaction.channel.send(embed=embed, view=view)
    await interaction.followup.send("✅ สร้างเมนูดรอปดาวน์เลือกยศในห้องนี้เรียบร้อยแล้วค่ะ!", ephemeral=True)


# ==========================================
# 6. ระบบ Tickets
# ==========================================
class CloseTicketView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="🔒 ปิดห้อง Ticket", style=nextcord.ButtonStyle.red, custom_id="close_ticket_btn")
    async def close_ticket(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_message("🔒 กำลังปิดห้อง Ticket นี้ใน 5 วินาที...", ephemeral=False)
        time.sleep(2)
        await interaction.channel.delete()


class TicketView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="🎫 เปิด Ticket (ติดต่อแอดมิน)", style=nextcord.ButtonStyle.primary, custom_id="create_ticket_btn")
    async def create_ticket(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        member = interaction.user

        existing_channel = nextcord.utils.get(guild.text_channels, name=f"ticket-{member.name.lower()}")
        if existing_channel:
            return await interaction.followup.send(f"❌ คุณมีห้อง Ticket เปิดไว้อยู่แล้วค่ะ: {existing_channel.mention}", ephemeral=True)

        overwrites = {
            guild.default_role: nextcord.PermissionOverwrite(view_channel=False),
            member: nextcord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: nextcord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{member.name}",
            overwrites=overwrites,
            topic=f"Ticket ของคุณ {member.name} ({member.id})"
        )

        embed = nextcord.Embed(
            title=f"🎫 Ticket ของคุณ {member.name}",
            description="สวัสดีค่ะ! แจ้งปัญหาหรือเรื่องที่ต้องการติดต่อกับแอดมินไว้ได้เลยนะคะ\nแอดมินจะรีบเข้ามาช่วยเหลือโดยเร็วที่สุดค่ะ 🌸",
            color=nextcord.Color.green()
        )
        embed.set_footer(text="กดปุ่มด้านล่างนี้เพื่อปิดห้องเมื่อเสร็จสิ้นธุระ")

        view = CloseTicketView()
        await ticket_channel.send(content=f"{member.mention} ยินดีต้อนรับสู่ Ticket ค่ะ!", embed=embed, view=view)
        await interaction.followup.send(f"✨ สร้างห้อง Ticket ส่วนตัวให้คุณแล้วค่ะ: {ticket_channel.mention}", ephemeral=True)


@bot.slash_command(name="setup-ticket", description="🎫 ส่งข้อความ, รูปภาพ Tickets และปุ่มเปิดห้องส่วนตัว")
async def setup_ticket(interaction: nextcord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.administrator:
        return await interaction.followup.send("❌ เฉพาะแอดมินเซิร์ฟเวอร์เท่านั้นถึงจะใช้คำสั่งนี้ได้ค่ะ", ephemeral=True)

    embed = nextcord.Embed(
        title="🎫 ศูนย์ช่วยเหลือและติดต่อแอดมิน (Tickets)",
        description="หากคุณมีปัญหา ติดต่อสอบถาม หรือต้องการแจ้งเรื่องต่างๆ สามารถกดปุ่ม **'🎫 เปิด Ticket'** ด้านล่างนี้เพื่อสร้างห้องพูดคุยส่วนตัวกับทีมงานได้เลยค่ะ!",
        color=nextcord.Color.gold()
    )
    embed.set_image(url="https://i.pinimg.com/1200x/ad/80/97/ad80973abc102722c5d27cb68bcd1363.jpg")
    embed.set_footer(text="ระบบห้องส่วนตัวปลอดภัยและเป็นความลับ 🌸")

    view = TicketView()
    await interaction.channel.send(embed=embed, view=view)
    await interaction.followup.send("✅ สร้างระบบ Tickets ในห้องนี้เรียบร้อยแล้วค่ะ!", ephemeral=True)


# ==========================================
# 7. ระบบตั้งค่าช่องคุยกับ AI และเลือกโหมด (Polite / Toxic)
# ==========================================
@bot.slash_command(name="set-ai-channel", description="🌸 กำหนดช่องให้ Frost AI พูดคุยด้วย")
async def set_ai_channel(interaction: nextcord.Interaction, channel: nextcord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.administrator:
        return await interaction.followup.send("❌ เฉพาะแอดมินเซิร์ฟเวอร์เท่านั้นถึงจะตั้งค่าได้ค่ะ", ephemeral=True)

    allowed_ai_channels[interaction.guild.id] = channel.id
    embed = nextcord.Embed(
        title="🌸 ตั้งค่าช่อง Frost AI สำเร็จแล้วค่ะ",
        description=f"พูดคุยกับฟรอยด์ได้ที่ช่อง {channel.mention} เลยนะคะ!",
        color=nextcord.Color.pink()
    )
    await interaction.followup.send(embed=embed, ephemeral=True)


# ปุ่มสำหรับเลือกโหมด AI (แบบ 2 โหมด)
class AIModeSelectView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="🌸 โหมดสุภาพ (น่ารัก อ่อนหวาน)", style=nextcord.ButtonStyle.green, custom_id="ai_mode_polite")
    async def set_polite(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ai_modes[interaction.guild.id] = "polite"
        await interaction.followup.send("🌸 ตั้งค่า AI เป็น **'โหมดสุภาพ'** เรียบร้อยแล้วค่ะ! พร้อมต้อนรับด้วยความน่ารักสดใส ✨", ephemeral=True)

    @nextcord.ui.button(label="😈 โหมดสายด่า / ปากแจ๋ว (ด่าได้ เถียงได้ สะใจ)", style=nextcord.ButtonStyle.red, custom_id="ai_mode_toxic")
    async def set_toxic(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ai_modes[interaction.guild.id] = "toxic"
        await interaction.followup.send("😈 ตั้งค่า AI เป็น **'โหมดสายด่า / ปากแจ๋ว'** เรียบร้อยแล้วค่ะ! อยากด่า อยากเถียงจัดมาได้เลยสะใจแน่นอน 🔥", ephemeral=True)


@bot.slash_command(name="ai-chat", description="⚙️ เลือกโหมดการสนทนากับ AI (โหมดสุภาพ หรือ โหมดสายด่าปากแจ๋ว)")
async def ai_chat_menu(interaction: nextcord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.administrator:
        return await interaction.followup.send("❌ เฉพาะแอดมินเซิร์ฟเวอร์เท่านั้นถึงจะเลือกโหมดนี้ได้ค่ะ", ephemeral=True)

    current_mode = ai_modes.get(interaction.guild.id, "polite")
    mode_text = "🌸 โหมดสุภาพ (น่ารัก)" if current_mode == "polite" else "😈 โหมดสายด่า / ปากแจ๋ว"

    embed = nextcord.Embed(
        title="🤖 ระบบเลือกโหมดสนทนากับ Frost AI",
        description=f"สถานะโหมดปัจจุบันของเซิร์ฟเวอร์: **{mode_text}**\n\nกรุณาเลือกโหมดที่ต้องการจากปุ่มด้านล่างนี้ได้เลยค่ะ!",
        color=nextcord.Color.purple()
    )
    
    view = AIModeSelectView()
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)


@bot.slash_command(name="ai-ready", description="🌸 ประกาศว่า Frost AI พร้อมใช้งานแล้วในช่องแชท")
async def ai_ready(interaction: nextcord.Interaction, channel: nextcord.TextChannel = None):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.administrator:
        return await interaction.followup.send("❌ เฉพาะแอดมินเซิร์ฟเวอร์เท่านั้นถึงจะใช้คำสั่งนี้ได้ค่ะ", ephemeral=True)
    
    target_channel = channel if channel else interaction.channel

    embed = nextcord.Embed(
        title="🌸 Frost AI พร้อมใช้งานแล้วงับ!",
        description="ตอนนี้น้องฟรอยด์พร้อมคุยกับทุกคนแล้วนะคะ พิมพ์ทักทายหรือถามคำถามมาได้เลยงับ 💖",
        color=nextcord.Color.pink()
    )
    embed.set_footer(text="ระบบ AI อัจฉริยะ 🌸")

    await target_channel.send(embed=embed)
    await interaction.followup.send(f"✅ ส่งข้อความประกาศ AI พร้อมใช้งานไปที่ {target_channel.mention} เรียบร้อยแล้วค่ะ!", ephemeral=True)


# ==========================================
# 8. ระบบพูดคุยโต้ตอบกับ AI ตามโหมดที่เลือก
# ==========================================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    guild_id = message.guild.id
    target_channel_id = allowed_ai_channels.get(guild_id)

    if target_channel_id and message.channel.id == target_channel_id:
        user_id = message.author.id
        current_time = time.time()

        if user_id in user_cooldowns:
            elapsed_time = current_time - user_cooldowns[user_id]
            if elapsed_time < COOLDOWN_TIME:
                remaining = round(COOLDOWN_TIME - elapsed_time, 1)
                warning_msg = await message.channel.send(f"⏳ ใจเย็นๆ ก่อนนะคะคุณ {message.author.name} รออีก **{remaining} วินาที** ค่อยพิมพ์คุยใหม่น้า 🥺")
                await warning_msg.delete(delay=3)
                return

        user_cooldowns[user_id] = current_time
        user_message = message.content

        # ตรวจสอบโหมดปัจจุบันของเซิร์ฟเวอร์
        current_mode = ai_modes.get(guild_id, "polite")

        if current_mode == "toxic":
            system_prompt = (
                "คุณคือ AI สายปากแจ๋ว กวนโอ๊ย และพร้อมบวก ปากจัด ด่าเก่ง เถียงคำไม่ตกฟาก พูดจาหยาบคายได้นิดหน่อยตามฟีลเพื่อนเกรียนๆ "
                "ชอบแซะ ชอบกวนประสาทคนที่ทักมา แต่ก็ยังให้ข้อมูลหรือตอบคำถามได้ปกติ ห้ามเรียบร้อยเด็ดขาด ต้องมีความกวนบาทาและดิบเถื่อนแบบวัยรุ่นสร้างตัว"
            )
        else:
            system_prompt = (
                "คุณคือ 'Frost AI' ผู้ช่วยสาวสวยสุดน่ารัก เป็นกันเอง พูดจาไพเราะ มีหางเสียงค่ะ/คะ ชอบยิ้มแย้มและเป็นมิตรกับทุกคนในดิสคอร์ด "
                "คุยเก่ง อบอุ่น และคอยช่วยเหลือสมาชิกด้วยความเต็มใจเสมอ ตอบข้อมูลได้ละเอียดและครบถ้วน"
            )

        async with message.channel.typing():
            try:
                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": f"ผู้ใช้ชื่อ {message.author.name} พูดว่า: {user_message}"
                        }
                    ],
                    temperature=0.8,
                    max_tokens=2048
                )
                ai_reply = response.choices[0].message.content
                
            except Exception as e:
                ai_reply = f"อุ๊ย... ขอโทษด้วยนะคะคุณ {message.author.name} ตอนนี้สมองกลเชื่อมต่อไม่สำเร็จค่ะ 🥺 (Error: {e})"

        if len(ai_reply) > 2000:
            for i in range(0, len(ai_reply), 2000):
                await message.channel.send(ai_reply[i:i+2000])
        else:
            await message.channel.send(ai_reply)

    await bot.process_commands(message)


keep_alive()
bot.run(token)
