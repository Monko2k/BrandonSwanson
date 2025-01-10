import discord
import datetime
import pymongo
import asyncio
import json
from discord.ext import commands, tasks

with open("config.json") as f:
    config = json.loads(f.read())

intents = discord.Intents.all()
intents.message_content = True

client = discord.Client(intents=intents)
tree =  discord.app_commands.CommandTree(client)

mongoClient = pymongo.MongoClient("localhost", int(config["mongoPort"]))
db = mongoClient.BrandonSwanson.activity
guild = None
activeRole = None
managerRole = None
updateChannel = None

@client.event
async def on_ready():
    global guild
    global activeRole
    global updateChannel
    global managerRole
    await client.wait_until_ready()
    await tree.sync()
    guild = client.get_guild(int(config["guildId"]))
    activeRole = guild.get_role(int(config["activeRole"]))
    managerRole = guild.get_role(int(config["managerRole"]))
    updateChannel = guild.get_channel(int(config["updateChannel"]))
    print(f"Initialized")
    purge.start()

@tree.command(name="deactivate", description="Set a user as inactive")
@discord.app_commands.default_permissions(create_instant_invite=True)
async def deactivate(interaction: discord.Interaction, user: discord.User):
    await setInactive(user, interaction.user)
    await interaction.response.send_message(f"{user.name} was deactivated")

@tree.command(name="reactivate", description="Set a user as active")
@discord.app_commands.default_permissions(create_instant_invite=True)
async def reactivate(interaction: discord.Interaction, user: discord.User):
    await setActive(user, interaction.user)
    await interaction.response.send_message(f"{user.name} was reactivated")

@tree.command(name="reset", description="Reset active status for all users")
@discord.app_commands.default_permissions(administrator=True)
async def reset(interaction: discord.Interaction, user: discord.User):
    for member in guild.members:
        if not activeRole in member.roles:
            await member.add_roles(activeRole)
        update(member)
    await interaction.response.send_message("Set all users as active")

@tree.command(name="forceupdate", description="Force update all users")
@discord.app_commands.default_permissions(administrator=True)
async def forceupdate(interaction: discord.Interaction, date_offset: int = None):
    timestamp = None
    if date_offset is not None:
        timestamp = datetime.now() - datetime.timedelta(days=date_offset)

    for member in guild.members:
        update(member, timestamp)

    await interaction.response.send_message("Updated all users.")

@tree.command(name="purge", description="Manually run a purge")
@discord.app_commands.default_permissions(administrator=True)
async def reset(interaction: discord.Interaction, user: discord.User):
    await purge()
    await interaction.response.send_message("Manually ran purge")

@tree.command(name="clear", description="Clear #tempchannel")
@discord.app_commands.default_permissions(create_instant_invite=True)
async def clear(interaction: discord.Interaction):
    tempChannel = config["tempChannel"]
    if interaction.channel.id != int(tempChannel):
        await interaction.response.send_message(f"This command can only be used in <#{tempChannel}>")
    else:
        await interaction.response.defer()
        deleted = await interaction.channel.purge()
        await interaction.channel.send(content=f"Cleared {len(deleted)} messages", delete_after=10)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    update(message.author)

    if message.content == "brandon":
        await message.channel.send("bruh")

    if message.content.lower() == "brandon is bald":
        await message.channel.send("no im not")

    if message.channel.id == int(config["tempChannel"]):
        await asyncio.sleep(config["messageLifespanSeconds"])
        await message.delete()


@client.event
async def on_voice_state_update(member, before, after):
    update(member)

@client.event
async def on_member_join(member):
    await member.add_roles(activeRole)

@tasks.loop(hours=config["purgeIntervalHours"])
async def purge():
    return
    cutoff = datetime.datetime.now() - datetime.timedelta(hours=config["inactivityLimitHours"])
    cursor = db.find({})
    members = {}
    for document in cursor:
        members[document["_id"]] = document["timestamp"]

    for member in guild.members:
        if member.bot: continue
        if not activeRole in member.roles: continue
        if member.id in members:
            if members[member.id] < cutoff:
                await setInactive(member)
        else:
            await setInactive(member)

async def setInactive(member, caller=""):
    await member.remove_roles(activeRole)
    if caller:
        await updateChannel.send(f"{member.name} has been purged by {caller.mention}")
    else:
        await updateChannel.send(f"{member.name} has been purged for inactivity")

async def setActive(member, caller):
    await member.add_roles(activeRole)
    await updateChannel.send(f"{member.name} has been set as active by {caller.mention}")

def update(member, timestamp=None):
    if timestamp is None:
        timestamp = datetime.datetime.now()

    payload = { "timestamp": timestamp }

    db.update_one({ "_id": member.id }, { "$set": payload }, upsert=True)

client.run(config["discordKey"])
