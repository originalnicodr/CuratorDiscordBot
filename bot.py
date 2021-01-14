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

import traceback
import sys


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# 2
bot = commands.Bot(command_prefix='!')


#----------Funcion separada en dos para debugging, despues juntar--------

def getchannelo(channelname):#not the best method to do this tho
    #print(list(discord.Client.guilds))
    #for g in list(discord.Client.guilds):

    for g in bot.guilds:
        if g.name== 'BotTest':
        #if g.name== 'FRAMED - Screenshot Community':
            return discord.utils.get(g.channels, name=channelname)

def getchanneli(channelname):#not the best method to do this tho
    #print(list(discord.Client.guilds))
    #for g in list(discord.Client.guilds):

    for g in bot.guilds:
        if g.name== 'BotTest':
        #if g.name== 'FRAMED - Screenshot Community':
            return discord.utils.get(g.channels, name=channelname)
#--------------------------------------

#------------Constants-----------------
reactiontrigger = 1
curatorintervals= 5 #time bwtween reaction checks
daystocheck=7#the maximun age of the messages to check

inputchannel=None
outputchannel=None
#---------------------------------------


#-------Curate algorithms-----------


#Takes the max number of reactions and compares it with the ractiontrigger value
def curate(message): 
    if message.attachments:#que tiene una imagen
        listNumberReactions= map(lambda m: m.count,message.reactions)
        #print(str(message.reactions))
        if message.reactions!=[]:
            reactions= max(listNumberReactions)
            #print(f'reacciones={reactions}')
            #print(f'Retorno la condicion, reactiontrigger <= reactions ={reactiontrigger <= reactions}')
            return (reactiontrigger <= reactions)
    return False

#-------------------------------------


#--------------------------Curation action functions
async def curateaction(ctx,message):
    await outputchannel.send(f'Shot by {message.author}\n "{message.content}"\n{message.attachments[0].url}')
    

async def curateaction2(ctx,message):
    gamename=message.content

    if not gamename:
        print('Buscando nombre del juego')
        gamename= await getgamename(ctx,message)


    embed=discord.Embed(title=gamename,description=f"[Message link]({message.jump_url})")
    embed.set_image(url=message.attachments[0].url)
    embed.set_author(name= f'Shot by {message.author}', icon_url=message.author.avatar_url)
    #embed.set_author(name= f'Shot by {message.author}')
    #embed.set_thumbnail(url=message.author.avatar_url)
    embed.set_footer(text=f"{message.created_at}")

    await outputchannel.send(embed=embed)
#----------------------------------------------------

#----------Aux Functions----------------------------------

def timedifabs(d1,d2):
    if d1-d2<timedelta(days = 0):
        return d2-d1
    return d1-d2

async def getgamename(ctx,message):#checks five messages before and after the message to see if it finds the name of the game
    messages=  inputchannel.history(around=message.created_at,oldest_first=True, limit=10)
    listmessages= await messages.flatten()
    #listmessages= list(filter(lambda m: m.content and (m.author==message.author), listmessages))
    listmessages= list(listmessages)
    #print(listmessages)

    listmessages= list(filter(lambda m: m.content and (m.author==message.author), listmessages))


    placeholdermessage= listmessages[0]
    #print(listmessages)
    #print(f'tiempo del mensaje principal:{message.created_at}')
    for m in listmessages:
        if  timedifabs(placeholdermessage.created_at,message.created_at) > timedifabs(m.created_at,message.created_at):#no necesito hacer m!=message por que message no tiene content y se filtro antes
            placeholdermessage=m
    
    return placeholdermessage.content

#Devuelve si el mensaje (identidificado por la url) se encuentra en el iterador del candidato
def candidatescheck(m,c):
    for mc in c:
        print(f'{m.id}=={mc.id}: {m.id==mc.id}')
        if m.id==mc.id:
            return True
    return False

async def getlistcandidates(ctx):
    global inputchannel
    candidates= inputchannel.history(after=(datetime.datetime.now() - timedelta(days = daystocheck)),oldest_first=True,limit=None)
    listcandidates= await candidates.flatten()
    #print(f'listcandidates.len= {len(listcandidates)}')
    listcandidates= list(filter(lambda m: m.attachments and (not curate(m)), listcandidates))

    #print(listcandidates)

    return listcandidates



