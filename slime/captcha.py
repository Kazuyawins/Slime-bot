"""Captcha features."""

from .logging_events import send_error_log
import io
import random
import string
import discord
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
from . import config
from .runtime import bot


@bot.tree.command(name="captcha_setup", description="認証パネル（ボタン）を設置します")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(role="認証完了時に付与するロール")
async def captcha_setup(interaction: discord.Interaction, role: discord.Role):
    embed = discord.Embed(
        title="🔒 サーバー認証",
        description="サーバーへようこそ！\n下の 「認証を開始する」 ボタンを押して、表示される画像認証をクリアしてください。",
        color=discord.Color.blue(),
    )
    view = CaptchaPanelView(role.id)
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message(
        "✅ 認証パネルを設置しました！", ephemeral=True
    )


def generate_captcha_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=5))


def create_captcha_image(code):
    width, height = (200, 80)
    image = Image.new("RGB", (width, height), color=(240, 240, 240))
    draw = ImageDraw.Draw(image)
    for _ in range(5):
        xy = (
            random.randint(0, width),
            random.randint(0, height),
            random.randint(0, width),
            random.randint(0, height),
        )
        draw.line(xy, fill=(random.randint(100, 200),) * 3, width=2)
    for _ in range(100):
        xy = (random.randint(0, width), random.randint(0, height))
        draw.point(xy, fill=(random.randint(50, 150),) * 3)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 36)
    except Exception:
        font = ImageFont.load_default()
    x = 30
    for char in code:
        y = random.randint(10, 30)
        draw.text((x, y), char, fill=(random.randint(0, 100),) * 3, font=font)
        x += 28
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


class CaptchaStartButton(discord.ui.Button):

    def __init__(self, role_id: int = None):
        custom_id = f"captcha_start_{role_id}" if role_id else "captcha_start_default"
        super().__init__(
            label="認証を開始する",
            style=discord.ButtonStyle.success,
            custom_id=custom_id,
        )
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        target_role_id = self.role_id
        if not target_role_id:
            custom_id = (interaction.data or {}).get("custom_id", "")
            parts = custom_id.split("_")
            if parts and parts[-1].isdigit():
                target_role_id = int(parts[-1])
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ サーバー内でのみ使用できます。", ephemeral=True
            )
            return
        target_role = (
            interaction.guild.get_role(target_role_id) if target_role_id else None
        )
        if not target_role:
            await interaction.response.send_message(
                "❌ 認証ロールが設定されていません。管理者にパネルの再作成を依頼してください。",
                ephemeral=True,
            )
            return
        if target_role in interaction.user.roles:
            await interaction.response.send_message(
                "ℹ️ すでに認証済みです！", ephemeral=True
            )
            return
        code = generate_captcha_code()
        image_bytes = create_captcha_image(code)
        file = discord.File(image_bytes, filename="captcha.png")
        view = CaptchaInputPromptView(target_role, code)
        await interaction.response.send_message(
            "下の画像に描かれている**5桁の英数字**を確認し、ボタンを押して入力してください：",
            file=file,
            view=view,
            ephemeral=True,
        )


class CaptchaPanelView(discord.ui.View):

    def __init__(self, role_id: int = None):
        super().__init__(timeout=None)
        self.role_id = role_id
        self.add_item(CaptchaStartButton(role_id))


class CaptchaInputPromptView(discord.ui.View):

    def __init__(self, role: discord.Role, correct_code: str):
        super().__init__(timeout=180)
        self.role = role
        self.correct_code = correct_code

    @discord.ui.button(
        label="コードを入力する", style=discord.ButtonStyle.primary, emoji="✍️"
    )
    async def open_modal(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        modal = CaptchaModal(self.role, self.correct_code)
        await interaction.response.send_modal(modal)


class CaptchaModal(discord.ui.Modal, title="CAPTCHA画像認証"):

    def __init__(self, role: discord.Role, correct_code: str):
        super().__init__()
        self.role = role
        self.correct_code = correct_code
        self.user_input = discord.ui.TextInput(
            label="画像の英数字を入力してください（大文字小文字区別）",
            placeholder="例: A3B9X",
            min_length=5,
            max_length=5,
            required=True,
        )
        self.add_item(self.user_input)

    async def on_submit(self, interaction: discord.Interaction):
        entered_text = self.user_input.value.strip()
        if entered_text == self.correct_code:
            try:
                await interaction.user.add_roles(self.role)
                await interaction.response.send_message(
                    "🎉 認証に成功しました！ロールが付与されました。", ephemeral=True
                )
            except Exception as e:
                await send_error_log(
                    interaction.guild,
                    "CAPTCHAロール付与失敗",
                    e,
                    f"対象ユーザー: {interaction.user.mention}",
                )
                await interaction.response.send_message(
                    "❌ ロール付与に失敗しました。管理者にお問い合わせください。",
                    ephemeral=True,
                )
        else:
            await interaction.response.send_message(
                "❌ 認証コードが違います。もう一度パネルのボタンからやり直してください。",
                ephemeral=True,
            )
