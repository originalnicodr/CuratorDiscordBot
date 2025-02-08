# CuratorBot
CuratorBot is a dedicated Discord bot that specializes in selecting the finest screenshots from one channel and forwarding them to another channel. Additionally, it uploads the shots to Backblaze and updates .json database files stored on a GitHub repository.

You can visit the website where the screenshots are displayed at [this link](https://framedsc.com/HallOfFramed/), and learn more about the process behind creating this bot in my [blog post](https://originalnicodr.github.io/blog/how-we-made-a-high-quality-image-gallery-without-paying-a-single-dime).

Since this bot was developed for a specific server, it includes certain assumptions. For instance, it searches for a message with contextual information when a screenshot message lacks explicit details about the game. Therefore, if you decide to host your own version of the bot, please bear in mind that you may need to make adjustments to accommodate your specific requirements.

<p align="center"><img src="https://user-images.githubusercontent.com/24371572/104781820-eb88fe00-5761-11eb-91d0-6daf4448ebad.png"><p>

In addition, the bot creates a comprehensive database of authors, which contains valuable information. This author's database is continuously updated whenever a shot is accepted into the shots database or when a message is sent to the socials channel, ensuring that the authors' information is added or updated accordingly.

## How it Works
The determination of "best screenshots" is based on the amount of unique users reacting to a message containing the shot. There are more algorithms that we played around with but this one proved to be by far the best metric.

Also, if no new shot has been pushed in the last couple of days, the bot will do a special type of curation in which it temporarily reduces the threshold to get some in.

## SetUp
To setup this as your own bot you will need to create an `.env` file with the discord bot token inside:

```
DISCORD_TOKEN={token}
GIT_TOKEN={token}
BACKBLAZE_KEY={key}
BACKBLAZE_KEY_ID={id}
BACKBLAZE_HOF_FOLDER_NAME={folder_name}
BACKBLAZE_TEST_FOLDER_NAME={folder_name}
BACKBLAZE_BUCKET_NAME={bucket_name}
```

Later on, you will also need to modify the following settings to customize the bot's behavior:

1. **Input Channel:** This is the channel where the bot will search for messages containing screenshots.
2. **Output Channel:** The bot will send the accepted messages (screenshots) to this channel.
4. **Socials Channel:** The bot retrieves social links for the authors' database from this channel.

You would need to edit the getchannel function to point towards the right server tho.

To change the repo where the bot will push change the link in the **Github integration** section.

To change the thumbnail options (extension of the file, size, filter used in the resizing, etc.) check the **Thumbnail creation** section.

The bot can ignore shots from people that have a specific role. To specify the names rol change it in the **is_user_ignored** function.

## Usage
The commands can be accepted via DMs, but these are only accepted by mods. Check the is_user_allowed and is_member_mod functions to edit that.

I made this bot to be able to curate retroactively, so the correct way to use it after setting it up would be to use the **!dawnoftimecuration** to curate all past screenshots.

If for some reason the bot goes offline, whenever it gets online again it will curate from where it left it to not miss any shot.

## Commands
Here is an updated list of commands for your bot:

- **!curationsince**: Curates the shots that are less than a certain number of days old.
- **!dawnoftimecuration**: Curates a designated channel since it was created.
- **!startcurating**: Starts actively curating shots from a specified number of days ago.
- **!forcepost MESSAGE_ID**: Forces the bot to post a message regardless of the number of reactions. Ensure that the MESSAGE_ID belongs to the input channel. Only force posts with an image attachment or text containing only an external image URL.
- **!forceremovepost HOF_ID**: Forces the bot to remove a shot posted in the message with the specified ID. Ensure that the ID is correct.
- **!forceremoveauthor AUTHOR_NICK**: Forces the bot to remove all shots from the author with the specified Discord ID (Nickname, e.g., JohnDoe#1234).
- **!updategamename HOF_ID "new name"**: If someone wrote the name of the game incorrectly when sharing a shot (or the bot picked up the wrong one depending on upload timing) then you can fix the name of the entry with this command.
- **!isshotonhof MESSAGE_ID**: Quick check if the shot is already on the HOF database.
- **!updatesocials**: If for some reason the user hasn't gotten their socials updated (that includes their name and avatar) they can send this command to the bot and it will do so. This command can be executed by anyone.
- **!hofcandidates AUTHOR_NICK**: When removing the rol that blocks a user from getting their shots pushed (as in, they were new) you can use this command to get a list of shots that would have gotten picked up if they weren't for the role blocking them, in case you want to manually push some of them. Keep in mind that this retrieves all messages in the sharing shot channel and checks the ones from this user, so if the user has joined the server a long time ago it might take a while to finish.
**!hofhitrate**: Create a report indicating how many of the shots in the last three weeks have been gotten into the hof, to adjust the threshold based on a specific number you want to achieve. It also does it automatically every Monday.
- **!help**: Show this help message.



Please note the instructions and warnings mentioned in the descriptions of the commands. Ensure that the message IDs provided correspond to the input channel to avoid any issues.

## JSON Database structure
The .json file generated, modified, and pushed by the bot follows a structure that includes elements with the following format:

### Shots DB
```
{
   "gameName": str,
   "shotUrl": str,
   "height": int,
   "width": int,
   "thumbnailUrl": str,
   "author": str,
   "date": str,
   "score": int,
   "ID": int,
   "epochTime": int,
   "spoiler": bool,
   "colorName": str,
   "message_id": int
}
```

- The "score" field represents the number of unique users reacting to the shot, acting as a measure of its popularity. This value will be updated when the bot runs the reaction checks.
- The "date" field follows the format `Year`-`Month`-`Day`T`Hour`:`Minute`:`Second`.`Millisecond` and indicates the date and time the shot was curated.
- The "ID" value is the value the tinyDB assigns to the element of the structure described and the epochTime is the Unix time in which the shot got picked up. Both can be used to iterate and sort, but I would say the latter one is more reliable.
- The "author" value is the authorid used in the author DB.
- The "colorName" field holds the name of the most prominent color in the shot, which can be useful for color-based searches or other related functionalities.
- The "spoiler" field indicates whether the shot is tagged as a spoiler or contains NSFW content, allowing for appropriate handling when displaying the shot on the gallery or other platforms.

### Authors DB
```
{
   "authorNick": string,
   "authorid": string,
   "authorsAvatarUrl": string,
   "socials": [string]
}
 ```

- The "authorsNick" field represents the latest nickname retrieved for the user.
- The "authorid" field corresponds to the internal value assigned by Discord to the user.
- The "authorsAvatarUrl" field contains the URL of the user's avatar.
- The "socials" field is a list that can hold links from websites the user shared in the share-your-socials channel.

## Final notes
I developed this bot during a free week I had, and it has gradually evolved since then. I apologize for not designing it to be easily usable by others on their own hosting platforms. However, I hope the code and explanations provided here are sufficient for you to set it up yourself.
