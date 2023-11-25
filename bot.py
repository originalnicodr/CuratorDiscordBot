# bot.py

# --------Modules---------------------------
DEBUG = True

import os
import shutil
from dotenv import load_dotenv

import discord
from discord.ext import tasks, commands

from discord import app_commands

from b2sdk.v2 import B2Api, InMemoryAccountInfo

import datetime
from datetime import timedelta
import pytz

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

# -----------------------------------------------

# --------------------Enviroment variables--------
if DEBUG:
    load_dotenv()
    TOKEN = os.environ.get("DISCORD_TOKEN")
    GIT_TOKEN = os.environ.get("GIT_TOKEN")

    BACKBLAZE_KEY = os.environ.get("BACKBLAZE_KEY")
    BACKBLAZE_KEY_ID = os.environ.get("BACKBLAZE_KEY_ID")
    BACKBLAZE_HOF_FOLDER_NAME = os.environ.get("BACKBLAZE_HOF_FOLDER_NAME")
    BACKBLAZE_BUCKET_NAME = os.environ.get("BACKBLAZE_BUCKET_NAME")
else:
    load_dotenv()
    # TOKEN = os.getenv('DISCORD_TOKEN')
    # GIT_TOKEN= os.getenv('GIT_TOKEN')

    TOKEN = os.environ.get("DISCORD_TOKEN", None)
    GIT_TOKEN = os.environ.get("GIT_TOKEN")
# -----------------------------------------------

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

client = discord.Client(intents=discord.Intents.default(), max_messages=None)
tree_cls = app_commands.CommandTree(client)

# ------------Backblaze Auth-------------

info = InMemoryAccountInfo()
b2_api = B2Api(info)
application_key_id = BACKBLAZE_KEY_ID
application_key = BACKBLAZE_KEY
b2_api.authorize_account("production", application_key_id, application_key)

# ------------Constants-----------------

# For basicCuration
# Updated in the startcurating() loop and on the on_ready() event, comment those lines if you dont want this value to get modified
reactiontrigger = 30

daystocheck = 7  # the maximun age of the messages to check


curationlgorithmpast = lambda m: historicalUniqueUsersCuration(m)
curationlgorithm = lambda m: uniqueUsersCuration(m)

# Curation Algorithms:
# basicCuration(m)
# historicalCuration(m)
# extendedCuration(m)
# completeCuration(m)

siteLink = "https://framedsc.com/HallOfFramed/"


# Users that dont want to be on the site, specified by their id (author.id)


def is_user_ignored(message):
    author = message.author
    server = message.guild
    # print(message)
    # print(message.id)
    if author is None:
        return False

    member = server.get_member(author.id)
    if member is None:
        return False
    rols = list(map(lambda x: x.name, member.roles))
    return ("HOFBlocked" in rols) or ("Padawan" in rols)


def is_member_mod(member):
    roles = list(map(lambda x: x.name, member.roles))
    return "Founders Edition" in roles

# Commands can only be detected in the outputchannel
#@bot.check
async def is_user_allowed(ctx):
    member = get_framed_server().get_member(ctx.author.id)
    if isinstance(ctx.channel, discord.channel.DMChannel):
        return is_member_mod(member)
    else:  # no es necesario el else pero bueno
        return ctx.channel.name == outputchannel.name

async def ignore_bcs_emoji(message):
    if message.reactions == []:
        return False
    for reaction in message.reactions:
        if str(reaction.emoji) == "🚫":
            async for user in reaction.users():  # I cant do "message.author in reaction.users()" for whatever reason
                if user == message.author or is_member_mod(user):
                    return True
            return False
    return False


# Users that can use commands in the bot dms
authorizedusers = [
    163919378285461504,
    310528138067181572,
    128245457141891072,
]  # jim, frans, nico

# initial values are set in the on_ready() event
inputchannel = None
outputchannel = None
socialschannel = None


def delete_websiterepo_folder():
    directory = os.getcwd()
    file_path = directory + "\websiterepo"
    if os.path.exists(file_path):
        shutil.rmtree(file_path)
        print("Deleted websiterepo folder succesfully.")


# ---------------------------------------

# -----------Github integration --------------------------


websiterepourl = f"https://originalnicodrgitbot:{GIT_TOKEN}@github.com/originalnicodrgitbot/hall-of-framed-db.git"
websiterepofolder = "websiterepo"

#delete_websiterepo_folder()
repo = Repo.clone_from(websiterepourl, websiterepofolder)
assert repo.__class__ is Repo

# database for using the shots in a website
shotsdb = TinyDB("websiterepo/shotsdb.json", indent=2)
authorsdb = TinyDB("websiterepo/authorsdb.json", indent=2)


def dbgitupdate():
    global repo
    repo.git.add("shotsdb.json")
    repo.git.add("authorsdb.json")
    repo.index.commit("DB update")

    repo = Repo(websiterepofolder)
    origin = repo.remote(name="origin")
    origin.push()


