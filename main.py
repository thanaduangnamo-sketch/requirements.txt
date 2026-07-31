import nextcord
from nextcord.ext import commands
import os
from flask import Flask
from threading import Thread

# --- ระบบเปิดเว็บจำลองสำหรับ Render (แก้ปัญหา Port scan timeout) ---
app = Flask('')

@app.route('/')
def home():
    return "Frost AI Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# -----------------------------------------------------------------

token = os.environ.get("DISCORD_TOKEN")
bot = commands.Bot(command_prefix="!", intents=nextcord.Intents.all())

# ตัวแปรเก็บข้อมูลช่องที่อนุญาตให้คุยกับ AI แยกตามแต่ละเซิร์ฟเวอร์ (Key: Guild ID, Value: Channel ID)
allowed_ai_channels = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")


# ==========================================
# 1. คำสั่งตั้งค่าช่องสำหรับคุยกับ Frost AI
# ==========================================
@bot.slash_command(name="set-ai-channel", description="🤖 กำหนดช่องให้ Frost AI สามารถพูดคุยด้วยได้")
async def set_ai_channel(interaction: nextcord.Interaction, channel: nextcord.TextChannel):
    # ตรวจสอบว่าผู้ใช้เป็นแอดมินเซิร์ฟเวอร์หรือไม่
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ เฉพาะแอดมินเซิร์ฟเวอร์เท่านั้นที่สามารถตั้งค่าได้", ephemeral=True)

    # บันทึก ID ช่องของเซิร์ฟเวอร์นี้
    allowed_ai_channels[interaction.guild.id] = channel.id
    
    embed = nextcord.Embed(
        title="🤖 ตั้งค่าช่อง Frost AI สำเร็จ",
        description=f"ตั้งค่าให้พูดคุยกับ Frost AI ได้ที่ช่อง: {channel.mention} เรียบร้อยแล้วครับ!",
        color=nextcord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================
# 2. ระบบรับ-ส่งข้อความพูดคุยกับ Frost AI
# ==========================================
@bot.event
async def on_message(message):
    # ป้องกันไม่ให้บอทตอบข้อความของตัวเอง หรือบอทตัวอื่น
    if message.author.bot or not message.guild:
        return

    guild_id = message.guild.id
    target_channel_id = allowed_ai_channels.get(guild_id)

    # ตรวจสอบว่าเซิร์ฟเวอร์นี้ได้ตั้งค่าช่องสำหรับคุยกับ AI หรือยัง และพิมพ์ในช่องนั้นหรือไม่
    if target_channel_id and message.channel.id == target_channel_id:
        user_message = message.content

        # ตัวอย่างการจำลองการตอบกลับของ Frost AI (คุณสามารถเปลี่ยนเป็นเชื่อมต่อ API ของ AI เช่น OpenAI ได้ในส่วนนี้)
        ai_response = f"สวัสดีครับคุณ {message.author.mention}! Frost AI ได้รับข้อความของคุณแล้ว: \"{user_message}\""

        # ส่งข้อความตอบกลับในช่องนั้นทันที
        await message.channel.send(ai_response)

    # ให้บอทสามารถทำงานคำสั่งอื่นๆ ต่อไปได้ (ถ้ามี)
    await bot.process_commands(message)


keep_alive()
bot.run(token)
