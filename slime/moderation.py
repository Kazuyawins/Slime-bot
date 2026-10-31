"""Moderation features."""

from .logging_events import send_error_log
import datetime
import discord
from discord import app_commands
from . import config
from .runtime import bot


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
    timeout_value="タイムアウトさせる任意の数値（任意・例: 10）",
    timeout_unit="タイムアウトの単位（任意・秒/分/時間/日）",
    warn_message="検知時にユーザーへ送信する警告メッセージ（任意）",
)
@app_commands.choices(
    action=[
        app_commands.Choice(name="タイムアウト (timeout)", value="timeout"),
        app_commands.Choice(name="キック (kick)", value="kick"),
        app_commands.Choice(name="BAN (ban)", value="ban"),
    ],
    timeout_unit=[
        app_commands.Choice(name="秒 (seconds)", value="seconds"),
        app_commands.Choice(name="分 (minutes)", value="minutes"),
        app_commands.Choice(name="時間 (hours)", value="hours"),
        app_commands.Choice(name="日 (days)", value="days"),
    ],
)
async def spamsetting(
    interaction: discord.Interaction,
    enabled: bool,
    seconds: int,
    count: int,
    action: str,
    timeout_value: int = 5,
    timeout_unit: str = "minutes",
    warn_message: str = "スパム行為が検知されたため制限されました。",
):
    guild_id = interaction.guild.id
    if timeout_unit == "seconds":
        timeout_seconds = timeout_value
        unit_str = f"{timeout_value}秒"
    elif timeout_unit == "minutes":
        timeout_seconds = timeout_value * 60
        unit_str = f"{timeout_value}分"
    elif timeout_unit == "hours":
        timeout_seconds = timeout_value * 3600
        unit_str = f"{timeout_value}時間"
    elif timeout_unit == "days":
        timeout_seconds = timeout_value * 86400
        unit_str = f"{timeout_value}日"
    else:
        timeout_seconds = timeout_value * 60
        unit_str = f"{timeout_value}分"
    config.SPAM_SETTINGS[guild_id] = {
        "enabled": enabled,
        "seconds": seconds,
        "count": count,
        "action": action,
        "timeout_duration": timeout_seconds,
        "warn_message": warn_message,
    }
    config.save_spam_settings()
    status_str = "🟢 有効 (オン)" if enabled else "🔴 無効 (オフ)"
    await interaction.response.send_message(
        f"✅ スパム設定を保存しました！\n・**状態:** {status_str}\n・**制限:** {seconds}秒間に {count}件\n・**処分方法:** {action}（タイムアウト時間: **{unit_str}**）\n・**警告メッセージ:** {warn_message}",
        ephemeral=True,
    )


async def handle_spam(message: discord.Message):
    guild_id = message.guild.id
    if guild_id in config.SPAM_SETTINGS:
        spam_conf = config.SPAM_SETTINGS[guild_id]
        if spam_conf.get("enabled", False):
            if not message.author.guild_permissions.administrator:
                limit_seconds = spam_conf.get("seconds", 5)
                limit_count = spam_conf.get("count", 5)
                action = spam_conf.get("action", "timeout")
                timeout_dur = spam_conf.get("timeout_duration", 300)
                warn_msg = spam_conf.get(
                    "warn_message", "スパム行為が検知されたため制限されました。"
                )
                now_ts = datetime.datetime.now(config.JST).timestamp()
                history = config.user_message_history[guild_id][message.author.id]
                while history and history[0] < now_ts - limit_seconds:
                    history.popleft()
                history.append(now_ts)
                if len(history) >= limit_count:
                    try:
                        if action == "timeout":
                            duration_delta = datetime.timedelta(seconds=timeout_dur)
                            await message.author.timeout(
                                duration_delta,
                                reason="アンチスパム検知: 短時間の連続投稿",
                            )
                        elif action == "kick":
                            await message.author.kick(
                                reason="アンチスパム検知: 短時間の連続投稿"
                            )
                        elif action == "ban":
                            await message.author.ban(
                                reason="アンチスパム検知: 短時間の連続投稿",
                                delete_message_days=0,
                            )
                        await message.channel.send(
                            f"{message.author.mention} {warn_msg}"
                        )
                    except Exception as e:
                        print(f"スパム処分の実行に失敗しました: {e}")
                        await send_error_log(
                            message.guild,
                            "スパム処分の実行失敗",
                            e,
                            f"対象ユーザー: {message.author.mention} (`{message.author.id}`)\n実行しようとしたアクション: `{action}` (設定時間: {timeout_dur}秒)",
                        )
                    history.clear()
                    return True
    return False