async def dbreactionsupdate(message):
    listUsers = await uniqueUsersReactions(
        message
    )  # max(map(lambda m: m.count,message.reactions))#the list shouldnt be empty
    updatedscore = len(list(listUsers))
    shotsdb.update(
        {"score": updatedscore}, Query().shotUrl == message.attachments[0].url
    )


# -------------------------------------------------------------

# -------------------Authors DB integration--------------------


def authorsdbupdate(author):
    authorid_str = str(author.id)
    print(f"author {author.name}")
    print(authorsdb.search(Query().authorid == authorid_str))
    if authorsdb.search(Query().authorid == authorid_str) != []:
        print("updating")
        authorsdb.update(
            {
                "authorNick": author.display_name,
                "authorsAvatarUrl": str(author.avatar.url),
            },
            Query().authorid == authorid_str,
        )  # avatar and nick update

    else:
        print("inserting")
        authorsdb.insert(
            {
                "authorNick": author.display_name,
                "authorid": authorid_str,
                "authorsAvatarUrl": str(author.avatar.url),
                "flickr": "",
                "twitter": "",
                "instagram": "",
                "steam": "",
                "othersocials": "",
            }
        )  # for discord id (name#042) you can save author directly, for the name before the # use author.name


def FindUrls(string):
    # findall() has been used
    # with valid conditions for urls in string
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    url = re.findall(regex, string)
    return [x[0] for x in url]


def addsocials(message):  # the message is the social media message
    author = message.author
    print(message.content)
    socials = FindUrls(message.content)

    flickr = ""
    instagram = ""
    steam = ""
    twitter = ""

    # Awful way of doing this, please dont judge

    for url in socials:
        if "flickr" in url:
            flickr = url
            socials.remove(url)
            break

    for url in socials:
        if "instagram" in url:
            instagram = url
            socials.remove(url)
            break

    for url in socials:
        if "steam" in url:
            steam = url
            socials.remove(url)
            break

    for url in socials:
        if "twitter" in url:
            twitter = url
            socials.remove(url)
            break

    authorid_str = str(author.id)

    if authorsdb.search(Query().authorid == authorid_str) != []:
        authorsdb.update(
            {
                "authorNick": author.display_name,
                "authorsAvatarUrl": str(author.avatar.url),
                "othersocials": socials,
            },
            Query().authorid == authorid_str,
        )  # avatar and nick update
        if flickr != "":
            authorsdb.update(
                {
                    "authorNick": author.display_name,
                    "authorsAvatarUrl": str(author.avatar.url),
                    "flickr": flickr,
                },
                Query().authorid == authorid_str,
            )
        if instagram != "":
            authorsdb.update(
                {
                    "authorNick": author.display_name,
                    "authorsAvatarUrl": str(author.avatar.url),
                    "instagram": instagram,
                },
                Query().authorid == authorid_str,
            )
        if twitter != "":
            authorsdb.update(
                {
                    "authorNick": author.display_name,
                    "authorsAvatarUrl": str(author.avatar.url),
                    "twitter": twitter,
                },
                Query().authorid == authorid_str,
            )
        if steam != "":
            authorsdb.update(
                {
                    "authorNick": author.display_name,
                    "authorsAvatarUrl": str(author.avatar.url),
                    "steam": steam,
                },
                Query().authorid == authorid_str,
            )
    else:
        authorsdb.insert(
            {
                "authorNick": author.display_name,
                "authorid": authorid_str,
                "authorsAvatarUrl": str(author.avatar.url),
                "flickr": flickr,
                "twitter": twitter,
                "instagram": instagram,
                "steam": steam,
                "othersocials": socials,
            }
        )  # for discord id (name#042) you can save author directly, for the name before the # use author.name


async def historicsocials():
    global socialschannel
    async for message in socialschannel.history(limit=None, oldest_first=True):
        addsocials(message)


async def updatesocials(d):  # d is a date
    global socialschannel
    newsocials = socialschannel.history(after=d, oldest_first=True, limit=None)
    # print(list(newsocials))
    async for m in newsocials:
        addsocials(m)
        print("added new social info")


# -------------------------------------------------------------

# -----------Thumbnail creation--------------------------
sizelimit = 400  # discord standar

# initial value is set in the on_ready() event
thumbnailchannel = None


def createthumbnail(shot, shot_filename):
    ar = shot.width / shot.height

    # Discord method
    """
    ht= sizelimit if h>w else int(ar*sizelimit)
    wt= sizelimit if w>h else int((1/ar)*sizelimit)
    """

    # Flickr method
    ht = sizelimit
    wt = int(ar * sizelimit)

    shot = shot.convert("RGB")  # to save it in jpg
    shot = shot.filter(ImageFilter.SHARPEN)

    # filter algorithms
    # Image.NEAREST, Image.BILINEAR, Image.BICUBIC, Image.ANTIALIAS
    thumbnail_shot = shot.resize((wt, ht), Image.BICUBIC)

    shot_filename_without_extension = os.path.splitext(shot_filename)[0]
    thumbnail_file_name = f"thumbnail_{shot_filename_without_extension}.jpg"
    thumbnail_shot.save(thumbnail_file_name, quality=95)

    return Image.open(thumbnail_file_name), thumbnail_file_name


