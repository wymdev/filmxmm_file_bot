"""Shared English/Myanmar user-facing messages."""


def bilingual(english, myanmar):
    return f"{english}\n\n🇲🇲 {myanmar}"


DATABASE_UNAVAILABLE = bilingual(
    "The database is temporarily unavailable. Please try again in a few minutes.",
    "ဒေတာဘေ့စ်ကို ယာယီအသုံးပြု၍ မရသေးပါ။ မိနစ်အနည်းငယ်ကြာပြီးနောက် ထပ်မံကြိုးစားပါ။",
)
PREPARING_FILES = bilingual(
    "Preparing your files…",
    "သင့်ဖိုင်များကို ပြင်ဆင်နေပါသည်…",
)
BATCH_INVALID = bilingual(
    "This batch link is invalid or has expired.",
    "ဤ batch လင့်ခ်သည် မမှန်ကန်ပါ သို့မဟုတ် သက်တမ်းကုန်သွားပါပြီ။",
)
BATCH_EMPTY = bilingual(
    "This batch does not contain any files.",
    "ဤ batch တွင် ဖိုင်မရှိပါ။",
)
SOURCE_UNAVAILABLE = bilingual(
    "I could not read the source channel for this batch.",
    "ဤ batch ၏ မူရင်းချန်နယ်ကို ဖတ်ရှု၍ မရပါ။",
)
NO_MESSAGES = bilingual(
    "No messages were found in this batch.",
    "ဤ batch တွင် မက်ဆေ့ချ်များ မတွေ့ပါ။",
)
NO_SUCH_FILE = bilingual(
    "This file could not be found. It may have been removed or expired.",
    "ဤဖိုင်ကို ရှာမတွေ့ပါ။ ဖယ်ရှားထားခြင်း သို့မဟုတ် သက်တမ်းကုန်ခြင်း ဖြစ်နိုင်ပါသည်။",
)
PROCESSING = bilingual("Processing… ⏳", "လုပ်ဆောင်နေပါသည်… ⏳")
JOIN_LOOKUP_FAILED = bilingual(
    "I couldn't open the required channel right now. Please try again shortly.",
    "လိုအပ်သောချန်နယ်ကို ယခုဖွင့်၍ မရသေးပါ။ ခဏကြာပြီးနောက် ထပ်မံကြိုးစားပါ။",
)
JOIN_REQUIRED_ALERT = bilingual(
    "❌ Please join the channel first.",
    "❌ ကျေးဇူးပြု၍ ချန်နယ်သို့ အရင်ဝင်ပါ။",
)
REQUEST_FINISHED = bilingual(
    "This request was already delivered or has expired.",
    "ဤတောင်းဆိုမှုကို ပို့ပြီးသား သို့မဟုတ် သက်တမ်းကုန်သွားပါပြီ။",
)
MEMBERSHIP_VERIFIED = bilingual(
    "✅ Membership verified!\n\n🎬 Sending your movie…",
    "✅ အဖွဲ့ဝင်ဖြစ်မှု အတည်ပြုပြီးပါပြီ။\n\n🎬 သင့်ရုပ်ရှင်ကို ပို့နေပါသည်…",
)
MEMBERSHIP_VERIFIED_SHORT = bilingual(
    "Membership verified — sending your movie.",
    "အဖွဲ့ဝင်ဖြစ်မှု အတည်ပြုပြီးပါပြီ — ရုပ်ရှင်ပို့နေပါသည်။",
)
FORCE_JOIN_TEXT = (
    "<b>🔐 One Step Left</b>\n\n"
    "Join our official channel to unlock this movie.\n\n"
    "✨ After joining, the bot will automatically send your movie.\n\n"
    "<b>🇲🇲 နောက်ဆုံးတစ်ဆင့်သာ ကျန်ပါသည်</b>\n\n"
    "ဤရုပ်ရှင်ကို ရယူရန် ကျွန်ုပ်တို့၏ တရားဝင်ချန်နယ်သို့ ဝင်ရောက်ပါ။\n\n"
    "✨ ဝင်ရောက်ပြီးသည်နှင့် bot က သင့်ရုပ်ရှင်ကို အလိုအလျောက် ပို့ပေးပါမည်။"
)
DELETE_REPLY_REQUIRED = bilingual(
    "Reply to the file you want to delete with /delete.",
    "ဖျက်လိုသောဖိုင်ကို reply လုပ်ပြီး /delete ပို့ပါ။",
)
UNSUPPORTED_FILE = bilingual(
    "This file format is not supported.",
    "ဤဖိုင်အမျိုးအစားကို မပံ့ပိုးပါ။",
)
FILE_DELETED = bilingual(
    "The file was deleted from the database.",
    "ဖိုင်ကို ဒေတာဘေ့စ်မှ ဖျက်ပြီးပါပြီ။",
)
FILE_NOT_IN_DATABASE = bilingual(
    "The file was not found in the database.",
    "ဖိုင်ကို ဒေတာဘေ့စ်တွင် မတွေ့ပါ။",
)
DELETE_ALL_CONFIRM = bilingual(
    "This will delete every indexed file. Do you want to continue?",
    "မှတ်တမ်းတင်ထားသောဖိုင်အားလုံးကို ဖျက်ပါမည်။ ဆက်လုပ်လိုပါသလား။",
)
FILES_DELETED = bilingual(
    "All indexed files were deleted successfully.",
    "မှတ်တမ်းတင်ထားသောဖိုင်အားလုံးကို အောင်မြင်စွာ ဖျက်ပြီးပါပြီ။",
)
BOT_NOT_IN_GROUP = bilingual(
    "Make sure the bot is present in your group and has the required permissions.",
    "Bot သည် သင့် group ထဲတွင်ရှိပြီး လိုအပ်သော permission များ ရရှိထားကြောင်း စစ်ဆေးပါ။",
)
NOT_CONNECTED = bilingual(
    "I'm not connected to any groups. Use /connect in a group first.",
    "မည်သည့် group နှင့်မျှ မချိတ်ဆက်ရသေးပါ။ Group ထဲတွင် /connect ကို အရင်အသုံးပြုပါ။",
)
GENERIC_ERROR = bilingual(
    "Something went wrong. Please try again later.",
    "တစ်ခုခု မှားယွင်းနေပါသည်။ ခဏကြာပြီးနောက် ထပ်မံကြိုးစားပါ။",
)
NO_INPUT = bilingual(
    "No input was provided.",
    "လိုအပ်သောစာသား မထည့်ထားပါ။",
)
