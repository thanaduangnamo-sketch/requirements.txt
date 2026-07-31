import nextcord
from nextcord.ext import commands
import os
from flask import Flask
from threading import Thread
import wavelink  # ใช้สำหรับระบบเพลงคุณภาพสูง

# --- ระบบเปิดเว็บจำลองสำหรับ Render (แก้ปัญหา Port scan timeout) ---
app = Flask('')

@app.route('/')
def home():
    return "Music Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# -----------------------------------------------------------------

token = os.environ.get("DISCORD_TOKEN")
bot = commands.Bot(command_prefix="!", intents=nextcord.Intents.all())

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    
    # เชื่อมต่อ Lavalink Node (เปลี่ยนค่า URI และ Password ตามเซิร์ฟเวอร์เพลงของคุณ)
    node = wavelink.Node(uri='YOUR_LAVALINK_HOST:PORT', password='YOUR_LAVALINK_PASSWORD')
    await wavelink.Pool.connect(client=bot, nodes=[node])

@bot.event
async def on_wavelink_node_ready(node: wavelink.Node):
    print(f"Lavalink Node {node.identifier} is ready!")


# ==========================================
# ระบบคำสั่งเพลงทั้งหมด (Music Commands)
# ==========================================

@bot.slash_command(name="play", description="🎵 เล่นเพลงจากชื่อเพลงหรือลิงก์ YouTube/Spotify")
async def play(interaction: nextcord.Interaction, search: str):
    await interaction.response.defer()

    if not interaction.user.voice:
        return await interaction.followup.send("❌ คุณต้องเข้าห้องเสียง (Voice Channel) ก่อนใช้งานคำสั่งนี้!", ephemeral=True)

    player: wavelink.Player = interaction.guild.voice_client

    if not player:
        try:
            player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
        except Exception:
            return await interaction.followup.send("❌ ไม่สามารถเชื่อมต่อเข้าห้องเสียงได้", ephemeral=True)

    # ค้นหาเพลง
    tracks = await wavelink.Playable.search(search)
    if not tracks:
        return await interaction.followup.send(f"❌ ไม่พบเพลงที่คุณค้นหา: `{search}`", ephemeral=True)

    track = tracks[0]
    
    if player.playing:
        await player.queue.put_wait(track)
        embed = nextcord.Embed(title="➕ เพิ่มเพลงลงในคิว", description=f"[{track.title}]({track.uri})", color=nextcord.Color.purple())
        embed.set_footer(text=f"ระยะเวลา: {int(track.length // 1000)} วินาที")
        await interaction.followup.send(embed=embed)
    else:
        await player.play(track)
        embed = nextcord.Embed(title="🎶 กำลังเล่นเพลง", description=f"[{track.title}]({track.uri})", color=nextcord.Color.purple())
        embed.set_footer(text=f"ระยะเวลา: {int(track.length // 1000)} วินาที")
        await interaction.followup.send(embed=embed)


@bot.slash_command(name="skip", description="⏭️ ข้ามเพลงที่กำลังเล่นอยู่")
async def skip(interaction: nextcord.Interaction):
    player: wavelink.Player = interaction.guild.voice_client
    if not player or not player.playing:
        return await interaction.response.send_message("❌ ไม่มีเพลงกำลังเล่นอยู่", ephemeral=True)

    await player.skip(force=True)
    await interaction.response.send_message("⏭️ ข้ามเพลงเรียบร้อยแล้ว!", ephemeral=True)


@bot.slash_command(name="stop", description="⏹️ หยุดเพลงและล้างคิวทั้งหมด")
async def stop(interaction: nextcord.Interaction):
    player: wavelink.Player = interaction.guild.voice_client
    if not player:
        return await interaction.response.send_message("❌ บอทไม่ได้อยู่ในห้องเสียง", ephemeral=True)

    player.queue.clear()
    await player.stop()
    await interaction.response.send_message("⏹️ หยุดเพลงและล้างคิวแล้ว", ephemeral=True)


@bot.slash_command(name="leave", description="👋 สั่งให้บอทออกจากห้องเสียง")
async def leave(interaction: nextcord.Interaction):
    player: wavelink.Player = interaction.guild.voice_client
    if not player:
        return await interaction.response.send_message("❌ บอทไม่ได้อยู่ในห้องเสียง", ephemeral=True)

    await player.disconnect()
    await interaction.response.send_message("👋 บอทออกจากห้องเสียงแล้ว", ephemeral=True)


@bot.slash_command(name="queue", description="📜 ดูรายการเพลงในคิวปัจจุบัน")
async def queue_list(interaction: nextcord.Interaction):
    player: wavelink.Player = interaction.guild.voice_client
    if not player or not player.queue:
        return await interaction.response.send_message("❌ ไม่มีเพลงในคิวขณะนี้", ephemeral=True)

    upcoming = [track.title for track in list(player.queue)[:10]]
    queue_str = "\n".join(f"{i+1}. {title}" for i, title in enumerate(upcoming))
    
    embed = nextcord.Embed(title="🎶 คิวเพลงปัจจุบัน", description=queue_str, color=nextcord.Color.blurple())
    await interaction.response.send_message(embed=embed, ephemeral=True)


keep_alive()
bot.run(token)
