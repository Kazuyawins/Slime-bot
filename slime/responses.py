"""Responses features."""

import discord
from discord import app_commands
from . import config
from .runtime import bot


@bot.tree.command(
    name="addresponse",
    description="【管理者用】メッセージが完全一致したときにBotが返す返信を登録します",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(keyword="完全一致させるキーワード", response="Botが返す返信内容")
async def addresponse(interaction: discord.Interaction, keyword: str, response: str):
    guild_id = interaction.guild.id
    if guild_id not in config.CUSTOM_RESPONSES:
        config.CUSTOM_RESPONSES[guild_id] = {}
    config.CUSTOM_RESPONSES[guild_id][keyword] = response
    config.save_custom_responses()
    await interaction.response.send_message(
        f"✅ キーワード「{keyword}」に対するカスタム返信を登録・保存しました！\n返信内容: {response}",
        ephemeral=True,
    )


@bot.tree.command(
    name="delresponse", description="【管理者用】登録したカスタム返信を削除します"
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(keyword="削除したいキーワード")
async def delresponse(interaction: discord.Interaction, keyword: str):
    guild_id = interaction.guild.id
    if (
        guild_id in config.CUSTOM_RESPONSES
        and keyword in config.CUSTOM_RESPONSES[guild_id]
    ):
        del config.CUSTOM_RESPONSES[guild_id][keyword]
        config.save_custom_responses()
        await interaction.response.send_message(
            f"🗑️ キーワード「{keyword}」のカスタム返信を削除しました。", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ キーワード「{keyword}」は登録されていません。", ephemeral=True
        )


async def handle_response(message: discord.Message):
    guild_id = message.guild.id
    if (
        guild_id in config.CUSTOM_RESPONSES
        and message.content in config.CUSTOM_RESPONSES[guild_id]
    ):
        await message.channel.send(config.CUSTOM_RESPONSES[guild_id][message.content])
        return True
    return False
