import os
import threading
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask

# ----------------- ส่วนของ Web Server (Flask) -----------------
app = Flask('')

@app.route('/')
def home():
    return "Voice Bot is running!"

# ----------------- ส่วนของ Discord Bot -----------------
intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True

class VoiceBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        # ซิงค์ Slash Commands กับ Discord
        await self.tree.sync()
        print("Slash commands synced.")

bot = VoiceBot()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('Bot is ready!')

# ----------------- สร้าง Slash Command แบบกดเลือกห้อง -----------------
@bot.tree.command(name="join", description="เลือกช่องเสียงเพื่อให้บอทเข้าไปสิง")
@app_commands.describe(channel="เลือกห้องเสียงที่ต้องการให้บอทเข้าไป")
async def join(interaction: discord.Interaction, channel: discord.VoiceChannel):
    # ตรวจสอบว่าบอทอยู่ในห้องเสียงอื่นอยู่แล้วหรือไม่
    voice_client = interaction.guild.voice_client

    try:
        if voice_client:
            await voice_client.move_to(channel)
        else:
            await channel.connect()
        
        await interaction.response.send_message(f'✅ บอทเข้ามาที่ห้องเสียง **{channel.name}** เรียบร้อยแล้ว!', ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f'❌ เกิดข้อผิดพลาด: {e}', ephemeral=True)

@bot.tree.command(name="leave", description="สั่งให้บอทออกจากห้องเสียง")
async def leave(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client:
        await voice_client.disconnect()
        await interaction.response.send_message('👋 บอทออกจากห้องเสียงแล้ว', ephemeral=False)
    else:
        await interaction.response.send_message('⚠️ บอทยังไม่ได้อยู่ในห้องเสียงไหนเลย', ephemeral=True)

# ฟังก์ชันรันบอท Discord แยก Thread
def run_bot():
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("Error: Please set DISCORD_TOKEN in environment variables.")

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