# --------------------------------------------------------


# -------Curation algorithms-----------


# returns the amount of reactions of the most reacted emoji
def maxReactions(message):
    listNumberReactions = map(lambda m: m.count, message.reactions)
    if message.reactions != []:
        return max(listNumberReactions)
    return 0


# Takes the max number of reactions and compares it with the ractiontrigger value
def basicCuration(message):
    if message.attachments:
        """
        listNumberReactions= map(lambda m: m.count,message.reactions)
        if message.reactions!=[]:
            reactions= max(listNumberReactions)
            return (reactiontrigger <= reactions)
        """
        return reactiontrigger <= maxReactions(message)
    return False


# returns the unique users reacting in a message
async def uniqueUsersReactions(message):
    uniqueUsers = []
    if message.reactions == []:
        return uniqueUsers
    # my attempt at a map
    print(message.jump_url)
    for reaction in message.reactions:
        if reaction.users() == []:
            return uniqueUsers
        async for user in reaction.users():
            uniqueUsers.append(user)

    uniqueUsers = list(
        filter(lambda u: u.id != message.author.id, dict.fromkeys(uniqueUsers))
    )  # deleting duplicates and not letting the author counts in the number of unique reactions
    return uniqueUsers


async def uniqueUsersCuration(message):
    if message.attachments:
        reactions = await uniqueUsersReactions(message)
        return reactiontrigger <= len(reactions)
    return False


async def lastChanceUniqueUsersCuration(message):
    lastChanceModifier = 0.75
    if message.attachments:
        reactions = await uniqueUsersReactions(message)
        return reactiontrigger * lastChanceModifier <= len(reactions)
    return False


async def historicalUniqueUsersCuration(message):
    # for some reason outputchannel.created_at gives a wrong date, so we will be using 2019-02-26
    channelscreationdate = datetime.datetime.strptime("2019-02-26", "%Y-%m-%d")

    # Minnimun and maximun values that are used in the linear interpolation
    minv = 10
    maxv = reactiontrigger

    if message.attachments:
        uniqueUsers = await uniqueUsersReactions(message)

        # print(uniqueUsers)

        if uniqueUsers != []:
            listNumberReactions = uniqueUsers

            # how new is the message from 0 to 1
            valueovertime = (message.created_at - channelscreationdate).days / (
                datetime.datetime.now(tz=pytz.UTC) - channelscreationdate
            ).days

            # linearinterpolation
            trigger = (valueovertime * maxv) + ((1 - valueovertime) * minv)
            reactions = len(listNumberReactions)
            print(f"Trigger value={trigger} <= {reactions} = unique users reacting")

            return trigger <= reactions
    return False


# Takes the max number of reactions and compares it with a ractiontrigger value that varies based on the time where the shot was posted
def historicalCuration(message):
    # for some reason outputchannel.created_at gives a wrong date, so we will be using 2019-02-26
    channelscreationdate = datetime.datetime.strptime("2019-02-26", "%Y-%m-%d")

    # Minnimun and maximun values that are used in the linear interpolation
    minv = 10
    maxv = reactiontrigger

    if message.attachments:
        if message.reactions != []:
            # how new is the message from 0 to 1
            valueovertime = (message.created_at - channelscreationdate).days / (
                datetime.datetime.now(tz=pytz.UTC) - channelscreationdate
            ).days

            # linearinterpolation
            trigger = (valueovertime * maxv) + ((1 - valueovertime) * minv)
            print(f"Trigger value={trigger}")

            reactions = maxReactions(message)
            return trigger <= reactions
    return False


def extendedCuration(message):
    if message.attachments:
        # How much do the other emojis "weight" to the final number
        secondvalue = 0.2

        listNumberReactions = list(map(lambda m: m.count, message.reactions))
        if message.reactions != []:
            premessagevalue = max(
                listNumberReactions
            )  # value of the emoji with biggest amount of reactions
            messagevalue = (
                premessagevalue
                + functools.reduce(
                    operator.add,
                    list(map(lambda r: r * secondvalue, listNumberReactions)),
                    0,
                )
                - premessagevalue * secondvalue
            )

            print(
                f"premessagevalue + fold list - premessagevalue*0.2={premessagevalue} + {functools.reduce(operator.add, list(map(lambda r: r*secondvalue,listNumberReactions)),0) } - {premessagevalue*secondvalue}"
            )

            print(f"Reactiontrigger={reactiontrigger} <=messagevalue={messagevalue}")
            return reactiontrigger <= messagevalue
    return False


