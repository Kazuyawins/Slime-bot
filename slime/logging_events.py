"""Logging events features."""

import datetime
import discord
from . import config
from .runtime import bot


def get_guild_log_channel(guild_id: int):
    if not guild_id or guild_id not in config.LOG_SETTINGS:
        return None
    settings = config.LOG_SETTINGS[guild_id]
    if not settings.get("enabled", True):
        return None
    return settings.get("channel_id")


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
    content_text = (
        message.content if message.content else "(テキストなし・添付ファイル等)"
    )
    embed = discord.Embed(
        description=f"🗑️ {message.author.mention} が送信したメッセージが <#{message.channel.id}> で削除されました。\nAuthor: {message.author.mention} {content_text}",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(config.JST),
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
        description=f"✏️ {before.author.mention} が送信したメッセージが <#{before.channel.id}> で編集されました。\nAuthor: {before.author.mention}\n**編集前:** {before_text}\n**編集後:** {after_text}",
        color=discord.Color.gold(),
        timestamp=datetime.datetime.now(config.JST),
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
        timestamp=datetime.datetime.now(config.JST),
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
        timestamp=datetime.datetime.now(config.JST),
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
        timestamp=datetime.datetime.now(config.JST),
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
        timestamp=datetime.datetime.now(config.JST),
    )
    try:
        await target_channel.send(embed=embed)
    except Exception as e:
        print(f"スレッド削除通知の送信に失敗しました: {e}")


async def send_error_log(
    guild: discord.Guild, title: str, error: Exception, details: str = None
):
    """エラー発生時にログチャンネルへエラー内容を送信する関数"""
    if not guild:
        return
    channel_id = get_guild_log_channel(guild.id)
    if not channel_id:
        return
    channel = bot.get_channel(channel_id)
    if not channel:
        try:
            channel = await bot.fetch_channel(channel_id)
        except Exception:
            return
    embed = discord.Embed(
        title=f"⚠️ エラーが発生しました: {title}",
        description=f"**エラー内容:** `{type(error).__name__}: {error}`",
        color=discord.Color.dark_red(),
        timestamp=datetime.datetime.now(config.JST),
    )
    if details:
        embed.add_field(name="詳細情報", value=details, inline=False)
    if isinstance(error, discord.Forbidden):
        embed.add_field(
            name="💡 解決策のヒント",
            value="・Botに必要な権限（メンバーのタイムアウト/キック/BANなど）が付与されているか確認してください。\n・Botの役職（ロール）が、対象ユーザーのロールよりも**上**に配置されているか確認してください。",
            inline=False,
        )
    embed.set_footer(text=f"{bot.user.name} / {guild.name}")
    try:
        await channel.send(embed=embed)
    except Exception as e:
        print(f"エラーログの送信自体に失敗しました: {e}")
