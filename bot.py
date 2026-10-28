import asyncio
import datetime
import io
import json
import os
import random
import re
import string
from collections import defaultdict, deque
from aiohttp import web
import discord
from discord import app_commands
from discord.ext import commands, tasks
from PIL import Image, ImageDraw, ImageFont
from zoneinfo import ZoneInfo

# Intentsの設定
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- 設定の永続化ファイル管理 ---
CONFIG_FILE = "channel_config.txt"
LOG_CONFIG_FILE = "log_channel_config.txt"
RESPONSES_FILE = "custom_responses.txt"
WELCOME_FILE = "welcome_settings.txt"
LEAVE_CONFIG_FILE = "leave_config.txt"
SPAM_CONFIG_FILE = "spam_settings.txt"

def load_notification_channel_id():
  if os.path.exists(CONFIG_FILE):
    try:
      with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if content.isdigit():
          return int(content)
    except Exception as e:
      print(f"チャンネル設定の読み込みに失敗しました: {e}")

  env_channel = os.getenv("CHANNEL_ID")
  if env_channel and env_channel.isdigit():
    return int(env_channel)

  return None

def save_notification_channel_id(channel_id):
  try:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
      f.write(str(channel_id))
  except Exception as e:
    print(f"チャンネル設定の保存に失敗しました: {e}")

NOTIFICATION_CHANNEL_ID = load_notification_channel_id()

# --- ログ通知チャンネル & オン・オフ設定の永続化管理（サーバーごと） ---
def load_log_settings():
  if os.path.exists(LOG_CONFIG_FILE):
    try:
      with open(LOG_CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, dict) and "guilds" in data:
          return {int(k): {"channel_id": v["channel_id"], "enabled": v.get("enabled", True)} for k, v in data["guilds"].items()}
    except Exception as e:
      print(f"ログ設定の読み込みに失敗しました: {e}")
  return {}

def save_log_settings():
  try:
    with open(LOG_CONFIG_FILE, "w", encoding="utf-8") as f:
      json.dump({"guilds": {str(k): v for k, v in LOG_SETTINGS.items()}}, f, ensure_ascii=False, indent=2)
  except Exception as e:
    print(f"ログ設定の保存に失敗しました: {e}")

LOG_SETTINGS = load_log_settings()

# --- カスタム返信（完全一致）の永続化管理 ---
def load_custom_responses():
  if os.path.exists(RESPONSES_FILE):
    try:
      with open(RESPONSES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return {int(k): v for k, v in data.items()}
    except Exception as e:
      print(f"カスタム返信の読み込みに失敗しました: {e}")
  return {}

def save_custom_responses():
  try:
    with open(RESPONSES_FILE, "w", encoding="utf-8") as f:
      json.dump(CUSTOM_RESPONSES, f, ensure_ascii=False, indent=2)
  except Exception as e:
    print(f"カスタム返信の保存に失敗しました: {e}")

CUSTOM_RESPONSES = load_custom_responses()

# --- ウェルカムメッセージ設定の永続化管理 ---
def load_welcome_settings():
  if os.path.exists(WELCOME_FILE):
    try:
      with open(WELCOME_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return {int(k): v for k, v in data.items()}
    except Exception as e:
      print(f"ウェルカム設定の読み込みに失敗しました: {e}")
  return {}

def save_welcome_settings():
  try:
    with open(WELCOME_FILE, "w", encoding="utf-8") as f:
      json.dump(WELCOME_SETTINGS, f, ensure_ascii=False, indent=2)
  except Exception as e:
    print(f"ウェルカム設定の保存に失敗しました: {e}")

WELCOME_SETTINGS = load_welcome_settings()

# --- 退出通知設定の永続化管理 ---
def load_leave_settings():
  if os.path.exists(LEAVE_CONFIG_FILE):
    try:
      with open(LEAVE_CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("guild_id"), data.get("channel_id")
    except Exception as e:
      print(f"退出通知設定の読み込みに失敗しました: {e}")
  return None, None

def save_leave_settings(guild_id, channel_id):
  try:
    with open(LEAVE_CONFIG_FILE, "w", encoding="utf-8") as f:
      json.dump({"guild_id": guild_id, "channel_id": channel_id}, f, ensure_ascii=False, indent=2)
  except Exception as e:
    print(f"退出通知設定の保存に失敗しました: {e}")

LEAVE_GUILD_ID, LEAVE_CHANNEL_ID = load_leave_settings()

# --- スパム設定の永続化管理 ---
def load_spam_settings():
  if os.path.exists(SPAM_CONFIG_FILE):
    try:
      with open(SPAM_CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return {int(k): v for k, v in data.items()}
    except Exception as e:
      print(f"スパム設定の読み込みに失敗しました: {e}")
  return {}

def save_spam_settings():
  try:
    with open(SPAM_CONFIG_FILE, "w", encoding="utf-8") as f:
      json.dump({str(k): v for k, v in SPAM_SETTINGS.items()}, f, ensure_ascii=False, indent=2)
  except Exception as e:
    print(f"スパム設定の保存に失敗しました: {e}")

SPAM_SETTINGS = load_spam_settings()

# ユーザーごとのメッセージ送信履歴保持用 (guild_id -> {user_id: deque([timestamp, ...])})
user_message_history = defaultdict(lambda: defaultdict(deque))

JST = ZoneInfo("Asia/Tokyo")

YOUTUBE_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com/watch\?v=([\w-]+)|youtu\.be/([\w-]+))(\S*)"
)
X_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+/status/\d+)(\S*)"
)
INSTAGRAM_PATTERN = re.compile(
    r"https?://(?:www\.)?instagram\.com/(p|reel|tv|stories)/[\w-]+(\S*)"
)
TIKTOK_PATTERN = re.compile(r"https?://(?:www\.|vm\.|vt\.)?tiktok\.com/\S+")
FACEBOOK_PATTERN = re.compile(r"https?://(?:www\.)?(?:facebook\.com|fb\.watch)/\S+")
THREADS_PATTERN = re.compile(r"https?://(?:www\.)?threads\.net/\S+")