def completeCuration(message):
    if message.attachments:
        # for some reason outputchannel.created_at gives a wrong date, so we will be using 2019-02-26
        channelscreationdate = datetime.datetime.strptime("2019-02-26", "%Y-%m-%d")

        # Minnimun and maximun values that are used in the linear interpolation
        minv = 15
        maxv = 25

        # How much do the other emojis weight
        secondvalue = 0.2

        listNumberReactions = list(map(lambda m: m.count, message.reactions))
        if message.reactions != []:
            valueovertime = (message.created_at - channelscreationdate).days / (
                datetime.datetime.now(tz=pytz.UTC) - channelscreationdate
            ).days
            trigger = (valueovertime * maxv) + ((1 - valueovertime) * minv)

            premessagevalue = max(
                listNumberReactions
            )  # value of the emoji with biggest amount of reactions
            messagevalue = (
                premessagevalue
                + functools.reduce(
                    operator.add,
                    list(map(lambda r: r * secondvalue, listNumberReactions)),
                    0,
                )
                - premessagevalue * secondvalue
            )

            print(f"Trigger value={trigger} <=messagevalue={messagevalue}")

            return trigger <= messagevalue
    return False


# -------------------------------------


# ------------Curation action functions--------------
async def postembed(message, shot_filename, gamename):
    embed = discord.Embed(
        title=gamename, description=f"[Message link]({message.jump_url})"
    )
    embed.set_image(url=message.attachments[0].url)
    embed.set_image(url=f"attachment://{shot_filename}")
    embed.set_author(
        name=f"Shot by {message.author}", icon_url=message.author.avatar.url
    )
    # embed.set_author(name= f'Shot by {message.author}')
    # embed.set_thumbnail(url=message.author.avatar.url)
    embed.set_footer(text=f"{message.created_at}")

    file = discord.File(shot_filename)
    await outputchannel.send(file=file, embed=embed)

async def upload_to_backblaze(local__filename, upload_filename, folder):
    b2_file_name = f'{BACKBLAZE_HOF_FOLDER_NAME}/{folder}/{upload_filename}'

    bucket = b2_api.get_bucket_by_name(BACKBLAZE_BUCKET_NAME)
    bucket.upload_local_file(
            local_file=local__filename,
            file_name=b2_file_name,
        )

def downloadImage(message):
    response = requests.get(message.attachments[0].url, stream=True)
    response.raw.decode_content = True
    shot = Image.open(response.raw)
    shot.save(message.attachments[0].filename, quality=95)
    return shot, message.attachments[0].filename

# instead of using the date of the message it uses the actual time, that way if you sort by new in the future website, the new shots would always be on top, instead of getting mixed
async def writedb(message, upload_filename, gamename, dominantColor, colorPalette, post_time):
    colorName1, closestClrName1 = get_colour_name(dominantColor, colorPalette)
    elementid = len(shotsdb) + 1
    score = await uniqueUsersReactions(message)
    score = len(list(score))
    shotsdb.insert(
        {
            "gameName": gamename,
            "shotUrl": f'https://cdn.framedsc.com/images/{upload_filename}',
            "height": message.attachments[0].height,
            "width": message.attachments[0].width,
            "thumbnailUrl": f'https://cdn.framedsc.com/thumbnails/{upload_filename}',
            "author": str(message.author.id),
            "date": post_time.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            "score": score,
            "ID": elementid,
            "epochTime": int(post_time.timestamp()),
            "spoiler": message.attachments[0].is_spoiler(),
            "colorName": closestClrName1,
            "message_id": message.id,
        }
    )
    shotsdb.all()

async def removeshotsfromauthor(ctx, authorid):
    q = Query()
    authors_shots = shotsdb.search(q.author == authorid)
    for shot in authors_shots:
        forceremovepost(ctx, shot.epochTime)


# ----------------------------------------------------
import functools
import typing
import asyncio


def to_thread(func: typing.Callable) -> typing.Coroutine:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        wrapped = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, wrapper)

    return wrapper


# ----------------------------------------------------

# post_time is now for new posts, or message.created_at for historical curation
async def maybePushToHof(message, post_time):
    if is_user_ignored(message):
        print("User ignored")
        return
    if await ignore_bcs_emoji(message):
        print("Shot ignored because of emoji")
        return
    pushToHof(message, post_time)

async def pushToHof(message, post_time):
    gamename = await getgamename(message)
    shot, shot_filename = downloadImage(message)
    thumbnail, thumbnail_filename = createthumbnail(shot, shot_filename)
    # We append the epoch time to avoid collisions between shots
    upload_filename = f'{int(post_time.timestamp())}_{shot_filename}'
    
    if not DEBUG:
        await upload_to_backblaze(shot_filename, upload_filename, 'images')
        await upload_to_backblaze(thumbnail_filename, upload_filename, 'thumbnails')

    dominantColor, colorPalette = getColor(shot_filename)
    await writedb(message, upload_filename, gamename, dominantColor, colorPalette, post_time)
    # If the server is not boosted and the shot is bigger than the max free size uploading the shot for
    # using in the embed might cause troubles. In that case, switch to thumbnail.
    await postembed(message, shot_filename, gamename)
    authorsdbupdate(message.author)

    #delete local files after upload
    del shot
    del thumbnail
    os.remove(shot_filename)
    os.remove(thumbnail_filename)

    if not DEBUG:
        dbgitupdate()

    # ----------------For forcing post actions-------------------

