import discord
from discord.ext import commands
import json
import os

# Load or initialize the data file
data_file = 'data.json'
if os.path.exists(data_file):
    with open(data_file, 'r') as f:
        data = json.load(f)
else:
    data = {}

# Initialize the bot
bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}')

@bot.command()
async def register(ctx, osu_id: int):
    user_id = str(ctx.author.id)
    data[user_id] = osu_id
    with open(data_file, 'w') as f:
        json.dump(data, f, indent=4)
    await ctx.send(f'Registered osu! ID {osu_id} for user {ctx.author.mention}')

# Run the bot
bot.run('MTIzNjE0MzgzNTM4MjI4NDM0MA.GmgbKN.xlG44fdqyKodmXTA3CbuVwtYKtPN5619otq7nM')
