# bot.py

#--------Modules---------------------------
import os
from dotenv import load_dotenv

import discord
from discord.ext import commands

import datetime
from datetime import timedelta

import asyncio

import time

import traceback
import sys

import functools
import operator

from tinydb import TinyDB, Query

from git import Repo




from PIL import Image, ImageFilter
import requests

#-----------------------------------------------

#--------------------Enviroment variables--------
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GIT_TOKEN= os.getenv('GIT_TOKEN')
#-----------------------------------------------

bot = commands.Bot(command_prefix='!')


#------------Constants-----------------

#For basicCuration
#Updated in the startcurating() loop and on the on_ready() event, comment those lines if you dont want this value to get modified
reactiontrigger = 25

curatorintervals= 5 #time bwtween reaction checks
daystocheck=7#the maximun age of the messages to check


curationlgorithmpast= lambda m : historicalCuration(m)
curationlgorithm= lambda m :  basicCuration(m)

#Curation Algorithms:
# basicCuration(m)
# historicalCuration(m)
# extendedCuration(m)
# completeCuration(m)



#Users that dont want to be on the site, specified by their id (author.id)
ignoredusers=[]


#initial values are set in the on_ready() event
inputchannel=None
outputchannel=None

#---------------------------------------

#-----------Github integration --------------------------


websiterepourl = f'https://githubuser:{GIT_TOKEN}@github.com/repo-owner/repo.git'
websiterepofolder = 'websiterepo'

repo = Repo.clone_from(websiterepourl, websiterepofolder)
assert repo.__class__ is Repo

#database for using the shots in a website
db = TinyDB('websiterepo/shotsdb.json')

def dbgitupdate():
    global repo
    repo.git.add('shotsdb.json')
    repo.index.commit("DB update")

    repo = Repo(websiterepofolder)
    origin = repo.remote(name="origin")
    origin.push()

def dbreactionsupdate(message):
    updatedscore= max(map(lambda m: m.count,message.reactions))#the list shouldnt be empty
    db.update({'score': updatedscore}, Query().shotUrl == message.attachments[0].url)

#-------------------------------------------------------------

#-----------Thumbnail creation--------------------------
sizelimit= 400 #discord standar

#initial value is set in the on_ready() event
thumbnailchannel=None


async def createthumbnail(message):
    response = requests.get(message.attachments[0].url, stream=True)
    response.raw.decode_content = True
    shot=Image.open(response.raw)

    h=message.attachments[0].height
    w=message.attachments[0].width
    ar=w/h

    #Discord method
    """
    ht= sizelimit if h>w else int(ar*sizelimit)
    wt= sizelimit if w>h else int((1/ar)*sizelimit)
    """

    #Flickr method
    ht= sizelimit
    wt= int(ar*sizelimit)
    print(f'ht:{ht} wt:{wt}, (1/ar):{1/ar}')


    shot=shot.convert('RGB')#to save it in jpg
    shot=shot.filter(ImageFilter.SHARPEN)
    
    #filter algorithms
    #Image.NEAREST, Image.BILINEAR, Image.BICUBIC, Image.ANTIALIAS
    shot=shot.resize((wt,ht),Image.BICUBIC)
    
    shot.save('thumbnailtemp.jpg',quality=95)
    thumbnail= await thumbnailchannel.send(file=discord.File('thumbnailtemp.jpg'))
    return thumbnail.attachments[0].url

#--------------------------------------------------------


#-------Curation algorithms-----------

#Takes the max number of reactions and compares it with the ractiontrigger value
def basicCuration(message): 
    if message.attachments:
    
        listNumberReactions= map(lambda m: m.count,message.reactions)
        if message.reactions!=[]:
            reactions= max(listNumberReactions)
            return (reactiontrigger <= reactions)
    return False

