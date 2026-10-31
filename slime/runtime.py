"""Single shared Discord client; importing this module never connects."""

import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)
