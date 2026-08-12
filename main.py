import asyncio
import os
from threading import Thread
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
import yt_dlp

app = Flask("")


@app.route("/")
def home():
  return "Discord Music Bot is running!"


def run_web():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port)


def keep_alive():
  t = Thread(target=run_web)
  t.start()


intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True


class MusicBot(commands.Bot):

  def __init__(self):
    super().__init__(command_prefix="!", intents=intents)

  async def setup_hook(self):
    await self.tree.sync()
    print("Synced slash commands.")


bot = MusicBot()

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


@bot.tree.command(name="join", description="ให้บอทเข้าห้องเสียงที่คุณอยู่")
async def join(interaction: discord.Interaction):
  if not interaction.user.voice:
    return await interaction.response.send_message(
        "❌ คุณต้องเข้าห้องเสียงก่อน!", ephemeral=True
    )

  await interaction.response.defer(thinking=True)
  channel = interaction.user.voice.channel
  if interaction.guild.voice_client:
    await interaction.guild.voice_client.move_to(channel)
  else:
    await channel.connect()
  await interaction.followup.send(f"✅ เชื่อมต่อห้อง: **{channel.name}**")


@bot.tree.command(name="play", description="เล่นเพลงจากชื่อหรือลิงก์ YouTube")
@app_commands.describe(query="ชื่อเพลงหรือลิงก์ YouTube")
async def play(interaction: discord.Interaction, query: str):
  if not interaction.user.voice:
    return await interaction.response.send_message(
        "❌ คุณต้องเข้าห้องเสียงก่อน!", ephemeral=True
    )

  await interaction.response.defer(thinking=True)

  if not interaction.guild.voice_client:
    await interaction.user.voice.channel.connect()

  player = await YTDLSource.from_url(query, loop=bot.loop, stream=True)
  if interaction.guild.voice_client.is_playing():
    interaction.guild.voice_client.stop()
  interaction.guild.voice_client.play(player)

  await interaction.followup.send(f"🎵 กำลังเล่น: **{player.title}**")


@bot.tree.command(name="stop", description="หยุดเพลงชั่วคราว")
async def stop(interaction: discord.Interaction):
  if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
    interaction.guild.voice_client.pause()
    await interaction.response.send_message("⏸️ หยุดเพลงชั่วคราวแล้ว")
  else:
    await interaction.response.send_message(
        "❌ บอทไม่ได้กำลังเล่นเพลงอยู่", ephemeral=True
    )


@bot.tree.command(name="resume", description="เล่นเพลงต่อ")
async def resume(interaction: discord.Interaction):
  if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
    interaction.guild.voice_client.resume()
    await interaction.response.send_message("▶️ เล่นเพลงต่อแล้ว")
  else:
    await interaction.response.send_message(
        "❌ เพลงไม่ได้ถูกหยุดไว้", ephemeral=True
    )


@bot.tree.command(name="leave", description="ให้บอทออกจากห้องเสียง")
async def leave(interaction: discord.Interaction):
  if interaction.guild.voice_client:
    await interaction.guild.voice_client.disconnect()
    await interaction.response.send_message("👋 บอทออกจากห้องแล้ว")
  else:
    await interaction.response.send_message(
        "❌ บอทไม่ได้อยู่ในห้องเสียง", ephemeral=True
    )


keep_alive()

TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)
