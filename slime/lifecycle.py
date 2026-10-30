"""Lifecycle features."""

from .logging_events import send_error_log
import discord
from discord import app_commands
from . import config
from .runtime import bot
from .captcha import CaptchaPanelView
from .roles import MultiRoleButtonView
from .links import LinkControlView
from .general import HelpLangButtonView
from .notifications import send_date_announcement


@bot.event
async def on_ready():
    print(f"ログインしました: {bot.user} (ID: {bot.user.id})")
    if not getattr(bot, "_persistent_views_added", False):
        bot.add_view(CaptchaPanelView())
        bot.add_view(MultiRoleButtonView())
        bot.add_view(LinkControlView(0, 0, ""))
        bot.add_view(HelpLangButtonView())
        for guild in bot.guilds:
            for role in guild.roles:
                bot.add_view(CaptchaPanelView(role.id))
                bot.add_view(MultiRoleButtonView([(role, "✨")]))
        bot._persistent_views_added = True
    try:
        synced = await bot.tree.sync()
        print(f"グローバル同期成功: {len(synced)} 個のコマンド")
    except Exception as e:
        print(f"グローバル同期エラー ({type(e).__name__}): {e}")
    if not send_date_announcement.is_running():
        send_date_announcement.start()


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
):
    guild = interaction.guild
    if guild:
        await send_error_log(
            guild,
            f"コマンド実行エラー (`/{(interaction.command.name if interaction.command else '不明')}`)",
            error,
            f"実行ユーザー: {interaction.user.mention}",
        )
    if not interaction.response.is_done():
        await interaction.response.send_message(
            "❌ コマンド実行中にエラーが発生しました。", ephemeral=True
        )
