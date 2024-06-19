import discord
from discord.ext import commands
import json
import re
import time
from datetime import datetime

# Use the provided token
TOKEN = 'MTIzNjE0MzgzNTM4MjI4NDM0MA.GmgbKN.xlG44fdqyKodmXTA3CbuVwtYKtPN5619otq7nM'

# Set up the intents
intents = discord.Intents.default()
intents.message_content = True  # Enable the intent to read message content (required for command handling)
intents.messages = True
intents.guilds = True
intents.members = True

# Channel ID where commands should be restricted
ALLOWED_CHANNEL_ID = 1252657982572073050

# Role IDs for Owner, Moderator, and Content Manager
ROLE_IDS = {
    "Owner": 994947833931235421,
    "Moderator": 1163949337777275020,
    "Content Manager": 1200081565787639848
}

# Default status for members without specific roles
DEFAULT_STATUS = "member"

# Create an instance of a bot with the specified intents and case insensitivity
bot = commands.Bot(command_prefix='!', intents=intents, case_insensitive=True)

# Start time of the bot session
start_time = time.time()

# Event triggered when the bot is ready and connected to Discord
@bot.event
async def on_ready():
    await update_presence()
    print(f'Bot is online as {bot.user}')

# Update bot presence with custom status
async def update_presence():
    activity = discord.Activity(name="osu!", type=discord.ActivityType.playing)
    await bot.change_presence(activity=activity)

# Debugging event to check if the bot is receiving commands
@bot.event
async def on_command(ctx):
    print(f'Command received: {ctx.message.content}')

# A simple command to test if the bot is working
@bot.command()
async def ping(ctx):
    print('Ping command received')
    await ctx.reply('Pong!')

# Command to register a user with osu! ID and roles-based status
@bot.command()
async def register(ctx, *args):
    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        await ctx.reply(f'Commands are restricted to <#{ALLOWED_CHANNEL_ID}> channel.')
        return

    if len(args) < 1:
        await ctx.reply('Please provide an osu! ID.')
        return

    osu_id = args[0]
    if not osu_id.isdigit():
        await ctx.reply('osu! ID should be a number.')
        return

    osu_id = int(osu_id)
    member = ctx.author
    guild = ctx.guild

    # Check if the user is already registered by osu! ID or Discord ID
    with open('members.json', 'r') as f:
        data = json.load(f)

    for user_id, info in data['members'].items():
        if info.get('osu_id') == osu_id:
            await ctx.reply('You are already registered.')
            return
        if info.get('discord_id') == str(member.id):
            await ctx.reply('You are already registered.')
            return

    # Determine user's highest priority role and corresponding status
    if guild.get_role(ROLE_IDS["Owner"]) in member.roles:
        highest_priority_status = "owner"
    elif guild.get_role(ROLE_IDS["Moderator"]) in member.roles:
        highest_priority_status = "moderator"
    elif guild.get_role(ROLE_IDS["Content Manager"]) in member.roles:
        highest_priority_status = "content_manager"
    else:
        highest_priority_status = DEFAULT_STATUS

    # Fetch username (not nickname)
    username = member.name

    # Add or update member data
    data['members'][str(member.id)] = {
        'osu_id': osu_id,
        'discord_id': str(member.id),
        'username': username,
        'status': highest_priority_status
    }

    with open('members.json', 'w') as f:
        json.dump(data, f, indent=4)

    await ctx.reply(f'User {member.name} registered with osu! ID {osu_id} and status {highest_priority_status}')

# Command to remove a user from the registration JSON
@bot.command()
async def remove(ctx, target_id: str = None):
    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        await ctx.reply(f'Commands are restricted to <#{ALLOWED_CHANNEL_ID}> channel.')
        return

    member = ctx.author
    guild = ctx.guild

    # Check if the user is a moderator
    is_moderator = ctx.author.guild_permissions.administrator or any(role.id == ROLE_IDS["Moderator"] for role in ctx.author.roles)

    if target_id is None:
        target_id = str(member.id)  # Default to the user's own Discord ID if no target ID is provided

    with open('members.json', 'r') as f:
        data = json.load(f)

    # If target_id is a mention, extract the user ID
    if target_id.startswith('<@') and target_id.endswith('>'):
        target_id = re.findall(r'\d+', target_id)[0]

    # Only allow moderators to remove another user by providing their ID
    if not is_moderator and str(ctx.author.id) != target_id:
        await ctx.reply("You do not have permission to remove another user.")
        return

    # Remove the user from the registration list
    if target_id.isdigit():
        target_id = int(target_id)
        for user_id, info in list(data['members'].items()):
            if info.get('discord_id') == str(target_id):
                del data['members'][user_id]
                with open('members.json', 'w') as f:
                    json.dump(data, f, indent=4)
                if str(ctx.author.id) == str(target_id):
                    await ctx.reply('You have been removed from our website members list.')
                else:
                    await ctx.reply(f'Removed user with Discord ID {target_id} from our website members list.')
                return

    await ctx.reply('User not found in our website members list.')

# Command to get the current session duration
@bot.command()
async def session(ctx):
    current_time = time.time()
    session_duration = current_time - start_time
    minutes, seconds = divmod(session_duration, 60)
    hours, minutes = divmod(minutes, 60)

    await ctx.reply(f'Current session duration: {int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds.')

# Keep the bot running
bot.run(TOKEN)

