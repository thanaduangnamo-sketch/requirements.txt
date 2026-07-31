import nextcord
from nextcord.ext import commands
import os
from flask import Flask
from threading import Thread
import time
from collections import defaultdict

# --- ระบบเปิดเว็บจำลองสำหรับ Render (แก้ปัญหา Port scan timeout) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# -----------------------------------------------------------------

token = os.environ.get("DISCORD_TOKEN")
bot = commands.Bot(command_prefix="!", intents=nextcord.Intents.all())

# ตัวแปรเปิด/ปิด ระบบป้องกันของแต่ละเซิร์ฟเวอร์
anti_link_status = {}
anti_mention_status = {}
anti_spam_status = {}
anti_nuke_status = {}

# ตัวแปรเก็บข้อมูลสแปมข้อความและการแท็ก
user_message_counts = defaultdict(list)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")

# --- ระบบตรวจสอบข้อความ (Anti-Link, Anti-Mention, Anti-Spam) ---
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    guild_id = message.guild.id
    current_time = time.time()

    # 1. ระบบกันลิ้ง (/anti-link)
    if anti_link_status.get(guild_id, False):
        if "http://" in message.content or "https://" in message.content or "discord.gg/" in message.content or "www." in message.content:
            try:
                await message.delete()
                embed = nextcord.Embed(
                    description=f"⚠️ {message.author.mention} **ไม่อนุญาตให้ส่งลิงก์ในห้องนี้!**",
                    color=nextcord.Color.red()
                )
                await message.channel.send(embed=embed, delete_after=5)
                return
            except Exception:
                pass

    # 2. ระบบกันแท็กซ้ำ (/anti-mention)
    if anti_mention_status.get(guild_id, False):
        if len(message.mentions) > 3 or len(message.role_mentions) > 2:
            try:
                await message.delete()
                embed = nextcord.Embed(
                    description=f"⚠️ {message.author.mention} **คุณแท็กผู้ใช้หรือยศมากเกินไป!**",
                    color=nextcord.Color.red()
                )
                await message.channel.send(embed=embed, delete_after=5)
                return
            except Exception:
                pass

    # 3. ระบบกันสแปม (/anti-spam)
    if anti_spam_status.get(guild_id, False):
        author_id = message.author.id
        user_message_counts[author_id] = [t for t in user_message_counts[author_id] if current_time - t < 5]
        user_message_counts[author_id].append(current_time)

        if len(user_message_counts[author_id]) > 5:
            try:
                await message.delete()
                embed = nextcord.Embed(
                    description=f"⚠️ {message.author.mention} **กรุณาอย่าสแปมข้อความ!**",
                    color=nextcord.Color.red()
                )
                await message.channel.send(embed=embed, delete_after=5)
                return
            except Exception:
                pass

    await bot.process_commands(message)

# --- 4. ระบบกันยิงดิส / Anti-Nuke ---
@bot.event
async def on_guild_channel_delete(channel):
    guild_id = channel.guild.id
    if anti_nuke_status.get(guild_id, False):
        try:
            await channel.guild.create_text_channel(name=channel.name)
        except Exception:
            pass

# --- คำสั่งเปิด/ปิดระบบป้องกัน (ดีไซน์ Embed สวยหรู) ---

@bot.slash_command(name="anti-link", description="[ 🎃 ระบบกันลิ้ง ] เปิด/ปิด ระบบป้องกันการส่งลิ้งก์")
async def anti_link(interaction: nextcord.Interaction, status: str = nextcord.SlashOption(name="status", choices={"เปิด": "on", "ปิด": "off"})):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(embed=nextcord.Embed(description="❌ **คุณต้องมีสิทธิ์ Administrator ถึงจะใช้คำสั่งนี้ได้**", color=nextcord.Color.red()), ephemeral=True)
    
    guild_id = interaction.guild.id
    if status == "on":
        anti_link_status[guild_id] = True
        embed = nextcord.Embed(title="🛡️ Security System | Anti-Link", description="✅ เปิดใช้งาน **ระบบกันลิงก์** เรียบร้อยแล้ว", color=nextcord.Color.green())
        embed.set_footer(text="ระบบป้องกันความปลอดภัยเซิร์ฟเวอร์")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        anti_link_status[guild_id] = False
        embed = nextcord.Embed(title="🛡️ Security System | Anti-Link", description="❌ ปิดใช้งาน **ระบบกันลิงก์** แล้ว", color=nextcord.Color.orange())
        embed.set_footer(text="ระบบป้องกันความปลอดภัยเซิร์ฟเวอร์")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.slash_command(name="anti-mention", description="[ 🎃 ระบบกันแท็กซ้ำ ] เปิด/ปิด ระบบป้องกันการแท็กสแปม")
