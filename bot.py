import discord
from discord.ext import commands
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ===== 設定 =====
TARGET_VC_ID = 1493583935333077155
REQUEST_TEXT_CHANNEL_ID = 1495085549504037139

queue = []
muted_users = set()
active_request = None

# ===== 起動 =====
@bot.event
async def on_ready():
    synced = await tree.sync()
    print(f"同期したコマンド数: {len(synced)}")
    print("起動成功！")

# ===== 承認UI =====
class RequestView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="承認", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.get_channel(TARGET_VC_ID)

        # VC内の人しか押せない
        if interaction.user not in vc.members:
            await interaction.response.send_message("VC参加者のみ承認できます", ephemeral=True)
            return

        member = interaction.guild.get_member(self.user_id)

        if member:
            await member.move_to(vc)
            await member.edit(mute=True)
            muted_users.add(member.id)

        await interaction.response.edit_message(content=f"{member.name} を承認しました", view=None)
        await process_next(interaction.guild)

    @discord.ui.button(label="拒否", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="拒否しました", view=None)
        await process_next(interaction.guild)

# ===== キュー処理 =====
async def process_next(guild):
    global active_request

    if len(queue) == 0:
        active_request = None
        return

    user_id = queue.pop(0)
    active_request = user_id

    channel = bot.get_channel(REQUEST_TEXT_CHANNEL_ID)
    if channel is None:
        print("❌ チャンネルが見つからない")
        return

    member = guild.get_member(user_id)
    if member is None:
        print("❌ メンバーが見つからない")
        return

    view = RequestView(user_id)

    await channel.send(f"{member.mention} の参加申請", view=view)# ===== コマンド =====
print("join_request 読み込まれた")
@tree.command(name="join_request", description="VC参加申請")
async def join_request(interaction: discord.Interaction):
    global active_request

    vc = interaction.guild.get_channel(TARGET_VC_ID)

    if len(vc.members) < vc.user_limit:
        await interaction.response.send_message("空きがあります", ephemeral=True)
        return

    queue.append(interaction.user.id)
    await interaction.response.send_message("申請しました（順番待ち）", ephemeral=True)

    if active_request is None:
        await process_next(interaction.guild)

# ===== ミュート固定 =====
@bot.event
async def on_voice_state_update(member, before, after):
    if member.id in muted_users:
        # 管理者ならスルー
        if member.guild_permissions.administrator:
            return

        # ミュート解除されたら戻す
        if not member.voice.mute:
            await member.edit(mute=True)

import os

bot.run(os.getenv("DISCORD_TOKEN"))