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
    return "Frost AI Girl Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# -----------------------------------------------------------------

token = os.environ.get("DISCORD_TOKEN")
gemini_api_key = os.environ.get("GEMINI_API_KEY")

bot = commands.Bot(command_prefix="!", intents=nextcord.Intents.all())

# ตั้งค่า Google GenAI Client
client = genai.Client(api_key=gemini_api_key)

# ตัวแปรเก็บข้อมูลช่องที่อนุญาตให้คุยกับ AI แยกตามแต่ละเซิร์ฟเวอร์
allowed_ai_channels = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (Frost AI - Girl Mode)")


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
# 2. ระบบพูดคุยโต้ตอบกับ Frost AI (สไตล์ผู้หญิง)
# ==========================================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    guild_id = message.guild.id
    target_channel_id = allowed_ai_channels.get(guild_id)

    # เช็คว่าพิมพ์ในช่องที่ตั้งค่าไว้ไหม
    if target_channel_id and message.channel.id == target_channel_id:
        user_message = message.content

        # แจ้งพิมพ์กำลังพิมพ์ (Typing) ให้ดูสมจริง
        async with message.channel.typing():
            try:
                # คำสั่งกำกับบุคลิกให้ AI ตอบแบบผู้หญิง น่ารัก เป็นกันเอง
                system_instruction = (
                    "คุณคือ 'Frost AI' ผู้ช่วยสาวสวยสุดน่ารัก เป็นกันเอง พูดจาไพเราะ มีหางเสียงค่ะ/คะ "
                    "ชอบยิ้มแย้มและเป็นมิตรกับทุกคนในดิสคอร์ด คุยเก่ง อบอุ่น และคอยช่วยเหลือสมาชิกด้วยความเต็มใจเสมอ"
                )
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=f"{system_instruction}\n\nผู้ใช้ชื่อ {message.author.name} พูดว่า: {user_message}"
                )
                ai_reply = response.text
            except Exception as e:
                ai_reply = "อุ๊ย... ช่วงนี้ฟรอยด์มึนๆ นิดหน่อยค่ะ ลองพิมพ์มาใหม่อีกรอบนะคะ 🥺"

        # ส่งข้อความตอบกลับ
        await message.channel.send(ai_reply)

    await bot.process_commands(message)


keep_alive()
bot.run(token)
