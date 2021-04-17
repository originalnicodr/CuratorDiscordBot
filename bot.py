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

from colorthief import ColorThief
import webcolors


import re 



#-----------------------------------------------

#--------------------Enviroment variables--------
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GIT_TOKEN= os.getenv('GIT_TOKEN')
#-----------------------------------------------

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)


#------------Constants-----------------

#For basicCuration
#Updated in the startcurating() loop and on the on_ready() event, comment those lines if you dont want this value to get modified
reactiontrigger = 28

curatorintervals= 5 #time bwtween reaction checks
daystocheck=7#the maximun age of the messages to check


curationlgorithmpast= lambda m : historicalUniqueUsersCuration(m)
curationlgorithm= lambda m :  uniqueUsersCuration(m)

#Curation Algorithms:
# basicCuration(m)
# historicalCuration(m)
# extendedCuration(m)
# completeCuration(m)


#Users that dont want to be on the site, specified by their id (author.id)

def is_user_ignored(message):
    author=message.author
    server=message.guild
    #print(server.members)

    member= server.get_member(author.id)
    rols=map(lambda x: x.name,member.roles)
    return "HOFBlocked" in rols
    
#Users that can use commands in the bot dms
authorizedusers=[]


#initial values are set in the on_ready() event
inputchannel=None
outputchannel=None
socialschannel=None

#---------------------------------------

#-----------Github integration --------------------------


websiterepourl = f'https://githubuser:{GIT_TOKEN}@github.com/githubuser/repo.git'
websiterepofolder = 'websiterepo'

repo = Repo.clone_from(websiterepourl, websiterepofolder)
assert repo.__class__ is Repo

#database for using the shots in a website
shotsdb = TinyDB('websiterepo/shotsdb.json')
authorsdb = TinyDB('websiterepo/authorsdb.json')

def dbgitupdate():
    global repo
    repo.git.add('shotsdb.json')
    repo.git.add('authorsdb.json')
    repo.index.commit("DB update")

    repo = Repo(websiterepofolder)
    origin = repo.remote(name="origin")
    origin.push()

async def dbreactionsupdate(message):
    listUsers= await uniqueUsersReactions(message)#max(map(lambda m: m.count,message.reactions))#the list shouldnt be empty
    updatedscore= len(list(listUsers))
    shotsdb.update({'score': updatedscore}, Query().shotUrl == message.attachments[0].url)

#-------------------------------------------------------------

#-------------------Authors DB integration--------------------

def authorsdbupdate(author):
    print(f'author{author.name}')
    print(authorsdb.search(Query().authorid == author.id))
    if authorsdb.search(Query().authorid == author.id)!=[]:
        print('updating')
        authorsdb.update({'authorNick': author.display_name, 'authorsAvatarUrl': str(author.avatar_url)}, Query().authorid == author.id)#avatar and nick update

    else:
        print('inserting')
        authorsdb.insert({'authorNick': author.display_name,'authorid': author.id, 'authorsAvatarUrl': str(author.avatar_url), 'flickr':'', 'twitter':'', 'instagram':'', 'steam':'', 'othersocials': ''}) #for discord id (name#042) you can save author directly, for the name before the # use author.name


def FindUrls(string): 
    # findall() has been used  
    # with valid conditions for urls in string 
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    url = re.findall(regex,string)       
    return [x[0] for x in url] 