# ----------------------------------------------------

# -----------Authors DB------------------------------

# ---------------------------------------------------

# ----------Aux Functions----------------------------------


def timedifabs(d1, d2):
    if d1 - d2 < timedelta(days=0):
        return d2 - d1
    return d1 - d2


# Checks five messages before and after the message to see if it finds a text to use as name of the game
async def getgamename(message):
    gamename = message.content  # message.content

    if gamename and len(gamename) < 255:
        # Please dont judge me its late and I am tired
        if "\n" in gamename:
            return gamename.split("\n", 1)[0]
        else:
            return gamename

    print("Looking for games name.")

    messages = inputchannel.history(
        around=message.created_at, oldest_first=True, limit=12
    )
    listmessages = messages
    # listmessages = list(listmessages)

    # listmessages = list(filter(lambda m: m.content and len(m.content)<255 and (m.author==message.author), listmessages))
    listmessages = [
        m
        async for m in listmessages
        if m.content and len(m.content) < 255 and (m.author == message.author)
    ]

    if not listmessages:
        return ""

    placeholdermessage = listmessages[0]  # it never fails because of the previous if
    for m in listmessages:
        if timedifabs(placeholdermessage.created_at, message.created_at) > timedifabs(
            m.created_at, message.created_at
        ):
            placeholdermessage = m

    # print(placeholdermessage.content)

    # Please dont judge me its late and I am tired
    if "\n" in placeholdermessage.content:
        return placeholdermessage.content.split("\n", 1)[0]
    else:
        return placeholdermessage.content


# Checks if the message (identified by the url) is on the list
def candidatescheck(m, c):
    for mc in c:
        print(f"{m.id}=={mc.id}: {m.id==mc.id}")
        if m.id == mc.id:
            return True
    return False


def creationDateCheck(message):
    if message.embeds:
        date = datetime.datetime.strptime(
            message.embeds[0].footer.text.split(".", 1)[0], "%Y-%m-%d %H:%M:%S"
        )
        # print(date)
        return datetime.datetime.now(tz=pytz.UTC) - timedelta(days=daystocheck) <= date


def getColor(fileName):
    color_thief = ColorThief(f'{fileName}')
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
        while closest_name == "black" or closest_name == "darkslategrey":
            closest_name = closest_colour(colorPalette[n])
            n += 1
        actual_name = None
    return actual_name, closest_name


# ----------These are divided in two functions to filter between channels (security messure)--------


# DONT CHANGE
# necesary for thumbnailchannel
def getchannelo(channelname):  # not the best method to do this tho
    # print(list(discord.Client.guilds))

    for g in bot.guilds:
        # if g.name== 'FRAMED - Screenshot Community':
        if g.name == "BotTest":
            return discord.utils.get(g.channels, name=channelname)


def getchanneli(channelname):  # not the best method to do this tho
    # print(list(discord.Client.guilds))

    for g in bot.guilds:
        # if g.name== 'BotTest':
        if g.name == "FRAMED - Screenshot Community":
            return discord.utils.get(g.channels, name=channelname)


def get_framed_server():
    for s in bot.guilds:
        # if g.name== 'BotTest':
        if s.name == "FRAMED - Screenshot Community":
            return s


# -------------------------------------------------------------------------------------------------

# --------------------------------------------------------------------


# ---------Events---------------------------------
@bot.event
async def on_ready():
    global inputchannel
    global outputchannel
    global thumbnailchannel
    global socialschannel
    print(f"{bot.user.name} has connected to Discord!")
    inputchannel = getchanneli("share-your-shot")
    outputchannel = (
        getchannelo("share-your-shot-bot") if DEBUG else getchanneli("hall-of-framed")
    )
    thumbnailchannel = getchannelo("thumbnail-dump")
    socialschannel = getchanneli("share-your-socials")

    # reactiontrigger=(len(outputchannel.guild.members))/10

    # Lets get the last messages published by the bot in the channel, and run a curationsince command based on that
    # ATTENTION: If for some reason the bot cant find one of his embbed messages it wont start, so make sure to run the command !dawnoftimecuration before
    # await debugtempcuration(180)

    # client.private_channels

    # Open DMs channel for command dms
    """
    for userid in authorizedusers:
        user = await bot.fetch_user(userid)
        await user.send("Message sent to open a DM channel for future DMs commands. Sorry for the inconvenience, send your complains to Nico I am just a bot beep beep boop.")
    """

    # Update databases to use strings for users.ids
    """
    for author in authorsdb.all():
        authorsdb.update({'authorid': str(author['authorid'])}, Query().authorid == author['authorid'])

    for shot in shotsdb.all():
        shotsdb.update({'author': str(shot['author'])}, Query().author == shot['author'])
    """

    print("running!")

    if DEBUG:

        #https://discord.com/channels/549986543650078722/549986930071175169/1177974660432932884
        message = await inputchannel.fetch_message(1177974660432932884)
        await pushToHof(message, datetime.datetime.now(tz=pytz.UTC))

    else:
        m = await outputchannel.history(limit=1).__anext__()
        print(m)
        if (m.author == bot.user and m.embeds) or DEBUG:
            last_curation_date = m.created_at - timedelta(days=daystocheck)
            print(m.created_at)
            # client = discord.Client(intents=discord.Intents.default(), max_messages=None)
            # await execqueuecommandssince(m.created_at)
            if DEBUG:
                startcurating.start(last_curation_date)
            else:
                # client.loop.create_task(curationActive(last_curation_date))
                startcurating.start(last_curation_date)
                await updatesocials(
                    m.created_at
                )  # update socials since the last time the bot sent a message


