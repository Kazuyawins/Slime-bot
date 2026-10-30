"""Slime Bot entry point. Run with: python bot.py."""

import asyncio
import os
from slime.runtime import bot
from slime import (
    administration,
    captcha,
    general,
    lifecycle,
    logging_events,
    members,
    messages,
    moderation,
    notifications,
    responses,
    roles,
)
from slime.web_server import start_web_server


async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("エラー: DISCORD_TOKEN が環境変数に設定されていません。")
        return

    await start_web_server()

    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
