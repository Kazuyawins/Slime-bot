"""Members features."""

import datetime
import discord
from . import config
from .runtime import bot


@bot.event
async def on_member_join(member: discord.Member):
    guild_id = member.guild.id
    if guild_id not in config.WELCOME_SETTINGS:
        return
    settings = config.WELCOME_SETTINGS[guild_id]
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
    formatted_text = text.replace("{guild.name}", member.guild.name).replace(
        "{member.name}", member.name
    )
    use_embed = settings.get("use_embed", False)
    title = settings.get("title", "👋 ようこそ！")
    mention = settings.get("mention", True)
    if use_embed:
        embed = discord.Embed(
            title=title, description=formatted_text, color=discord.Color.blue()
        )
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
    if config.LEAVE_CHANNEL_ID is None or config.LEAVE_GUILD_ID is None:
        return
    if member.guild.id != config.LEAVE_GUILD_ID:
        return
    if member.id == bot.user.id:
        return
    channel = bot.get_channel(config.LEAVE_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(config.LEAVE_CHANNEL_ID)
        except Exception:
            return
    if member.joined_at:
        now = datetime.datetime.now(datetime.timezone.utc)
        duration = now - member.joined_at
        total_seconds = int(duration.total_seconds())
        days = total_seconds // 86400
        hours = total_seconds % 86400 // 3600
        minutes = total_seconds % 3600 // 60
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
        description=f"ユーザー: {member} ({member.id})\n滞在時間: {time_str}",
        color=discord.Color.red(),
    )
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    await channel.send(embed=embed)
