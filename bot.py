# bot.py
import os
from dotenv import load_dotenv

# 1
import discord
from discord.ext import commands

#import timedelta
import datetime
from datetime import timedelta

import asyncio

from aiostream import stream, pipe
import time


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# 2
bot = commands.Bot(command_prefix='!')

#---Constants
reactiontrigger = 1
inputchannel= 'general'
outputchannel= 'curator'
curatorintervals= 5 #time bwtween reaction checks
daystocheck=7#the maximun age of the messages to check



def curate(message): #takes the max number of reactions and compares it with the ractiontrigger value
    if message.attachments:#que tiene una imagen
        listNumberReactions= map(lambda m: m.count,message.reactions)
        #print(str(message.reactions))
        if message.reactions!=[]:
            reactions= max(listNumberReactions)
            #print(f'reacciones={reactions}')
            #print(f'Retorno la condicion, reactiontrigger <= reactions ={reactiontrigger <= reactions}')
            return (reactiontrigger <= reactions)
    return False

async def curateaction(ctx,message):
    channel = discord.utils.get(ctx.guild.channels, name=outputchannel)
    #shot=map(lambda m: m.url,message.attachments)
    await channel.send(f'Shot by {message.author}\n "{message.content}"\n{message.attachments[0].url}')
    

async def curateaction2(ctx,message):
    channel = discord.utils.get(ctx.guild.channels, name=outputchannel)
    #shot=map(lambda m: m.url,message.attachments)

    embed=discord.Embed(title=message.content,description=f"[Message link]({message.jump_url})")
    embed.set_image(url=message.attachments[0].url)
    embed.set_author(name= f'Shot by {message.author}', icon_url=message.author.avatar_url)
    #embed.set_author(name= f'Shot by {message.author}')
    #embed.set_thumbnail(url=message.author.avatar_url)
    embed.set_footer(text=f"{message.created_at}")

    await channel.send(embed=embed)


def candidatescheck(m,c):#devuelve si el mensaje (identidificado por la url) se encuentra en el iterador del candidato
    for mc in c:
        print(f'{m.id}=={mc.id}: {m.id==mc.id}')
        if m.id==mc.id:
            return True
    return False



@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')



@bot.command(name='setinputchannel', help='Define from what channel will the bot curate.')
async def setinputchannel(ctx, channelsName):
    global inputchannel
    inputchannel= channelsName

@bot.command(name='setoutputchannel', help='Define the channel where the curated messages will be sent.')
async def setoutputchannel(ctx, channelsName):
    global outputchannel
    outputchannel= channelsName

@bot.command(name='setreactiontrigger', help='Define the channel where the curated messages will be sent.')
async def setreactiontrigger(ctx, n):
    global reactiontrigger 
    reactiontrigger = n

@bot.command(name='setcuratorintervals', help='Define the time interval (in seconds) between reactions revisions.')
async def setcuratorintervals(ctx, s):
    global curatorintervals
    curatorintervals= s

@bot.command(name='setdaystocheck', help='Define the maximun age of the messages to check')
async def setdaystocheck(ctx, n):
    global daystocheck
    daystocheck= n



async def getlistcandidates(ctx):
    channel = discord.utils.get(ctx.guild.channels, name=inputchannel)

    candidates= channel.history(after=(datetime.datetime.now() - timedelta(days = 7)),oldest_first=True)
    listcandidates= await candidates.flatten()
    listcandidates= list(filter(lambda m: m.attachments and (not curate(m)), listcandidates))

    print(listcandidates)

    return listcandidates



async def getlistcandidatesupdate(ctx):
    channel = discord.utils.get(ctx.guild.channels, name=inputchannel)

    candidatesupdate= channel.history(after=(datetime.datetime.now() - timedelta(days = 7)),oldest_first=True)
    listcandidatesupdate= await candidatesupdate.flatten()
    listcandidatesupdate= list(filter(lambda m: curate(m), listcandidatesupdate))

    print(listcandidatesupdate)

    return listcandidatesupdate



@bot.command(name='startcurating', help='Start curating the shots from the past week in the curator\'s output channel')
async def startcurating(ctx):
    while True:

        listcandidates= await getlistcandidates(ctx)

        print('Esperando que reaccionen capturas...')
        await asyncio.sleep(curatorintervals)

        listcandidatesupdate= await getlistcandidatesupdate(ctx)
        
        for message in filter(lambda m: candidatescheck(m,listcandidates),listcandidatesupdate):
            await curateaction(ctx,message)
            print(f'Nice shot bro')



@bot.command(name='dawnoftimecuration', help='Curate a seted up channel since it was created.')
async def dawnoftime(ctx):
    channel = discord.utils.get(ctx.guild.channels, name=inputchannel) #ver si hay mejor forma de hacerlo
    async for message in channel.history(limit=200,oldest_first=True):
        if curate(message):
            await curateaction2(ctx,message)
            print(f'Nice shot bro')


bot.run(TOKEN)