@tasks.loop(seconds=5)
async def ping():
    print("is the function being called")


@bot.event
async def on_message(message):

    #await bot.process_commands(message)
    # print("social messages detected")
    # print(type(message.channel))
    # print(message.channel is discord.channel.TextChannel)
    # print(message.channel.name)
    # print(message.channel.name == 'share-your-socials')
    if (
        message.channel is discord.channel.TextChannel
        and message.channel.name == "share-your-socials"
    ):  # message.channel is discord.channel.TextChannel #dont know what this isnt working
        addsocials(message)
        if not DEBUG:
            dbgitupdate()
    else:
        await bot.process_commands(message)


# -------------------------------------------------

# ---------------Commands----------------------------------------------

@bot.command(name='forcepost', brief='Pushes a shot into the HOF.', description="Force the bot to curate a message regardless of the amount of reactions. ATTENTION: Make sure to only force posts with an image or ONLY with an external image.url")
@commands.check(is_user_allowed)
async def forcepostcommand(ctx, id):
    await forcepost(ctx, id)

@bot.command(name='forceremovepost', brief='Remove post from HOF.', description="Force the bot to remove a shot given its HoF id.")
@commands.check(is_user_allowed)
async def forceremovepostcommand(ctx, hof_id):
    await forceremovepost(ctx, hof_id)

@bot.command(name='forceremoveauthor', brief='Remove all of the authors shots from the HOF.', description="Force the bot to remove all shots from the author with the Discord id (Nickname, like JohnDoe#1234) specified")
@commands.check(is_user_allowed)
async def forceremoveauthorcommand(ctx, id):
    await forceremoveauthor(ctx, id)

@bot.command(name='updategamename', brief='Update the game name of a shot in the hof.', description="Updates the game name of the given HoF id with a new one.")
@commands.check(is_user_allowed)
async def updategamenamecommand(ctx, hof_id, newGameName):
    await updategamename(ctx, hof_id, newGameName)

@bot.command(name="shutdown", help="Shuts down the bot.")
@commands.check(is_user_allowed)
async def shutdown(ctx):
    await ctx.channel.send(content="Shutting down...")
    sys.exit()

@bot.command(name='isshotonhof', brief='Checks if the shot is in the hof.', description="Debug command.")
@commands.check(is_user_allowed)
async def command_is_shot_already_posted(ctx, id: int):
    message = await inputchannel.fetch_message(id)
    await ctx.channel.send(
        content=f"Is shot already in hof? {is_shot_already_posted(message)}"
    )

@bot.command(name='updatesocials', brief='Update socials in HOF.', description="Be sure to have the socials message on #share-your-socials channel first.")
async def command_update_socials(ctx):
    global socialschannel

    start_of_channel = datetime.datetime(year=2020, month=8, day=1)

    socialsMessage = None

    async for message in socialschannel.history(after=start_of_channel):
        if message.author.id == ctx.author.id:
            socialsMessage = message
            break

    if socialsMessage is not None:
        addsocials(socialsMessage)
        print("added new social info")
        if not DEBUG:
            dbgitupdate()
        await ctx.channel.send(
            content="Socials updated!"
        )
    else:
        print("No socials message found")
        await ctx.channel.send(
            content="Message not found on the #share-your-socials channel. Please post one so I can update the author's DB."
        )

async def async_filter(async_pred, iterable):
    for item in iterable:
        should_yield = await async_pred(item)
        if should_yield:
            yield item

