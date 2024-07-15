import discord
from discord.ext import commands, tasks
import json
import shutil  # For file operations
import time
import asyncio
import re  # For regular expressions
from datetime import datetime
from typing import Union  # Import Union from typing module

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

# Paths for JSON files
MEMBERS_JSON_PATH = 'members.json'
WEB_MEMBERS_JSON_PATH = '/var/www/sop/backend/data/members.json'

# Create an instance of a bot with the specified intents and case insensitivity
bot = commands.Bot(command_prefix='!', intents=intents, case_insensitive=True)

# Store bot startup time
bot.startup_time = datetime.now()

# Event triggered when the bot is ready and connected to Discord
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="osu!"))
    print(f'Bot is online as {bot.user}')
    # Copy members.json to /var/www/sop/data/members.json on bot startup
    shutil.copy(MEMBERS_JSON_PATH, WEB_MEMBERS_JSON_PATH)
    print('Copied members.json to /var/www/sop/data/members.json on startup.')

# Debugging event to check if the bot is receiving commands
@bot.event
async def on_command(ctx):
    print(f'Command received: {ctx.message.content}')

# Command to check bot's latency
@bot.command()
async def ping(ctx):
    print('Ping command received')
    start_time = time.monotonic()
    message = await ctx.reply('Pong!')
    end_time = time.monotonic()
    latency_ms = round((end_time - start_time) * 1000)
    await message.edit(content=f'Pong! ({latency_ms} ms)')

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
    with open(MEMBERS_JSON_PATH, 'r') as f:
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

    with open(MEMBERS_JSON_PATH, 'w') as f:
        json.dump(data, f, indent=4)

    # Copy updated members.json to /var/www/sop/data/members.json
    shutil.copy(MEMBERS_JSON_PATH, WEB_MEMBERS_JSON_PATH)
    print('Copied members.json to /var/www/sop/data/members.json on update.')

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

    with open(MEMBERS_JSON_PATH, 'r') as f:
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
                with open(MEMBERS_JSON_PATH, 'w') as f:
                    json.dump(data, f, indent=4)
                # Copy updated members.json to /var/www/sop/data/members.json
                shutil.copy(MEMBERS_JSON_PATH, WEB_MEMBERS_JSON_PATH)
                print('Copied members.json to /var/www/sop/data/members.json on update.')

                if str(ctx.author.id) == str(target_id):
                    await ctx.reply('You have been removed from our website members list.')
                else:
                    await ctx.reply(f'Removed user with Discord ID {target_id} from our website members list.')
                return

    await ctx.reply('User not found in our website members list.')

@bot.command()
async def createreactionroles(ctx, channel_or_title: str, *args):
    # Initialize variables
    channel_id = None
    title = None
    color = None
    role_pairs = []

    # Check if the first argument is a channel ID
    if channel_or_title.isdigit() and len(channel_or_title) == 18:
        channel_id = int(channel_or_title)
    else:
        title = channel_or_title

    # Process remaining arguments
    for arg in args:
        # Check if argument is a title
        if title is None and arg.startswith('"') and arg.endswith('"'):
            title = arg[1:-1]
        # Check if argument is a color
        elif color is None and arg.startswith('#') and re.match(r'^#[0-9a-fA-F]{6}$', arg):
            color = arg
        # Check if argument is a role or emoji pair
        elif arg.startswith('<@&') and arg.endswith('>'):
            role_pairs.append(arg)
        elif arg.startswith(':') and arg.endswith(':'):
            role_pairs.append(arg)
        else:
            await ctx.reply(f"Invalid argument: {arg}")

    # Validate required parameters
    if not channel_id:
        await ctx.reply('Please provide a valid channel ID.')
        return
    if not title:
        await ctx.reply('Please provide a title for the reaction roles message.')
        return
    if not color:
        await ctx.reply('Please provide a valid color in hex format (e.g., #c249ff).')
        return
    if not role_pairs:
        await ctx.reply('Please provide at least one role-emoji pair.')
        return

    # Convert color to integer representation
    color = int(color.lstrip('#'), 16)

    # Fetch the target channel based on provided channel_id or use current channel
    target_channel = ctx.guild.get_channel(channel_id) if channel_id else ctx.channel

    # Create embed
    embed = discord.Embed(title=title, color=color)
    embed.set_footer(text="React to this message to get the corresponding role")

    description = ""
    for item in role_pairs:
        description += f"{item}\n"
    embed.description = description

    try:
        message = await target_channel.send(embed=embed)

        # React to the message with emojis
        for item in role_pairs:
            await message.add_reaction(item)

    except discord.errors.HTTPException as e:
        await ctx.reply(f"Failed to create reaction roles message: {e}")
        return

    await ctx.reply('Reaction roles message created successfully.')