async def getlistcandidatesupdate(ctx):
    candidatesupdate= inputchannel.history(after=(datetime.datetime.now() - timedelta(days = daystocheck)),oldest_first=True,limit=None)
    listcandidatesupdate= await candidatesupdate.flatten()
    #print(f'listcandidatesupdate.len= {len(listcandidatesupdate)}')
    listcandidatesupdate= list(filter(lambda m: curate(m), listcandidatesupdate))

    #print(listcandidatesupdate)

    return listcandidatesupdate


#--------------------------------------------------------------------


#---------Events---------------------------------
@bot.event
async def on_ready():
    global inputchannel
    global outputchannel
    print(f'{bot.user.name} has connected to Discord!')
    inputchannel=getchanneli('share-your-shot-bot')
    outputchannel=getchannelo('curator-bot')

#Commands can only be done in the outputchannel
@bot.check
async def predicate(ctx):
    return ctx.channel.name==outputchannel.name

#Allows me to keep using other commands after the check above fails
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        pass
    else:
        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

#-------------------------------------------------


#-----------------Commands-------------------------

class BotActions(commands.Cog):
    """Diferent type of curations the bot can make"""

    
    @commands.command(name='startcurating', help='Start curating the shots from the past week in the curator\'s output channel')
    async def startcurating(self,ctx):
        while True:

            listcandidates= await getlistcandidates(ctx)

            print('Esperando que reaccionen capturas...')
            await asyncio.sleep(curatorintervals)

            listcandidatesupdate= await getlistcandidatesupdate(ctx)

            for message in filter(lambda m: candidatescheck(m,listcandidates),listcandidatesupdate):
                await curateaction2(ctx,message)
                print(f'Nice shot bro')

    @commands.command(name='dawnoftimecuration', help='Curate a seated up channel since it was created.')
    async def dawnoftime(self,ctx):
        async for message in inputchannel.history(limit=None,oldest_first=True):
            if curate(message):
                await curateaction2(ctx,message)
                print(f'Nice shot bro')

    @commands.command(name='curationsince', help='Curate a seated up channel since a specific number of days.')
    async def curationsince(self,ctx,d):
        async for message in inputchannel.history(after=(datetime.datetime.now() - timedelta(days = d)),oldest_first=True,limit=None):
            if curate(message):
                await curateaction2(ctx,message)
                print(f'Nice shot bro')

bot.add_cog(BotActions())

"""

@bot.command(name='startcurating', help='Start curating the shots from the past week in the curator\'s output channel')
async def startcurating(ctx):
    while True:

        listcandidates= await getlistcandidates(ctx)

        print('Esperando que reaccionen capturas...')
        await asyncio.sleep(curatorintervals)

        listcandidatesupdate= await getlistcandidatesupdate(ctx)
        
        for message in filter(lambda m: candidatescheck(m,listcandidates),listcandidatesupdate):
            await curateaction2(ctx,message)
            print(f'Nice shot bro')
    
@bot.command(name='dawnoftimecuration', help='Curate a seated up channel since it was created.')
async def dawnoftime(ctx):
    async for message in inputchannel.history(limit=None,oldest_first=True):
        if curate(message):
            await curateaction2(ctx,message)
            print(f'Nice shot bro')

@bot.command(name='curationsince', help='Curate a seated up channel since a specific number of days.')
async def curationsince(ctx,d):
    async for message in inputchannel.history(after=(datetime.datetime.now() - timedelta(days = d)),oldest_first=True,limit=None):
        if curate(message):
            await curateaction2(ctx,message)
            print(f'Nice shot bro')
"""



class ConfigCommands(commands.Cog):
    """Configuration of the curation commands"""

    @commands.command(name='setinputchannel', help='Define from what channel will the bot curate.')
    async def setinputchannel(self,ctx, channelsName):
        global inputchannel
        inputchannel= getchanneli(channelsName)

    @commands.command(name='setoutputchannel', help='Define the channel where the curated messages will be sent.')
    async def setoutputchannel(self,ctx, channelsName):
        global outputchannel
        outputchannel= getchannelo(channelsName)

    @commands.command(name='setreactiontrigger', help='Define the amount of reactions necessary to accept the message.')
    async def setreactiontrigger(self,ctx, n):
        global reactiontrigger 
        reactiontrigger = int(n)

    @commands.command(name='setcuratorintervals', help='Define the time interval (in seconds) between reactions revisions.')
    async def setcuratorintervals(self,ctx, s):
        global curatorintervals
        curatorintervals= int(s)

    @commands.command(name='setdaystocheck', help='Define the maximum age of the messages to check')
    async def setdaystocheck(self,ctx, n):
        global daystocheck
        daystocheck= int(n)

bot.add_cog(ConfigCommands())

#--------------------------------------------------

bot.run(TOKEN)