async def forceremovepost(ctx, id: int):
    try:
        dbEntry = shotsdb.search(Query().epochTime == int(id))[0]

        shot_filename = dbEntry.shotUrl.rsplit('/', 1)

        shotsdb.remove(Query().epochTime == int(id))
        shotsdb.all()
        await ctx.channel.send(
            content=f"Entry deleted \n<{siteLink}?imageId={str(dbEntry['epochTime'])}>"
        )
        if not DEBUG:
            shot_file = b2_api.get_file_info_by_name(BACKBLAZE_BUCKET_NAME, f'{BACKBLAZE_HOF_FOLDER_NAME}/images/{shot_filename}')
            shot_file.delete()

            thumbnail_file = b2_api.get_file_info_by_name(BACKBLAZE_BUCKET_NAME, f'{BACKBLAZE_HOF_FOLDER_NAME}/thumbnails/{shot_filename}')
            thumbnail_file.delete()
            dbgitupdate()
    except:
        await ctx.channel.send(content="Error: Shot not found")

async def forceremoveauthor(ctx, id: int):
    authorQuery = Query()
    authorsMatching = authorsdb.search(authorQuery.authorNick == id)
    if len(authorsMatching) > 0:
        await removeshotsfromauthor(authorsMatching[0]["authorid"])
        print("Author found, shots removed.")
        await ctx.channel.send(content="Author found, shots removed.")
        if not DEBUG:
            dbgitupdate()
    else:
        print("Author not found.")
        await ctx.channel.send(content="Author not found.")

async def updategamename(ctx, id: int, newGameName: str):
    try:
        dbEntry = shotsdb.search(Query().epochTime == int(id))[0]
        shotsdb.update({'gameName': newGameName}, Query().epochTime == int(id))
        if not DEBUG:
            dbgitupdate()
            await ctx.channel.send(
                content="Game name updated! \n"
                + siteLink
                + "?imageId="
                + str(dbEntry["epochTime"])
            )
    except:
        await ctx.channel.send(content="Error: Shot not found")


# Doesnt seem to be working
async def execqueuecommandssince(date):
    commands = []
    for userid in authorizedusers:
        user = await bot.fetch_user(userid)

        if not (user.dm_channel):
            await user.create_dm()
        userchannel = user.dm_channel
        morecommands = userchannel.history(after=date, oldest_first=True, limit=None)
        commands = commands + list(morecommands)

    for m in commands:
        print(m.content)
        if "!forcepost " == m.content[:11]:
            await forcepost(m.content[11:])


#@app_commands.describe(id='Message id')
async def forcepost(ctx, id: int):
    message = await inputchannel.fetch_message(id)
    if message.attachments:
        await pushToHof(message, datetime.datetime.now(tz=pytz.UTC))  # so it uses the date of the screenshot
        print(f"Nice shot bro")
    else:
        #TODO: Support adding external links upload
        print(f"Cant post shot, its not uploaded to discord.")


# reads the messages since a number of days and post the accepted shots that havent been posted yet
async def curationActive(d):
    # We iterate one day at the time to optimize the ram used by the bot
    days_iterator = 0
    while d + timedelta(days=days_iterator) < datetime.datetime.now(tz=pytz.UTC):
        beginning_day = d + timedelta(days=days_iterator)
        end_day = d + timedelta(days=days_iterator + 1)

        print("Beginning_day: ", beginning_day)
        print("End_day: ", end_day)

        # -----------------get listcandidates
        candidatesupdate = inputchannel.history(
            after=beginning_day, before=end_day, oldest_first=True, limit=None
        )
        listCandidates = candidatesupdate
        # listcandidates= [i async for i in async_filter(curationlgorithm,listcandidatesprev)]#[]#list(async_filter(lambda m: curationlgorithm(m),listcandidatesprev))
        # my attempt at a filter

        """
        for m in listcandidatesprev:
            b = await curationlgorithm(m)
            if b:
                listcandidates.append(m)
        """

        # ---------------
        listCandidates = [
            c async for c in listCandidates if not is_shot_already_posted(c)
        ]
        print("schedule curation")

        for m in listCandidates:
            if DEBUG:
                import os, psutil

                print(
                    "Memory used: ",
                    psutil.Process(os.getpid()).memory_info().rss / 1024**2,
                )

            check = await curationlgorithm(
                m
            )  # it would be faster if we could filter the listcandidates instead of doing this, right?
            if check:
                await maybePushToHof(m, datetime.datetime.now(tz=pytz.UTC))
                print(f"Nice shot bro")

        # Continue with the normal curation after the initial one is done.

        days_iterator = days_iterator + 1


@tasks.loop(hours=1)
async def startcurating(last_curation_date):
    if startcurating.current_loop == 0:
        await curationActive(last_curation_date)
    else:
        await curationActive(
            (datetime.datetime.now(tz=pytz.UTC) - timedelta(days=daystocheck))
        )
        no_new_shots = await no_new_shot_x_days(2)
        if no_new_shots:
            await curate_last_chance(0, 2)
        print(f"Current trigger: {reactiontrigger}")


# ---------------------------------------------------------------------------------
async def no_new_shot_x_days(days):
    lowerTime = datetime.datetime.now(tz=pytz.UTC) - timedelta(days=days)
    # shots = shotsdb.search(Query().epochTime > lowerTime)
    # return not bool(shots)
    lastMessage = await outputchannel.history(limit=1).__anext__()
    print(lastMessage.created_at < lowerTime)
    return lastMessage.created_at < lowerTime