def addsocials(message):#the message is the social media message
    author=message.author
    socials= FindUrls(message.content)

    flickr=''
    instagram=''
    steam=''
    twitter=''

    #Awful way of doing this, please dont judge

    for url in socials:
        if 'flickr' in url:
            flickr=url
            socials.remove(url)
            break

    for url in socials:
        if 'instagram' in url:
            instagram=url
            socials.remove(url)
            break

    for url in socials:
        if 'steam' in url:
            steam=url
            socials.remove(url)
            break

    for url in socials:
        if 'twitter' in url:
            twitter=url
            socials.remove(url)
            break

    if authorsdb.search(Query().authorid == author.id)!=[]:
        authorsdb.update({'authorNick': author.display_name, 'authorsAvatarUrl': str(author.avatar_url), 'othersocials': socials}, Query().authorid == author.id)#avatar and nick update
        if flickr!='':
            authorsdb.update({'authorNick': author.display_name, 'authorsAvatarUrl': str(author.avatar_url), 'flickr':flickr}, Query().authorid == author.id)
        if instagram!='':
            authorsdb.update({'authorNick': author.display_name, 'authorsAvatarUrl': str(author.avatar_url), 'instagram':instagram}, Query().authorid == author.id)
        if twitter!='':
            authorsdb.update({'authorNick': author.display_name, 'authorsAvatarUrl': str(author.avatar_url), 'twitter':twitter}, Query().authorid == author.id)
        if steam!='':
            authorsdb.update({'authorNick': author.display_name, 'authorsAvatarUrl': str(author.avatar_url), 'steam':steam}, Query().authorid == author.id)
    else:
        authorsdb.insert({'authorNick': author.display_name,'authorid': author.id, 'authorsAvatarUrl': str(author.avatar_url), 'flickr': flickr, 'twitter':twitter, 'instagram':instagram, 'steam':steam, 'othersocials': socials}) #for discord id (name#042) you can save author directly, for the name before the # use author.name



async def historicsocials():
    global socialschannel
    async for message in socialschannel.history(limit=None,oldest_first=True):
        addsocials(message)


async def updatesocials(d):#d is a date
    global socialschannel
    newsocials= socialschannel.history(after=d,oldest_first=True,limit=None)
    async for m in newsocials:
        addsocials(m)
        print("added new social info")


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


    shot=shot.convert('RGB')#to save it in jpg
    shot=shot.filter(ImageFilter.SHARPEN)
    
    #filter algorithms
    #Image.NEAREST, Image.BILINEAR, Image.BICUBIC, Image.ANTIALIAS
    shot=shot.resize((wt,ht),Image.BICUBIC)
    
    shot.save('thumbnailtemp.jpg',quality=95)
    dominantColor, colorPalette = getColor('thumbnailtemp.jpg')
    thumbnail= await thumbnailchannel.send(file=discord.File('thumbnailtemp.jpg'))
    return thumbnail.attachments[0].url, dominantColor, colorPalette

#--------------------------------------------------------


#-------Curation algorithms-----------

#returns the amount of reactions of the most reacted emoji
def maxReactions(message):
    listNumberReactions= map(lambda m: m.count,message.reactions)
    if message.reactions!=[]:
        return max(listNumberReactions)
    return 0

#Takes the max number of reactions and compares it with the ractiontrigger value
def basicCuration(message): 
    if message.attachments:
        """
        listNumberReactions= map(lambda m: m.count,message.reactions)
        if message.reactions!=[]:
            reactions= max(listNumberReactions)
            return (reactiontrigger <= reactions)
        """
        return (reactiontrigger <= maxReactions(message))
    return False

#returns the unique users reacting in a message
async def uniqueUsersReactions(message):
    uniqueUsers=[] 
    if message.reactions==[]:
        return uniqueUsers
    #my attempt at a map
    for reaction in message.reactions:
        async for user in reaction.users():
            uniqueUsers.append(user)
    
    uniqueUsers=list(filter(lambda u: u.id != message.author.id,dict.fromkeys(uniqueUsers)))#deleting duplicates and not letting the author counts in the number of unique reactions
    return uniqueUsers

async def uniqueUsersCuration(message): 
    if message.attachments:
        reactions= await uniqueUsersReactions(message)
        return (reactiontrigger <= len(reactions))
    return False



