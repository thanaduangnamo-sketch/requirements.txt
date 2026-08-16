import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from aiohttp import web

load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # สำคัญ: ต้องเปิด Server Members Intent ใน Discord Developer Portal ด้วย
bot = commands.Bot(command_prefix="!", intents=intents)

# ----------------- Dummy Server สำหรับ Render -----------------
async def handle_dummy(request):
    return web.Response(text="Bot is running!")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get("/", handle_dummy)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# ----------------- ข้อมูลภูมิภาคและจังหวัด -----------------
PROVINCES_DATA = {
    "central": {
        "name": "ภาคกลาง",
        "items": ["กรุงเทพมหานคร", "นนทบุรี", "ปทุมธานี", "สมุทรปราการ", "พระนครศรีอยุธยา", "นครปฐม", "สมุทรสาคร"]
    },
    "north": {
        "name": "ภาคเหนือ",
        "items": ["เชียงใหม่", "เชียงราย", "ลำปาง", "ลำพูน", "แม่ฮ่องสอน", "น่าน", "แพร่", "พิษณุโลก"]
    },
    "ne": {
        "name": "ภาคตะวันออกเฉียงเหนือ",
        "items": ["นครราชสีมา", "ขอนแก่น", "อุดรธานี", "อุบลราชธานี", "บุรีรัมย์", "ร้อยเอ็ด", "ศรีสะเกษ"]
    },
    "east": {
        "name": "ภาคตะวันออก",
        "items": ["ชลบุรี", "ระยอง", "จันทบุรี", "ตราด", "ฉะเชิงเทรา", "ปราจีนบุรี", "สระแก้ว"]
    },
    "west": {
        "name": "ภาคตะวันตก",
        "items": ["กาญจนบุรี", "ตาก", "เพชรบุรี", "ประจวบคีรีขันธ์", "ราชบุรี"]
    },
    "south": {
        "name": "ภาคใต้",
        "items": ["ภูเก็ต", "สุราษฎร์ธานี", "สงขลา", "กระบี่", "นครศรีธรรมราช", "พังงา", "ตรัง", "หาดใหญ่/อื่น ๆ"]
    }
}

# ----------------- Helper Function: มอบหรือสร้างยศอัตโนมัติ -----------------
async def assign_or_create_role(guild: discord.Guild, member: discord.Member, role_name: str):
    # ค้นหายศในเซิร์ฟเวอร์
    role = discord.utils.get(guild.roles, name=role_name)
    created_new = False

    # ถ้ายังไม่มี ให้สร้างยศขึ้นใหม่
    if not role:
        try:
            role = await guild.create_role(
                name=role_name,
                color=discord.Color.blue(),
                reason="สร้างยศอัตโนมัติจากระบบเลือกจังหวัด"
            )
            created_new = True
        except discord.Forbidden:
            return False, "❌ บอทไม่มีสิทธิ์สร้างยศ (กรุณาเช็ก Bot Permissions)", False

    # มอบยศให้สมาชิก
    try:
        await member.add_roles(role)
        return True, f"✅ รับยศ **{role.name}** เรียบร้อยแล้ว!", created_new
    except discord.Forbidden:
        return False, "❌ บอทไม่มีสิทธิ์มอบยศนี้ (ลำดับ Role ของบอทต้องอยู่สูงกว่ายศที่แจก)", False

