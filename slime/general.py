"""General features."""

import discord
from discord import app_commands
from . import config
from .runtime import bot


def get_help_embed(lang="ja"):
    if lang == "en":
        embed = discord.Embed(
            title="🤖 Bot Command & Feature Guide",
            description="Here is a list of available commands and features for this bot.",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="🔗 Link Transformation",
            value="Automatically transforms social media links for optimal preview embeds in Discord:\n• **YouTube** → `koutube.com`\n• **X / Twitter** → `fxtwitter.com`\n• **Instagram** → `oginstagram.com`\n• **TikTok** → `tnktok.com`\n• **Facebook** → `facebed.com`\n• **Threads** → `fixthreads.com`\n• **Reddit** → `fxreddit.seria.moe`\n• **Pixiv** → `phixiv.net`\n• **Bluesky** → `bskx.app`\n• **Niconico** → `nicovideo.gay`",
            inline=False,
        )
        embed.add_field(
            name="⚙️ Admin Commands",
            value="• `/setchannel` - Set the current channel for daily date notifications.\n• `/setlog` - Set the logging channel for messages, channels, and threads.\n• `/logtoggle` - Toggle the logging feature ON/OFF.\n• `/spamsetting` - Configure anti-spam protection (custom timeout duration, kick, ban).\n• `/setwelcome` - Configure welcome messages (Text or Embed format).\n• `/setleave` - Set the channel for member leave duration logs.\n• `/addrole` - Create multi-role emoji button panels (up to 10 roles).\n• `/captcha_setup` - Set up image verification (CAPTCHA) panels.\n• `/addresponse` / `/delresponse` - Register or delete exact-match custom auto-replies.\n• `/exportconfig` / `/importconfig` - Backup or restore all bot settings (JSON).\n• `/sendmessage` / `/sendembed` - Make the bot send regular text or embed messages.",
            inline=False,
        )
        embed.set_footer(text="Use the buttons below to switch languages.")
    else:
        embed = discord.Embed(
            title="🤖 ボットのコマンド・機能一覧",
            description="このサーバーで使用できる主なコマンドと機能のガイドです。",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="🔗 SNSリンク自動変換",
            value="SNSのリンクを送信すると、埋め込みプレビューが見やすいURLへ自動変換されます：\n• **YouTube** → `koutube.com`\n• **X (Twitter)** → `fxtwitter.com`\n• **Instagram** → `oginstagram.com`\n• **TikTok** → `tnktok.com`\n• **Facebook** → `facebed.com`\n• **Threads** → `fixthreads.com`\n• **Reddit** → `fxreddit.seria.moe`\n• **Pixiv** → `phixiv.net`\n• **Bluesky** → `bskx.app`\n• **ニコニコ動画** → `nicovideo.gay`",
            inline=False,
        )
        embed.add_field(
            name="⚙️ 管理者用コマンド",
            value="• `/setchannel` - 日付が変わった際のお知らせチャンネルを設定\n• `/setlog` - 各種ログ（メッセージ・チャンネル・スレッド）の通知先を設定\n• `/logtoggle` - ログ通知機能の有効／無効を切り替え\n• `/spamsetting` - スパム対策（任意のタイムアウト時間・キック・BAN）を設定\n• `/setwelcome` - ウェルカムメッセージを設定（テキスト・埋め込み対応）\n• `/setleave` - メンバー退出時の滞在時間記録チャンネルを設定\n• `/addrole` - 最大10個の絵文字ロール取得パネルを作成\n• `/captcha_setup` - 画像認証（CAPTCHA）パネルを設置\n• `/addresponse` / `/delresponse` - 完全一致のカスタム返信を登録・削除\n• `/exportconfig` / `/importconfig` - 設定データのバックアップ・復元（JSON）\n• `/sendmessage` / `/sendembed` - Botにテキストや埋め込みを送信させる",
            inline=False,
        )
        embed.set_footer(text="下のボタンで表示言語を切り替えることができます。")
    return embed


class HelpLangButtonView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="日本語 (Japanese)",
        style=discord.ButtonStyle.primary,
        emoji="🇯🇵",
        custom_id="help_lang_ja",
    )
    async def lang_ja(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        embed = get_help_embed("ja")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="English",
        style=discord.ButtonStyle.secondary,
        emoji="🇬🇧",
        custom_id="help_lang_en",
    )
    async def lang_en(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        embed = get_help_embed("en")
        await interaction.response.edit_message(embed=embed, view=self)


@bot.tree.command(name="help", description="ボットのコマンドや機能の一覧を表示します")
async def help_command(interaction: discord.Interaction):
    embed = get_help_embed("ja")
    view = HelpLangButtonView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@bot.tree.command(
    name="history",
    description="このサーバーに登録されている完全一致メッセージの一覧を表示します",
)
@app_commands.default_permissions(manage_messages=True)
async def history(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    responses = config.CUSTOM_RESPONSES.get(guild_id, {})
    if not responses:
        await interaction.response.send_message(
            "ℹ️ このサーバーに登録されている完全一致メッセージはありません。",
            ephemeral=True,
        )
        return
    embed = discord.Embed(
        title="📜 登録された完全一致メッセージ一覧", color=discord.Color.blue()
    )
    for keyword, res in responses.items():
        display_res = res if len(res) <= 100 else res[:97] + "..."
        embed.add_field(
            name=f"🔑 キーワード: {keyword}", value=f"返信: {display_res}", inline=False
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="ping", description="Botの応答速度（レイテンシ）を確認します")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(
        f"🏓 ポン！ 応答速度: {latency}ms", ephemeral=True
    )


@bot.tree.command(
    name="avatar", description="指定したユーザー（または自分）のアバターを表示します"
)
@app_commands.describe(user="アバターを確認したいユーザー（省略時は自分）")
async def avatar(interaction: discord.Interaction, user: discord.User = None):
    target_user = user if user else interaction.user
    avatar_url = target_user.display_avatar.url
    embed = discord.Embed(
        title=f"🖼️ {target_user.display_name} のアバター", color=discord.Color.blue()
    )
    embed.set_image(url=avatar_url)
    embed.set_footer(text=f"Requested by {interaction.user.display_name}")
    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(
            label="ブラウザで開く", style=discord.ButtonStyle.link, url=avatar_url
        )
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
