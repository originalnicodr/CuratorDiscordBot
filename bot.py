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

from tinydb import TinyDB

from git import Repo
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
reactiontrigger = 20

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


websiterepourl = f'https://originalnicodrgitbot:{GIT_TOKEN}@github.com/originalnicodrgitbot/test-git-python.git'
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

#-------------------------------------------------------------

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
    db.insert({'gameName': gamename, 'shotUrl': message.attachments[0].url, 'author': message.author.name, 'authorsAvatarUrl': str(message.author.avatar_url), 'date': message.created_at.strftime('%Y-%m-%dT%H:%M:%S.%f')})

#instead of using the date of the message it uses the actual time, that way if you sort by new in the future website, the new shots would always be on top, instead of getting mixed
async def writedb(message,gamename):
    if message.author.id in ignoredusers:
        return
    db.insert({'gameName': gamename, 'shotUrl': message.attachments[0].url, 'author': message.author.name, 'authorsAvatarUrl': str(message.author.avatar_url), 'date': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')})
    dbgitupdate()

async def curateaction(message):
    gamename= await getgamename(message)
    await writedb(message,gamename)
    await postembed(message,gamename)


async def curateactiondawnoftime(message):
    gamename= await getgamename(message)
    await postembed(message,gamename)
    await writedbdawnoftime(message,gamename)


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

    messages=  inputchannel.history(around=message.created_at,oldest_first=True, limit=10)
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
        if g.name== 'Output server':
        #if g.name== 'FRAMED - Screenshot Community':
            return discord.utils.get(g.channels, name=channelname)

def getchanneli(channelname):#not the best method to do this tho
    #print(list(discord.Client.guilds))
    #for g in list(discord.Client.guilds):

    for g in bot.guilds:
        if g.name== 'Input server':
            return discord.utils.get(g.channels, name=channelname)
#-------------------------------------------------------------------------------------------------

#--------------------------------------------------------------------


#---------Events---------------------------------
@bot.event
async def on_ready():
    global inputchannel
    global outputchannel
    print(f'{bot.user.name} has connected to Discord!')
    inputchannel=getchanneli('inputschannelname')
    outputchannel=getchannelo('outputschannelname')

    reactiontrigger=(len(outputchannel.guild.members))/10

    #Lets get the last messages published by the bot in the channel, and run a curationsince command based on that
    #ATTENTION: If for some reason the bot cant find one of his embbed messages it wont start, so make sure to run the command !dawnoftimecuration before
    #await debugtempcuration(180)

    async for m in outputchannel.history(limit=10):
        if m.author == bot.user and m.embeds:
            date= m.created_at - timedelta(days = daystocheck)
            await curationActive(date)
            await startcurating() #never stops
            break
    

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
                    flag=False
                    break
        if flag:
            await curateaction(m1)
            print(f'Nice shot bro')

async def startcurating():
    while True:
        await curationActive((datetime.datetime.now() - timedelta(days = daystocheck)))
        await asyncio.sleep(curatorintervals)

        reactiontrigger= (len(outputchannel.guild.members))/10
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