async def handle_ping(request):
  return web.Response(text="Bot is running!")


async def start_web_server():
  app = web.Application()
  app.add_routes([web.get("/", handle_ping)])
  runner = web.AppRunner(app)
  await runner.setup()
  port = int(os.getenv("PORT", 10000))
  site = web.TCPSite(runner, "0.0.0.0", port)
  await site.start()
  print(f"Webサーバーをポート {port} で起動しました（UptimeRobot用）")


daily_time = datetime.time(hour=0, minute=0, second=0, tzinfo=JST)


@tasks.loop(time=daily_time)
async def send_date_announcement():
  global NOTIFICATION_CHANNEL_ID
  if NOTIFICATION_CHANNEL_ID is None:
    return
  channel = bot.get_channel(NOTIFICATION_CHANNEL_ID)
  if channel is None:
    try:
      channel = await bot.fetch_channel(NOTIFICATION_CHANNEL_ID)
    except Exception as e:
      print(f"チャンネルの取得に失敗しました: {e}")
      return
  now = datetime.datetime.now(JST)
  weekdays = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
  weekday_str = weekdays[now.weekday()]
  message_text = f"📅 日付が変わりました！\n本日は {now.month}月{now.day}日 ({weekday_str}) です。"
  await channel.send(message_text)


@send_date_announcement.before_loop
async def before_send_date_announcement():
  await bot.wait_until_ready()


# --- 日英対応ヘルプ機能 ---
def get_help_embed(lang="ja"):
  if lang == "en":
    embed = discord.Embed(
        title="🤖 Bot Command & Feature Guide",
        description="Here is a list of available commands and features for this bot.",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="🔗 Link Transformation",
        value="Automatically converts social media links (YouTube, X/Twitter, Instagram, TikTok, Facebook, Threads) for better preview. Includes a control panel to delete links (only for the message author).",
        inline=False
    )
    embed.add_field(
        name="⚙️ Admin Commands",
        value=(
            "• `/setchannel` - Set daily date notification channel.\n"
            "• `/setlog` - Set logging channel (messages, channels, threads).\n"
            "• `/logtoggle` - Enable/disable logging feature.\n"
            "• `/spamsetting` - Configure anti-spam (timeout, kick, ban).\n"
            "• `/setwelcome` - Configure welcome messages (Text or Embed).\n"
            "• `/setleave` - Configure member leave duration tracking channel.\n"
            "• `/addrole` - Create multi-role emoji button panels (up to 10).\n"
            "• `/captcha_setup` - Create image verification (CAPTCHA) panels.\n"
            "• `/addresponse` / `/delresponse` - Manage exact-match custom auto-replies.\n"
            "• `/exportconfig` / `/importconfig` - Backup or restore bot settings (JSON).\n"
            "• `/sendmessage` / `/sendembed` - Send custom bot messages."
        ),
        inline=False
    )
    embed.add_field(
        name="🛠️ General Commands",
        value=(
            "• `/help` - Show this help guide.\n"
            "• `/ping` - Check bot latency.\n"
            "• `/avatar` - Display user avatar.\n"
            "• `/history` - View registered custom responses."
        ),
        inline=False
    )
    embed.set_footer(text="Use the buttons below to switch languages.")
  else:
    embed = discord.Embed(
        title="🤖 ボットのコマンド・機能一覧",
        description="このサーバーで使用できる主なコマンドと機能のガイドです。",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="🔗 SNSリンク自動変換",
        value="YouTube、X（Twitter）、Instagram、TikTok、Facebook、Threadsのリンクを送信すると、見やすいビューに自動変換します。送信者本人のみ操作できる削除パネル付きです。",
        inline=False
    )
    embed.add_field(
        name="⚙️ 管理者用コマンド",
        value=(
            "• `/setchannel` - 日付が変わった際のお知らせチャンネルを設定\n"
            "• `/setlog` - 各種ログ（メッセージ・チャンネル・スレッド）の通知先を設定\n"
            "• `/logtoggle` - ログ通知機能の有効／無効を切り替え\n"
            "• `/spamsetting` - スパム対策（自動タイムアウト・キック・BAN）を設定\n"
            "• `/setwelcome` - ウェルカムメッセージを設定（テキスト・埋め込み対応）\n"
            "• `/setleave` - メンバー退出時の滞在時間記録チャンネルを設定\n"
            "• `/addrole` - 最大10個の絵文字ロール取得パネルを作成\n"
            "• `/captcha_setup` - 画像認証（CAPTCHA）パネルを設置\n"
            "• `/addresponse` / `/delresponse` - 完全一致のカスタム返信を登録・削除\n"
            "• `/exportconfig` / `/importconfig` - 設定データのバックアップ・復元（JSON）\n"
            "• `/sendmessage` / `/sendembed` - Botにテキストや埋め込みを送信させる"
        ),
        inline=False
    )
    embed.add_field(
        name="🛠️ 一般コマンド",
        value=(
            "• `/help` - このヘルプガイドを表示\n"
            "• `/ping` - Botの応答速度を確認\n"
            "• `/avatar` - 指定したユーザーのアバターを表示\n"
            "• `/history` - 登録されているカスタム返信一覧を表示"
        ),
        inline=False
    )
    embed.set_footer(text="下のボタンで表示言語を切り替えることができます。")
  return embed

class HelpLangButtonView(discord.ui.View):
  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(label="日本語 (Japanese)", style=discord.ButtonStyle.primary, emoji="🇯🇵", custom_id="help_lang_ja")
  async def lang_ja(self, interaction: discord.Interaction, button: discord.ui.Button):
    embed = get_help_embed("ja")
    await interaction.response.edit_message(embed=embed, view=self)

  @discord.ui.button(label="English", style=discord.ButtonStyle.secondary, emoji="🇬🇧", custom_id="help_lang_en")
  async def lang_en(self, interaction: discord.Interaction, button: discord.ui.Button):
    embed = get_help_embed("en")
    await interaction.response.edit_message(embed=embed, view=self)


