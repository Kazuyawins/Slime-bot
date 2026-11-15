import discord
from discord import app_commands
import json
import os

SETTINGS_FILE = "twitter_settings.json"

def load_twitter_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_twitter_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ボットのツリーにコマンドを登録する関数（またはCogの仕組みを使用）
def setup_twitter_commands(bot):
    @bot.tree.command(name="settwitter", description="指定したXアカウントのポストをこのチャンネルに自動通知します")
    @app_commands.describe(username="通知を受け取りたいXのユーザー名")
    async def settwitter(interaction: discord.Interaction, username: str):
        settings = load_twitter_settings()
        guild_id = str(interaction.guild_id)
        
        settings[guild_id] = {
            "channel_id": interaction.channel_id,
            "username": username,
            "last_post_id": None # 重複防止用
        }
        save_twitter_settings(settings)
        
        await interaction.response.send_message(
            f"✅ X (@{username}) の新しいポストをこのチャンネルに自動送信するように設定しました！",
            ephemeral=True
        )