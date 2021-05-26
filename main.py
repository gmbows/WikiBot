import discord,os,sys,random,requests
from discord.ext import commands

from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

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