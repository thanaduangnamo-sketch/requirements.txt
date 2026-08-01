import discord
from discord import app_commands
from discord.ext import commands
import os

token = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (Custom Image Verify Mode)")
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    streaming_activity = discord.Streaming(
        name="ระบบยืนยันตัวตนสไตล์เท่ๆ พร้อมใช้งานครับ",
        url="https://www.twitch.tv/discord"
    )
    await bot.change_presence(status=discord.Status.online, activity=streaming_activity)
    print("✅ บอทออนไลน์ในสถานะสตรีมมิ่ง (เม็ดม่วง) เรียบร้อยแล้วครับ")


class VerifyView(discord.ui.View):
    def __init__(self, role_id: int):
        super().__init__(timeout=None)
        self.role_id = role_id

    @discord.ui.button(
        label="ยืนยันตัวตน",
        style=discord.ButtonStyle.success,
        emoji="🍀"
    )
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(self.role_id)

        if not role:
            return await interaction.response.send_message(
                "❌ ไม่พบยศนี้ในเซิร์ฟเวอร์",
                ephemeral=True
            )

        if role in interaction.user.roles:
            return await interaction.response.send_message(
                "❌ คุณได้ทำการยืนยันตัวตนไปแล้ว",
                ephemeral=True
            )

        await interaction.user.add_roles(role)
        await interaction.response.send_message(
            f"✅ รับยศ {role.mention} เรียบร้อยแล้ว",
            ephemeral=True
        )


@bot.tree.command(name="ยืนยันตัวตน", description="สร้างระบบยืนยันตัวตนพร้อมปรับแต่งรูปภาพและข้อความได้")
@app_commands.describe(
    role="เลือกยศที่ต้องการให้ผู้ใช้งานได้รับ",
    image="อัปโหลดรูปภาพที่ต้องการใส่ใน Embed (ไม่บังคับ)",
    image_url="หรือใส่ลิงก์รูปภาพ (URL) แทนการอัปโหลด (ไม่บังคับ)"
)
async def verify_command(
    interaction: discord.Interaction, 
    role: discord.Role, 
    image: discord.Attachment = None,
    image_url: str = None
):
    embed = discord.Embed(
        title="🧸 ระบบยืนยันตัวตน",
        description=(
            "```ansi\n"
            "\u001b[32m┌─────────────────────────────┐\n"
            "  ✨ Welcome to our Server ✨\n"
            "└─────────────────────────────┘\n"
            "\u001b[0m```\n"
            "☘️ เพื่อรับสิทธิ์ในการใช้งานและพูดคุย\n"
            "🍀 กรุณากกดปุ่มด้านล่างเพื่อ **ยืนยันตัวตน**\n\n"
            f"» ยศที่คุณจะได้รับคือ: {role.mention}\n\n"
            "```ansi\n"
            "\u001b[32m┌─────────── •°·.•°- ───────────┐\n"
            "  🍀 กดเลย แล้วเจอกันข้างใน! 🦋\n"
            "└─────────── •°·.•°- ───────────┘\n"
            "\u001b[0m"
        ),
        color=0x2b2d31
    )

    # จัดการเรื่องรูปภาพ (เลือกจากไฟล์ที่อัปโหลด หรือลิงก์ที่พิมพ์มา)
    target_image = None
    if image:
        target_image = image.url
    elif image_url:
        target_image = image_url

    if target_image:
        embed.set_image(url=target_image)

    await interaction.channel.send(
        embed=embed,
        view=VerifyView(role.id)
    )

    await interaction.response.send_message(
        "✅ สร้างหน้าต่างยืนยันตัวตนเรียบร้อยครับ",
        ephemeral=True
    )

bot.run(token)
