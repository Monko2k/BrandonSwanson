import discord
import datetime
import pymongo
import json
from discord.ext import commands, tasks

with open("config.json") as f:
    config = json.loads(f.read())

intents = discord.Intents.all()
intents.message_content = True

client = discord.Client(intents=intents)
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
    guild = client.get_guild(int(config["guildId"]))
    activeRole = guild.get_role(int(config["activeRole"]))
    managerRole = guild.get_role(int(config["managerRole"]))
    updateChannel = guild.get_channel(int(config["updateChannel"]))
    print(f"Initialized")
    purge.start()

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    update(message.author)

    if message.content == "brandon":
        await message.channel.send("bruh")

    if message.content.lower() == "brandon is bald":
        await message.channel.send("no im not")

    if message.content.startswith("&deactivate"):
        if not message.author.guild_permissions.administrator and not managerRole in message.author.roles:
            await message.channel.send("Nope")
            return
        if len(message.mentions) != 1:
            await message.channel.send("Tag one user to deactivate")
            return
        await setInactive(message.mentions[0])

    if message.content.startswith("&reactivate"):
        if not message.author.guild_permissions.administrator and not managerRole in message.author.roles:
            await message.channel.send("Nope")
            return
        if len(message.mentions) != 1:
            await message.channel.send("Tag one user to reactivate")
            return
        await setActive(message.mentions[0])


    if message.content == "&reset":
        if not message.author.guild_permissions.administrator:
            await message.channel.send("Fuck you")
            return

        for member in guild.members:
            if not activeRole in member.roles:
                await member.add_roles(activeRole)
            update(member)

        await message.channel.send("Set all users as active")

    if message.content == "&purge":
        if not message.author.guild_permissions.administrator:
            await message.channel.send("Fuck you")
            return

        await purge()
        await message.channel.send("Overrode and purged")


@client.event
async def on_voice_state_update(member, before, after):
    update(member)

@client.event
async def on_member_join(member):
    await member.add_roles(activeRole)

@tasks.loop(hours=config["purgeInterval"])
async def purge():
    await updateChannel.send("Purging inactive users")
    cutoff = datetime.datetime.now() - datetime.timedelta(hours=config["inactivityLimit"])
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
            setInactive(member)

async def setInactive(member):
    await member.remove_roles(activeRole)
    await updateChannel.send(f"{member.name} has been purged for inactivity")

async def setActive(member):
    await member.add_roles(activeRole)
    await updateChannel.send(f"{member.name} has been set as active")

def update(member):
    payload = {
        "timestamp": datetime.datetime.now()
    }

    db.update_one({ "_id": member.id }, { "$set": payload }, upsert=True)

client.run(config["discordKey"])