async def curate_last_chance_old(daysBehind):
    lowerTime = datetime.datetime.now(tz=pytz.UTC) - timedelta(
        days=daystocheck + daysBehind + 1
    )
    upperTime = datetime.datetime.now(tz=pytz.UTC) - timedelta(
        days=daystocheck + daysBehind
    )

    candidatesUpdate = inputchannel.history(
        after=lowerTime, before=upperTime, oldest_first=True, limit=None
    )
    listCandidates = candidatesUpdate
    print("last chance curation")

    async for m in listCandidates:
        check = await lastChanceUniqueUsersCuration(m)
        if check:
            if is_shot_already_posted(m):
                await maybePushToHof(m, datetime.datetime.now(tz=pytz.UTC))
                print("Nice shot bro")
            else:
                print("Already posted")
    print("finished")


async def curate_last_chance(daysBehind, window_of_days):
    lowerTime = datetime.datetime.now(tz=pytz.UTC) - timedelta(
        days=daystocheck + daysBehind + window_of_days
    )
    upperTime = datetime.datetime.now(tz=pytz.UTC) - timedelta(
        days=daystocheck + daysBehind
    )

    candidatesUpdate = inputchannel.history(
        after=lowerTime, before=upperTime, oldest_first=True, limit=None
    )
    listCandidates = candidatesUpdate
    print("last chance curation")

    listCandidates = [c async for c in listCandidates if not is_shot_already_posted(c)]

    # messageWithReactions = map(await reaction_and_message, listCandidates).sort(key=lambda x: x[1], reverse = True)
    messageWithReactions = []
    # cant use await in map function, ffs...
    for m in listCandidates:
        reactions = await uniqueUsersReactions(m)
        messageWithReactions.append((m, len(reactions)))
    messageWithReactions.sort(key=lambda x: x[1], reverse=True)

    lastChanceModifier = 0.75
    if messageWithReactions[0][1] > reactiontrigger * lastChanceModifier:
        print(messageWithReactions[0][1])
        await maybePushToHof(messageWithReactions[0][0], datetime.datetime.now(tz=pytz.UTC))
    # if(messageWithReactions[1][1] > reactiontrigger*lastChanceModifier):
    #    print(messageWithReactions[1][1])
    #    await maybePushToHof(messageWithReactions[1][0], datetime.datetime.now(tz=pytz.UTC))


def is_shot_already_posted(message):
    if len(message.attachments) == 0:
        return False
    
    # Discord has been changing the URL of shots by appending it with extra stuff, so instead of checking if a shot URL is already in the DB, we check if one URL is 'in' another.
    is_same_shot = lambda shotUrl: shotUrl.split('?')[0] == message.attachments[0].url.split('?')[0]
    # test_func = lambda shotUrl: shotUrl in message.attachments[0].url or message.attachments[0].url in shotUrl
    shot = shotsdb.search(Query().shotUrl.test(is_same_shot))
    #shot = shotsdb.search(Query().shotUrl in message.attachments[0].url or message.attachments[0].url in Query().shotUrl)
    return len(shot) > 0


# --------------------------------------------------

async def add_message_url_to_db():
    lowerTime = datetime.datetime(year=2021, month=1, day=19)
    #upperTime = datetime.datetime.now(tz=pytz.UTC) - timedelta(minutes=5)

    hofMessages = outputchannel.history(
        after=lowerTime, oldest_first=False, limit=None
    )

    print(f"Input channel:{inputchannel}")

    async for hof_m in hofMessages:
        if hof_m.embeds != []:
            message_id_regex = r"\[(.*?)\]\(https:\/\/discord\.com\/channels\/\d+\/\d+\/(\d+)\)"
            sys_message_id = re.search(message_id_regex, hof_m.embeds[0].description).group(2)

            print(f"Message link: {hof_m.embeds[0].description}")
            print(f"Sys message id: {sys_message_id}")

            try:
                sys_m = await inputchannel.fetch_message(sys_message_id)

                if is_shot_already_posted(sys_m): #some hof shots arent on the DB, so before updating their links we check that they actually are in there.
                    is_same_shot = lambda shotUrl: shotUrl.split('?')[0] == sys_m.attachments[0].url.split('?')[0]

                    shotsdb.update(
                        {"message_id": sys_message_id}, Query().shotUrl.test(is_same_shot)
                    )
            except discord.errors.NotFound:
                print(f"Couldn't find sys message {hof_m.jump_url}\n HOF id: {int(hof_m.created_at.timestamp())}")
                
    print("finished")


# Allows me to keep using other commands after the check above fails
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        pass
    else:
        print("Ignoring exception in command {}:".format(ctx.command), file=sys.stderr)
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr
        )

bot.run(TOKEN)