# ----------------- UI Component: เมนูเลือกจังหวัด -----------------
class ProvinceSelect(discord.ui.Select):
    def __init__(self, region_key: str):
        region_info = PROVINCES_DATA.get(region_key, {})
        provinces = region_info.get("items", [])
        
        options = [
            discord.SelectOption(label=prov, value=prov, emoji="📍")
            for prov in provinces
        ]
        
        super().__init__(
            placeholder=f"📍 เลือกจังหวัดใน {region_info.get('name')}",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"province_select_{region_key}"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        selected_province = self.values[0]
        
        success, message, created_new = await assign_or_create_role(
            interaction.guild, 
            interaction.user, 
            selected_province
        )
        
        if success and created_new:
            message += " *(สร้างยศใหม่ในเซิร์ฟเวอร์ให้อัตโนมัติ)*"
            
        await interaction.followup.send(message, ephemeral=True)

class ProvinceView(discord.ui.View):
    def __init__(self, region_key: str):
        super().__init__(timeout=180)
        self.add_item(ProvinceSelect(region_key))

# ----------------- UI Component: เมนูเลือกภูมิภาค (หลัก) -----------------
class RegionSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="ภาคกลาง", value="central", emoji="🏢", description="กรุงเทพฯ, นนทบุรี, ปทุมธานี ฯลฯ"),
            discord.SelectOption(label="ภาคเหนือ", value="north", emoji="⛰️", description="เชียงใหม่, เชียงราย, ลำปาง ฯลฯ"),
            discord.SelectOption(label="ภาคตะวันออกเฉียงเหนือ", value="ne", emoji="🌾", description="โคราช, ขอนแก่น, อุดรธานี ฯลฯ"),
            discord.SelectOption(label="ภาคตะวันออก", value="east", emoji="🏖️", description="ชลบุรี, ระยอง, จันทบุรี ฯลฯ"),
            discord.SelectOption(label="ภาคตะวันตก", value="west", emoji="🏞️", description="กาญจนบุรี, ตาก, เพชรบุรี ฯลฯ"),
            discord.SelectOption(label="ภาคใต้", value="south", emoji="🌊", description="ภูเก็ต, สุราษฎร์ฯ, สงขลา ฯลฯ"),
        ]
        super().__init__(
            placeholder="🔻 เลือกภูมิภาคของคุณ",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="region_select_main"
        )

    async def callback(self, interaction: discord.Interaction):
        region_key = self.values[0]
        region_name = PROVINCES_DATA[region_key]["name"]
        
        # ส่งเมนูเลือกจังหวัดของภูมิภาคนั้นๆ
        view = ProvinceView(region_key)
        await interaction.response.send_message(
            f"📍 คุณเลือก **{region_name}** กรุณาเลือกจังหวัดของคุณจากเมนูด้านล่าง:",
            view=view,
            ephemeral=True
        )

class RegionPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RegionSelect())

# ----------------- Embed แสดงผลหน้าแรก -----------------
def create_region_embed():
    embed = discord.Embed(
        title="🇹🇭 เลือกจังหวัดของคุณ | Thailand Provinces",
        description=(
            "👋 **ยินดีต้อนรับสมาชิกทุกท่าน!**\n"
            "เลือกจังหวัดที่คุณอาศัยอยู่ เพื่อรับยศและตามหาเพื่อนในพื้นที่เดียวกัน\n\n"
            "🔰 **วิธีการใช้งาน:**\n"
            "1️⃣ คลิกที่เมนู \"🔻 เลือกภูมิภาคของคุณ\" ด้านล่าง\n"
            "2️⃣ เลือก \"จังหวัด\" ที่คุณต้องการ\n"
            "3️⃣ บอทจะมอบยศให้อัตโนมัติทันที!\n\n"
            "✨ *ง่าย สะดวก และรวดเร็ว*"
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text="✅ ระบบยศอัตโนมัติ • กดเลือกด้านล่างได้เลยครับ")
    return embed

# ----------------- Events & Commands -----------------
@bot.event
async def on_ready():
    print(f"Bot Online: {bot.user.name}")
    await start_dummy_server()
    bot.add_view(RegionPanelView())
    try:
        await bot.tree.sync()
        print("✅ Sync Commands เรียบร้อย")
    except Exception as e:
        print(f"Sync error: {e}")

# คำสั่งส่งแผงเลือกภูมิภาค (เฉพาะ Admin)
@bot.command(name="setup_region")
@commands.has_permissions(administrator=True)
async def cmd_setup_region(ctx):
    await ctx.send(embed=create_region_embed(), view=RegionPanelView())

@bot.tree.command(name="setup_region", description="ส่งแผงรับยศเลือกจังหวัด/ภูมิภาค")
@app_commands.checks.has_permissions(administrator=True)
async def setup_region(interaction: discord.Interaction):
    await interaction.channel.send(embed=create_region_embed(), view=RegionPanelView())
    await interaction.response.send_message("✅ ส่งแผงเลือกภูมิภาคเรียบร้อยแล้ว!", ephemeral=True)

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
