"""Roles features."""

import re
import discord
from discord import app_commands
from . import config
from .runtime import bot


@bot.tree.command(
    name="addrole",
    description="【管理者用】最大10個までのロールをまとめて取得できるボタンパネル（絵文字のみ）を作成します",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    title="埋め込みのタイトル",
    description="説明文",
    role1="対象ロール1",
    emoji1="ロール1の絵文字",
    role2="対象ロール2（任意）",
    emoji2="ロール2の絵文字（任意）",
    role3="対象ロール3（任意）",
    emoji3="ロール3の絵文字（任意）",
    role4="対象ロール4（任意）",
    emoji4="ロール4の絵文字（任意）",
    role5="対象ロール5（任意）",
    emoji5="ロール5の絵文字（任意）",
    role6="対象ロール6（任意）",
    emoji6="ロール6の絵文字（任意）",
    role7="対象ロール7（任意）",
    emoji7="ロール7の絵文字（任意）",
    role8="対象ロール8（任意）",
    emoji8="ロール8の絵文字（任意）",
    role9="対象ロール9（任意）",
    emoji9="ロール9の絵文字（任意）",
    role10="対象ロール10（任意）",
    emoji10="ロール10の絵文字（任意）",
)
async def addrole(
    interaction: discord.Interaction,
    title: str,
    description: str,
    role1: discord.Role,
    emoji1: str,
    role2: discord.Role = None,
    emoji2: str = None,
    role3: discord.Role = None,
    emoji3: str = None,
    role4: discord.Role = None,
    emoji4: str = None,
    role5: discord.Role = None,
    emoji5: str = None,
    role6: discord.Role = None,
    emoji6: str = None,
    role7: discord.Role = None,
    emoji7: str = None,
    role8: discord.Role = None,
    emoji8: str = None,
    role9: discord.Role = None,
    emoji9: str = None,
    role10: discord.Role = None,
    emoji10: str = None,
):
    raw_roles = [
        (role1, emoji1),
        (role2, emoji2),
        (role3, emoji3),
        (role4, emoji4),
        (role5, emoji5),
        (role6, emoji6),
        (role7, emoji7),
        (role8, emoji8),
        (role9, emoji9),
        (role10, emoji10),
    ]
    roles_data = []
    for r, emoji_str in raw_roles:
        if r and emoji_str:
            if interaction.guild.me.top_role <= r:
                await interaction.response.send_message(
                    f"❌ 指定されたロール（{r.name}）がボットのロールよりも上にあるため管理できません。",
                    ephemeral=True,
                )
                return
            emoji_obj = None
            custom_emoji_match = re.match(
                "<(a?):([a-zA-Z0-9\\_]+):(\\d+)>", emoji_str.strip()
            )
            if custom_emoji_match:
                animated, name, emoji_id = custom_emoji_match.groups()
                emoji_obj = discord.PartialEmoji(
                    name=name, id=int(emoji_id), animated=bool(animated)
                )
            else:
                emoji_obj = emoji_str.strip()
            roles_data.append((r, emoji_obj))
    if not roles_data:
        await interaction.response.send_message(
            "❌ 有効なロールと絵文字が設定されていません。", ephemeral=True
        )
        return
    embed = discord.Embed(
        title=title, description=description, color=discord.Color.blue()
    )
    view = MultiRoleButtonView(roles_data)
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message(
        "✅ 複数ロール取得の**絵文字ボタンパネル**を作成しました！", ephemeral=True
    )


class MultiRoleToggleButton(discord.ui.Button):

    def __init__(self, role_id: int, emoji):
        super().__init__(
            label=None,
            emoji=emoji,
            style=discord.ButtonStyle.primary,
            custom_id=f"multirole_{role_id}",
        )
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ サーバー内でのみ使用できます。", ephemeral=True
            )
            return
        role = interaction.guild.get_role(self.role_id)
        if role is None:
            await interaction.response.send_message(
                "❌ ロールが見つかりませんでした。", ephemeral=True
            )
            return
        try:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(
                    f"❌ ロール「{role.name}」を解除しました。", ephemeral=True
                )
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(
                    f"🎉 ロール「{role.name}」を付与しました！", ephemeral=True
                )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ ボットにロールを管理する権限がありません。", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ エラーが発生しました: {e}", ephemeral=True
            )


class MultiRoleButtonView(discord.ui.View):

    def __init__(self, roles_data=None):
        super().__init__(timeout=None)
        if roles_data:
            for role, emoji in roles_data:
                self.add_item(MultiRoleToggleButton(role.id, emoji))
        else:
            self.add_item(MultiRoleToggleButton(0, "✨"))
