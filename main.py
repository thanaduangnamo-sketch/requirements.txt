import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread

# ==================================================
# 🌐 WEB SERVER FOR RENDER (Keep-Alive)
# ==================================================
app = Flask('')

@app.route('/')
def home():
    return "Bot is running online 24/7!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.start()

# ==================================================
# ⚙️ BOT INITIALIZATION
# ==================================================
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# In-Memory Database (ควรเปลี่ยนเป็น SQLite/JSON ในภายหลัง)
VOICE_CONFIG = {}       # { guild_id: voice_channel_id }
VERIFY_CONFIG = {}      # { guild_id: role_id }

def is_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator or (interaction.user.id == interaction.guild.owner_id)

# ==================================================
# 🔐 VERIFICATION UI COMPONENTS (ปุ่มกดยืนยันตัวตน)
# ==================================================
class VerifyView(discord.ui.View):
    def __init__():
        # timeout=None เพื่อให้ปุ่มใช้งานได้ถาวรแม้บอทรีสตาร์ท
        super().__init__(timeout=None)

    @discord.ui.button(
        label="ยืนยันตัวตน (Verify)", 
        style=discord.ButtonStyle.success, 
        emoji="✅", 
        custom_id="persistent_verify_button"
    )
    async def verify_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild_id
        role_id = VERIFY_CONFIG.get(guild_id)

        if not role_id:
            await interaction.response.send_message("❌ เซิร์ฟเวอร์นี้ยังไม่ได้ตั้งค่ายศสำหรับการยืนยันตัวตน", ephemeral=True)
            return

        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message("❌ ไม่พบบทบาท (Role) ที่ตั้งค่าไว้ในระบบ", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.response.send_message("⚠️ คุณผ่านการยืนยันตัวตนไปแล้ว!", ephemeral=True)
            return

        try:
            await interaction.user.add_roles(role)
            embed = discord.Embed(
                title="✅ ยืนยันตัวตนสำเร็จ",
                description=f"คุณได้รับยศ {role.mention} เรียบร้อยแล้ว ยินดีต้อนรับสู่เซิร์ฟเวอร์!",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ บอทไม่มีสิทธิ์แจกยศนี้ (กรุณาจัดตำแหน่งยศของบอทให้อยู่สูงกว่ายศที่จะแจก)", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)

# ==================================================
# 🤖 BOT EVENTS & PURPLE STATUS
# ==================================================
@bot.event
async def on_ready():
    # ลงทะเบียน View ถาวรเพื่อให้ปุ่มทำงานได้ตลอดแม้บอทรีสตาร์ท
    bot.add_view(VerifyView())

    try:
        synced = await bot.tree.sync()
        print(f"🔥 Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

    # สถานะออนไลน์สีม่วง (Streaming)
    stream_activity = discord.Streaming(
        name="ระบบยืนยันตัวตนออนไลน์ 24/7 💜", 
        url="https://www.twitch.tv/discord"
    )
    await bot.change_presence(activity=stream_activity)
    print(f"⚡ Bot online as [{bot.user}] with Purple Status")

    # Auto-join voice
    for guild in bot.guilds:
        channel_id = VOICE_CONFIG.get(guild.id)
        if channel_id:
            channel = guild.get_channel(channel_id)
            if isinstance(channel, discord.VoiceChannel):
                try:
                    await channel.connect(self_deaf=True, self_mute=True)
                except Exception as e:
                    print(f"❌ Auto-join failed: {e}")

@bot.event
async def on_voice_state_update(member, before, after):
    if member.id == bot.user.id and before.channel and not after.channel:
        guild = before.channel.guild
        target_channel_id = VOICE_CONFIG.get(guild.id)
        if target_channel_id:
            await asyncio.sleep(3)
            target_channel = guild.get_channel(target_channel_id)
            if target_channel and not guild.voice_client:
                try:
                    await target_channel.connect(self_deaf=True, self_mute=True)
                except Exception as e:
                    print(f"❌ Reconnect failed: {e}")

# ==================================================
# 🔐 VERIFICATION SYSTEM COMMANDS
# ==================================================
@bot.tree.command(name="setup_verify", description="[Admin] ส่งข้อความพร้อมปุ่มกดกดรับยศยืนยันตัวตน")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    channel="เลือกช่องที่ต้องการส่งข้อความยืนยันตัวตน",
    role="เลือกยศที่จะแจกเมื่อกดปุ่มยืนยัน"
)
async def setup_verify(interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role):
    if not is_admin(interaction):
        await interaction.response.send_message("⛔ สิทธิ์ไม่เพียงพอ", ephemeral=True)
        return

    # บันทึกยศลง Config
    VERIFY_CONFIG[interaction.guild_id] = role.id

    embed = discord.Embed(
        title="🔒 ยืนยันตัวตนเพื่อเข้าถึงเซิร์ฟเวอร์",
        description="กรุณากดปุ่ม **\"ยืนยันตัวตน (Verify)\"** ด้านล่างนี้เพื่อรับยศและเข้าถึงห้องพูดคุยทั้งหมด",
        color=discord.Color.purple()
    )
    embed.set_footer(text="ระบบยืนยันตัวตนอัตโนมัติ")

    try:
        await channel.send(embed=embed, view=VerifyView())
        await interaction.response.send_message(
            f"✅ ส่งระบบยืนยันตัวตนไปยังช่อง {channel.mention} เรียบร้อย! (แจกยศ: {role.mention})", 
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ ไม่สามารถส่งข้อความได้: {e}", ephemeral=True)

# ==================================================
# 🔊 VOICE SYSTEM COMMANDS
# ==================================================
@bot.tree.command(name="setup_voice", description="[Admin] ตั้งค่าห้องเสียงให้ออนค้างไว้ 24/7")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(channel="เลือกห้องเสียง")
async def setup_voice(interaction: discord.Interaction, channel: discord.VoiceChannel):
    if not is_admin(interaction):
        await interaction.response.send_message("⛔ สิทธิ์ไม่เพียงพอ", ephemeral=True)
        return

    VOICE_CONFIG[interaction.guild_id] = channel.id
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()

    try:
        await channel.connect(self_deaf=True, self_mute=True)
        embed = discord.Embed(title="⚙️ Voice Setup", description=f"✅ เชื่อมต่อห้อง {channel.mention} เรียบร้อย", color=discord.Color.purple())
    except Exception as e:
        embed = discord.Embed(title="❌ Error", description=f"ไม่สามารถเชื่อมต่อได้: {e}", color=discord.Color.red())
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="leave_voice", description="[Admin] สั่งให้บอทออกจากห้องเสียง")
@app_commands.default_permissions(administrator=True)
async def leave_voice(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message("⛔ สิทธิ์ไม่เพียงพอ", ephemeral=True)
        return

    vc = interaction.guild.voice_client
    if vc and vc.is_connected():
        await vc.disconnect()
        embed = discord.Embed(title="🔌 Disconnected", description="ออกจากห้องเสียงเรียบร้อย", color=discord.Color.purple())
    else:
        embed = discord.Embed(title="⚠️ Warning", description="บอทไม่ได้อยู่ในห้องเสียง", color=discord.Color.orange())
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="voice_status", description="[Admin] เช็กสถานะการเชื่อมต่อห้องเสียง")
@app_commands.default_permissions(administrator=True)
async def voice_status(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message("⛔ สิทธิ์ไม่เพียงพอ", ephemeral=True)
        return

    vc = interaction.guild.voice_client
    if vc and vc.is_connected():
        embed = discord.Embed(
            title="📊 Voice Status",
            description=f"เชื่อมต่ออยู่ที่: {vc.channel.mention}\n• Mute: `{vc.self_mute}` | Deaf: `{vc.self_deaf}`",
            color=discord.Color.purple()
        )
    else:
        embed = discord.Embed(title="📊 Voice Status", description="ไม่ได้เชื่อมต่อห้องเสียงใดๆ", color=discord.Color.red())

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================================================
# 🚀 START BOT
# ==================================================
if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ ERROR: DISCORD_TOKEN is missing!")