#Takes the max number of reactions and compares it with a ractiontrigger value that varies based on the time where the shot was posted
def historicalCuration(message): 

    #for some reason outputchannel.created_at gives a wrong date, so we will be using 2019-02-26
    channelscreationdate= datetime.datetime.strptime('2019-02-26','%Y-%m-%d')

    #Minnimun and maximun values that are used in the linear interpolation
    minv=10
    maxv=reactiontrigger

    if message.attachments:
        listNumberReactions= map(lambda m: m.count,message.reactions)
        if message.reactions!=[]:
            
            #how new is the message from 0 to 1
            valueovertime=(message.created_at-channelscreationdate).days/(datetime.datetime.now()-channelscreationdate).days
            

            #linearinterpolation
            trigger = (valueovertime * maxv) + ((1-valueovertime) * minv)
            print(f'Trigger value={trigger}')

            reactions= max(listNumberReactions)
            return (trigger <= reactions)
    return False


def extendedCuration(message): 
    if message.attachments:

        #How much do the other emojis "weight" to the final number
        secondvalue=0.2
    
        listNumberReactions= list(map(lambda m: m.count,message.reactions))
        if message.reactions!=[]:

            premessagevalue= max(listNumberReactions)#value of the emoji with biggest amount of reactions
            messagevalue= premessagevalue +  functools.reduce(operator.add, list(map(lambda r: r*secondvalue,listNumberReactions)),0) - premessagevalue*secondvalue


            
            print(f'premessagevalue + fold list - premessagevalue*0.2={premessagevalue} + {functools.reduce(operator.add, list(map(lambda r: r*secondvalue,listNumberReactions)),0) } - {premessagevalue*secondvalue}')

            print(f'Reactiontrigger={reactiontrigger} <=messagevalue={messagevalue}')
            return (reactiontrigger <= messagevalue)
    return False


def completeCuration(message): 
    if message.attachments:

        #for some reason outputchannel.created_at gives a wrong date, so we will be using 2019-02-26
        channelscreationdate= datetime.datetime.strptime('2019-02-26','%Y-%m-%d')

        #Minnimun and maximun values that are used in the linear interpolation
        minv=15
        maxv=25

        #How much do the other emojis weight
        secondvalue=0.2
    
        listNumberReactions= list(map(lambda m: m.count,message.reactions))
        if message.reactions!=[]:

            valueovertime=(message.created_at-channelscreationdate).days/(datetime.datetime.now()-channelscreationdate).days
            trigger = (valueovertime * maxv) + ((1-valueovertime) * minv)

            premessagevalue= max(listNumberReactions)#value of the emoji with biggest amount of reactions
            messagevalue= premessagevalue +  functools.reduce(operator.add, list(map(lambda r: r*secondvalue,listNumberReactions)),0) - premessagevalue*secondvalue

            print(f'Trigger value={trigger} <=messagevalue={messagevalue}')

            return (trigger <= messagevalue)
    return False

#-------------------------------------


#------------Curation action functions--------------
async def postembed(message,gamename):
    embed=discord.Embed(title=gamename,description=f"[Message link]({message.jump_url})")
    embed.set_image(url=message.attachments[0].url)
    embed.set_author(name= f'Shot by {message.author}', icon_url=message.author.avatar_url)
    #embed.set_author(name= f'Shot by {message.author}')
    #embed.set_thumbnail(url=message.author.avatar_url)
    embed.set_footer(text=f"{message.created_at}")

    await outputchannel.send(embed=embed)


async def writedbdawnoftime(message,gamename):
    if message.author.id in ignoredusers:
        return
    thumbnail= await createthumbnail(message) #link of the thumbnail
    elementid=len(db)+1
    db.insert({'gameName': gamename, 'shotUrl': message.attachments[0].url, 'height': message.attachments[0].height, 'width': message.attachments[0].width, 'thumbnailUrl': thumbnail ,'author': message.author.name, 'authorsAvatarUrl': str(message.author.avatar_url), 'date': message.created_at.strftime('%Y-%m-%dT%H:%M:%S.%f'), 'score': max(map(lambda m: m.count,message.reactions)), 'ID': elementid, 'iteratorID': int(message.created_at.timestamp())})
    