async def historicalUniqueUsersCuration(message): 

    #for some reason outputchannel.created_at gives a wrong date, so we will be using 2019-02-26
    channelscreationdate= datetime.datetime.strptime('2019-02-26','%Y-%m-%d')

    #Minnimun and maximun values that are used in the linear interpolation
    minv=10
    maxv=reactiontrigger

    if message.attachments:
        uniqueUsers=await uniqueUsersReactions(message)

        #print(uniqueUsers)

        if uniqueUsers!=[]:
            listNumberReactions= uniqueUsers
            
            #how new is the message from 0 to 1
            valueovertime=(message.created_at-channelscreationdate).days/(datetime.datetime.now()-channelscreationdate).days
            

            #linearinterpolation
            trigger = (valueovertime * maxv) + ((1-valueovertime) * minv)
            reactions= len(listNumberReactions)
            print(f'Trigger value={trigger} <= {reactions} = unique users reacting')
            
            return (trigger <= reactions)
    return False



#Takes the max number of reactions and compares it with a ractiontrigger value that varies based on the time where the shot was posted
def historicalCuration(message): 

    #for some reason outputchannel.created_at gives a wrong date, so we will be using 2019-02-26
    channelscreationdate= datetime.datetime.strptime('2019-02-26','%Y-%m-%d')

    #Minnimun and maximun values that are used in the linear interpolation
    minv=10
    maxv=reactiontrigger

    if message.attachments:
        if message.reactions!=[]:
            
            #how new is the message from 0 to 1
            valueovertime=(message.created_at-channelscreationdate).days/(datetime.datetime.now()-channelscreationdate).days
            

            #linearinterpolation
            trigger = (valueovertime * maxv) + ((1-valueovertime) * minv)
            print(f'Trigger value={trigger}')

            reactions= maxReactions(message)
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
    thumbnail, dominantColor, colorPalette = await createthumbnail(message) #link of the thumbnail
    colorName1, closestClrName1 = get_colour_name(dominantColor, colorPalette)
    elementid=len(shotsdb)+1
    score=await uniqueUsersReactions(message)
    score=len(list(score))
    shotsdb.insert({'gameName': gamename, 'shotUrl': message.attachments[0].url, 'height': message.attachments[0].height, 'width': message.attachments[0].width, 'thumbnailUrl': thumbnail ,'author': message.author.id, 'date': message.created_at.strftime('%Y-%m-%dT%H:%M:%S.%f'), 'score': score, 'ID': elementid, 'epochTime': int(message.created_at.timestamp()), 'spoiler': message.attachments[0].is_spoiler(), 'colorName': closestClrName1})
    