@bot.tree.command(name="help", description="ボットのコマンドや機能の一覧を表示します / Show bot command guide")
async def help_command(interaction: discord.Interaction):
  embed = get_help_embed("ja")
  view = HelpLangButtonView()
  await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@bot.tree.command(
    name="setchannel",
    description="日付お知らせを送信するチャンネルを現在のチャンネルに設定します",
)
@app_commands.default_permissions(manage_channels=True)
async def setchannel(interaction: discord.Interaction):
  global NOTIFICATION_CHANNEL_ID
  NOTIFICATION_CHANNEL_ID = interaction.channel.id
  save_notification_channel_id(NOTIFICATION_CHANNEL_ID)

  await interaction.response.send_message(
      f"✅ このチャンネル（{interaction.channel.mention}）を日付お知らせの送信先として設定し、保存しました！",
      ephemeral=True,
  )


@bot.tree.command(
    name="setlog",
    description="【管理者用】各種ログ（メッセージ・チャンネル・スレッド）を送信するチャンネルを設定します",
)
@app_commands.default_permissions(manage_channels=True)
async def setlog(interaction: discord.Interaction):
  guild_id = interaction.guild.id
  if guild_id not in LOG_SETTINGS:
    LOG_SETTINGS[guild_id] = {"channel_id": interaction.channel.id, "enabled": True}
  else:
    LOG_SETTINGS[guild_id]["channel_id"] = interaction.channel.id
  save_log_settings()

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
  if guild_id not in LOG_SETTINGS:
    LOG_SETTINGS[guild_id] = {"channel_id": interaction.channel.id, "enabled": True}
  else:
    LOG_SETTINGS[guild_id]["enabled"] = not LOG_SETTINGS[guild_id].get("enabled", True)
  save_log_settings()

  current_status = LOG_SETTINGS[guild_id]["enabled"]
  status_str = "🟢 有効 (オン)" if current_status else "🔴 無効 (オフ)"
  await interaction.response.send_message(
      f"✅ ログ通知機能を切り替えました。\n現在の状態: **{status_str}**",
      ephemeral=True,
  )


# --- スパム設定コマンド ---
@bot.tree.command(
    name="spamsetting",
    description="【管理者用】スパム対策（自動タイムアウト・キック・BAN）を設定します",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    enabled="スパム対策を有効にするか (True: オン, False: オフ)",
    seconds="何秒間の間に制限するか（例: 5）",
    count="何件メッセージを送ったら制限するか（例: 5）",
    action="処分方法 (timeout: タイムアウト, kick: キック, ban: BAN)",
    timeout_duration="タイムアウトさせる秒数（actionがtimeoutの時のみ有効、例: 300）",
    warn_message="検知時にユーザーへ送信する警告メッセージ（任意）",
)
@app_commands.choices(
    action=[
        app_commands.Choice(name="タイムアウト (timeout)", value="timeout"),
        app_commands.Choice(name="キック (kick)", value="kick"),
        app_commands.Choice(name="BAN (ban)", value="ban"),
    ]
)
async def spamsetting(
    interaction: discord.Interaction,
    enabled: bool,
    seconds: int,
    count: int,
    action: str,
    timeout_duration: int = 300,
    warn_message: str = "スパム行為が検知されたため制限されました。",
):
  guild_id = interaction.guild.id
  SPAM_SETTINGS[guild_id] = {
      "enabled": enabled,
      "seconds": seconds,
      "count": count,
      "action": action,
      "timeout_duration": timeout_duration,
      "warn_message": warn_message,
  }
  save_spam_settings()

  status_str = "🟢 有効 (オン)" if enabled else "🔴 無効 (オフ)"
  await interaction.response.send_message(
      f"✅ スパム設定を保存しました！\n"
      f"・**状態:** {status_str}\n"
      f"・**制限:** {seconds}秒間に {count}件\n"
      f"・**処分方法:** {action}（タイムアウト時間: {timeout_duration}秒）\n"
      f"・**警告メッセージ:** {warn_message}",
      ephemeral=True,
  )