#instead of using the date of the message it uses the actual time, that way if you sort by new in the future website, the new shots would always be on top, instead of getting mixed
async def writedb(message,gamename):
    if message.author.id in ignoredusers:
        return
    thumbnail= await createthumbnail(message) #link of the thumbnail
    elementid=len(db)+1
    db.insert({'gameName': gamename, 'shotUrl': message.attachments[0].url, 'height': message.attachments[0].height, 'width': message.attachments[0].width, 'thumbnailUrl': thumbnail ,'author': message.author.name, 'authorsAvatarUrl': str(message.author.avatar_url), 'date': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f'), 'score': max(map(lambda m: m.count,message.reactions)), 'ID': elementid, 'iteratorID': int(datetime.datetime.now().timestamp())})
    #dbgitupdate()

async def curateaction(message):
    gamename= await getgamename(message)
    await writedb(message,gamename)
    await postembed(message,gamename)


async def curateactiondawnoftime(message):
    gamename= await getgamename(message)
    await postembed(message,gamename)
    await writedbdawnoftime(message,gamename)

    #----------------For forcing post actions-------------------

async def postembedexternal(message,gamename):
    embed=discord.Embed(title=gamename,description=f"[Message link]({message.jump_url})")
    embed.set_image(url=message.content)
    embed.set_author(name= f'Shot by {message.author}', icon_url=message.author.avatar_url)
    #embed.set_author(name= f'Shot by {message.author}')
    #embed.set_thumbnail(url=message.author.avatar_url)
    embed.set_footer(text=f"{message.created_at}")

    await outputchannel.send(embed=embed)

#external shots wont be added to the page
"""
async def writedbexternal(message,gamename):
    if message.author.id in ignoredusers:
        return
    db.insert({'gameName': gamename, 'shotUrl': message.content, 'author': message.author.name, 'authorsAvatarUrl': str(message.author.avatar_url), 'date': message.created_at.strftime('%Y-%m-%dT%H:%M:%S.%f'), 'score': max(map(lambda m: m.count,message.reactions))})
"""

async def curateactionexternal(message):
    #await writedbexternal(message,'')
    await postembedexternal(message,'')

    #--------------------------------------------------------

#----------------------------------------------------

#----------Aux Functions----------------------------------

def timedifabs(d1,d2):
    if d1-d2<timedelta(days = 0):
        return d2-d1
    return d1-d2

#Checks five messages before and after the message to see if it finds a text to use as name of the game
async def getgamename(message):
    gamename=message.content

    if gamename and len(gamename)<255:
        return gamename

    print('Buscando nombre del juego')

    messages=  inputchannel.history(around=message.created_at,oldest_first=True, limit=12)
    listmessages= await messages.flatten()
    listmessages= list(listmessages)

    listmessages= list(filter(lambda m: m.content and len(m.content)<255 and (m.author==message.author), listmessages))

    if (not listmessages):
        return ''

    placeholdermessage= listmessages[0]#it never fails because of the previous if
    for m in listmessages:
        if  timedifabs(placeholdermessage.created_at,message.created_at) > timedifabs(m.created_at,message.created_at):
            placeholdermessage=m
    
    return placeholdermessage.content

#Checks if the message (identified by the url) is on the list
def candidatescheck(m,c):
    for mc in c:
        print(f'{m.id}=={mc.id}: {m.id==mc.id}')
        if m.id==mc.id:
            return True
    return False

def creationDateCheck(message):
    if message.embeds:
        date=datetime.datetime.strptime(message.embeds[0].footer.text.split('.',1)[0],'%Y-%m-%d %H:%M:%S')
        return datetime.datetime.now() - timedelta(days = daystocheck) <= date


#----------These are divided in two functions to filter between channels (security messure)--------

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
        #if g.name== 'BotTest':
        if g.name== 'FRAMED - Screenshot Community':
            return discord.utils.get(g.channels, name=channelname)
#-------------------------------------------------------------------------------------------------

#--------------------------------------------------------------------


#---------Events---------------------------------
@bot.event
async def on_ready():
    global inputchannel
    global outputchannel
    global thumbnailchannel
    print(f'{bot.user.name} has connected to Discord!')
    inputchannel=getchanneli('share-your-shot')
    outputchannel=getchannelo('share-your-shot-bot')
    thumbnailchannel=getchannelo('thumbnail-dump')

    #reactiontrigger=(len(outputchannel.guild.members))/10

    #Lets get the last messages published by the bot in the channel, and run a curationsince command based on that
    #ATTENTION: If for some reason the bot cant find one of his embbed messages it wont start, so make sure to run the command !dawnoftimecuration before
    #await debugtempcuration(180)

    async for m in outputchannel.history(limit=10):
        if m.author == bot.user and m.embeds:
            date= m.created_at - timedelta(days = daystocheck)
            await curationActive(date)
            await startcurating() #never stops
            break
    
"""
@bot.event
async def on_guild_channel_pins_update(channel, last_pin):
    if inputchannel.name==channel.name:
        pins= await channel.pins()
        #print(f'pins: {pins}')
        if pins and pins[-1].attachments:
            print(f'Last messages pinned: {pins[-1]}')
            curateaction(pins[-1])
            #dbgitupdate()
"""

#Commands can only be detected in the outputchannel
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

#---------------Command functions----------------------------------------------

#reads the messages since a number of days and post the accepted shots that havent been posted yet
async def curationActive(d):

    #-----------------get listcandidates
    candidatesupdate= inputchannel.history(after=d,oldest_first=True,limit=None)
    listcandidates= await candidatesupdate.flatten()
    listcandidates= list(filter(lambda m: curationlgorithm(m), listcandidates))
    #---------------

    alreadyposted= outputchannel.history(after=d,oldest_first=True,limit=None)
    listalreadyposted= await alreadyposted.flatten()
    listalreadyposted=list(filter(creationDateCheck,listalreadyposted))
    print('schedule curation')

    for m1 in listcandidates:
        flag= True
        for m2 in listalreadyposted:

            if m2.embeds:
                if m1.jump_url == m2.embeds[0].description[m2.embeds[0].description.find("(")+1:m2.embeds[0].description.find(")")]:
                    print('Already posted')
                    dbreactionsupdate(m1)
                    flag=False
                    break
        if flag:
            await curateaction(m1)
            print(f'Nice shot bro')

async def startcurating():
    while True:
        await curationActive((datetime.datetime.now() - timedelta(days = daystocheck)))
        dbgitupdate()
        await asyncio.sleep(curatorintervals)

        #reactiontrigger= (len(outputchannel.guild.members))/10
        print(f'Current trigger: {reactiontrigger}')
#---------------------------------------------------------------------------------

#-----------------Commands-------------------------
class BotActions(commands.Cog):
    """Diferent type of curations the bot can make"""

    @commands.command(name='dawnoftimecuration', help='Curate a seated up channel since it was created.')
    async def dawnoftime(self,ctx):
        async for message in inputchannel.history(limit=None,oldest_first=True):
            if curationlgorithmpast(message):
                await curateactiondawnoftime(message)
                print(f'Nice shot bro')
        dbgitupdate()
        print(f'Done curating')
    
    @commands.command(name='startcurating', help='Start activly curating the shots since the number of days specified by the daystocheck value')
    async def startcuratingcommand(self,ctx):
        await startcurating()
    
    
    @commands.command(name='curationsince', help='Curate the shots since a given number of days.')
    async def curationsince(self,ctx,d):
        await curationActive((datetime.datetime.now() - timedelta(days = int(d))))


    #ATTENTION: an id from a message that doesnt belongs to the inputchannel will crash the bot
    @commands.command(name='forcepost', help='Force the bot to curate a message regardless of the amount of reactions. ATTENTION: an id from a message that doesnt belongs to the inputchannel will crash the bot. Make sure to only force posts with an image or ONLY with an external image.url')
    async def forcepost(self,ctx,id):
        message= await inputchannel.fetch_message(id)
        if message.attachments:
            await curateactiondawnoftime(message) #so it uses the date of the screenshot
            print(f'Nice shot bro')
            dbgitupdate()
        else:
            await curateactionexternal(message)
            print(f'Nice shot bro')

bot.add_cog(BotActions())



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
