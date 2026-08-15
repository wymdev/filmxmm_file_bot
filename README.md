# FilmX File Sharing Bot

> **Notice:** This project is a fork of the original [Advance-File-Share-Bot by VJBots](https://github.com/VJBots/Advance-File-Share-Bot). 
> Continued development and maintenance by **FilmX**.
> © FilmX. All Rights Reserved where applicable, under the original GNU General Public License.

Telegram Bot to store Posts and Documents that can be accessed via Special Links.
Optimized for FilmX community deployments. 

##

**If you need any more modes in repo or If you find out any bugs, mention in [@support ](https://t.me/vj_bot_disscussion)**

**Make sure to see [contributing.md](https://github.com/VJBots/Advance-File-Share-Bot/blob/main/CONTRIBUTING.md) for instructions on contributing to the project!**



### Features
- Request To Join Force Subscribe Feature
- Fully customisable.
- Customisable welcome & Forcesub messages.
- More than one Posts in One Link.
- Can be deployed deploy anywhere directly.

### Setup

- Create a bot with [@BotFather](https://t.me/BotFather) and get Telegram API credentials from [my.telegram.org](https://my.telegram.org).
- Create a MongoDB database and copy `.env.example` to `.env` for local use.
- Add the bot to the channels listed in `CHANNELS` and `LOG_CHANNEL` with the permissions needed to read and send messages.
- If force subscribe is enabled, add the bot to `AUTH_CHANNEL` or `REQ_CHANNEL` as an admin with invite-user permission.

The bot validates required configuration during startup. It will report the exact missing variable instead of using embedded credentials.

##
### Installation
#### Deploy on Heroku
**BEFORE YOU DEPLOY ON HEROKU, YOU SHOULD FORK THE REPO AND CHANGE ITS NAME TO ANYTHING ELSE**<br>
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)</br>
<a href="">
  <img src="https://img.shields.io/badge/How%20to-Deploy-red?logo=youtube" width="147">
</a><br>
**Check This Tutorial Video on YouTube for any Help**<br>
**Thanks to [Tech VJ](https://t.me/VJ_Botz) and his [Tech VJ](https://youtube.com/@Tech_VJ) for this Video**

#### Deploy on Railway
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template/1jKLr4)

#### Deploy on Koyeb

The fastest way to deploy the application is to click the **Deploy to Koyeb** button below.


[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?type=git&repository=github.com/VJBots/Advance-File-Share-Bot&branch=Tech_VJ&name=filesharingbot)


#### Deploy in your VPS
````bash
git clone <your-repository-url>
cd filmxbot
cp .env.example .env
# Edit .env with your deployment values.
pip3 install -r requirements.txt
python3 bot.py
````

### Admin Commands

```
/start - start the bot or get posts

/batch - create link for more than one posts

/link - create link for one post

/status - view bot statistics

/broadcast - broadcast any messages to bot users

/stats - checking your bot uptime
```

### Variables

- `API_ID`, `API_HASH`, `BOT_TOKEN`: required Telegram credentials.
- `DATABASE_URI`: required MongoDB connection string.
- `ADMINS`: required, space-separated Telegram user IDs or usernames.
- `LOG_CHANNEL`: required Telegram channel ID used for logs and stored batch data.
- `CHANNELS`: optional space-separated source channel IDs or usernames to index.
- `DATABASE_NAME`: optional database name; defaults to `FilmXBot`.
- `COLLECTION_NAME`: optional media collection; defaults to `Telegram_files`.
- `AUTH_CHANNEL`: optional force-subscribe channel ID.
- `REQ_CHANNEL`: optional request-to-join channel ID.
- `FILE_STORE_CHANNEL`: optional space-separated channel IDs used for direct-store links.
- `PROTECT_CONTENT`: optional boolean controlling forwarding protection.
- `USE_CAPTION_FILTER`: optional boolean enabling caption search.

See [.env.example](.env.example) for a minimal working configuration.

### Extra Variables

- `CUSTOM_FILE_CAPTION`: custom HTML caption for delivered files.
- `BATCH_FILE_CAPTION`: custom HTML caption for batch-delivered files.
- `PUBLIC_FILE_STORE`: allow all users to create share links when enabled.
- `CACHE_TIME`: inline result cache duration in seconds.
- `PICS`: space-separated image URLs used by bot responses.


### Fillings
#### START_MESSAGE | FORCE_SUB_MESSAGE

* `{first}` - User first name
* `{last}` - User last name
* `{id}` - User ID
* `{mention}` - Mention the user
* `{username}` - Username

#### CUSTOM_CAPTION

* `{filename}` - file name of the Document
* `{previouscaption}` - Original Caption

#### CUSTOM_STATS

* `{uptime}` - Bot Uptime


## Support   
Join Our [Telegram Group](https://www.telegram.dog/vj_bot_disscussion) For Support/Assistance And Our [Channel](https://www.telegram.dog/VJ_Botz) For Updates.   
   
Report Bugs, Give Feature Requests There..   

### Credits

- Thanks To Dan For His Awsome [Libary](https://github.com/pyrogram/pyrogram)
- Our Support Group Members

### Licence
[![GNU GPLv3 Image](https://www.gnu.org/graphics/gplv3-127x51.png)](http://www.gnu.org/licenses/gpl-3.0.en.html)  

[FILE-SHARING-BOT](https://github.com/VJBots/Advance-File-Share-Bot) is Free Software: You can use, study share and improve it at your
will. Specifically you can redistribute and/or modify it under the terms of the
[GNU General Public License](https://www.gnu.org/licenses/gpl.html) as
published by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version. 

##

   **Star this Repo if you Liked it ⭐⭐⭐**
