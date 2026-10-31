"""Links features."""

import re
import discord


def transform_links(content: str) -> tuple[str, bool]:
    replaced = False
    if YOUTUBE_PATTERN.search(content):
        content = content.replace("youtube.com", "koutube.com").replace(
            "youtu.be", "koutube.com"
        )
        replaced = True
    if X_PATTERN.search(content):
        content = content.replace("twitter.com", "fxtwitter.com").replace(
            "x.com", "fxtwitter.com"
        )
        replaced = True
    if INSTAGRAM_PATTERN.search(content):
        content = content.replace("instagram.com", "oginstagram.com")
        replaced = True
    if TIKTOK_PATTERN.search(content):
        content = re.sub(
            "https?://(?:www\\.|vm\\.|vt\\.)?tiktok\\.com",
            "https://tnktok.com",
            content,
        )
        replaced = True
    if FACEBOOK_PATTERN.search(content):
        content = content.replace("facebook.com", "facebed.com")
        replaced = True
    if THREADS_PATTERN.search(content):
        content = content.replace("threads.net", "fixthreads.com")
        replaced = True
    if REDDIT_PATTERN.search(content):
        content = (
            content.replace("reddit.com", "fxreddit.seria.moe")
            .replace("redd.it", "fxreddit.seria.moe")
            .replace("reddit.seria.moe", "fxreddit.seria.moe")
        )
        replaced = True
    if PIXIV_PATTERN.search(content):
        content = content.replace("pixiv.net", "phixiv.net")
        replaced = True
    if BLUESKY_PATTERN.search(content):
        content = content.replace("bsky.app", "bskx.app").replace(
            "Bluesky.app", "bskx.app"
        )
        replaced = True
    if NICO_PATTERN.search(content):
        content = content.replace("nicovideo.jp", "nicovideo.gay").replace(
            "nicovideo.com", "nicovideo.gay"
        )
        replaced = True
    return (content, replaced)


from . import config
from .runtime import bot

YOUTUBE_PATTERN = re.compile(
    "https?://(?:www\\.)?(?:youtube\\.com/watch\\?v=([\\w-]+)|youtu\\.be/([\\w-]+))(\\S*)"
)
X_PATTERN = re.compile(
    "https?://(?:www\\.)?(?:twitter\\.com|x\\.com)/([a-zA-Z0-9_]+/status/\\d+)(\\S*)"
)
INSTAGRAM_PATTERN = re.compile(
    "https?://(?:www\\.)?instagram\\.com/(p|reel|tv|stories)/[\\w-]+(\\S*)"
)
TIKTOK_PATTERN = re.compile("https?://(?:www\\.|vm\\.|vt\\.)?tiktok\\.com/\\S+")
FACEBOOK_PATTERN = re.compile("https?://(?:www\\.)?(?:facebook\\.com|fb\\.watch)/\\S+")
THREADS_PATTERN = re.compile("https?://(?:www\\.)?threads\\.net/\\S+")
REDDIT_PATTERN = re.compile(
    "https?://(?:www\\.)?(?:reddit\\.com|redd\\.it|reddit\\.seria\\.moe)/\\S+"
)
PIXIV_PATTERN = re.compile("https?://(?:www\\.)?pixiv\\.net/\\S+")
BLUESKY_PATTERN = re.compile("https?://(?:www\\.)?(?:bsky\\.app|Bluesky\\.app)/\\S+")
NICO_PATTERN = re.compile("https?://(?:www\\.)?nicovideo\\.(?:jp|com)/\\S+")


class LinkControlView(discord.ui.View):

    def __init__(self, author_id: int, user_message_id: int, original_content: str):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.user_message_id = user_message_id
        self.original_content = original_content

    @discord.ui.button(
        label="更新する",
        style=discord.ButtonStyle.success,
        emoji="🔄",
        custom_id="update_converted_link_btn",
    )
    async def update_link_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        try:
            try:
                user_msg = await interaction.channel.fetch_message(self.user_message_id)
                current_text = user_msg.content
            except Exception:
                current_text = self.original_content
            new_content, _ = transform_links(current_text)
            updated_display_content = f"{new_content}\n\n-# 🔄 更新済み"
            await interaction.message.edit(content=updated_display_content, view=self)
            await interaction.response.send_message(
                "✅ リンクと埋め込み情報（プレビュー・高評価等）を更新しました！",
                ephemeral=True,
            )
        except discord.NotFound:
            await interaction.response.send_message(
                "❌ 元のメッセージが見つかりませんでした。", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ 更新に失敗しました: {e}", ephemeral=True
            )

    @discord.ui.button(
        label="Botのリンクを消す",
        style=discord.ButtonStyle.secondary,
        emoji="🧹",
        custom_id="delete_bot_msg_btn",
    )
    async def delete_bot_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ あなたが送信したリンクではないため操作できません。", ephemeral=True
            )
            return
        try:
            await interaction.message.delete()
        except discord.NotFound:
            pass
        except Exception as e:
            await interaction.response.send_message(
                f"❌ 削除に失敗しました: {e}", ephemeral=True
            )

    @discord.ui.button(
        label="元のリンクを消す",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
        custom_id="delete_user_msg_btn",
    )
    async def delete_user_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ あなたが送信したリンクではないため操作できません。", ephemeral=True
            )
            return
        try:
            user_msg = await interaction.channel.fetch_message(self.user_message_id)
            await user_msg.delete()
            await interaction.response.defer()
        except discord.NotFound:
            await interaction.response.send_message(
                "ℹ️ 元のメッセージはすでに削除されています。", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ ユーザーメッセージの削除に失敗しました: {e}", ephemeral=True
            )


async def handle_links(message: discord.Message):
    new_content, replaced = transform_links(message.content)
    if replaced:
        view = LinkControlView(message.author.id, message.id, message.content)
        await message.channel.send(new_content, view=view)
