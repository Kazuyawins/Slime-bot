import discord
from discord import app_commands
from discord.ext import tasks
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

class TwitterNotifier:
    def __init__(self, bot):
        self.bot = bot
        # タスクが開始していなければループをスタート
        if not self.check_twitter_loop.is_running():
            self.check_twitter_loop.start()

    def register_commands(self):
        @self.bot.tree.command(
            name="settwitter",
            description="指定したXアカウントのポストをこのチャンネルに自動通知します"
        )
        @app_commands.describe(username="通知を受け取りたいXのユーザー名（例: username）")
        async def settwitter(interaction: discord.Interaction, username: str):
            settings = load_twitter_settings()
            guild_id = str(interaction.guild_id)
            
            settings[guild_id] = {
                "channel_id": interaction.channel_id,
                "username": username,
                "last_post_id": None  # 重複送信防止用
            }
            save_twitter_settings(settings)
            
            await interaction.response.send_message(
                f"✅ X (@{username}) の新しいポストをこのチャンネルに自動送信するように設定しました！",
                ephemeral=True
            )

    @tasks.loop(minutes=5)
    async def check_twitter_loop(self):
        settings = load_twitter_settings()
        if not settings:
            return

        for guild_id, data in settings.items():
            channel_id = data.get("channel_id")
            username = data.get("username")
            
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                continue

            try:
                # TODO: ここでXの最新ポストを取得する処理を実装します
                # 例: latest_post = await fetch_latest_post(username)
                # if latest_post and latest_post['id'] != data.get('last_post_id'):
                #     await channel.send(f"📢 @{username} の新しいポスト:\n{latest_post['url']}")
                #     data['last_post_id'] = latest_post['id']
                #     save_twitter_settings(settings)
                pass
            except Exception as e:
                print(f"Twitter fetch error for {username}: {e}")

    @check_twitter_loop.before_loop
    async def before_check_twitter(self):
        await self.bot.wait_until_ready()