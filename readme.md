<p align="center"><img src="https://user-images.githubusercontent.com/24371572/104768884-1fa5f400-574d-11eb-93c4-10b24f8ce06e.jpg">
 
# <p align="center">CuratorBot</p>
 <p align="center">
  <a href="https://github.com/Rapptz/discord.py/">
     <img src="https://img.shields.io/badge/discordpy-1.6.0-blue.svg" alt="discord.py"></a>
  <a href="https://github.com/msiemens/tinydb">
     <img src="https://img.shields.io/badge/tinyDB-4.3.0-blue.svg" alt="discord.py"></a>
  <a href="https://github.com/gitpython-developers/GitPython">
     <img src="https://img.shields.io/badge/gitPython-3.1.12-blue.svg" alt="discord.py"></a>
  <a href="https://github.com/python-pillow/Pillow">
     <img src="https://img.shields.io/badge/pillow-8.3.2-blue.svg" alt="discord.py"></a>
  <a href="https://github.com/psf/requests">
     <img src="https://img.shields.io/badge/requests-2.22.0-blue.svg" alt="discord.py"></a>
  <a href="https://github.com/fengsp/color-thief-py">
     <img src="https://img.shields.io/badge/colorthief-0.2.1-blue.svg" alt="discord.py"></a>
  <a href="https://github.com/ubernostrum/webcolors">
     <img src="https://img.shields.io/badge/webcolors-1.3-blue.svg" alt="discord.py"></a>
  <a href="https://github.com/theskumar/python-dotenv">
     <img src="https://img.shields.io/badge/pythondotenv-0.19.0-blue.svg" alt="discord.py"></a>
 
## About
 
CuratorBot is a dedicated Discord bot that specializes in selecting the finest screenshots from one channel and forwarding them to another channel. Additionally, it utilizes Discord as a hosting platform for a website and exports a few .json database files to a GitHub repository (apologies, I do not like pay for paid hosting).