#instead of using the date of the message it uses the actual time, that way if you sort by new in the future website, the new shots would always be on top, instead of getting mixed
async def writedb(message,gamename):
    thumbnail, dominantColor, colorPalette = await createthumbnail(message) #link of the thumbnail
    colorName1, closestClrName1 = get_colour_name(dominantColor, colorPalette)
    elementid=len(shotsdb)+1
    score=await uniqueUsersReactions(message)
    score=len(list(score))
    shotsdb.insert({'gameName': gamename, 'shotUrl': message.attachments[0].url, 'height': message.attachments[0].height, 'width': message.attachments[0].width, 'thumbnailUrl': thumbnail ,'author': message.author.id, 'date': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f'), 'score': score, 'ID': elementid, 'epochTime': int(datetime.datetime.now().timestamp()), 'spoiler': message.attachments[0].is_spoiler(), 'colorName': closestClrName1})
    shotsdb.all()

async def curateaction(message):
    if is_user_ignored(message):
        print("User ignored")
        return
    gamename= await getgamename(message)
    await writedb(message,gamename)
    await postembed(message,gamename)
    authorsdbupdate(message.author)
    dbgitupdate()


async def curateactiondawnoftime(message):
    if is_user_ignored(message):
        return
    gamename= await getgamename(message)
    await postembed(message,gamename)
    await writedbdawnoftime(message,gamename)
    authorsdbupdate(message.author)

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
    shotsdb.insert({'gameName': gamename, 'shotUrl': message.content, 'author': message.author.name, 'authorsAvatarUrl': str(message.author.avatar_url), 'date': message.created_at.strftime('%Y-%m-%dT%H:%M:%S.%f'), 'score': max(map(lambda m: m.count,message.reactions))})
"""

async def curateactionexternal(message):
    #await writedbexternal(message,'')
    if is_user_ignored(message):
        return
    await postembedexternal(message,'')

    #--------------------------------------------------------

#----------------------------------------------------

#-----------Authors DB------------------------------

#---------------------------------------------------

#----------Aux Functions----------------------------------

def timedifabs(d1,d2):
    if d1-d2<timedelta(days = 0):
        return d2-d1
    return d1-d2

#Checks five messages before and after the message to see if it finds a text to use as name of the game
async def getgamename(message):
    gamename=message.content#message.content

    if gamename and len(gamename)<255:
        #Please dont judge me its late and I am tired
        if '\n' in gamename:
            return gamename.split('\n', 1)[0]
        else:
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


    #print(placeholdermessage.content)

    #Please dont judge me its late and I am tired
    if '\n' in placeholdermessage.content:
        return placeholdermessage.content.split('\n', 1)[1]
    else:
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
        #print(date)
        return datetime.datetime.now() - timedelta(days = daystocheck) <= date

def getColor(fileName): 
    color_thief = ColorThief(fileName)
    """
    quality settings, 1 is the highest quality, the bigger
    the number, the faster a color will be returned but
    the greater the likelihood that it will not be the
    visually most dominant color
    """
    colorPalette = color_thief.get_palette(quality=3)
    dominantColor = colorPalette[0]
    return dominantColor, colorPalette

def closest_colour(requested_colour):
    min_colours = {}
    for key, name in webcolors.css3_hex_to_names.items():
        r_c, g_c, b_c = webcolors.hex_to_rgb(key)
        rd = (r_c - requested_colour[0] - 10) ** 2
        gd = (g_c - requested_colour[1] - 10) ** 2
        bd = (b_c - requested_colour[2] - 10) ** 2
        min_colours[(rd + gd + bd)] = name
    return min_colours[min(min_colours.keys())]

def get_colour_name(requested_colour, colorPalette):
    n = 1
    try:
        closest_name = actual_name = webcolors.rgb_to_name(requested_colour)
    except ValueError:
        closest_name = closest_colour(requested_colour)
        while closest_name == 'black' or closest_name == 'darkslategrey':
            closest_name = closest_colour(colorPalette[n])
            n += 1
        actual_name = None
    return actual_name, closest_name


#----------These are divided in two functions to filter between channels (security messure)--------

#DONT CHANGE
#necesary for thumbnailchannel
def getchannelo(channelname):#not the best method to do this tho
    #print(list(discord.Client.guilds))

    for g in bot.guilds:
        if g.name== 'OutputChannelName':
            return discord.utils.get(g.channels, name=channelname)

def getchanneli(channelname):#not the best method to do this tho
    #print(list(discord.Client.guilds))

    for g in bot.guilds:
        #if g.name== 'BotTest':
        if g.name== 'InputChannelName':
            return discord.utils.get(g.channels, name=channelname)
#-------------------------------------------------------------------------------------------------

#--------------------------------------------------------------------


#---------Events---------------------------------
@bot.event
async def on_ready():
    global inputchannel
    global outputchannel
    global thumbnailchannel
    global socialschannel
    print(f'{bot.user.name} has connected to Discord!')
    inputchannel=getchanneli('share-your-shot')
    outputchannel=getchanneli('hall-of-framed')
    thumbnailchannel=getchannelo('thumbnail-dump')
    socialschannel=getchanneli('share-your-socials')

    #reactiontrigger=(len(outputchannel.guild.members))/10

    #Lets get the last messages published by the bot in the channel, and run a curationsince command based on that
    #ATTENTION: If for some reason the bot cant find one of his embbed messages it wont start, so make sure to run the command !dawnoftimecuration before
    #await debugtempcuration(180)

    
    #client.private_channels

    #Open DMs channel for command dms
    """
    for userid in authorizedusers:
        user = await bot.fetch_user(userid)
        await user.send("Message sent to open a DM channel for future DMs commands. Sorry for the inconvenience, send your complains to Nico I am just a bot beep beep boop.")
    """

    
    

    
    async for m in outputchannel.history(limit=10):
        if m.author == bot.user and m.embeds:
            date= m.created_at - timedelta(days = daystocheck)
            #await execqueuecommandssince(m.created_at)
            await updatesocials(m.created_at) #update socials since the last time the bot sent a message
            await curationActive(date)
            await startcurating() #never stops
            break
    
    
    


@bot.event
async def on_message(message):
    if (message.channel.name == 'share-your-socials'):
        addsocials(message)
        dbgitupdate()
    else:
        await bot.process_commands(message)


#Commands can only be detected in the outputchannel
@bot.check
async def predicate(ctx):
    if isinstance(ctx.channel, discord.channel.DMChannel):
        return (ctx.author.id in authorizedusers)
    else:#no es necesario el else pero bueno
        return (ctx.channel.name==outputchannel.name)



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

async def async_filter(async_pred, iterable):
    for item in iterable:
        should_yield = await async_pred(item)
        if should_yield:
            yield item

async def execqueuecommandssince(date):
    commands=[]
    for userid in authorizedusers:
        user=await bot.fetch_user(userid) 

        if not (user.dm_channel):
            await user.create_dm()
        userchannel= user.dm_channel

        morecommands=await userchannel.history(after=date,oldest_first=True,limit=None).flatten()

        commands=commands+list(morecommands)
        
    
    for m in commands:
        print(m.content)
        if "!forcepost " == m.content[:11]:
            await forcepost(m.content[11:])
            

async def forcepost(id):
    message= await inputchannel.fetch_message(id)
    if message.attachments:
        await curateaction(message) #so it uses the date of the screenshot
        print(f'Nice shot bro')
    else:
        await curateactionexternal(message)
        print(f'Nice shot bro')


#reads the messages since a number of days and post the accepted shots that havent been posted yet
async def curationActive(d):

    #-----------------get listcandidates
    candidatesupdate= inputchannel.history(after=d,oldest_first=True,limit=None)
    listcandidates= await candidatesupdate.flatten()
    #listcandidates= [i async for i in async_filter(curationlgorithm,listcandidatesprev)]#[]#list(async_filter(lambda m: curationlgorithm(m),listcandidatesprev))
    #my attempt at a filter
    
    """
    for m in listcandidatesprev:
        b = await curationlgorithm(m)
        if b:
            listcandidates.append(m)
    """
    
    #---------------

    alreadyposted= outputchannel.history(after=d,oldest_first=True,limit=None)
    listalreadyposted= await alreadyposted.flatten()
    listalreadyposted=list(listalreadyposted)
    print('schedule curation')

    for m1 in listcandidates:
        check= await curationlgorithm(m1)#it would be faster if we could filter the listcandidates instead of doing this, right?
        if check:
            flag= True
            for m2 in listalreadyposted:

                if m2.embeds:
                    if m1.jump_url == m2.embeds[0].description[m2.embeds[0].description.find("(")+1:m2.embeds[0].description.find(")")]:
                        print('Already posted')
                        await dbreactionsupdate(m1)
                        flag=False
                        break
            if flag:
                await curateaction(m1)
                print(f'Nice shot bro')

async def startcurating():
    while True:
        await curationActive((datetime.datetime.now() - timedelta(days = daystocheck)))
        await asyncio.sleep(curatorintervals)

        #reactiontrigger= (len(outputchannel.guild.members))/10
        print(f'Current trigger: {reactiontrigger}')
#---------------------------------------------------------------------------------

#-----------------Commands-------------------------
class BotActions(commands.Cog):
    """Diferent type of curations the bot can make"""

    @commands.command(name='dawnoftimecuration', help='Curate a seated up channel since it was created.')
    async def dawnoftime(self,ctx):
        await historicsocials()
        async for message in inputchannel.history(limit=None,oldest_first=True):
            check= await curationlgorithmpast(message)#because of async function (if the algorithm used in curationlgorithmpast is not async take out the await)
            if check:
                await curateactiondawnoftime(message)
                authorsdbupdate(message.author)
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
    async def forcepostcommand(self,ctx,id):
        await forcepost(id)

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
