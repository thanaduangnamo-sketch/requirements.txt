import nextcord
from nextcord.ext import commands, tasks
import os
from flask import Flask
from threading import Thread
from groq import Groq
import time
from datetime import datetime, timezone, timedelta

# --- ระบบเปิดเว็บจำลองสำหรับ Render (แก้ปัญหา Port scan timeout) ---
app = Flask('')

@app.route('/')
def home():
    return "Frost AI Bot (AI + Verification + Dropdown Roles + Tickets + Auto-Kick) is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# -----------------------------------------------------------------

token = os.environ.get("DISCORD_TOKEN")
groq_api_key = os.environ.get("GROQ_API_KEY")

# เปิด Intents ทั้งหมด (ต้องเปิด Intents.members ด้วยเพื่อให้ระบบจับเวลาคนเข้าเซิร์ฟเวอร์ทำงานได้)
intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ตั้งค่า Groq Client
groq_client = Groq(api_key=groq_api_key)

# ตัวแปรเก็บข้อมูลช่อง AI, ระบบป้องกันสแปม (Cooldown) และเก็บเวลาสมาชิกเข้าเซิร์ฟเวอร์
allowed_ai_channels = {}
user_cooldowns = {}
pending_verifications = {} # เก็บข้อมูลสมาชิกที่รอการยืนยันตัวตน
COOLDOWN_TIME = 3.0  # กำหนดให้รอ 3 วินาทีก่อนคุยใหม่

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (Frost AI - Auto-Kick Mode)")
    
    # เริ่มต้น Loop ตรวจสอบเวลา 5 นาที
    if not check_unverified_users.is_running():
        check_unverified_users.start()

    # ตั้งค่าสถานะบอท
    activity = nextcord.Activity(type=nextcord.ActivityType.watching, name="ดูแลความปลอดภัยและระบบยืนยันตัวตน 🌸")
    await bot.change_presence(status=nextcord.Status.online, activity=activity)
    print("✅ ตั้งค่าสถานะบอทและระบบ Auto-Kick สำเร็จแล้วค่ะ!")


# ==========================================
# 1. ระบบดักจับสมาชิกใหม่เข้าเซิร์ฟเวอร์
# ==========================================
@bot.event
async def on_member_join(member):
    # บันทึกเวลาที่สมาชิกเข้ามา (ใช้เวลา UTC ปัจจุบัน)
    pending_verifications[member.id] = {
        "guild": member.guild,
        "join_time": datetime.now(timezone.utc)
    }


# ==========================================
# 2. ระบบ Background Task ตรวจสอบ 5 นาที & เตะออก
# ==========================================
@tasks.loop(seconds=30) # วนลูปเช็กทุกๆ 30 วินาที
async def check_unverified_users():
    # ตรวจสอบว่ามีการติดตั้งระบบปุ่มยืนยันตัวตนในบอทหรือยัง (เช็กจาก View หรือคำสั่ง setup)
    # ถ้ายังไม่มีการตั้งค่า Verified Role หรือไม่มีคนกด setup ระบบจะไม่เตะ
    current_time = datetime.now(timezone.utc)
    to_remove = []

    for member_id, data in list(pending_verifications.items()):
        guild = data["guild"]
        join_time = data["join_time"]

        # ค้นหายศ Verified ในเซิร์ฟเวอร์
        verified_role = nextcord.utils.get(guild.roles, name="Verified")
        if not verified_role:
            continue # ถ้ายังไม่ได้สร้างยศ Verified ข้ามการตรวจสอบไปก่อน (ตามเงื่อนไข: ถ้าไม่กุยืนยันตัวตนในดิสไม่เตะ)

        member = guild.get_member(member_id)
        if not member:
            # ถ้าหาตัวไม่พบ (ออกจากเซิร์ฟเวอร์ไปเองแล้ว) ให้ลบออกจากรายการรอ
            to_remove.append(member_id)
            continue

        # ถ้าสมาชิกยืนยันตัวตนแล้ว (มีสวมยศ Verified แล้ว) ให้เอาออกจากรายการรอ
        if verified_role in member.roles:
            to_remove.append(member_id)
            continue

        # คำนวณเวลาว่าเกิน 5 นาทีหรือยัง (300 วินาที)
        elapsed_seconds = (current_time - join_time).total_seconds()
        if elapsed_seconds >= 300: # 5 นาที
            try:
                # ส่งข้อความไปบอกส่วนตัว (DM) ก่อนเตะ
                try:
                    await member.send(f"⚠️ สวัสดีค่ะคุณ {member.name} เนื่องจากคุณไม่ได้ทำการกด **'ยืนยันตัวตน'** ภายในเวลา 5 นาทีที่กำหนด ระบบจึงขออนุญาตเชิญคุณออกจากเซิร์ฟเวอร์ **{guild.name}** ก่อนนะคะ สามารถกดลิงก์เชิญกลับเข้ามาใหม่และยืนยันตัวตนได้เสมอนะคะ 🌸")
                except:
                    pass # เผื่อกรณีที่สมาชิกปิดรับ DM จากบอท

                # ทำการเตะ (Kick) สมาชิกออกจากเซิร์ฟเวอร์
                await guild.kick(member, reason="ไม่ยืนยันตัวตนภายในเวลา 5 นาที")
                print(f"👢 เตะสมาชิก {member.name} ออกจากเซิร์ฟเวอร์ {guild.name} เรียบร้อยแล้ว (เนื่องจากไม่ยืนยันตัวตน)")
            except Exception as e:
                print(f"❌ เกิดข้อผิดพลาดในการเตะสมาชิก: {e}")
            
            to_remove.append(member_id)

    # ลบรายชื่อที่จัดการเสร็จแล้วออกจากตัวแปร
    for member_id in to_remove:
        pending_verifications.pop(member_id, None)

