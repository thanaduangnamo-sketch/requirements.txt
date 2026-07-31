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

# ตัวแปรสถานะระบบป้องกัน
anti_link_status = {}
anti_mention_status = {}
anti_spam_status = {}
anti_nuke_status = {}

user_message_counts = defaultdict(list)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")

# --- ระบบตรวจสอบข้อความ ---
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    guild_id = message.guild.id
    current_time = time.time()

    # 1. ป้องกันลิงก์
    if anti_link_status.get(guild_id, False):
        if any(domain in message.content for domain in ["http://", "https://", "discord.gg/", "www."]):
            try:
                await message.delete()
                await message.channel.send(f"🚫 `{message.author.name}` ตรวจพบการส่งลิงก์ ระบบได้ทำการบล็อกข้อความนี้ทันที", delete_after=4)
                return
            except Exception:
                pass

    # 2. ป้องกันแท็กซ้ำ
    if anti_mention_status.get(guild_id, False):
        if len(message.mentions) > 3 or len(message.role_mentions) > 2:
            try:
                await message.delete()
                await message.channel.send(f"🚫 `{message.author.name}` แท็กผู้ใช้หรือยศมากเกินกำหนด!", delete_after=4)
                return
            except Exception:
                pass

    # 3. ป้องกันสแปม
    if anti_spam_status.get(guild_id, False):
        author_id = message.author.id
        user_message_counts[author_id] = [t for t in user_message_counts[author_id] if current_time - t < 5]
        user_message_counts[author_id].append(current_time)

        if len(user_message_counts[author_id]) > 5:
            try:
                await message.delete()
                await message.channel.send(f"🚫 `{message.author.name}` ส่งข้อความเร็วเกินไป (สแปม)", delete_after=4)
                return
            except Exception:
                pass

    await bot.process_commands(message)

# --- 4. ป้องกันการลบห้อง (Anti-Nuke) ---
@bot.event
async def on_guild_channel_delete(channel):
    guild_id = channel.guild.id
    if anti_nuke_status.get(guild_id, False):
        try:
            await channel.guild.create_text_channel(name=channel.name)
        except Exception:
            pass

# --- คำสั่งจัดการระบบป้องกัน (ดีไซน์ใหม่สไตล์ Minimal Panel) ---

def security_embed(title, status_type, desc):
    if status_type == "on":
        embed = nextcord.Embed(title=f"🔒 {title}", description=f"**สถานะ:** ` เปิดใช้งานสำเร็จ `\n\n{desc}", color=nextcord.Color.blurple())
    else:
        embed = nextcord.Embed(title=f"🔓 {title}", description=f"**สถานะ:** ` ปิดการใช้งาน `\n\n{desc}", color=nextcord.Color.dark_gray())
    embed.set_footer(text="• ระบบรักษาความปลอดภัยเซิร์ฟเวอร์อัตโนมัติ")
    return embed

@bot.slash_command(name="anti-link", description="[ 🎃 ระบบกันลิ้ง ] ควบคุมการกรองลิงก์แปลกปลอม")
async def anti_link(interaction: nextcord.Interaction, status: str = nextcord.SlashOption(name="status", choices={"เปิด": "on", "ปิด": "off"})):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ เฉพาะผู้ดูแลระบบ (Administrator) เท่านั้น", ephemeral=True)
    
    guild_id = interaction.guild.id
    is_on = (status == "on")
    anti_link_status[guild_id] = is_on
    
    await interaction.response.send_message(embed=security_embed("ANTI-LINK FILTER", status, "ตรวจสอบและบล็อกลิงก์เว็บไซต์หรือลิงก์เชิญเซิร์ฟเวอร์อื่นโดยอัตโนมัติ"), ephemeral=True)

@bot.slash_command(name="anti-mention", description="[ 🎃 ระบบกันแท็กซ้ำ ] ควบคุมการแท็กสแปม")
async def anti_mention(interaction: nextcord.Interaction, status: str = nextcord.SlashOption(name="status", choices={"เปิด": "on", "ปิด": "off"})):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ เฉพาะผู้ดูแลระบบ (Administrator) เท่านั้น", ephemeral=True)
    
    guild_id = interaction.guild.id
    is_on = (status == "on")
    anti_mention_status[guild_id] = is_on
    
    await interaction.response.send_message(embed=security_embed("ANTI-MASS MENTION", status, "ป้องกันการแท็กสมาชิกหรือยศจำนวนมากในข้อความเดียวเพื่อก่อกวน"), ephemeral=True)

@bot.slash_command(name="anti-spam", description="[ 🎃 ระบบกันสแปม ] ควบคุมการส่งข้อความรัว")
async def anti_spam(interaction: nextcord.Interaction, status: str = nextcord.SlashOption(name="status", choices={"เปิด": "on", "ปิด": "off"})):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ เฉพาะผู้ดูแลระบบ (Administrator) เท่านั้น", ephemeral=True)
    
    guild_id = interaction.guild.id
    is_on = (status == "on")
    anti_spam_status[guild_id] = is_on
    
    await interaction.response.send_message(embed=security_embed("ANTI-SPAM PROTECTION", status, "จำกัดความเร็วในการพิมพ์ข้อความ ป้องกันการสแปมห้องแชท"), ephemeral=True)

@bot.slash_command(name="anti-nuke", description="[ 🎃 ระบบกันยิงดิส ] ควบคุมความปลอดภัยเซิร์ฟเวอร์")
async def anti_nuke(interaction: nextcord.Interaction, status: str = nextcord.SlashOption(name="status", choices={"เปิด": "on", "ปิด": "off"})):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ เฉพาะผู้ดูแลระบบ (Administrator) เท่านั้น", ephemeral=True)
    
    guild_id = interaction.guild.id
    is_on = (status == "on")
    anti_nuke_status[guild_id] = is_on
    
    await interaction.response.send_message(embed=security_embed("ANTI-NUKE SYSTEM", status, "ป้องกันการลบห้องหรือทำลายโครงสร้างเซิร์ฟเวอร์จากผู้ไม่หวังดี"), ephemeral=True)

keep_alive()
bot.run(token)
