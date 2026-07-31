import nextcord
from nextcord.ext import commands
import os
from flask import Flask
from threading import Thread
from google import genai

# --- ระบบเปิดเว็บจำลองสำหรับ Render (แก้ปัญหา Port scan timeout) ---
app = Flask('')

@app.route('/')
def home():
    return "Frost AI Girl Bot is running with Streaming Status!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# -----------------------------------------------------------------

token = os.environ.get("DISCORD_TOKEN")
gemini_api_key = os.environ.get("GEMINI_API_KEY")

# เปิด Intents ทั้งหมดเพื่อให้บอททำงานได้เต็มที่
intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ตั้งค่า Google GenAI Client
client = genai.Client(api_key=gemini_api_key)

# ตัวแปรเก็บข้อมูลช่องที่อนุญาตให้คุยกับ AI แยกตามแต่ละเซิร์ฟเวอร์
allowed_ai_channels = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (Frost AI - Girl Mode, Purple Status)")

    # 🌸 ตั้งค่าสถานะบอทให้เป็น "กำลังสตรีม" (Streaming - สีม่วง) 🌸
    streaming_message = "กำลังคุยกับทุกคนอย่างน่ารักเลยค่ะ 🌸"
    twitch_url = "https://www.twitch.tv/monstercat"

    activity = nextcord.Streaming(name=streaming_message, url=twitch_url)
    await bot.change_presence(status=nextcord.Status.online, activity=activity)
    print("✅ ตั้งค่าสถานะสีม่วงสำเร็จแล้วค่ะ!")


# ==========================================
# 1. คำสั่งตั้งค่าช่องสำหรับคุยกับ Frost AI
# ==========================================
@bot.slash_command(name="set-ai-channel", description="🌸 กำหนดช่องให้ Frost AI (สาวน้อยน่ารัก) สามารถพูดคุยด้วยได้")
async def set_ai_channel(interaction: nextcord.Interaction, channel: nextcord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ ขอโทษด้วยนะคะ เฉพาะแอดมินเซิร์ฟเวอร์เท่านั้นถึงจะตั้งค่าได้ค่ะ", ephemeral=True)

    allowed_ai_channels[interaction.guild.id] = channel.id
    
    embed = nextcord.Embed(
        title="🌸 ตั้งค่าช่อง Frost AI สำเร็จแล้วค่ะ",
        description=f"ตอนนี้ฟรอยด์พร้อมพูดคุยกับทุกคนที่ช่อง {channel.mention} แล้วนะคะ มาคุยกันเยอะๆ น้า!",
        color=nextcord.Color.pink()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================
# 2. ระบบพูดคุยโต้ตอบกับ Frost AI (สไตล์ผู้หญิง + แก้บัค)
# ==========================================
@bot.event
async def on_message(message):
    # ป้องกันบอทตอบตัวเองหรือข้อความจากระบบอื่น
    if message.author.bot or not message.guild:
        return

    guild_id = message.guild.id
    target_channel_id = allowed_ai_channels.get(guild_id)

    # เช็คว่าพิมพ์ในช่องที่ตั้งค่าไว้ไหม
    if target_channel_id and message.channel.id == target_channel_id:
        user_message = message.content

        # แจ้งว่าบอทกำลังพิมพ์ (Typing)
        async with message.channel.typing():
            try:
                # คำสั่งกำกับบุคลิกให้ AI ตอบแบบผู้หญิง น่ารัก เป็นกันเอง
                system_instruction = (
                    "คุณคือ 'Frost AI' ผู้ช่วยสาวสวยสุดน่ารัก เป็นกันเอง พูดจาไพเราะ มีหางเสียงค่ะ/คะ "
                    "ชอบยิ้มแย้มและเป็นมิตรกับทุกคนในดิสคอร์ด คุยเก่ง อบอุ่น และคอยช่วยเหลือสมาชิกด้วยความเต็มใจเสมอ"
                )
                
                # ใช้โมเดลเวอร์ชันมาตรฐานล่าสุด
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=f"{system_instruction}\n\nผู้ใช้ชื่อ {message.author.name} พูดว่า: {user_message}"
                )
                ai_reply = response.text
            except Exception as e:
                # ปริ้นท์ Error จริงออกดูที่หน้า Logs ของ Render เพื่อความโปร่งใส
                print(f"Gemini API Error: {e}")
                ai_reply = f"อุ๊ย... ขอโทษด้วยนะคะคุณ {message.author.name} ตอนนี้ฟรอยด์เชื่อมต่อสมองกล AI ไม่สำเร็จค่ะ ลองเช็ค API Key ใน Render ดูใหม่อีกรอบนะคะ 🥺"

        # ส่งข้อความตอบกลับ
        await message.channel.send(ai_reply)

    # สำคัญ: เพื่อให้บอทรับคำสั่ง Slash Command อื่นๆ ได้ด้วย
    await bot.process_commands(message)


keep_alive()
bot.run(token)
