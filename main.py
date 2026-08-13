import os
import threading
from flask import Flask, request, render_template_string
import discord
from discord.ext import commands
import requests

# ตั้งค่าตัวแปร (แก้ไขรูปแบบ os.getenv ให้ถูกต้อง)
TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "1532644387639660627")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "6LajyZZ6DfRr42xIESMp_gRRxqXlK1R3")
GUILD_ID = int(os.getenv("GUILD_ID", "1522224772258332792"))
ROLE_ID = int(os.getenv("ROLE_ID", "1537445693625598122"))

intents = discord.Intents.default()
intents.guilds = True
intents.guild_members = True
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot logged in as {bot.user} and Slash Commands synced.")

@bot.tree.command(name="ping", description="เช็คความหน่วงของบอท")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! 🏓 {round(bot.latency * 1000)}ms")

app = Flask(__name__)

INDEX_HTML = """
<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <title>Verification</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-[#0a0a0c] text-white h-screen flex justify-center items-center">
  <div class="bg-[#121216] border border-white/10 p-8 rounded-3xl text-center max-w-md w-full">
    <h1 class="text-2xl font-black mb-4">ยืนยันตัวตนเพื่อรับยศ</h1>
    <a href="https://discord.com/api/oauth2/authorize?client_id={{ client_id }}&redirect_uri={{ redirect_uri }}&response_type=code&scope=identify+guilds.join" 
       class="block w-full py-4 bg-[#5865F2] hover:bg-[#4752C4] transition rounded-2xl font-bold text-white">
      ยืนยันตัวตนผ่าน Discord
    </a>
  </div>
</body>
</html>
"""

SUCCESS_HTML = """
<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <title>Success</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-[#0a0a0c] text-white h-screen flex justify-center items-center">
  <div class="bg-[#121216] border border-emerald-500/30 p-8 rounded-3xl text-center max-w-md w-full">
    <h1 class="text-2xl font-black mb-2 text-emerald-400">ยืนยันตัวตนสำเร็จ!</h1>
    <p class="text-gray-300 text-sm mb-4">ยินดีต้อนรับคุณ <b>{{ username }}</b></p>
    <a href="/" class="inline-block px-6 py-3 bg-white/10 hover:bg-white/20 rounded-xl text-sm font-bold">กลับหน้าแรก</a>
  </div>
</body>
</html>
"""

@app.route("/")
def home():
    redirect_uri = request.url_root.rstrip('/') + "/verify"
    return render_template_string(INDEX_HTML, client_id=CLIENT_ID, redirect_uri=redirect_uri)

@app.route("/verify")
def verify():
    code = request.args.get("code")
    if not code:
        return "ไม่พบ Code", 400

    redirect_uri = request.url_root.rstrip('/') + "/verify"
    token_res = requests.post("https://discord.com/api/oauth2/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    
    token_data = token_res.json()
    access_token = token_data.get("access_token")
    if not access_token:
        return "Token Error", 400

    user_res = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {access_token}"})
    user_data = user_res.json()
    user_id = int(user_data.get("id"))
    username = user_data.get("username")

    bot.loop.create_task(assign_role(user_id, access_token))
    return render_template_string(SUCCESS_HTML, username=username)

async def assign_role(user_id, access_token):
    await bot.wait_until_ready()
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        try:
            guild = await bot.fetch_guild(GUILD_ID)
        except:
            return

    requests.put(f"https://discord.com/api/guilds/{GUILD_ID}/members/{user_id}", json={"access_token": access_token}, headers={"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"})

    try:
        member = guild.get_member(user_id) or await guild.fetch_member(user_id)
        role = guild.get_role(ROLE_ID)
        if member and role:
            await member.add_roles(role)
    except Exception as e:
        print(f"Error: {e}")

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.run(TOKEN)
