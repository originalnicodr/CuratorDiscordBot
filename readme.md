<p align="center"><img src="https://user-images.githubusercontent.com/24371572/104768884-1fa5f400-574d-11eb-93c4-10b24f8ce06e.jpg">
 
# <p align="center">CuratorBot</p>
 
  <a href="https://github.com/Rapptz/discord.py/">
     <img src="https://img.shields.io/badge/discord-py-blue.svg" alt="discord.py"></a>
 
## About
 
CuratorBot is a bot dedicated to select the best screenshots from a channel and resents them to another channel.
 
Since I made this for a server I am in it has a lot of assumptions, like searching for a message with text around the screenshot message if this one has no text specifying the game, so I apologise for it.
 
<p align="center"><img src="https://user-images.githubusercontent.com/24371572/104781820-eb88fe00-5761-11eb-91d0-6daf4448ebad.png">
 
## How does it work
 
The concept of "best screenshots" is determined by the reactions of the messages where the images are, so I made a number of algorithms to use these reactions in order to determine if the image is worth resenting.
 
### Algorithms
 
- Basic Curation: Simplest of algorithms, takes the amount of times people reacted to the most reacted emoji of the message and compares it to a trigger value. If the number taken is bigger than said trigger the message is resent.
 
- Historical Curation: Given the start of a channel (this has to be hardcoded since I was getting a wrong date with the created_at method, sorry) and a "min" a "max" value it does a linear interpolation with said values and a value representing how new is a message so it can vaguely understand the grow of a server overtime. The result of this linear interpolation is used as a trigger value like the Basic Curation.
 
- Extended Curation: The same as Historical Curation but besides taking the amount of the most reacted emoji it also counts the other emojis as well, reduced by a constant.
 
 
All algorithms also check if the message has an image, if not they discard the message.
 
## SetUp
 
To setup this as your own bot you will need to create an `.env` file with the discord bot token inside:
 
```
DISCORD_TOKEN=yourbotdiscordtoken
```
 
Later you will have to change the input channel (where the bot looks up for screenshots) and the output channel (where the bot will send the accepted screenshots). You can change these values on runtime or change the initial values from the code, alongside the curation algorithm used and its values.
 
Keep in mind that you can discriminate between different servers for the input and output channels.
 
## Usage
 
The commands can only be accepted in the channel where the images will be sent.
 
I made this bot for being able to curate retroactively, so the correct way to use it after setting it up would be to use the **!dawnoftimecuration** to curate all past screenshots, and later use **!starcurating** to constantly check for new screenshots for the bot to resent.
 
## Commands