@check_unverified_users.before_loop
async def before_check_unverified_users():
    await bot.wait_until_ready()


# ==========================================
# 3. ระบบปุ่มยืนยันตัวตน (พร้อมรูปภาพใหม่)
# ==========================================
class VerificationView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="✅ ยืนยันตัวตน", style=nextcord.ButtonStyle.green, custom_id="verify_button")
    async def verify(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        role = nextcord.utils.get(interaction.guild.roles, name="Verified")
        
        if not role:
            return await interaction.response.send_message("❌ ยังไม่ได้สร้างยศชื่อ `Verified` ในเซิร์ฟเวอร์นี้ค่ะ รบกวนให้แอดมินสร้างยศก่อนน้า!", ephemeral=True)

        if role in interaction.user.roles:
            await interaction.response.send_message("✨ คุณได้ทำการยืนยันตัวตนไปเรียบร้อยแล้วนะคะ!", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            # เอาออกจากรายชื่อรอเตะทันทีเมื่อยืนยันสำเร็จ
            pending_verifications.pop(interaction.user.id, None)
            await interaction.response.send_message("🎉 ยืนยันตัวตนสำเร็จแล้วค่ะ! ยินดีต้อนรับเข้าสู่เซิร์ฟเวอร์นะคะ 💖", ephemeral=True)


@bot.slash_command(name="setup-verification", description="🛡️ ส่งข้อความ, รูปภาพยืนยันตัวตนใหม่ และปุ่มสำหรับสมาชิกใหม่")
async def setup_verification(interaction: nextcord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ เฉพาะแอดมินเซิร์ฟเวอร์เท่านั้นถึงจะใช้คำสั่งนี้ได้ค่ะ", ephemeral=True)

    embed = nextcord.Embed(
        title="🛡️ ยืนยันตัวตนเพื่อเข้าสู่เซิร์ฟเวอร์",
        description="กรุณากดปุ่ม **'✅ ยืนยันตัวตน'** ด้านล่างนี้ภายใน **5 นาที** เพื่อรับยศและป้องกันการถูกเตะออกจากเซิร์ฟเวอร์ค่ะ!",
        color=nextcord.Color.blurple()
    )
    # รูปภาพใหม่สำหรับยืนยันตัวตน
    embed.set_image(url="https://i.pinimg.com/1200x/19/b3/90/19b390db882386287fb4a5f4e7d4177e.jpg")
    embed.set_footer(text="ระบบยืนยันตัวตนแบบอัตโนมัติ 🌸")

    view = VerificationView()
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ สร้างระบบปุ่มยืนยันตัวตนและเปิดใช้งานระบบตรวจสอบ 5 นาทีเรียบร้อยแล้วค่ะ!", ephemeral=True)


# ==========================================
# 4. ระบบเลือกยศแบบดรอปดาวน์ (Role Dropdown)
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
        selected_role_name = self.values[0]
        role = nextcord.utils.get(interaction.guild.roles, name=selected_role_name)

        if not role:
            return await interaction.response.send_message(f"❌ ไม่พบยศชื่อ `{selected_role_name}` ในเซิร์ฟเวอร์นี้ รบกวนให้แอดมินสร้างยศนี้ก่อนนะคะ!", ephemeral=True)

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"📤 ระบบได้ทำการถอดออกยศ **{selected_role_name}** ให้เรียบร้อยแล้วค่ะ", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"📥 ระบบได้มอบยศ **{selected_role_name}** ให้เรียบร้อยแล้วค่ะ!", ephemeral=True)


class RoleSelectView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleSelect())


@bot.slash_command(name="setup-selfroles", description="🏷️ ส่งเมนูดรอปดาวน์เลือกยศพร้อมรูปภาพ")
async def setup_selfroles(interaction: nextcord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ เฉพาะแอดมินเซิร์ฟเวอร์เท่านั้นถึงจะใช้คำสั่งนี้ได้ค่ะ", ephemeral=True)

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
    await interaction.response.send_message("✅ สร้างเมนูดรอปดาวน์เลือกยศในห้องนี้เรียบร้อยแล้วค่ะ!", ephemeral=True)


# ==========================================
# 5. ระบบ Tickets (สร้างห้องคุยส่วนตัว)
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
        guild = interaction.guild
        member = interaction.user

        existing_channel = nextcord.utils.get(guild.text_channels, name=f"ticket-{member.name.lower()}")
        if existing_channel:
            return await interaction.response.send_message(f"❌ คุณมีห้อง Ticket เปิดไว้อยู่แล้วค่ะ: {existing_channel.mention}", ephemeral=True)

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
        await interaction.response.send_message(f"✨ สร้างห้อง Ticket ส่วนตัวให้คุณแล้วค่ะ: {ticket_channel.mention}", ephemeral=True)


@bot.slash_command(name="setup-ticket", description="🎫 ส่งข้อความ, รูปภาพ Tickets และปุ่มเปิดห้องส่วนตัว")
async def setup_ticket(interaction: nextcord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ เฉพาะแอดมินเซิร์ฟเวอร์เท่านั้นถึงจะใช้คำสั่งนี้ได้ค่ะ", ephemeral=True)

    embed = nextcord.Embed(
        title="🎫 ศูนย์ช่วยเหลือและติดต่อแอดมิน (Tickets)",
        description="หากคุณมีปัญหา ติดต่อสอบถาม หรือต้องการแจ้งเรื่องต่างๆ สามารถกดปุ่ม **'🎫 เปิด Ticket'** ด้านล่างนี้เพื่อสร้างห้องพูดคุยส่วนตัวกับทีมงานได้เลยค่ะ!",
        color=nextcord.Color.gold()
    )
    embed.set_image(url="https://i.pinimg.com/1200x/ad/80/97/ad80973abc102722c5d27cb68bcd1363.jpg")
    embed.set_footer(text="ระบบห้องส่วนตัวปลอดภัยและเป็นความลับ 🌸")

    view = TicketView()
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ สร้างระบบ Tickets ในห้องนี้เรียบร้อยแล้วค่ะ!", ephemeral=True)


# ==========================================
# 6. ระบบตั้งค่าช่องคุยกับ Frost AI
# ==========================================
@bot.slash_command(name="set-ai-channel", description="🌸 กำหนดช่องให้ Frost AI พูดคุยด้วย")
async def set_ai_channel(interaction: nextcord.Interaction, channel: nextcord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ เฉพาะแอดมินเซิร์ฟเวอร์เท่านั้นถึงจะตั้งค่าได้ค่ะ", ephemeral=True)

    allowed_ai_channels[interaction.guild.id] = channel.id
    
    embed = nextcord.Embed(
        title="🌸 ตั้งค่าช่อง Frost AI สำเร็จแล้วค่ะ",
        description=f"พูดคุยกับฟรอยด์ได้ที่ช่อง {channel.mention} เลยนะคะ!",
        color=nextcord.Color.pink()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================
# 7. ระบบพูดคุยโต้ตอบกับ Frost AI (พร้อมระบบกันสแปม Cooldown)
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
                warning_msg = await message.channel.send(f"⏳ ใจเย็นๆ ก่อนนะคะคุณ {message.author.name} รออีก **{remaining} วินาที** ค่อยพิมพ์คุยกับฟรอยด์ใหม่น้า 🥺")
                await warning_msg.delete(delay=3)
                return

        user_cooldowns[user_id] = current_time
        user_message = message.content

        async with message.channel.typing():
            try:
                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "system",
                            "content": "คุณคือ 'Frost AI' ผู้ช่วยสาวสวยสุดน่ารัก เป็นกันเอง พูดจาไพเราะ มีหางเสียงค่ะ/คะ ชอบยิ้มแย้มและเป็นมิตรกับทุกคนในดิสคอร์ด คุยเก่ง อบอุ่น และคอยช่วยเหลือสมาชิกด้วยความเต็มใจเสมอ ตอบข้อมูลได้ละเอียดและครบถ้วน"
                        },
                        {
                            "role": "user",
                            "content": f"ผู้ใช้ชื่อ {message.author.name} พูดว่า: {user_message}"
                        }
                    ],
                    temperature=0.7,
                    max_tokens=2048
                )
                ai_reply = response.choices[0].message.content
                
            except Exception as e:
                ai_reply = f"อุ๊ย... ขอโทษด้วยนะคะคุณ {message.author.name} ตอนนี้สมองกล Groq ของฟรอยด์เชื่อมต่อไม่สำเร็จค่ะ 🥺 (Error: {e})"

        if len(ai_reply) > 2000:
            for i in range(0, len(ai_reply), 2000):
                await message.channel.send(ai_reply[i:i+2000])
        else:
            await message.channel.send(ai_reply)

    await bot.process_commands(message)


keep_alive()
bot.run(token)
