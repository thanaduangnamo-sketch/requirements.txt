import nextcord
from nextcord.ext import commands
import os
from flask import Flask
from threading import Thread
from groq import Groq
import time

# --- ระบบเปิดเว็บจำลองสำหรับ Render (แก้ปัญหา Port scan timeout) ---
app = Flask('')

@app.route('/')
def home():
    return "Frost AI Bot (AI + Verification + Dropdown Roles with New Image) is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# -----------------------------------------------------------------

token = os.environ.get("DISCORD_TOKEN")
groq_api_key = os.environ.get("GROQ_API_KEY")

# เปิด Intents ทั้งหมด
intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ตั้งค่า Groq Client
groq_client = Groq(api_key=groq_api_key)

# ตัวแปรเก็บข้อมูลช่อง AI และระบบป้องกันสแปม (Cooldown)
allowed_ai_channels = {}
user_cooldowns = {}
COOLDOWN_TIME = 3.0  # กำหนดให้รอ 3 วินาทีก่อนคุยใหม่

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (Frost AI - New Image Mode)")

    # ตั้งค่าสถานะบอท
    activity = nextcord.Activity(type=nextcord.ActivityType.watching, name="ระบบยืนยันตัวตนและเลือกยศ 🌸")
    await bot.change_presence(status=nextcord.Status.online, activity=activity)
    print("✅ ตั้งค่าสถานะบอทสำเร็จแล้วค่ะ!")


# ==========================================
# 1. ระบบปุ่มยืนยันตัวตน (พร้อมรูปภาพใหม่)
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
            await interaction.response.send_message("🎉 ยืนยันตัวตนสำเร็จแล้วค่ะ! ยินดีต้อนรับเข้าสู่เซิร์ฟเวอร์นะคะ 💖", ephemeral=True)


@bot.slash_command(name="setup-verification", description="🛡️ ส่งข้อความ, รูปภาพใหม่ และปุ่มยืนยันตัวตนสำหรับสมาชิกใหม่")
async def setup_verification(interaction: nextcord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ เฉพาะแอดมินเซิร์ฟเวอร์เท่านั้นถึงจะใช้คำสั่งนี้ได้ค่ะ", ephemeral=True)

    embed = nextcord.Embed(
        title="🛡️ ยืนยันตัวตนเพื่อเข้าสู่เซิร์ฟเวอร์",
        description="กรุณากดปุ่ม **'✅ ยืนยันตัวตน'** ด้านล่างนี้ เพื่อรับยศและปลดล็อกห้องพูดคุยทั้งหมดภายในเซิร์ฟเวอร์ของเราค่ะ!",
        color=nextcord.Color.blurple()
    )
    # อัปเดตรูปภาพใหม่ตามที่คุณส่งมา
    embed.set_image(url="https://i.pinimg.com/736x/57/6b/75/576b75f28cd7812560fd2984e3af10c3.jpg")
    embed.set_footer(text="ระบบยืนยันตัวตนแบบรวดเร็วและปลอดภัย 🌸")

    view = VerificationView()
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ สร้างระบบปุ่มยืนยันตัวตนพร้อมรูปภาพใหม่ในห้องนี้เรียบร้อยแล้วค่ะ!", ephemeral=True)


# ==========================================
# 2. ระบบเลือกยศแบบเมนูเลือกลงมา (Role Dropdown Select Menu + รูปภาพใหม่)
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


@bot.slash_command(name="setup-selfroles", description="🏷️ ส่งเมนูดรอปดาวน์เลือกยศพร้อมรูปภาพใหม่")
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
    # อัปเดตรูปภาพใหม่ตามที่คุณส่งมา
    embed.set_image(url="https://i.pinimg.com/736x/57/6b/75/576b75f28cd7812560fd2984e3af10c3.jpg")
    embed.set_footer(text="เลือกซ้ำเพื่อถอดออก หรือเลือกเพื่อรับยศ 🌸")

    view = RoleSelectView()
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ สร้างเมนูดรอปดาวน์เลือกยศพร้อมรูปภาพใหม่ในห้องนี้เรียบร้อยแล้วค่ะ!", ephemeral=True)


# ==========================================
# 3. ระบบตั้งค่าช่องคุยกับ Frost AI
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
# 4. ระบบพูดคุยโต้ตอบกับ Frost AI (พร้อมระบบกันสแปม Cooldown)
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
