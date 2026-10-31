"""Existing configuration formats and shared mutable state."""

import json
import os
from collections import defaultdict, deque
from zoneinfo import ZoneInfo

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


def load_log_settings():
    if os.path.exists(LOG_CONFIG_FILE):
        try:
            with open(LOG_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.loads(f.read())
                if isinstance(data, dict) and "guilds" in data:
                    return {
                        int(k): {
                            "channel_id": v["channel_id"],
                            "enabled": v.get("enabled", True),
                        }
                        for k, v in data["guilds"].items()
                    }
        except Exception as e:
            print(f"ログ設定の読み込みに失敗しました: {e}")
    return {}


def save_log_settings():
    try:
        with open(LOG_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"guilds": {str(k): v for k, v in LOG_SETTINGS.items()}},
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception as e:
        print(f"ログ設定の保存に失敗しました: {e}")


LOG_SETTINGS = load_log_settings()


def load_custom_responses():
    if os.path.exists(RESPONSES_FILE):
        try:
            with open(RESPONSES_FILE, "r", encoding="utf-8") as f:
                data = json.loads(f.read())
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


def load_welcome_settings():
    if os.path.exists(WELCOME_FILE):
        try:
            with open(WELCOME_FILE, "r", encoding="utf-8") as f:
                data = json.loads(f.read())
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


def load_leave_settings():
    if os.path.exists(LEAVE_CONFIG_FILE):
        try:
            with open(LEAVE_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.loads(f.read())
                return (data.get("guild_id"), data.get("channel_id"))
        except Exception as e:
            print(f"退出通知設定の読み込みに失敗しました: {e}")
    return (None, None)


def save_leave_settings(guild_id, channel_id):
    try:
        with open(LEAVE_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"guild_id": guild_id, "channel_id": channel_id},
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception as e:
        print(f"退出通知設定の保存に失敗しました: {e}")


LEAVE_GUILD_ID, LEAVE_CHANNEL_ID = load_leave_settings()


def load_spam_settings():
    if os.path.exists(SPAM_CONFIG_FILE):
        try:
            with open(SPAM_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.loads(f.read())
                return {int(k): v for k, v in data.items()}
        except Exception as e:
            print(f"スパム設定の読み込みに失敗しました: {e}")
    return {}


def save_spam_settings():
    try:
        with open(SPAM_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {str(k): v for k, v in SPAM_SETTINGS.items()},
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception as e:
        print(f"スパム設定の保存に失敗しました: {e}")


SPAM_SETTINGS = load_spam_settings()
user_message_history = defaultdict(lambda: defaultdict(deque))
JST = ZoneInfo("Asia/Tokyo")