You can visit the website where the screenshots are displayed at [this link](https://framedsc.com/HallOfFramed/), and learn more about the process behind creating this bot in my [blog post](https://originalnicodr.github.io/blog/how-we-made-a-high-quality-image-gallery-without-paying-a-single-dime).

Since this bot was developed for a specific server, it includes certain assumptions. For instance, it searches for a message with contextual information when a screenshot message lacks explicit details about the game. Therefore, if you decide to host your own version of the bot, please bear in mind that you may need to make adjustments to accommodate your specific requirements.
 
<p align="center"><img src="https://user-images.githubusercontent.com/24371572/104781820-eb88fe00-5761-11eb-91d0-6daf4448ebad.png">
 
The bot adds the shot to the .json file we are using as a DB, including the screenshot link, along with a corresponding thumbnail that is generated and uploaded to Discord by the bot. These files are then pushed to a GitHub repository, allowing them to be utilized as a database for the HallofFramed website, where the screenshots are showcased.
 
In addition, the bot creates a comprehensive database of authors, which contains valuable information. This authors database is continuously updated whenever a shot is accepted into the shots database or when a message is sent to the socials channel, ensuring that the authors' information is added or updated accordingly.
 
## How it Works
 
The determination of "best screenshots" is based on the reactions received by the messages containing the images. To achieve this, I prototyped a set of algorithms that utilize these reactions to evaluate the quality of each image and decide whether it is worth highlighting. The one currently being used takes the amount of unique users reaction to the shot and compares that number to a threshold.
 
## SetUp
 
To setup this as your own bot you will need to create an `.env` file with the discord bot token inside:
 
```
DISCORD_TOKEN=yourDiscordBotToken
GIT_TOKEN=githubPersonalAccessTokens
```
 
Later on, you will also need to modify the following settings to customize the bot's behavior:

1. **Input Channel:** This is the channel where the bot will search for messages containing screenshots.
2. **Output Channel:** The bot will send the accepted messages (screenshots) to this channel.
3. **Thumbnail Channel:** This channel is where the bot will store and upload the thumbnails it creates for the screenshots.
4. **Socials Channel:** The bot retrieves social links for the authors' database from this channel.
 
Keep in mind that you can also discriminate between different servers for the input and output channels in the **getchannel** functions.
 
To change the repo where the bot will push change the link in the **Github integration** section.
 
To change the thumbnails options (extension of the file, size, filter used in the resizing, etc.) check the **Thumbnail creation** section.
 
The bot can ignore shots from people that have an specific rol. To specify the names rol change it in the **is_user_ignored** function.
 
## Usage
 
The commands can be accepted in the channel where the images will be sent or via DMs, but you would need to include the users ID in the **authorizedusers** list for the latter to be accepted.
 
I made this bot for being able to curate retroactively, so the correct way to use it after setting it up would be to use the **!dawnoftimecuration** (using a new, clean channel as an output channel) to curate all past screenshots.

If for some reason the bot goes offline, whenever it gets online again it will curate from where he was.
 
## Commands
 
Here is an updated list of commands for your bot:

- **!curationsince**: Curates the shots that are less than a certain number of days old.
- **!dawnoftimecuration**: Curates a designated channel since it was created.
- **!startcurating**: Starts actively curating shots from a specified number of days ago.
- **!forcepost MESSAGE_ID**: Forces the bot to post a message regardless of the number of reactions. Ensure that the MESSAGE_ID belongs to the input channel. Only force posts with an image attachment or text containing only an external image URL.
- **!forceremovepost MESSAGE_ID**: Forces the bot to remove a shot posted in the message with the specified ID. Ensure that the MESSAGE_ID belongs to the input channel.
- **!forceremoveauthor AUTHOR_NICK**: Forces the bot to remove all shots from the author with the specified Discord ID (Nickname, e.g., JohnDoe#1234).
- **!setcuratorintervals**: Sets the time interval (in seconds) between channel reaction checks.
- **!setdaystocheck**: Sets the maximum age of the messages to actively check.
- **!setinputchannel**: Sets the channel from which the bot will curate.
- **!setoutputchannel**: Sets the channel where the curated messages will be sent.
- **!help**: Show this help message.

Please note the instructions and warnings mentioned in the descriptions of the commands. Ensure that the message IDs provided correspond to the input channel to avoid any issues.
 
Do bear in mind that the values changed by the set commands work only on runtime. If you don't know if your bot will go down temporarily change the values in the file instead.
 
## JSON Database structure
 
The .json file generated, modified, and pushed by the bot follows a structure that includes elements with the following format:
 
### Shots DB
 
```
{"gameName": string,
 "shotUrl": string,
 "height": int,
 "width": int,
 "thumbnailUrl": string 
 "author": string,
 "date": string,
 "score": int,
 "ID": int,
 "epochTime": int,
 "spoiler": bool,
 "colorName": string }
```
 
 
The "score" field represents the number of unique users reacting to the shot, acting as a measure of its popularity. This value will be updated when the bot runs the reaction checks.
The "date" field follows the format `Year`-`Month`-`Day`T`Hour`:`Minute`:`Second`.`Millisecond` and indicates the date and time the shot was curated.
The "ID" value is the value the tinyDB assigns to the element of the structure being described and the epochTime is the epoch time of the shot. Both can be used to iterate and sort, but I would say the latter one is more reliable.
The "author" value is the authorid used in the authors DB.
The "colorName" field holds the name of the most prominent color in the shot, which can be useful for color-based searches or other related functionalities.
The "spoiler" field indicates whether the shot is tagged as a spoiler or contains NSFW content, allowing for appropriate handling when displaying the shot on the gallery or other platforms.

 
### Authors DB
 
```
{"authorNick": string,
 "authorid": string,
 "authorsAvatarUrl": string,
 "flickr": string,
 "twitter": string,
 "instagram": string,
 "steam": string,
 "othersocials": [string]}
 ```
 
- The "authorsNick" field represents the latest nickname retrieved for the user.
- The "authorid" field corresponds to the internal value assigned by Discord to the user.
- The "authorsAvatarUrl" field contains the URL of the user's avatar.
- The "flickr", "twitter", "instagram", and "steam" fields store the corresponding links for those specific websites.
- The "othersocials" field is a list that can hold links from websites not covered by the mentioned platforms.

## TODO

- Upload the last version of the bot, with all the latest features.
- Update the readme to describe said features and clarify the set up.
- Delete prototype functions and make the code more clear.
- Take the config options such as the channels being used into the config env file, to make it easier to setup for other peopone and update the github version of the bot from the work I do on the one in production.
- Modularize it in multiple files.
- Refactor the fuck out of it.
 
## Final notes
 
I developed this bot during a free week I had, and it has gradually evolved since then. I apologize for not designing it to be easily usable by others on their own hosting platforms. However, I hope the code and explanations provided here are sufficient for you to set it up yourself.
