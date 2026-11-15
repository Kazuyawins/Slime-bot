"""Single shared Discord client; importing this module never connects."""

import discord
from discord.ext import commands
from slime.twitter import TwitterNotifier  # 追加

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Twitter通知機能の初期化とスラッシュコマンドの登録
twitter_notifier = TwitterNotifier(bot)
twitter_notifier.register_commands()