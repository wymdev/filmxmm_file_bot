"""Shared English/Myanmar user-facing messages."""


def bilingual(english, myanmar):
    return f"{english}\n\n🇲🇲 {myanmar}"


DATABASE_UNAVAILABLE = bilingual(
    "Give me a moment — the database's taking a quick breather. Try again in a few minutes!",
    "ခဏစောင့်ပေးပါနော် — ဒေတာဘေ့စ်က ခဏငြိနေလို့ပါ။ မိနစ်အနည်းငယ်ကြာရင် ပြန်စမ်းကြည့်ပါ!",
)
PREPARING_FILES = bilingual(
    "Getting your files ready…",
    "သင့်ဖိုင်တွေကို ပြင်ဆင်နေပါတယ်နော်…",
)
BATCH_INVALID = bilingual(
    "This link looks broken or has expired.",
    "ဒီလင့်ခ်က မမှန်ကန်တော့ဘူး၊ ဒါမှမဟုတ် သက်တမ်းကုန်သွားပြီနော်။",
)
BATCH_EMPTY = bilingual(
    "Hmm, there aren't any files in this batch.",
    "ဟင်… ဒီ batch ထဲမှာ ဖိုင်တွေ မရှိဘူးနော်။",
)
SOURCE_UNAVAILABLE = bilingual(
    "I couldn't reach the source channel for this batch.",
    "ဒီ batch ရဲ့ မူရင်းချန်နယ်ကို ဖတ်လို့မရဘူးနော်။",
)
NO_MESSAGES = bilingual(
    "No messages turned up in this batch.",
    "ဒီ batch ထဲမှာ မက်ဆေ့ချ်တွေ မတွေ့ဘူးနော်။",
)
NO_SUCH_FILE = bilingual(
    "Couldn't find that file — it may have been removed or its link expired.",
    "ဒီဖိုင်ကို ရှာမတွေ့ဘူးနော် — ဖျက်ထားလိုက်တာ ဒါမှမဟုတ် သက်တမ်းကုန်သွားတာ ဖြစ်နိုင်ပါတယ်။",
)
PROCESSING = bilingual("Working on it… ⏳", "လုပ်ဆောင်နေပါတယ်နော်… ⏳")
JOIN_LOOKUP_FAILED = bilingual(
    "I couldn't reach the channel right now — give it another try in a bit.",
    "အခုချိန်မှာ လိုအပ်တဲ့ချန်နယ်ကို ဖွင့်လို့မရသေးဘူး — ခဏနေရင် ထပ်စမ်းကြည့်ပါနော်။",
)
JOIN_REQUIRED_ALERT = bilingual(
    "❌ Join the channel first, then try again!",
    "❌ ချန်နယ်ကို အရင်ဝင်ပါဦးနော်။",
)
REQUEST_FINISHED = bilingual(
    "This one's already been delivered, or the request expired.",
    "ဒီတောင်းဆိုမှုကို ပို့ပြီးသားပါ၊ ဒါမှမဟုတ် သက်တမ်းကုန်သွားပြီနော်။",
)
MEMBERSHIP_VERIFIED = bilingual(
    "✅ You're in!\n\n🎬 Sending your movie…",
    "✅ အဖွဲ့ဝင်ဖြစ်ကြောင်း အတည်ပြုပြီးပါပြီ!\n\n🎬 သင့်ရုပ်ရှင်ကို ပို့နေပါပြီနော်…",
)
MEMBERSHIP_VERIFIED_SHORT = bilingual(
    "You're verified — your movie's on its way!",
    "အတည်ပြုပြီးပါပြီ — ရုပ်ရှင်ရောက်တော့မယ်နော်!",
)
FORCE_JOIN_TEXT = (
    "<b>🔐 Almost there!</b>\n\n"
    "Just join our official channel and this movie is all yours.\n\n"
    "✨ Once you've joined, I'll send it your way automatically.\n\n"
    "<b>🇲🇲 နောက်တစ်ဆင့်ပဲ ကျန်တော့တယ်!</b>\n\n"
    "ကျွန်တော်တို့ရဲ့ တရားဝင်ချန်နယ်ကို ဝင်လိုက်ရုံနဲ့ ဒီရုပ်ရှင်ကို ရရှိပါပြီ။\n\n"
    "✨ ဝင်ပြီးတာနဲ့ ရုပ်ရှင်ကို အလိုအလျောက် ပို့ပေးပါ့မယ်နော်။"
)
DELETE_REPLY_REQUIRED = bilingual(
    "Reply to the file you'd like removed with /delete.",
    "ဖျက်ချင်တဲ့ ဖိုင်ကို reply လုပ်ပြီး /delete လို့ ပို့ပါနော်။",
)
UNSUPPORTED_FILE = bilingual(
    "Sorry, this file type isn't supported.",
    "စိတ်မကောင်းပါဘူး၊ ဒီဖိုင်အမျိုးအစားကို ပံ့ပိုးမထားသေးပါဘူး။",
)
FILE_DELETED = bilingual(
    "Done — that file's been removed from the database.",
    "ပြီးပါပြီ — ဒီဖိုင်ကို ဒေတာဘေ့စ်ကနေ ဖျက်လိုက်ပါပြီ။",
)
FILE_NOT_IN_DATABASE = bilingual(
    "Couldn't find that file in the database.",
    "ဒီဖိုင်ကို ဒေတာဘေ့စ်ထဲမှာ ရှာမတွေ့ပါဘူး။",
)
DELETE_ALL_CONFIRM = bilingual(
    "Heads up — this wipes every indexed file. Still want to go ahead?",
    "သတိပေးချက် — ဒါက မှတ်တမ်းတင်ထားသမျှ ဖိုင်အားလုံးကို ဖျက်ပစ်ပါမယ်။ ဆက်လုပ်ချင်သေးလား?",
)
FILES_DELETED = bilingual(
    "All done — every indexed file has been deleted.",
    "ပြီးပါပြီ — မှတ်တမ်းတင်ထားတဲ့ ဖိုင်အားလုံးကို ဖျက်ပြီးပါပြီ။",
)
BOT_NOT_IN_GROUP = bilingual(
    "Double-check that I'm in your group and have the right permissions.",
    "Bot ကို group ထဲမှာ ထည့်ထားပြီး၊ လိုအပ်တဲ့ permission တွေ ပေးထားကြောင်း စစ်ကြည့်ပါနော်။",
)
NOT_CONNECTED = bilingual(
    "I'm not linked to any group yet — use /connect there first.",
    "ကျွန်တော် group တစ်ခုနဲ့မှ မချိတ်ဆက်ရသေးပါဘူး — group ထဲမှာ /connect ကို အရင်သုံးပါနော်။",
)
GENERIC_ERROR = bilingual(
    "Oops, something went wrong — try again in a bit.",
    "အိုး၊ တစ်ခုခု မှားသွားပါပြီ — နည်းနည်းနေရင် ထပ်စမ်းကြည့်ပါနော်။",
)
NO_INPUT = bilingual(
    "Looks like you didn't type anything.",
    "ဘာမှ မထည့်ရသေးဘူးနော်။",
)
