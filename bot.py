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

from aiostream import stream
import time


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# 2
bot = commands.Bot(command_prefix='!')

reactiontrigger = 1
inputchannel= 'general'
outputchannel= 'curator'
curatorintervals= 5

candidates=[]

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
    

async def candidatescheck(m,c):#devuelve si el mensaje (identidificado por la url) se encuentra en el iterador del candidato
    async for mc in c:
        print(m.id==mc.id)
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

"""
@bot.command(name='startcurating', help='Start curating the shots from the past week in the curator\'s output channel')
async def startcurating(ctx):
    #se puede cambiar la cantidad de dias en las que se fija para atras
    global candidates
    channel = discord.utils.get(ctx.guild.channels, name=inputchannel) #ver si hay mejor forma de hacerlo
    candidates= channel.history(after=(datetime.datetime.now() - timedelta(days = 7)),oldest_first=True)#.filter(lambda m: m.attachments and (not curate(m)))#candidatos "viejos"

    lstcandidates = await stream.list(candidates)
    lstcandidates= filter(lambda m: m.attachments and (not curate(m)),lstcandidates)

    #async for m in candidates:#debug
    #    print(m.attachments[0].url)
        

    while True:
        
        candidatesupdate= channel.history(after=(datetime.datetime.now() - timedelta(days = 7)),oldest_first=True)#.filter(lambda m : curate(m))

        lstcandidatesupdate= await stream.list(candidatesupdate)
        lstcandidatesupdate=filter(curate, lstcandidatesupdate)
        

        topost=  list(set(lstcandidates) & set(lstcandidatesupdate))  #me va a dar vacio probablemente

        print(f'topost={topost}')
        print(f'lstcandidatesupdate={lstcandidatesupdate}')
        print(f'lstcandidates={lstcandidates}')

        async for message in candidatesupdate:
            #if message.author != client.user:
            if message in topost:
                await curateaction(ctx,message)
                print(f'Nice shot bro')
        
        lstcandidates= filter(lambda m: m.attachments and (not curate(m)),await stream.list(channel.history(after=(datetime.datetime.now() - timedelta(days = 7)),oldest_first=True)))#.filter(lambda m : not curate(m)))#candidatos "viejos"
        print('Esperando que reaccionen capturas...')
        await asyncio.sleep(curatorintervals)
"""

@bot.command(name='startcurating', help='Start curating the shots from the past week in the curator\'s output channel')
async def startcurating(ctx):
    #se puede cambiar la cantidad de dias en las que se fija para atras
    #global candidates
    channel = discord.utils.get(ctx.guild.channels, name=inputchannel) #ver si hay mejor forma de hacerlo
    candidates= channel.history(after=(datetime.datetime.now() - timedelta(days = 7)),oldest_first=True).filter(lambda m: m.attachments and (not curate(m)))#candidatos "viejos"
    
    #async for m in candidates:#debug
    #    print(f'checheko de debugging: {curate(m)}')

    candidatesupdate= channel.history(after=(datetime.datetime.now() - timedelta(days = 7)),oldest_first=True).filter(lambda m : curate(m))

    while True:

        #candidatesupdate= channel.history(after=(datetime.datetime.now() - timedelta(days = 7)),oldest_first=True).filter(lambda m : curate(m))
        #me avisa cuales son los candidatos que pueden publicarse
        
        async for m in candidatesupdate:#debug
            print(f'Reviso candidatesupdate: {m.id}')

        async for m in candidates:#debug
            print(f'Reviso candidates: {m.id}')



        async for message in candidates.filter(lambda m: candidatescheck(m,candidatesupdate)):#se fija si de su lista de candidatos que no publico si alguno se puede publicar ahora
            #if message.author != client.user:
            await curateaction(ctx,message)
            print(f'Nice shot bro')
        
        await asyncio.gather(
        candidates= channel.history(after=(datetime.datetime.now() - timedelta(days = 7)),oldest_first=True).filter(lambda m: m.attachments and (not curate(m))),#candidatos "viejos"
        print('Esperando que reaccionen capturas...'),
        await asyncio.sleep(curatorintervals),
        candidatesupdate= channel.history(after=(datetime.datetime.now() - timedelta(days = 7)),oldest_first=True).filter(lambda m : curate(m)))
        


"""
@bot.event
async def on_message(message):
    global candidates
    if message.channel.name==inputchannel and message.attachments!=[]:
        candidates.append(message)
"""


@bot.command(name='dawnoftimecuration', help='Curate a seted up channel since it was created.')
async def dawnoftime(ctx):
    channel = discord.utils.get(ctx.guild.channels, name=inputchannel) #ver si hay mejor forma de hacerlo
    async for message in channel.history(limit=200,oldest_first=True):
        #if message.author != client.user:
        if curate(message):
            await curateaction(ctx,message)
            print(f'Nice shot bro')


bot.run(TOKEN)