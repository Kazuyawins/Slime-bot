"""Administration features."""

import datetime
import io
import json
import discord
from discord import app_commands
from . import config
from .runtime import bot


@bot.tree.command(
    name="setchannel",
    description="日付お知らせを送信するチャンネルを現在のチャンネルに設定します",
)
@app_commands.default_permissions(manage_channels=True)
async def setchannel(interaction: discord.Interaction):
    config.NOTIFICATION_CHANNEL_ID = interaction.channel.id
    config.save_notification_channel_id(config.NOTIFICATION_CHANNEL_ID)
    await interaction.response.send_message(
        f"✅ このチャンネル（{interaction.channel.mention}）を日付お知らせの送信先として設定し、保存しました！",
        ephemeral=True,
    )


@bot.tree.command(
    name="setlog",
    description="【管理者用】各種ログ（メッセージ・チャンネル・スレッド・エラー）を送信するチャンネルを設定します",
)
@app_commands.default_permissions(manage_channels=True)
async def setlog(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if guild_id not in config.LOG_SETTINGS:
        config.LOG_SETTINGS[guild_id] = {
            "channel_id": interaction.channel.id,
            "enabled": True,
        }
    else:
        config.LOG_SETTINGS[guild_id]["channel_id"] = interaction.channel.id
    config.save_log_settings()
    await interaction.response.send_message(
        f"✅ このチャンネル（{interaction.channel.mention}）をこのサーバーのログ通知先として設定し、保存しました！",
        ephemeral=True,
    )


@bot.tree.command(
    name="logtoggle",
    description="【管理者用】このサーバーのログ通知機能のオン（有効）／オフ（無効）を切り替えます",
)
@app_commands.default_permissions(manage_channels=True)
async def logtoggle(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if guild_id not in config.LOG_SETTINGS:
        config.LOG_SETTINGS[guild_id] = {
            "channel_id": interaction.channel.id,
            "enabled": True,
        }
    else:
        config.LOG_SETTINGS[guild_id]["enabled"] = not config.LOG_SETTINGS[
            guild_id
        ].get("enabled", True)
    config.save_log_settings()
    current_status = config.LOG_SETTINGS[guild_id]["enabled"]
    status_str = "🟢 有効 (オン)" if current_status else "🔴 無効 (オフ)"
    await interaction.response.send_message(
        f"✅ ログ通知機能を切り替えました。\n現在の状態: **{status_str}**",
        ephemeral=True,
    )


@bot.tree.command(
    name="test",
    description="【管理者用】日付お知らせのテスト送信と認証パネルの動作テストを行います",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(role="認証テストで使用するロール（任意）")
async def test_command(interaction: discord.Interaction, role: discord.Role = None):
    now = datetime.datetime.now(config.JST)
    weekdays = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
    weekday_str = weekdays[now.weekday()]
    date_text = f"🧪 【テスト】日付お知らせ確認\n本日は {now.month}月{now.day}日 ({weekday_str}) です。"
    test_role = role if role else interaction.guild.default_role
    embed = discord.Embed(
        title="🧪 【テスト】サーバー認証パネル",
        description=f"これは認証システムのテストパネルです。\n対象ロール: {test_role.mention}\n\n下の 「認証を開始する」 ボタンを押して、画像認証が正常に動作するかテストしてください。",
        color=discord.Color.orange(),
    )
    view = CaptchaPanelView(test_role.id)
    await interaction.response.send_message(
        f"✅ テストメッセージを送信します。\n1️⃣ 日付お知らせのテスト:\n{date_text}\n\n2️⃣ 認証パネルのテスト:",
        embed=embed,
        view=view,
        ephemeral=True,
    )


@bot.tree.command(
    name="testchannel",
    description="【管理者用】指定したチャンネルに日付お知らせのテストメッセージを送信します",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(channel="テスト送信先のチャンネル")
async def testchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    now = datetime.datetime.now(config.JST)
    weekdays = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
    weekday_str = weekdays[now.weekday()]
    message_text = f"🧪 【テスト送信】日付が変わりました！\n本日は {now.month}月{now.day}日 ({weekday_str}) です。"
    try:
        await channel.send(message_text)
        await interaction.response.send_message(
            f"✅ {channel.mention} に日付お知らせのテストメッセージを送信しました！",
            ephemeral=True,
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ 送信に失敗しました（ボットに権限がない可能性があります）: {e}",
            ephemeral=True,
        )


@bot.tree.command(
    name="exportconfig",
    description="【管理者用】現在のすべての設定データをJSONファイルとしてエクスポートします",
)
@app_commands.default_permissions(administrator=True)
async def exportconfig(interaction: discord.Interaction):
    export_data = {
        "notification_channel_id": config.NOTIFICATION_CHANNEL_ID,
        "log_settings": {str(k): v for k, v in config.LOG_SETTINGS.items()},
        "custom_responses": {str(k): v for k, v in config.CUSTOM_RESPONSES.items()},
        "welcome_settings": {str(k): v for k, v in config.WELCOME_SETTINGS.items()},
        "leave_guild_id": config.LEAVE_GUILD_ID,
        "leave_channel_id": config.LEAVE_CHANNEL_ID,
        "spam_settings": {str(k): v for k, v in config.SPAM_SETTINGS.items()},
    }
    json_bytes = json.dumps(export_data, ensure_ascii=False, indent=2).encode("utf-8")
    file = discord.File(io.BytesIO(json_bytes), filename="bot_config_backup.json")
    await interaction.response.send_message(
        "📦 すべての設定データをエクスポートしました。バックアップとして保管してください：",
        file=file,
        ephemeral=True,
    )


@bot.tree.command(
    name="importconfig",
    description="【管理者用】エクスポートしたJSONファイルをアップロードして設定を復元します",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(file="エクスポートしたJSONファイル")
async def importconfig(interaction: discord.Interaction, file: discord.Attachment):
    if not file.filename.endswith(".json"):
        await interaction.response.send_message(
            "❌ 拡張子が `.json` のファイルをアップロードしてください。", ephemeral=True
        )
        return
    try:
        file_bytes = await file.read()
        data = json.loads(file_bytes.decode("utf-8"))
        config.NOTIFICATION_CHANNEL_ID = data.get("notification_channel_id")
        if config.NOTIFICATION_CHANNEL_ID:
            config.save_notification_channel_id(config.NOTIFICATION_CHANNEL_ID)
        raw_log = data.get("log_settings", {})
        config.LOG_SETTINGS = {int(k): v for k, v in raw_log.items()}
        config.save_log_settings()
        raw_responses = data.get("custom_responses", {})
        config.CUSTOM_RESPONSES = {int(k): v for k, v in raw_responses.items()}
        config.save_custom_responses()
        raw_welcome = data.get("welcome_settings", {})
        config.WELCOME_SETTINGS = {int(k): v for k, v in raw_welcome.items()}
        config.save_welcome_settings()
        config.LEAVE_GUILD_ID = data.get("leave_guild_id")
        config.LEAVE_CHANNEL_ID = data.get("leave_channel_id")
        config.save_leave_settings(config.LEAVE_GUILD_ID, config.LEAVE_CHANNEL_ID)
        raw_spam = data.get("spam_settings", {})
        config.SPAM_SETTINGS = {int(k): v for k, v in raw_spam.items()}
        config.save_spam_settings()
        await interaction.response.send_message(
            "✅ 設定データのインポートと復元が正常に完了しました！", ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ 設定の読み込みに失敗しました（ファイル形式が不正な可能性があります）: {e}",
            ephemeral=True,
        )


@bot.tree.command(
    name="setwelcome",
    description="【管理者用】このサーバーのウェルカムメッセージを設定します",
)
@app_commands.default_permissions(manage_channels=True)
@app_commands.describe(
    enabled="ウェルカムメッセージを有効にするか (True: オン, False: オフ)",
    use_embed="埋め込み（Embed）形式にするか (True: 埋め込み, False: 通常テキスト)",
    mention="メンバーをメンションするか (True: あり, False: なし)",
    title="埋め込みの場合のタイトル（通常テキスト時は無視されます）",
    text="送信する本文（例: {member.name}さん、{guild.name}へようこそ！）",
)
async def setwelcome(
    interaction: discord.Interaction,
    enabled: bool,
    use_embed: bool,
    mention: bool,
    text: str,
    title: str = "👋 ようこそ！",
):
    guild_id = interaction.guild.id
    config.WELCOME_SETTINGS[guild_id] = {
        "channel_id": interaction.channel.id,
        "enabled": enabled,
        "use_embed": use_embed,
        "mention": mention,
        "title": title,
        "text": text,
    }
    config.save_welcome_settings()
    status_str = "🟢 有効 (オン)" if enabled else "🔴 無効 (オフ)"
    type_str = "📦 埋め込み (Embed)" if use_embed else "💬 通常テキスト"
    mention_str = "あり" if mention else "なし"
    await interaction.response.send_message(
        f"✅ このサーバーのウェルカムメッセージ設定を保存しました！\n・**状態:** {status_str}\n・**形式:** {type_str}\n・**送信チャンネル:** {interaction.channel.mention}\n・**メンション:** {mention_str}\n・**タイトル:** {title}\n・**本文:** {text}",
        ephemeral=True,
    )


@bot.tree.command(
    name="setleave",
    description="【管理者用】メンバー退出時の滞在時間記録を送信するチャンネルを設定します",
)
@app_commands.default_permissions(manage_channels=True)
async def setleave(interaction: discord.Interaction):
    config.LEAVE_GUILD_ID = interaction.guild.id
    config.LEAVE_CHANNEL_ID = interaction.channel.id
    config.save_leave_settings(config.LEAVE_GUILD_ID, config.LEAVE_CHANNEL_ID)
    await interaction.response.send_message(
        f"✅ このチャンネル（{interaction.channel.mention}）を退出時間記録の送信先に設定し、保存しました！",
        ephemeral=True,
    )


@bot.tree.command(
    name="sendembed",
    description="【管理者用】指定した内容の埋め込み（Embed）メッセージを送信します",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    title="埋め込みのタイトル",
    description="本文（説明文）",
    url="リンクを持たせるURL（任意）",
    color="カラー (blue, green, red, gold など)",
)
async def sendembed(
    interaction: discord.Interaction,
    title: str,
    description: str,
    url: str = None,
    color: str = "blue",
):
    color_map = {
        "blue": discord.Color.blue(),
        "green": discord.Color.green(),
        "red": discord.Color.red(),
        "gold": discord.Color.gold(),
        "purple": discord.Color.purple(),
    }
    embed_color = color_map.get(color.lower(), discord.Color.blue())
    embed = discord.Embed(
        title=title, description=description, color=embed_color, url=url
    )
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message(
        "✅ 埋め込みメッセージを送信しました！", ephemeral=True
    )


@bot.tree.command(
    name="sendmessage",
    description="【管理者用】指定した通常のテキストメッセージをBotに送信させます",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(content="送信したいメッセージの内容")
async def sendmessage(interaction: discord.Interaction, content: str):
    await interaction.channel.send(content)
    await interaction.response.send_message(
        "✅ メッセージを送信しました！", ephemeral=True
    )
