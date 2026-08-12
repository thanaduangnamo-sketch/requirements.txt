import asyncio
import os
from threading import Thread
import discord
from discord.ext import commands
from flask import Flask
import yt_dlp

# --- ส่วนของ Flask (เพื่อให้ Render เปิดพอร์ตและไม่ปิดบอท) ---
app = Flask("")


@app.route("/")
def home():
  return "Discord Music Bot is running!"


def run_web():
  # Render จะกำหนด Port มาให้ทาง Environment Variable ชื่อ PORT
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port)


def keep_alive():
  t = Thread(target=run_web)
  t.start()


# --- ส่วนของบอท Discord (โค้ดเดิม) ---
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

ytdl_format_options = {
    "format": "bestaudio/best",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",
}

ffmpeg_options = {
    "before_options": (
        "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    ),
    "options": "-vn",
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):

  def __init__(self, source, *, data, volume=0.5):
    super().__init__(source, volume)
    self.data = data
    self.title = data.get("title")
    self.url = data.get("url")

  @classmethod
  async def from_url(cls, url, *, loop=None, stream=False):
    loop = loop or asyncio.get_running_loop()
    data = await loop.run_in_executor(
        None, lambda: ytdl.extract_info(url, download=not stream)
    )
    if "entries" in data:
      data = data["entries"][0]
    filename = data["url"] if stream else ytdl.prepare_filename(data)
    return cls(
        discord.FFmpegPCMAudio(filename, **ffmpeg_options),
        data=data,
    )


@bot.event
async def on_ready():
  print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")


@bot.command(name="join")
async def join(ctx):
  if not ctx.author.voice:
    return await ctx.send("❌ คุณต้องเข้าห้องเสียงก่อน!")
  channel = ctx.author.voice.channel
  if ctx.voice_client:
    await ctx.voice_client.move_to(channel)
  else:
    await channel.connect()
  await ctx.send(f"✅ เชื่อมต่อห้อง: **{channel.name}**")


@bot.command(name="play")
async def play(ctx, *, query):
  if not ctx.author.voice:
    return await ctx.send("❌ คุณต้องเข้าห้องเสียงก่อน!")
  if not ctx.voice_client:
    await ctx.author.voice.channel.connect()

  async with ctx.typing():
    player = await YTDLSource.from_url(query, loop=bot.loop, stream=True)
    if ctx.voice_client.is_playing():
      ctx.voice_client.stop()
    ctx.voice_client.play(player)

  await ctx.send(f"🎵 กำลังเล่น: **{player.title}**")


@bot.command(name="leave")
async def leave(ctx):
  if ctx.voice_client:
    await ctx.voice_client.disconnect()
    await ctx.send("👋 บอทออกจากห้องแล้ว")


# รัน Web Server หลอก Render ไว้ก่อน
keep_alive()

# ดึง Token จาก Environment Variable ของ Render (แนะนำวิธีนี้เพื่อความปลอดภัย)
TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)
