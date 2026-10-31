"""One message event, preserving moderation → replies → previews ordering."""

import discord
from .runtime import bot
from .moderation import handle_spam
from .responses import handle_response
from .links import handle_links


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if message.guild:
        if await handle_spam(message):
            return
        if await handle_response(message):
            return
    await handle_links(message)