# Command to add reaction roles to an existing message
@bot.command()
async def addreactionroles(ctx, message_id: int, *role_pairs):
    if not any(role.id == ROLE_IDS["Moderator"] for role in ctx.author.roles):
        await ctx.reply("You do not have permission to use this command.")
        return

    # Fetch the message object
    try:
        message = await ctx.channel.fetch_message(message_id)
    except discord.NotFound:
        await ctx.reply(f"Message with ID {message_id} not found in this channel.")
        return

    parsed_role_pairs = []
    for role_pair in role_pairs:
        role_pair = role_pair.strip()  # Remove leading and trailing whitespace
        match = re.match(r'(<a?:\w+:\d+>|:\w+:)\s*<@&(\d+)>', role_pair)
        if match:
            parsed_role_pairs.append((match.group(1), match.group(2)))
        else:
            await ctx.reply(f'Invalid format for role pair: {role_pair}\n'
                            'Please use the format ":emoji: @role".\n'
                            'Usage: !addreactionroles (message_id) :emoji: @role :emoji: @role')
            return

    # Add reactions to the message
    for emoji, _ in parsed_role_pairs:
        await message.add_reaction(emoji)

    # Update reaction roles data (if needed)
    try:
        with open('reaction_roles.json', 'r') as f:
            reaction_roles_data = json.load(f)
    except FileNotFoundError:
        reaction_roles_data = {}

    reaction_roles_data[str(message.id)] = {
        'channel_id': message.channel.id,
        'role_pairs': parsed_role_pairs
    }

    with open('reaction_roles.json', 'w') as f:
        json.dump(reaction_roles_data, f, indent=4)

    # No reply here to indicate success

# Command to remove reaction roles from an existing message
@bot.command()
async def removereactionroles(ctx, message_id: int):
    if not any(role.id == ROLE_IDS["Moderator"] for role in ctx.author.roles):
        await ctx.reply("You do not have permission to use this command.")
        return

    # Fetch the message object
    try:
        message = await ctx.channel.fetch_message(message_id)
    except discord.NotFound:
        await ctx.reply(f"Message with ID {message_id} not found in this channel.")
        return

    # Clear all reactions from the message
    await message.clear_reactions()

    # Update reaction roles data (if needed)
    try:
        with open('reaction_roles.json', 'r') as f:
            reaction_roles_data = json.load(f)
    except FileNotFoundError:
        reaction_roles_data = {}

    if str(message.id) in reaction_roles_data:
        del reaction_roles_data[str(message.id)]

    with open('reaction_roles.json', 'w') as f:
        json.dump(reaction_roles_data, f, indent=4)

    # No reply here to indicate success

# Command to check bot's uptime
@bot.command()
async def uptime(ctx):
    delta = datetime.now() - bot.startup_time
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Construct the uptime message
    uptime_msg = "Uptime: "

    # Conditional formatting based on elapsed time
    if days > 0:
        uptime_msg += f"{days}d "
    if hours > 0:
        uptime_msg += f"{hours}h "
    if minutes > 0:
        uptime_msg += f"{minutes}m "
    uptime_msg += f"{seconds}s"

    await ctx.send(uptime_msg)

# Run the bot with the provided token
bot.run(TOKEN)
