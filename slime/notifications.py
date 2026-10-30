"""Notifications features."""

import datetime
from discord.ext import tasks
from . import config
from .runtime import bot

daily_time = datetime.time(hour=0, minute=0, second=0, tzinfo=config.JST)


@tasks.loop(time=daily_time)
async def send_date_announcement():
    if config.NOTIFICATION_CHANNEL_ID is None:
        return
    channel = bot.get_channel(config.NOTIFICATION_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(config.NOTIFICATION_CHANNEL_ID)
        except Exception as e:
            print(f"チャンネルの取得に失敗しました: {e}")
            return
    now = datetime.datetime.now(config.JST)
    weekdays = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
    weekday_str = weekdays[now.weekday()]
    message_text = f"📅 日付が変わりました！\n本日は {now.month}月{now.day}日 ({weekday_str}) です。"
    await channel.send(message_text)


@send_date_announcement.before_loop
async def before_send_date_announcement():
    await bot.wait_until_ready()
