import discord
from discord import app_commands
from discord.ext import tasks
import json
import os
import aiohttp
import xml.etree.ElementTree as ET

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
        
        # ボットの準備完了時 (on_ready) にタスクが安全に開始されるようにする
        @self.bot.event
        async def on_ready():
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
                "last_post_id": None
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
            last_post_id = data.get("last_post_id")
            
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                continue

            try:
                # 例として、NitterなどのパブリックRSSインスタンス等を利用して最新ポストを取得する場合
                # （※環境に応じて安定したRSS/APIエンドポイントに変更してください）
                rss_url = f"https://nitter.privacydev.net/{username}/rss"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(rss_url, timeout=10) as resp:
                        if resp.status != 200:
                            continue
                        text = await resp.text()

                # 簡単なXMLパースで最新の投稿（guidまたはlink）を取得
                root = ET.fromstring(text)
                item = root.find(".//item")
                if item is not None:
                    post_id = item.find("guid").text if item.find("guid") is not None else None
                    post_link = item.find("link").text if item.find("link") is not None else None
                    
                    if post_id and post_id != last_post_id:
                        # 新着ポストがある場合、Discordに送信
                        await channel.send(f"📢 **@{username}** の新しいポスト:\n{post_link}")
                        
                        # 最後に送信したIDを更新して保存
                        data["last_post_id"] = post_id
                        save_twitter_settings(settings)

            except Exception as e:
                print(f"Twitter fetch error for {username}: {e}")

    @check_twitter_loop.before_loop
    async def before_check_twitter_loop(self):
        await self.bot.wait_until_ready()