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
    return "Frost AI Bot (Pure Auto Mode) is running!"

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

# กำหนดค่าห้องทำงานต่างๆ (สามารถปรับเปลี่ยน ID ช่องแชทตรงนี้ได้ตามต้องการเลยค่ะ)
ALLOWED_AI_CHANNELS = [123456789012345678]  # ใส่ ID ห้องที่อนุญาตให้คุยกับ AI
LOG_CHANNEL_ID = 123456789012345678       # ใส่ ID ห้องสำหรับส่ง Log ข้อความและสมาชิก

ai_mode = "polite"  # โหมดเริ่มต้น ("polite" หรือ "toxic")
user_cooldowns = {}
pending_verifications = {}
COOLDOWN_TIME = 3.0

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (Frost AI - No Commands Mode)")
    
    if not check_unverified_users.is_running():
        check_unverified_users.start()

    activity = nextcord.Activity(type=nextcord.ActivityType.watching, name="ระบบ AI อัตโนมัติเต็มรูปแบบ 🌸")
    await bot.change_presence(status=nextcord.Status.online, activity=activity)
    print("✅ บอทพร้อมทำงานแบบไร้คำสั่งแล้วค่ะ!")


# ==========================================
# 1. ระบบดักจับสมาชิกใหม่เข้าเซิร์ฟเวอร์ (Auto-Kick 5 นาที)
# ==========================================
@bot.event
async def on_member_join(member):
    pending_verifications[member.id] = {
        "guild": member.guild,
        "join_time": datetime.now(timezone.utc)
    }

    if LOG_CHANNEL_ID:
        log_channel = member.guild.get_channel(LOG_CHANNEL_ID)
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
    if LOG_CHANNEL_ID:
        log_channel = member.guild.get_channel(LOG_CHANNEL_ID)
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
    if message.author.bot or not message.guild or not LOG_CHANNEL_ID:
        return
    log_channel = message.guild.get_channel(LOG_CHANNEL_ID)
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
    if before.author.bot or not before.guild or before.content == after.content or not LOG_CHANNEL_ID:
        return
    log_channel = before.guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = nextcord.Embed(
            title="✏️ ข้อความถูกแก้ไข",
            description=f"**ผู้ส่ง:** {before.author.mention}\n**ห้อง:** {before.channel.mention}\n\n**ก่อนแก้:** {before.content}\n**หลังแก้:** {after.content}",
            color=nextcord.Color.blue()
        )
        embed.set_footer(text=f"Author ID: {before.author.id}")
        await log_channel.send(embed=embed)


# ==========================================
# 3. ระบบพูดคุยโต้ตอบกับ AI อัตโนมัติ
# ==========================================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    if message.channel.id in ALLOWED_AI_CHANNELS:
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

        if ai_mode == "toxic":
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
