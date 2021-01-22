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
     <img src="https://img.shields.io/badge/pillow-8.1.0-blue.svg" alt="discord.py"></a>
  <a href="https://github.com/psf/requests">
     <img src="https://img.shields.io/badge/requests-2.22.0-blue.svg" alt="discord.py"></a>
 
## About
 
CuratorBot is a bot dedicated to selecting the best screenshots from a channel and sending them to another channel. In addition, it uses discord as a host for a website and exports a .json database to a github repo (I don't like to pay for good hosting, sorry).
 
Since I made this for a server I am in, it has a lot of assumptions, like searching for a message with text around the screenshot message if this one has no text specifying the game, so I apologise for it.
 
<p align="center"><img src="https://user-images.githubusercontent.com/24371572/104781820-eb88fe00-5761-11eb-91d0-6daf4448ebad.png">
 
The bot puts every curated shot link in a .json file, creates a thumbnail which is also uploaded to discord and includes it in said .json file and pushes it to a github repo, so the file can be used as a database for a website showing the screenshots and the bot as an updater for said database.
 
## How does it work
 
The concept of "best screenshots" is determined by the reactions of the messages where the images are, so I made a number of algorithms to use these reactions in order to determine if the image is worth sending.
 
### Algorithms
 
- Basic Curation: Simplest of algorithms, takes the amount of times people reacted to the most reacted emoji of the message and compares it to a trigger value. If the number taken is bigger than said trigger the message is sent.
 
- Historical Curation: Given the start of a channel (this has to be hardcoded since I was getting a wrong date with the created_at method, sorry) and a "min" a "max" value it does a linear interpolation with said values and a value representing how new is a message so it can vaguely understand the grow of a server overtime. The result of this linear interpolation is used as a trigger value like the Basic Curation.
 
- Extended Curation: Like Basic Curation but besides taking the amount of the most reacted emoji it also counts the other emojis as well, reduced by a constant.
 
- CompleteCuration: A combination of Historical Curation and Extended Curation
 
All algorithms also check if the message has an image, if not they discard the message.
 
## SetUp
 
To setup this as your own bot you will need to create an `.env` file with the discord bot token inside:
 
```
DISCORD_TOKEN=yourDiscordBotToken
GIT_TOKEN=githubPersonalAccessTokens
```
 
Later you will have to change the input channel (where the bot looks up for messages), the output channel (where the bot will send the accepted messages) and the thumbnail channel (where the bot will drop the thumbnails it makes).
 
You can change the curation algorithms and their values from the code. The info is in the **Constants** section and at the start of each algorithm function.
 
Keep in mind that you can also discriminate between different servers for the input and output channels in the **getchannel** functions.
 
To change the repo where the bot will push change the link in the **Github integration** section.
 
To change the the thumbnails options (extension of the fil, size, filter used in the resizing, etc.) check the **Thumbnail creation** section.
 
## Usage
 
The commands can only be accepted in the channel where the images will be sent.
 
I made this bot for being able to curate retroactively, so the correct way to use it after setting it up would be to use the **!dawnoftimecuration** (using a new, clean channel as an output channel) to curate all past screenshots, and later use **!starcurating** to constantly check for new screenshots for the bot to send. If for some reason the bot goes offline, whenever it gets online again it will curate from where he was (make sure to run the **!dawnoftimecuration** command first).
 
## Commands
 
  - **!curationsince**:       Curate the shots that are less than a certain number of days old.
  - **!dawnoftimecuration**:  Curate a seated up channel since it was created.
  - **!startcurating**: Start actively curating the shots since the number of days specified by the daystocheck value.
   - **!forcepost MESSAGE_ID**: Force the bot to post a message regardless of the amount of reactions. **ATTENTION**: a MESSAGE_ID that doesnt belongs to the inputchannel will crash the bot. Make sure to only force posts with an image in an attachment (aka uploading it to discord) or text with ONLY an external image.url.
 
  - **!setcuratorintervals**: Define the time interval (in seconds) between the channel reactions check.
  - **!setdaystocheck**:      Define the maximum age of the messages to activly check.
  - **!setinputchannel**:     Define from what channel will the bot curate.
  - **!setoutputchannel**:    Define the channel where the curated messages will be sent.
 
  - **!help**: Show this help message.
 
  Do bear in mind that the values changed by the set commands work only on runtime. If you don't know if your bot will go down temporarily change the values in the file instead.
 
## JSON Database structure
 
The .json file generated, modified and pushed by the bot consists of elements of the following structure
 
```
{"gameName": string,
 "shotUrl": string,
 "height": int,
 "width": int,
 "thumbnailUrl": string 
 "author": string,
 "authorsAvatarUrl": string,
 "date": string,
 "score": int,
 "ID": int,
 "iteratorID": int}
```
 
 
The "score" value represents the amount of "points" the shot got before being picked up by the bot. The way is set up is the amount of reactions of the most reacted emoji.
The "date" is using the format `Year`-`Month`-`Day`T`Hour`:`Minute`:`Second`.`Millisecond`.
 
## To do
- The score value isnt updated after the shots get picked up, I could update it with every check pass the bot makes.
 
## Final notes
 
I made this bot in a free week that I had and it kinda grew up from there. Unfortunately I don't have time at the moment to learn front-end programming to make a website showing the shots. Hopefully someone will make one and I will be sure to include a link here whenever that happens.
 
I apologize that I didn't write the bot so everyone can use the one I am hosting. Hopefully the code and explanation here are enough for setting it up yourself, and if not I hope at least you learned something from it. I know I did.
