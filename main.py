import discord,os,sys,random,requests
from discord.ext import commands

from dotenv import load_dotenv

load_dotenv()
TOKEN = 'ODQ3MTU4MTk2MzkyOTUxODA5.YK5_jQ.0gROilMU3FNn6jFs0yRFHzwEHFA'

client = discord.ext.commands.Bot("!")

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    print(client.users)

@client.command(pass_context=True)
async def getguild(ctx):
    id = ctx.message.guild.id
    print(id)


client.run(TOKEN)