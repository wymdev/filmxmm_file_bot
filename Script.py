class script(object):
    START_TXT = """<b>🎬 {2}</b>

Hi {0}!

Find and receive your movies instantly.

Send a movie name, use search, or open one of our movie links."""
    START_TXT = START_TXT + """

🇲🇲 မင်္ဂလာပါ {0}။

ရုပ်ရှင်များကို လွယ်ကူလျင်မြန်စွာ ရှာဖွေပြီး ရယူနိုင်ပါသည်။

ရုပ်ရှင်အမည်ပို့ပါ၊ Search ကိုသုံးပါ သို့မဟုတ် ရုပ်ရှင်လင့်ခ်ကို ဖွင့်ပါ။"""
    HELP_TXT = """𝙷𝙴𝚈 {0}
𝙷𝙴𝚁𝙴 𝙸𝚂 𝚃𝙷𝙴 𝙷𝙴𝙻𝙿 𝙵𝙾𝚁 𝙼𝚈 𝙲𝙾𝙼𝙼𝙰𝙽𝙳𝚂.

🇲🇲 မင်္ဂလာပါ {0}။ Bot command များ၏ အကူအညီကို အောက်တွင် ကြည့်နိုင်ပါသည်။"""
    ABOUT_TXT = """✯ 𝙼𝚈 𝙽𝙰𝙼𝙴: {}
✯ 𝙲𝚁𝙴𝙰𝚃𝙾𝚁: <a href=https://t.me/FilmX_Group>FilmX</a>
✯ 𝙻𝙸𝙱𝚁𝙰𝚁𝚈: 𝙿𝚈𝚁𝙾𝙶𝚁𝙰𝙼
✯ 𝙻𝙰𝙽𝙶𝚄𝙰𝙶𝙴: 𝙿𝚈𝚃𝙷𝙾𝙽 𝟹
✯ 𝙳𝙰𝚃𝙰 𝙱𝙰𝚂𝙴: 𝙼𝙾𝙽𝙶𝙾 𝙳𝙱"""
    SOURCE_TXT = """<b>Source Code Of This Bot is provided by FilmX 😊"""
    MANUELFILTER_TXT = """Help: <b>Filters</b>

- Filter is the feature were users can set automated replies for a particular keyword and 𝐉𝐞𝐫𝐫𝐲 will respond whenever a keyword is found the message

<b>NOTE:</b>
1. 𝐉𝐞𝐫𝐫𝐲 should have admin privillage.
2. only admins can add filters in a chat.
3. alert buttons have a limit of 64 characters.

<b>Commands and Usage:</b>
• /filter - <code>add a filter in chat</code>
• /filters - <code>list all the filters of a chat</code>
• /del - <code>delete a specific filter in chat</code>
• /delall - <code>delete the whole filters in a chat (chat owner only)</code>

<b>🇲🇲 Filter အကူအညီ</b>
Filter သည် သတ်မှတ်ထားသော keyword တွေ့သည့်အခါ bot က အလိုအလျောက် ပြန်ကြားပေးသော လုပ်ဆောင်ချက်ဖြစ်ပါသည်။

<b>မှတ်ချက်:</b>
1. Bot ကို admin ခန့်ထားရပါမည်။
2. Admin များသာ filter ထည့်နိုင်ပါသည်။
3. Alert button စာသားသည် စာလုံးရေ ၆၄ လုံးထက် မပိုရပါ။

• /filter - <code>filter ထည့်ရန်</code>
• /filters - <code>filter အားလုံးကြည့်ရန်</code>
• /del - <code>filter တစ်ခုဖျက်ရန်</code>
• /delall - <code>filter အားလုံးဖျက်ရန် (ပိုင်ရှင်သာ)</code>"""
    BUTTON_TXT = """Help: <b>Buttons</b>

- 𝐉𝐞𝐫𝐫𝐲 Supports both url and alert inline buttons.

<b>NOTE:</b>
1. Telegram will not allows you to send buttons without any content, so content is mandatory.
2. 𝐉𝐞𝐫𝐫𝐲 supports buttons with any telegram media type.
3. Buttons should be properly parsed as markdown format

<b>URL buttons:</b>
<code>[Button Text](buttonurl:https://t.me/EnthadaNokunne)</code>

<b>Alert buttons:</b>
<code>[Button Text](buttonalert:This is an alert message)</code>

<b>🇲🇲 Button အကူအညီ</b>
Bot သည် URL button နှင့် alert button နှစ်မျိုးလုံးကို ပံ့ပိုးပါသည်။ Button တစ်ခုတည်း ပို့၍မရသောကြောင့် စာသား သို့မဟုတ် media နှင့်အတူ ပို့ရပါမည်။ Button များကို Markdown ပုံစံမှန်ကန်စွာ ရေးသားပါ။"""
    AUTOFILTER_TXT = """Help: <b>Auto Filter</b>

<b>NOTE:</b>
1. Make me the admin of your channel if it's private.
2. make sure that your channel does not contains camrips, porn and fake files.
3. Forward the last message to me with quotes.
 I'll add all the files in that channel to my db.

<b>🇲🇲 Auto Filter မှတ်ချက်</b>
1. Private channel ဖြစ်ပါက bot ကို admin ခန့်ထားပါ။
2. မမှန်ကန်သော သို့မဟုတ် မသင့်လျော်သောဖိုင်များ မပါဝင်ကြောင်း စစ်ဆေးပါ။
3. Channel ၏ နောက်ဆုံးမက်ဆေ့ချ်ကို quote ဖြင့် bot ထံ forward လုပ်ပါ။ Bot က ဖိုင်များကို database ထဲ ထည့်ပေးပါမည်။"""
    CONNECTION_TXT = """Help: <b>Connections</b>

- Used to connect bot to PM for managing filters 
- it helps to avoid spamming in groups.

<b>NOTE:</b>
1. Only admins can add a connection.
2. Send <code>/connect</code> for connecting me to ur PM

<b>Commands and Usage:</b>
• /connect  - <code>connect a particular chat to your PM</code>
• /disconnect  - <code>disconnect from a chat</code>
• /connections - <code>list all your connections</code>

<b>🇲🇲 Connection အကူအညီ</b>
Group filter များကို private chat မှ စီမံရန် bot နှင့် group ကို ချိတ်ဆက်ပေးပါသည်။ Admin များသာ ချိတ်ဆက်နိုင်ပါသည်။

• /connect - <code>group ကို ချိတ်ဆက်ရန်</code>
• /disconnect - <code>ချိတ်ဆက်မှုဖြုတ်ရန်</code>
• /connections - <code>ချိတ်ဆက်ထားသမျှ ကြည့်ရန်</code>"""
    EXTRAMOD_TXT = """Help: <b>Extra Modules</b>

<b>NOTE:</b>
these are the extra features of Eva Maria

<b>Commands and Usage:</b>
• /id - <code>get id of a specified user.</code>
• /info  - <code>get information about a user.</code>
• /imdb  - <code>get the film information from IMDb source.</code>
• /search  - <code>get the film information from various sources.</code>

<b>🇲🇲 အပိုလုပ်ဆောင်ချက်များ</b>
• /id - <code>အသုံးပြုသူ ID ရယူရန်</code>
• /info - <code>အသုံးပြုသူအချက်အလက် ကြည့်ရန်</code>
• /imdb - <code>IMDb ရုပ်ရှင်အချက်အလက် ရယူရန်</code>
• /search - <code>ရုပ်ရှင်အချက်အလက် ရှာဖွေရန်</code>"""
    ADMIN_TXT = """Help: <b>Admin mods</b>

<b>NOTE:</b>
This module only works for my admins

<b>Commands and Usage:</b>
• /logs - <code>to get the rescent errors</code>
• /stats - <code>to get status of files in db.</code>
• /delete - <code>to delete a specific file from db.</code>
• /users - <code>to get list of my users and ids.</code>
• /chats - <code>to get list of the my chats and ids </code>
• /leave  - <code>to leave from a chat.</code>
• /disable  -  <code>do disable a chat.</code>
• /ban  - <code>to ban a user.</code>
• /unban  - <code>to unban a user.</code>
• /channel - <code>to get list of total connected channels</code>
• /broadcast - <code>to broadcast a message to all users</code>

<b>🇲🇲 Admin လုပ်ဆောင်ချက်များ</b>
ဤ command များကို သတ်မှတ်ထားသော bot admin များသာ အသုံးပြုနိုင်ပါသည်။
• /logs - <code>error log များရယူရန်</code>
• /stats - <code>database အခြေအနေကြည့်ရန်</code>
• /delete - <code>ဖိုင်တစ်ခုဖျက်ရန်</code>
• /users၊ /chats - <code>အသုံးပြုသူနှင့် chat စာရင်းကြည့်ရန်</code>
• /ban၊ /unban - <code>အသုံးပြုသူကို ပိတ်ရန်/ပြန်ဖွင့်ရန်</code>
• /broadcast - <code>အသုံးပြုသူအားလုံးထံ မက်ဆေ့ချ်ပို့ရန်</code>"""
    STATUS_TXT = """★ 𝚃𝙾𝚃𝙰𝙻 𝙵𝙸𝙻𝙴𝚂: <code>{}</code>
★ 𝚃𝙾𝚃𝙰𝙻 𝚄𝚂𝙴𝚁𝚂: <code>{}</code>
★ 𝚃𝙾𝚃𝙰𝙻 𝙲𝙷𝙰𝚃𝚂: <code>{}</code>
★ 𝚄𝚂𝙴𝙳 𝚂𝚃𝙾𝚁𝙰𝙶𝙴: <code>{}</code> 𝙼𝚒𝙱
★ 𝙵𝚁𝙴𝙴 𝚂𝚃𝙾𝚁𝙰𝙶𝙴: <code>{}</code> 𝙼𝚒𝙱"""
    LOG_TEXT_G = """#NewGroup
Group = {}(<code>{}</code>)
Total Members = <code>{}</code>
Added By - {}
"""
    LOG_TEXT_P = """#NewUser
ID - <code>{}</code>
Name - {}
"""
