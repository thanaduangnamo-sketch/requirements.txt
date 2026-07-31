import nextcord
from nextcord.ext import commands
import os
from flask import Flask
from threading import Thread
import wavelink
from groq import Groq

# --- ระบบเปิดเว็บจำลองสำหรับ Render (แก้ปัญหา Port scan timeout) ---
app = Flask('')

@app.route('/')
def home():
    return "Frost AI Bot (Music + Groq AI + Purple Status) is running!"

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

# ตัวแปรเก็บข้อมูลช่อง AI
allowed_ai_channels = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (Frost AI - Groq Mode)")

    # 1. เชื่อมต่อ Wavelink ผ่านโฮสต์สาธารณะฟรีตัวสำรอง
    try:
        node = wavelink.Node(uri='https://lavalink.astu.dev', password='youshallnotpass')
        await wavelink.Pool.connect(nodes=[node], client=bot)
        print("✅ เชื่อมต่อ Lavalink สำเร็จแล้วค่ะ!")
    except Exception as e:
        print(f"⚠️ เชื่อมต่อ Lavalink ไม่สำเร็จ: {e}")

    # 2. ตั้งค่าสถานะเม็ดม่วง (Streaming)
    streaming_message = "กำลังเปิดเพลงและคุยกับทุกคนนะค้า 🎶🌸"
    twitch_url = "https://www.twitch.tv/monstercat"
    activity = nextcord.Streaming(name=streaming_message, url=twitch_url)
    await bot.change_presence(status=nextcord.Status.online, activity=activity)
    print("✅ ตั้งค่าสถานะสีม่วงสำเร็จแล้วค่ะ!")


# ==========================================
# ระบบเพลง (Wavelink)
# ==========================================
@bot.slash_command(name="play", description="🎶 สั่งให้บอทเข้าห้องเสียงและเปิดเพลงที่คุณต้องการ")
async def play(interaction: nextcord.Interaction, search: str):
    if not interaction.user.voice or not interaction.user.voice.channel:
        return await interaction.send("❌ คุณต้องเข้าห้องเสียงก่อนถึงจะใช้คำสั่งนี้ได้นะคะ!", ephemeral=True)

    player = interaction.guild.voice_client
    if not player:
        try:
            player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
        except Exception as e:
            return await interaction.send(f"❌ ไม่สามารถเชื่อมต่อห้องเสียงได้: {e}", ephemeral=True)

    tracks = await wavelink.Playable.search(search)
    if not tracks:
        return await interaction.send("❌ หาเพลงที่ไม่เจอนะคะ ลองพิมพ์ชื่ออื่นดูน้า 🥺", ephemeral=True)

    track = tracks[0]
    await player.play(track)
    await interaction.send(f"🎶 กำลังเปิดเพลง: **{track.title}** ให้ฟังแล้วค่ะแม่จ๋า 💖")


@bot.slash_command(name="stop", description="⏹️ หยุดเพลงและให้บอทออกจากห้องเสียง")
async def stop(interaction: nextcord.Interaction):
    player = interaction.guild.voice_client
    if player:
        await player.disconnect()
        await interaction.send("⏹️ หยุดเพลงและออกจากห้องเสียงให้เรียบร้อยแล้วค่ะ บายๆ น้า 👋")
    else:
        await interaction.send("❌ ตอนนี้บอทไม่ได้อยู่ในห้องเสียงเลยนะคะ", ephemeral=True)


# ==========================================
# ระบบตั้งค่าช่องคุยกับ Frost AI
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
# ระบบพูดคุยโต้ตอบกับ Frost AI (ใช้ Groq API)
# ==========================================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    guild_id = message.guild.id
    target_channel_id = allowed_ai_channels.get(guild_id)

    if target_channel_id and message.channel.id == target_channel_id:
        user_message = message.content

        async with message.channel.typing():
            try:
                # เรียกใช้งาน Groq API
                response = groq_client.chat.completions.create(
                    model="llama3-70b-8192", # ใช้โมเดลตัวเก่งของ Llama 3
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

        # แบ่งส่งข้อความหากยาวเกินขีดจำกัดของ Discord (2000 ตัวอักษร)
        if len(ai_reply) > 2000:
            for i in range(0, len(ai_reply), 2000):
                await message.channel.send(ai_reply[i:i+2000])
        else:
            await message.channel.send(ai_reply)

    await bot.process_commands(message)


keep_alive()
bot.run(token)