async def anti_mention(interaction: nextcord.Interaction, status: str = nextcord.SlashOption(name="status", choices={"เปิด": "on", "ปิด": "off"})):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(embed=nextcord.Embed(description="❌ **คุณต้องมีสิทธิ์ Administrator ถึงจะใช้คำสั่งนี้ได้**", color=nextcord.Color.red()), ephemeral=True)
    
    guild_id = interaction.guild.id
    if status == "on":
        anti_mention_status[guild_id] = True
        embed = nextcord.Embed(title="🛡️ Security System | Anti-Mention", description="✅ เปิดใช้งาน **ระบบกันแท็กซ้ำ** เรียบร้อยแล้ว", color=nextcord.Color.green())
        embed.set_footer(text="ระบบป้องกันความปลอดภัยเซิร์ฟเวอร์")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        anti_mention_status[guild_id] = False
        embed = nextcord.Embed(title="🛡️ Security System | Anti-Mention", description="❌ ปิดใช้งาน **ระบบกันแท็กซ้ำ** แล้ว", color=nextcord.Color.orange())
        embed.set_footer(text="ระบบป้องกันความปลอดภัยเซิร์ฟเวอร์")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.slash_command(name="anti-spam", description="[ 🎃 ระบบกันสแปม ] เปิด/ปิด ระบบป้องกันสแปมข้อความ")
async def anti_spam(interaction: nextcord.Interaction, status: str = nextcord.SlashOption(name="status", choices={"เปิด": "on", "ปิด": "off"})):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(embed=nextcord.Embed(description="❌ **คุณต้องมีสิทธิ์ Administrator ถึงจะใช้คำสั่งนี้ได้**", color=nextcord.Color.red()), ephemeral=True)
    
    guild_id = interaction.guild.id
    if status == "on":
        anti_spam_status[guild_id] = True
        embed = nextcord.Embed(title="🛡️ Security System | Anti-Spam", description="✅ เปิดใช้งาน **ระบบกันสแปม** เรียบร้อยแล้ว", color=nextcord.Color.green())
        embed.set_footer(text="ระบบป้องกันความปลอดภัยเซิร์ฟเวอร์")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        anti_spam_status[guild_id] = False
        embed = nextcord.Embed(title="🛡️ Security System | Anti-Spam", description="❌ ปิดใช้งาน **ระบบกันสแปม** แล้ว", color=nextcord.Color.orange())
        embed.set_footer(text="ระบบป้องกันความปลอดภัยเซิร์ฟเวอร์")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.slash_command(name="anti-nuke", description="[ 🎃 ระบบกันยิงดิส ] เปิด/ปิด ระบบป้องกันการทำลายเซิร์ฟเวอร์")
async def anti_nuke(interaction: nextcord.Interaction, status: str = nextcord.SlashOption(name="status", choices={"เปิด": "on", "ปิด": "off"})):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(embed=nextcord.Embed(description="❌ **คุณต้องมีสิทธิ์ Administrator ถึงจะใช้คำสั่งนี้ได้**", color=nextcord.Color.red()), ephemeral=True)
    
    guild_id = interaction.guild.id
    if status == "on":
        anti_nuke_status[guild_id] = True
        embed = nextcord.Embed(title="🛡️ Security System | Anti-Nuke", description="✅ เปิดใช้งาน **ระบบกันยิงดิส** เรียบร้อยแล้ว", color=nextcord.Color.green())
        embed.set_footer(text="ระบบป้องกันความปลอดภัยเซิร์ฟเวอร์")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        anti_nuke_status[guild_id] = False
        embed = nextcord.Embed(title="🛡️ Security System | Anti-Nuke", description="❌ ปิดใช้งาน **ระบบกันยิงดิส** แล้ว", color=nextcord.Color.orange())
        embed.set_footer(text="ระบบป้องกันความปลอดภัยเซิร์ฟเวอร์")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# เริ่มรันระบบเว็บจำลองควบคู่ไปกับบอท
keep_alive()
bot.run(token)