@bot.tree.command(
    name="test",
    description="【管理者用】日付お知らせのテスト送信と認証パネルの動作テストを行います",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(role="認証テストで使用するロール（任意）")
async def test_command(interaction: discord.Interaction, role: discord.Role = None):
  now = datetime.datetime.now(JST)
  weekdays = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
  weekday_str = weekdays[now.weekday()]
  date_text = f"🧪 【テスト】日付お知らせ確認\n本日は {now.month}月{now.day}日 ({weekday_str}) です。"

  test_role = role if role else interaction.guild.default_role

  embed = discord.Embed(
      title="🧪 【テスト】サーバー認証パネル",
      description=(
          "これは認証システムのテストパネルです。\n"
          f"対象ロール: {test_role.mention}\n\n"
          "下の 「認証を開始する」 ボタンを押して、画像認証が正常に動作するかテストしてください。"
      ),
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
  now = datetime.datetime.now(JST)
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


# --- 設定のエクスポート（バックアップ）コマンド ---
@bot.tree.command(
    name="exportconfig",
    description="【管理者用】現在のすべての設定データをJSONファイルとしてエクスポートします",
)
@app_commands.default_permissions(administrator=True)
async def exportconfig(interaction: discord.Interaction):
  export_data = {
      "notification_channel_id": NOTIFICATION_CHANNEL_ID,
      "log_settings": {str(k): v for k, v in LOG_SETTINGS.items()},
      "custom_responses": {str(k): v for k, v in CUSTOM_RESPONSES.items()},
      "welcome_settings": {str(k): v for k, v in WELCOME_SETTINGS.items()},
      "leave_guild_id": LEAVE_GUILD_ID,
      "leave_channel_id": LEAVE_CHANNEL_ID,
      "spam_settings": {str(k): v for k, v in SPAM_SETTINGS.items()},
  }

  json_bytes = json.dumps(export_data, ensure_ascii=False, indent=2).encode("utf-8")
  file = discord.File(io.BytesIO(json_bytes), filename="bot_config_backup.json")

  await interaction.response.send_message(
      "📦 すべての設定データをエクスポートしました。バックアップとして保管してください：",
      file=file,
      ephemeral=True,
  )


# --- 設定のインポート（復元）コマンド ---
@bot.tree.command(
    name="importconfig",
    description="【管理者用】エクスポートしたJSONファイルをアップロードして設定を復元します",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(file="エクスポートしたJSONファイル")
async def importconfig(interaction: discord.Interaction, file: discord.Attachment):
  global NOTIFICATION_CHANNEL_ID, LOG_SETTINGS, CUSTOM_RESPONSES, WELCOME_SETTINGS, LEAVE_GUILD_ID, LEAVE_CHANNEL_ID, SPAM_SETTINGS

  if not file.filename.endswith(".json"):
    await interaction.response.send_message(
        "❌ 拡張子が `.json` のファイルをアップロードしてください。", ephemeral=True
    )
    return

  try:
    file_bytes = await file.read()
    data = json.loads(file_bytes.decode("utf-8"))

    NOTIFICATION_CHANNEL_ID = data.get("notification_channel_id")
    if NOTIFICATION_CHANNEL_ID:
      save_notification_channel_id(NOTIFICATION_CHANNEL_ID)

    raw_log = data.get("log_settings", {})
    LOG_SETTINGS = {int(k): v for k, v in raw_log.items()}
    save_log_settings()

    raw_responses = data.get("custom_responses", {})
    CUSTOM_RESPONSES = {int(k): v for k, v in raw_responses.items()}
    save_custom_responses()

    raw_welcome = data.get("welcome_settings", {})
    WELCOME_SETTINGS = {int(k): v for k, v in raw_welcome.items()}
    save_welcome_settings()

    LEAVE_GUILD_ID = data.get("leave_guild_id")
    LEAVE_CHANNEL_ID = data.get("leave_channel_id")
    save_leave_settings(LEAVE_GUILD_ID, LEAVE_CHANNEL_ID)

    raw_spam = data.get("spam_settings", {})
    SPAM_SETTINGS = {int(k): v for k, v in raw_spam.items()}
    save_spam_settings()

    await interaction.response.send_message(
        "✅ 設定データのインポートと復元が正常に完了しました！", ephemeral=True
    )
  except Exception as e:
    await interaction.response.send_message(
        f"❌ 設定の読み込みに失敗しました（ファイル形式が不正な可能性があります）: {e}",
        ephemeral=True,
    )


# --- 複数ロール一括付与パネル作成コマンド（最大10個対応・絵文字のみ対応） ---
@bot.tree.command(
    name="addrole",
    description="【管理者用】最大10個までのロールをまとめて取得できるボタンパネル（絵文字のみ）を作成します",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    title="埋め込みのタイトル",
    description="説明文",
    role1="対象ロール1", emoji1="ロール1の絵文字",
    role2="対象ロール2（任意）", emoji2="ロール2の絵文字（任意）",
    role3="対象ロール3（任意）", emoji3="ロール3の絵文字（任意）",
    role4="対象ロール4（任意）", emoji4="ロール4の絵文字（任意）",
    role5="対象ロール5（任意）", emoji5="ロール5の絵文字（任意）",
    role6="対象ロール6（任意）", emoji6="ロール6の絵文字（任意）",
    role7="対象ロール7（任意）", emoji7="ロール7の絵文字（任意）",
    role8="対象ロール8（任意）", emoji8="ロール8の絵文字（任意）",
    role9="対象ロール9（任意）", emoji9="ロール9の絵文字（任意）",
    role10="対象ロール10（任意）", emoji10="ロール10の絵文字（任意）",
)
async def addrole(
    interaction: discord.Interaction,
    title: str,
    description: str,
    role1: discord.Role, emoji1: str,
    role2: discord.Role = None, emoji2: str = None,
    role3: discord.Role = None, emoji3: str = None,
    role4: discord.Role = None, emoji4: str = None,
    role5: discord.Role = None, emoji5: str = None,
    role6: discord.Role = None, emoji6: str = None,
    role7: discord.Role = None, emoji7: str = None,
    role8: discord.Role = None, emoji8: str = None,
    role9: discord.Role = None, emoji9: str = None,
    role10: discord.Role = None, emoji10: str = None,
):
  raw_roles = [
      (role1, emoji1), (role2, emoji2),
      (role3, emoji3), (role4, emoji4),
      (role5, emoji5), (role6, emoji6),
      (role7, emoji7), (role8, emoji8),
      (role9, emoji9), (role10, emoji10),
  ]

  roles_data = []
  for r, emoji_str in raw_roles:
    if r and emoji_str:
      if interaction.guild.me.top_role <= r:
        await interaction.response.send_message(
            f"❌ 指定されたロール（{r.name}）がボットのロールよりも上にあるため管理できません。",
            ephemeral=True,
        )
        return

      emoji_obj = None
      custom_emoji_match = re.match(r"<(a?):([a-zA-Z0-9\_]+):(\d+)>", emoji_str.strip())
      if custom_emoji_match:
        animated, name, emoji_id = custom_emoji_match.groups()
        emoji_obj = discord.PartialEmoji(name=name, id=int(emoji_id), animated=bool(animated))
      else:
        emoji_obj = emoji_str.strip()

      roles_data.append((r, emoji_obj))

  if not roles_data:
    await interaction.response.send_message(
        "❌ 有効なロールと絵文字が設定されていません。", ephemeral=True
    )
    return

  embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
  view = MultiRoleButtonView(roles_data)

  await interaction.channel.send(embed=embed, view=view)
  await interaction.response.send_message(
      "✅ 複数ロール取得の**絵文字ボタンパネル**を作成しました！", ephemeral=True
  )


class MultiRoleToggleButton(discord.ui.Button):
  def __init__(self, role_id: int, emoji):
    super().__init__(
        label=None,
        emoji=emoji,
        style=discord.ButtonStyle.primary,
        custom_id=f"multirole_{role_id}",
    )
    self.role_id = role_id

  async def callback(self, interaction: discord.Interaction):
    if interaction.guild is None:
      await interaction.response.send_message("❌ サーバー内でのみ使用できます。", ephemeral=True)
      return

    role = interaction.guild.get_role(self.role_id)
    if role is None:
      await interaction.response.send_message("❌ ロールが見つかりませんでした。", ephemeral=True)
      return

    try:
      if role in interaction.user.roles:
        await interaction.user.remove_roles(role)
        await interaction.response.send_message(f"❌ ロール「{role.name}」を解除しました。", ephemeral=True)
      else:
        await interaction.user.add_roles(role)
        await interaction.response.send_message(f"🎉 ロール「{role.name}」を付与しました！", ephemeral=True)
    except discord.Forbidden:
      await interaction.response.send_message("❌ ボットにロールを管理する権限がありません。", ephemeral=True)
    except Exception as e:
      await interaction.response.send_message(f"❌ エラーが発生しました: {e}", ephemeral=True)


class MultiRoleButtonView(discord.ui.View):
  def __init__(self, roles_data=None):
    super().__init__(timeout=None)
    if roles_data:
      for role, emoji in roles_data:
        self.add_item(MultiRoleToggleButton(role.id, emoji))
    else:
      self.add_item(MultiRoleToggleButton(0, "✨"))


@bot.tree.command(
    name="addresponse",
    description="【管理者用】メッセージが完全一致したときにBotが返す返信を登録します",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    keyword="完全一致させるキーワード",
    response="Botが返す返信内容",
)
async def addresponse(interaction: discord.Interaction, keyword: str, response: str):
  guild_id = interaction.guild.id
  if guild_id not in CUSTOM_RESPONSES:
    CUSTOM_RESPONSES[guild_id] = {}

  CUSTOM_RESPONSES[guild_id][keyword] = response
  save_custom_responses()
  await interaction.response.send_message(
      f"✅ キーワード「{keyword}」に対するカスタム返信を登録・保存しました！\n返信内容: {response}",
      ephemeral=True,
  )


@bot.tree.command(
    name="delresponse",
    description="【管理者用】登録したカスタム返信を削除します",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(keyword="削除したいキーワード")
async def delresponse(interaction: discord.Interaction, keyword: str):
  guild_id = interaction.guild.id
  if guild_id in CUSTOM_RESPONSES and keyword in CUSTOM_RESPONSES[guild_id]:
    del CUSTOM_RESPONSES[guild_id][keyword]
    save_custom_responses()
    await interaction.response.send_message(
        f"🗑️ キーワード「{keyword}」のカスタム返信を削除しました。",
        ephemeral=True,
    )
  else:
    await interaction.response.send_message(
        f"❌ キーワード「{keyword}」は登録されていません。",
        ephemeral=True,
    )


@bot.tree.command(
    name="history",
    description="このサーバーに登録されている完全一致メッセージの一覧を表示します",
)
@app_commands.default_permissions(manage_messages=True)
async def history(interaction: discord.Interaction):
  guild_id = interaction.guild.id
  responses = CUSTOM_RESPONSES.get(guild_id, {})

  if not responses:
    await interaction.response.send_message(
        "ℹ️ このサーバーに登録されている完全一致メッセージはありません。",
        ephemeral=True,
    )
    return

  embed = discord.Embed(
      title="📜 登録された完全一致メッセージ一覧",
      color=discord.Color.blue(),
  )

  for keyword, res in responses.items():
    display_res = res if len(res) <= 100 else res[:97] + "..."
    embed.add_field(
        name=f"🔑 キーワード: {keyword}",
        value=f"返信: {display_res}",
        inline=False,
    )

  await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(
    name="setwelcome",
    description="【管理者用】このサーバーのウェルカムメッセージを設定します（通常テキストまたは埋め込み対応）",
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
    interaction: discord.Interaction, enabled: bool, use_embed: bool, mention: bool, text: str, title: str = "👋 ようこそ！"
):
  guild_id = interaction.guild.id
  WELCOME_SETTINGS[guild_id] = {
      "channel_id": interaction.channel.id,
      "enabled": enabled,
      "use_embed": use_embed,
      "mention": mention,
      "title": title,
      "text": text,
  }
  save_welcome_settings()

  status_str = "🟢 有効 (オン)" if enabled else "🔴 無効 (オフ)"
  type_str = "📦 埋め込み (Embed)" if use_embed else "💬 通常テキスト"
  mention_str = "あり" if mention else "なし"

  await interaction.response.send_message(
      f"✅ このサーバーのウェルカムメッセージ設定を保存しました！\n"
      f"・**状態:** {status_str}\n"
      f"・**形式:** {type_str}\n"
      f"・**送信チャンネル:** {interaction.channel.mention}\n"
      f"・**メンション:** {mention_str}\n"
      f"・**タイトル:** {title}\n"
      f"・**本文:** {text}",
      ephemeral=True,
  )


@bot.tree.command(
    name="setleave",
    description="【管理者用】メンバー退出時の滞在時間記録を送信するチャンネルを設定します",
)
@app_commands.default_permissions(manage_channels=True)
async def setleave(interaction: discord.Interaction):
  global LEAVE_CHANNEL_ID, LEAVE_GUILD_ID
  LEAVE_GUILD_ID = interaction.guild.id
  LEAVE_CHANNEL_ID = interaction.channel.id
  save_leave_settings(LEAVE_GUILD_ID, LEAVE_CHANNEL_ID)

  await interaction.response.send_message(
      f"✅ このチャンネル（{interaction.channel.mention}）を退出時間記録の送信先に設定し、保存しました！",
      ephemeral=True,
  )


@bot.tree.command(
    name="ping", description="Botの応答速度（レイテンシ）を確認します"
)
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
      title=f"🖼️ {target_user.display_name} のアバター",
      color=discord.Color.blue(),
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


@bot.tree.command(
    name="captcha_setup", description="認証パネル（ボタン）を設置します"
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(role="認証完了時に付与するロール")
async def captcha_setup(interaction: discord.Interaction, role: discord.Role):
  embed = discord.Embed(
      title="🔒 サーバー認証",
      description=(
          "サーバーへようこそ！\n下の 「認証を開始する」 ボタンを押して、"
          "表示される画像認証をクリアしてください。"
      ),
      color=discord.Color.blue(),
  )
  view = CaptchaPanelView(role.id)
  await interaction.channel.send(embed=embed, view=view)
  await interaction.response.send_message(
      "✅ 認証パネルを設置しました！", ephemeral=True
  )


def generate_captcha_code():
  return "".join(
      random.choices(string.ascii_uppercase + string.digits, k=5)
  )


def create_captcha_image(code):
  width, height = 200, 80
  image = Image.new("RGB", (width, height), color=(240, 240, 240))
  draw = ImageDraw.Draw(image)

  for _ in range(5):
    xy = (
        random.randint(0, width),
        random.randint(0, height),
        random.randint(0, width),
        random.randint(0, height),
    )
    draw.line(xy, fill=(random.randint(100, 200),) * 3, width=2)

  for _ in range(100):
    xy = (random.randint(0, width), random.randint(0, height))
    draw.point(xy, fill=(random.randint(50, 150),) * 3)

  try:
    font = ImageFont.truetype("DejaVuSans.ttf", 36)
  except Exception:
    font = ImageFont.load_default()

  x = 30
  for char in code:
    y = random.randint(10, 30)
    draw.text(
        (x, y),
        char,
        fill=(random.randint(0, 100),) * 3,
        font=font,
    )
    x += 28

  buffer = io.BytesIO()
  image.save(buffer, format="PNG")
  buffer.seek(0)
  return buffer


class CaptchaStartButton(discord.ui.Button):
  def __init__(self, role_id: int = None):
    custom_id = f"captcha_start_{role_id}" if role_id else "captcha_start_default"
    super().__init__(
        label="認証を開始する",
        style=discord.ButtonStyle.success,
        custom_id=custom_id,
    )
    self.role_id = role_id

  async def callback(self, interaction: discord.Interaction):
    target_role_id = self.role_id
    if not target_role_id:
      custom_id = (interaction.data or {}).get("custom_id", "")
      parts = custom_id.split("_")
      if parts and parts[-1].isdigit():
        target_role_id = int(parts[-1])

    if interaction.guild is None:
      await interaction.response.send_message(
          "❌ サーバー内でのみ使用できます。", ephemeral=True
      )
      return

    target_role = interaction.guild.get_role(target_role_id) if target_role_id else None
    if not target_role:
      await interaction.response.send_message(
          "❌ 認証ロールが設定されていません。管理者にパネルの再作成を依頼してください。",
          ephemeral=True,
      )
      return

    if target_role in interaction.user.roles:
      await interaction.response.send_message(
          "ℹ️ すでに認証済みです！", ephemeral=True
      )
      return

    code = generate_captcha_code()
    image_bytes = create_captcha_image(code)
    file = discord.File(image_bytes, filename="captcha.png")

    view = CaptchaInputPromptView(target_role, code)
    await interaction.response.send_message(
        "下の画像に描かれている**5桁の英数字**を確認し、ボタンを押して入力してください：",
        file=file,
        view=view,
        ephemeral=True,
    )


class CaptchaPanelView(discord.ui.View):
  def __init__(self, role_id: int = None):
    super().__init__(timeout=None)
    self.role_id = role_id
    self.add_item(CaptchaStartButton(role_id))


class CaptchaInputPromptView(discord.ui.View):

  def __init__(self, role: discord.Role, correct_code: str):
    super().__init__(timeout=180)
    self.role = role
    self.correct_code = correct_code

  @discord.ui.button(
      label="コードを入力する", style=discord.ButtonStyle.primary, emoji="✍️"
  )
  async def open_modal(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    modal = CaptchaModal(self.role, self.correct_code)
    await interaction.response.send_modal(modal)


class CaptchaModal(discord.ui.Modal, title="CAPTCHA画像認証"):

  def __init__(self, role: discord.Role, correct_code: str):
    super().__init__()
    self.role = role
    self.correct_code = correct_code

    self.user_input = discord.ui.TextInput(
        label="画像の英数字を入力してください（大文字小文字区別）",
        placeholder="例: A3B9X",
        min_length=5,
        max_length=5,
        required=True,
    )
    self.add_item(self.user_input)

  async def on_submit(self, interaction: discord.Interaction):
    entered_text = self.user_input.value.strip()

    if entered_text == self.correct_code:
      try:
        await interaction.user.add_roles(self.role)
        await interaction.response.send_message(
            "🎉 認証に成功しました！ロールが付与されました。",
            ephemeral=True,
        )
      except discord.Forbidden:
        await interaction.response.send_message(
            "❌ ボットにロールを付与する権限がありません。", ephemeral=True
        )
    else:
      await interaction.response.send_message(
          "❌ 認証コードが違います。もう一度パネルのボタンからやり直してください。",
          ephemeral=True,
      )


# --- リンク削除用の統合ビュー（元のリンクのみ消す場合はBotメッセージを残すように修正） ---
class LinkControlView(discord.ui.View):
  def __init__(self, author_id: int, user_message_id: int):
    super().__init__(timeout=None)
    self.author_id = author_id
    self.user_message_id = user_message_id

  @discord.ui.button(
      label="Botのリンクを消す", style=discord.ButtonStyle.secondary, emoji="🧹", custom_id="delete_bot_msg_btn"
  )
  async def delete_bot_button(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    if interaction.user.id != self.author_id:
      await interaction.response.send_message(
          "❌ あなたが送信したリンクではないため操作できません。",
          ephemeral=True,
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
      label="元のリンクを消す", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="delete_user_msg_btn"
  )
  async def delete_user_button(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    if interaction.user.id != self.author_id:
      await interaction.response.send_message(
          "❌ あなたが送信したリンクではないため操作できません。",
          ephemeral=True,
      )
      return

    try:
      # ユーザーが送信した元のメッセージだけを削除する（Botメッセージは残す）
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


# --- サーバーごとのログ送信判定ヘルパー ---
def get_guild_log_channel(guild_id: int):
  if not guild_id or guild_id not in LOG_SETTINGS:
    return None
  settings = LOG_SETTINGS[guild_id]
  if not settings.get("enabled", True):
    return None
  return settings.get("channel_id")


# --- メッセージ・チャンネル・スレッドのログ通知イベントハンドラー（サーバーごとに独立） ---
@bot.event
async def on_message_delete(message: discord.Message):
  if message.author.bot or not message.guild:
    return

  channel_id = get_guild_log_channel(message.guild.id)
  if channel_id is None:
    return
  target_channel = bot.get_channel(channel_id)
  if target_channel is None:
    return

  content_text = message.content if message.content else "(テキストなし・添付ファイル等)"
  embed = discord.Embed(
      description=(
          f"🗑️ {message.author.mention} が送信したメッセージが <#{message.channel.id}> で削除されました。\n"
          f"Author: {message.author.mention} {content_text}"
      ),
      color=discord.Color.red(),
      timestamp=datetime.datetime.now(JST)
  )
  embed.set_footer(text=f"{bot.user.name} / {message.guild.name}")
  try:
    await target_channel.send(embed=embed)
  except Exception as e:
    print(f"メッセージ削除通知の送信に失敗しました: {e}")


@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
  if before.author.bot or not before.guild:
    return
  if before.content == after.content:
    return

  channel_id = get_guild_log_channel(before.guild.id)
  if channel_id is None:
    return
  target_channel = bot.get_channel(channel_id)
  if target_channel is None:
    return

  before_text = before.content if before.content else "(なし)"
  after_text = after.content if after.content else "(なし)"

  embed = discord.Embed(
      description=(
          f"✏️ {before.author.mention} が送信したメッセージが <#{before.channel.id}> で編集されました。\n"
          f"Author: {before.author.mention}\n"
          f"**編集前:** {before_text}\n"
          f"**編集後:** {after_text}"
      ),
      color=discord.Color.gold(),
      timestamp=datetime.datetime.now(JST)
  )
  embed.set_footer(text=f"{bot.user.name} / {before.guild.name}")
  try:
    await target_channel.send(embed=embed)
  except Exception as e:
    print(f"メッセージ編集通知の送信に失敗しました: {e}")


@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
  if not channel.guild:
    return
  channel_id = get_guild_log_channel(channel.guild.id)
  if channel_id is None:
    return
  target_channel = bot.get_channel(channel_id)
  if target_channel is None:
    return

  embed = discord.Embed(
      description=f"📁 チャンネル **{channel.name}** ({channel.type}) が作成されました。",
      color=discord.Color.green(),
      timestamp=datetime.datetime.now(JST)
  )
  try:
    await target_channel.send(embed=embed)
  except Exception as e:
    print(f"チャンネル作成通知の送信に失敗しました: {e}")


@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
  if not channel.guild:
    return
  channel_id = get_guild_log_channel(channel.guild.id)
  if channel_id is None:
    return
  target_channel = bot.get_channel(channel_id)
  if target_channel is None:
    return

  embed = discord.Embed(
      description=f"🗑️ チャンネル **{channel.name}** ({channel.type}) が削除されました。",
      color=discord.Color.red(),
      timestamp=datetime.datetime.now(JST)
  )
  try:
    await target_channel.send(embed=embed)
  except Exception as e:
    print(f"チャンネル削除通知の送信に失敗しました: {e}")


@bot.event
async def on_thread_create(thread: discord.Thread):
  if not thread.guild:
    return
  channel_id = get_guild_log_channel(thread.guild.id)
  if channel_id is None:
    return
  target_channel = bot.get_channel(channel_id)
  if target_channel is None:
    return

  embed = discord.Embed(
      description=f"🧵 スレッド **{thread.name}** が作成されました (親: <#{thread.parent_id}>)。",
      color=discord.Color.blurple(),
      timestamp=datetime.datetime.now(JST)
  )
  try:
    await target_channel.send(embed=embed)
  except Exception as e:
    print(f"スレッド作成通知の送信に失敗しました: {e}")


@bot.event
async def on_thread_delete(thread: discord.Thread):
  if not thread.guild:
    return
  channel_id = get_guild_log_channel(thread.guild.id)
  if channel_id is None:
    return
  target_channel = bot.get_channel(channel_id)
  if target_channel is None:
    return

  embed = discord.Embed(
      description=f"🗑️ スレッド **{thread.name}** が削除されました。",
      color=discord.Color.dark_red(),
      timestamp=datetime.datetime.now(JST)
  )
  try:
    await target_channel.send(embed=embed)
  except Exception as e:
    print(f"スレッド削除通知の送信に失敗しました: {e}")


@bot.event
async def on_ready():
  print(f"ログインしました: {bot.user} (ID: {bot.user.id})")

  if not getattr(bot, "_persistent_views_added", False):
    bot.add_view(CaptchaPanelView())
    bot.add_view(MultiRoleButtonView())
    bot.add_view(LinkControlView(0, 0))
    bot.add_view(HelpLangButtonView())

    for guild in bot.guilds:
      for role in guild.roles:
        bot.add_view(CaptchaPanelView(role.id))
        bot.add_view(MultiRoleButtonView([(role, "✨")]))

    bot._persistent_views_added = True

  try:
    synced = await bot.tree.sync()
    print(f"グローバル同期成功: {len(synced)} 個のコマンド")
    print("同期済みコマンド:", ", ".join(cmd.name for cmd in synced))
  except Exception as e:
    print(f"グローバル同期エラー ({type(e).__name__}): {e}")

  if not send_date_announcement.is_running():
    send_date_announcement.start()


@bot.event
async def on_member_join(member: discord.Member):
  guild_id = member.guild.id
  if guild_id not in WELCOME_SETTINGS:
    return

  settings = WELCOME_SETTINGS[guild_id]
  if not settings.get("enabled", False):
    return

  channel_id = settings.get("channel_id")
  if channel_id is None:
    return

  channel = bot.get_channel(channel_id)
  if channel is None:
    try:
      channel = await bot.fetch_channel(channel_id)
    except Exception:
      return

  text = settings.get("text", "")
  formatted_text = text.replace("{guild.name}", member.guild.name).replace("{member.name}", member.name)
  use_embed = settings.get("use_embed", False)
  title = settings.get("title", "👋 ようこそ！")
  mention = settings.get("mention", True)

  if use_embed:
    embed = discord.Embed(title=title, description=formatted_text, color=discord.Color.blue())
    if member.avatar:
      embed.set_thumbnail(url=member.avatar.url)

    content = member.mention if mention else None
    await channel.send(content=content, embed=embed)
  else:
    if mention:
      final_message = f"{member.mention} {formatted_text}"
    else:
      final_message = formatted_text
    await channel.send(final_message)


@bot.event
async def on_member_remove(member: discord.Member):
  global LEAVE_CHANNEL_ID, LEAVE_GUILD_ID

  if LEAVE_CHANNEL_ID is None or LEAVE_GUILD_ID is None:
    return
  if member.guild.id != LEAVE_GUILD_ID:
    return

  if member.id == bot.user.id:
    return

  channel = bot.get_channel(LEAVE_CHANNEL_ID)
  if channel is None:
    try:
      channel = await bot.fetch_channel(LEAVE_CHANNEL_ID)
    except Exception:
      return

  if member.joined_at:
    now = datetime.datetime.now(datetime.timezone.utc)
    duration = now - member.joined_at

    total_seconds = int(duration.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    time_str = ""
    if days > 0:
      time_str += f"{days}日 "
    if hours > 0:
      time_str += f"{hours}時間 "
    if minutes > 0:
      time_str += f"{minutes}分 "
    time_str += f"{seconds}秒"
  else:
    time_str = "不明"

  embed = discord.Embed(
      title="🚪 メンバーが退出しました",
      description=(
          f"ユーザー: {member} ({member.id})\n"
          f"滞在時間: {time_str}"
      ),
      color=discord.Color.red(),
  )
  if member.avatar:
    embed.set_thumbnail(url=member.avatar.url)

  await channel.send(embed=embed)


@bot.event
async def on_message(message: discord.Message):
  if message.author.bot:
    return

  if message.guild:
    guild_id = message.guild.id

    # --- アンチスパム（荒らし対策）チェック ---
    if guild_id in SPAM_SETTINGS:
      spam_conf = SPAM_SETTINGS[guild_id]
      if spam_conf.get("enabled", False):
        # 管理者はスパム対象外にする場合 (必要に応じて)
        if not message.author.guild_permissions.administrator:
          limit_seconds = spam_conf.get("seconds", 5)
          limit_count = spam_conf.get("count", 5)
          action = spam_conf.get("action", "timeout")
          timeout_dur = spam_conf.get("timeout_duration", 300)
          warn_msg = spam_conf.get("warn_message", "スパム行為が検知されたため制限されました。")

          now_ts = datetime.datetime.now(JST).timestamp()
          history = user_message_history[guild_id][message.author.id]

          # 古い履歴を削除
          while history and history[0] < now_ts - limit_seconds:
            history.popleft()

          history.append(now_ts)

          if len(history) >= limit_count:
            try:
              if action == "timeout":
                duration_delta = datetime.timedelta(seconds=timeout_dur)
                await message.author.timeout(duration_delta, reason="アンチスパム検知: 短時間の連続投稿")
              elif action == "kick":
                await message.author.kick(reason="アンチスパム検知: 短時間の連続投稿")
              elif action == "ban":
                await message.author.ban(reason="アンチスパム検知: 短時間の連続投稿", delete_message_days=0)

              await message.channel.send(f"{message.author.mention} {warn_msg}")
            except Exception as e:
              print(f"スパム処分の実行に失敗しました: {e}")

            # 履歴をクリア
            history.clear()
            return

    # --- カスタム返信チェック ---
    if guild_id in CUSTOM_RESPONSES and message.content in CUSTOM_RESPONSES[guild_id]:
      await message.channel.send(CUSTOM_RESPONSES[guild_id][message.content])
      return

  content = message.content
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
        r"https?://(?:www\.|vm\.|vt\.)?tiktok\.com",
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

  if replaced:
    view = LinkControlView(message.author.id, message.id)
    await message.channel.send(content, view=view)


async def main():
  token = os.getenv("DISCORD_TOKEN")
  if not token:
    print("エラー: DISCORD_TOKEN が環境変数に設定されていません。")
    return

  await start_web_server()

  async with bot:
    await bot.start(token)


if __name__ == "__main__":
  import asyncio

  asyncio.run(main())