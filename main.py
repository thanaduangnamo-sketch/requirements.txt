import asyncio
import os
from threading import Thread
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask

# --- ส่วนของ Flask (รันเว็บเซิร์ฟเวอร์หลอก Render ให้บอทออนไลน์) ---
app = Flask("")


@app.route("/")
def home():
  return "Amazing-like Bot is running!"


def run_web():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port)


def keep_alive():
  t = Thread(target=run_web)
  t.start()


# --- ส่วนตั้งค่าบอท Discord ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True


class MultiBot(commands.Bot):

  def __init__(self):
    super().__init__(command_prefix="!", intents=intents)

  async def setup_hook(self):
    await self.tree.sync()
    print("Synced slash commands successfully.")


bot = MultiBot()


@bot.event
async def on_ready():
  print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")


# --- ระบบที่ 1: ต้อนรับสมาชิกใหม่ (Welcome) ---
@bot.event
async def on_member_join(member):
  # หาช่องชื่อว่า welcome หรือ general อัตโนมัติ
  channel = discord.utils.get(member.guild.text_channels, name="welcome")
  if not channel:
    channel = discord.utils.get(member.guild.text_channels, name="general")

  if channel:
    embed = discord.Embed(
        title=f"ยินดีต้อนรับคุณ {member.name}!",
        description=(
            "ยินดีต้อนรับเข้าสู่คอมมูนิตี้ของเรา ขอให้สนุกกับเซิร์ฟเวอร์ครับ 🎉"
        ),
        color=discord.Color.blurple(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    await channel.send(embed=embed)


# --- ระบบที่ 2: Slash Command ประกาศข้อความ (Announce) ---
@bot.tree.command(name="announce", description="ส่งประกาศสำคัญในเซิร์ฟเวอร์")
@app_commands.describe(message="ข้อความที่ต้องการประกาศ")
async def announce(interaction: discord.Interaction, message: str):
  if not interaction.user.guild_permissions.administrator:
    return await interaction.response.send_message(
        "❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้!", ephemeral=True
    )

  embed = discord.Embed(
      title="📢 ประกาศจากผู้ดูแลเซิร์ฟเวอร์",
      description=message,
      color=discord.Color.gold(),
  )
  embed.set_footer(text=f"ประกาศโดย: {interaction.user.name}")

  await interaction.response.send_message(
      "✅ ส่งประกาศเรียบร้อยแล้ว!", ephemeral=True
  )
  await interaction.channel.send(embed=embed)


# --- ระบบที่ 3: Slash Command เช็คสถานะบอท (Ping) ---
@bot.tree.command(name="ping", description="เช็คความเร็วและสถานะของบอท")
async def ping(interaction: discord.Interaction):
  latency = round(bot.latency * 1000)
  await interaction.response.send_message(
      f"🏓 Pong! ความหน่วงของบอท: **{latency} ms**", ephemeral=True
  )


# --- ระบบที่ 4: Slash Command ข้อมูลเซิร์ฟเวอร์ (Server Info) ---
@bot.tree.command(
    name="serverinfo", description="แสดงข้อมูลเบื้องต้นของเซิร์ฟเวอร์นี้"
)
async def serverinfo(interaction: discord.Interaction):
  guild = interaction.guild
  embed = discord.Embed(
      title=f"📊 ข้อมูลเซิร์ฟเวอร์: {guild.name}", color=discord.Color.green()
  )
  embed.add_field(
      name="👑 เจ้าของเซิร์ฟเวอร์", value=guild.owner, inline=True
  )
  embed.add_field(
      name="👥 สมาชิกทั้งหมด", value=f"{guild.member_count} คน", inline=True
  )
  embed.add_field(
      name="💬 จำนวนห้อง",
      value=f"{len(guild.text_channels)} ข้อความ / {len(guild.voice_channels)} เสียง",
      inline=False,
  )
  await interaction.response.send_message(embed=embed)


# เริ่มต้นระบบเว็บจำลอง
keep_alive()

# ดึง Token จาก Environment Variables ของ Render
TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)
