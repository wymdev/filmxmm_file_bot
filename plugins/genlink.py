import io
import json
import logging
import re

from pyrogram import filters, Client, enums
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, UsernameInvalid, UsernameNotModified
from info import ADMINS, LOG_CHANNEL, FILE_STORE_CHANNEL, PUBLIC_FILE_STORE
from utils import temp
from translations import BATCH_INVALID, GENERIC_ERROR, bilingual
import base64

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PENDING_BATCHES = {}
MAX_PENDING_BATCH_FILES = 500

BATCH_LINK_RE = re.compile(
    r"^(?:https?://)?(?:t\.me|telegram\.me|telegram\.dog)/"
    r"(?:c/)?(?P<chat>\d+|[a-zA-Z_][a-zA-Z_0-9]*)/"
    r"(?P<message>\d+)/?(?:\?.*)?$",
    re.IGNORECASE,
)


def parse_batch_link(link):
    """Return a Pyrogram chat ID/username and message ID from a post link."""
    match = BATCH_LINK_RE.fullmatch(link.strip())
    if not match:
        raise ValueError("Invalid Telegram post link")

    chat_id = match.group("chat")
    if chat_id.isnumeric():
        chat_id = int(f"-100{chat_id}")
    return chat_id, int(match.group("message"))


def serialize_batch_message(message, protect=False):
    """Convert a Telegram media message into the stored batch format."""
    if message.empty or message.service or not message.media:
        return None
    media = getattr(message, message.media.value, None)
    if not media or not getattr(media, "file_id", None):
        return None
    caption = getattr(message, "caption", "") or ""
    caption = getattr(caption, "html", str(caption))
    return {
        "file_id": media.file_id,
        "caption": caption,
        "title": getattr(media, "file_name", "") or "",
        "size": getattr(media, "file_size", 0) or 0,
        "protect": protect,
    }


def batch_requester_id(message):
    """Return a stable ID even for anonymous-admin/channel commands."""
    if message.from_user:
        return message.from_user.id
    if getattr(message, "sender_chat", None):
        return message.sender_chat.id
    return message.chat.id


async def publish_batch(bot, message, status, files):
    """Store a batch manifest and edit the status with its deep link."""
    if not files:
        return await status.edit(bilingual(
            "No media files were found for this batch.",
            "ဤ batch အတွက် media ဖိုင်များ မတွေ့ပါ။",
        ))
    batch_file = io.BytesIO(json.dumps(files).encode("utf-8"))
    batch_file.name = f"batchmode_{batch_requester_id(message)}.json"
    post = await bot.send_document(
        LOG_CHANNEL,
        batch_file,
        file_name="Batch.json",
        caption="⚠️Generated for filestore.",
    )
    await status.edit(
        f"Here is your link\nContains `{len(files)}` files.\n"
        f"https://t.me/{temp.U_NAME}?start=BATCH-{post.id}"
    )


async def allowed(_, __, message):
    if PUBLIC_FILE_STORE:
        return True
    if message.from_user and message.from_user.id in ADMINS:
        return True
    return False


@Client.on_message(
    filters.private
    & filters.incoming
    & filters.forwarded
    & filters.media
    & filters.create(allowed),
    group=-1,
)
async def collect_forwarded_batch(_, message):
    """Queue forwarded media until the user sends /batch or /pbatch."""
    if not message.from_user:
        return
    file_data = serialize_batch_message(message)
    if not file_data:
        return
    pending = PENDING_BATCHES.setdefault(message.from_user.id, [])
    if len(pending) >= MAX_PENDING_BATCH_FILES:
        await message.reply(
            f"Your batch queue is full ({MAX_PENDING_BATCH_FILES} files). "
            "Send /batch to create the link."
        )
    else:
        pending.append(file_data)
        if len(pending) == 1:
            await message.reply(
                "Added to your batch. Forward more media, then send /batch "
                "(/pbatch for protected files)."
            )
        elif len(pending) % 10 == 0:
            await message.reply(
                f"{len(pending)} files are ready. Send /batch when finished."
            )

    # Forwarded media used for a batch must not also trigger the older channel
    # indexing workflow, which listens for every forwarded private message.
    stop = getattr(message, "stop_propagation", None)
    if stop:
        stop()

@Client.on_message(filters.command(['link', 'plink']) & filters.create(allowed))
async def gen_link_s(bot, message):
    replied = message.reply_to_message
    if not replied:
        return await message.reply(bilingual(
            "Reply to a message to create a shareable link.",
            "မျှဝေနိုင်သောလင့်ခ် ဖန်တီးရန် မက်ဆေ့ချ်တစ်ခုကို reply လုပ်ပါ။",
        ))
    file_type = replied.media
    if file_type not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
        return await message.reply(bilingual(
            "Reply to a supported video, audio, or document.",
            "ပံ့ပိုးထားသော video၊ audio သို့မဟုတ် document ကို reply လုပ်ပါ။",
        ))
    if message.has_protected_content and (
        not message.from_user or message.from_user.id not in ADMINS
    ):
        return await message.reply("okDa")
    media = getattr(replied, file_type.value)
    media.file_type = file_type.value
    media.caption = replied.caption
    from database.ia_filterdb import save_file, Media
    await save_file(media)
    
    file_doc = await Media.find_one({'file_unique_id': media.file_unique_id})
    if not file_doc:
        return await message.reply(bilingual(
            "The file could not be loaded from the database.",
            "ဖိုင်ကို ဒေတာဘေ့စ်မှ ရယူ၍ မရပါ။",
        ))
        
    string = 'filep_' if message.text.lower().strip() == "/plink" else 'file_'
    string += str(file_doc.id)
    outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
    await message.reply(f"Here is your Link:\nhttps://t.me/{temp.U_NAME}?start={outstr}")
    
    
@Client.on_message(filters.command(['batch', 'pbatch']) & filters.create(allowed))
async def gen_link_batch(bot, message):
    parts = message.text.split()
    cmd, link_texts = parts[0], parts[1:]
    protect_batch = cmd.lower().split("@", 1)[0] == "/pbatch"

    # Forwarded-media workflow: forward files first, then send /batch.
    if not link_texts:
        requester_id = batch_requester_id(message)
        pending = PENDING_BATCHES.get(requester_id, [])
        if not pending:
            return await message.reply(bilingual(
                "Nothing is queued. Forward media files and then send /batch, or use "
                "<code>/batch link1 link2 link3</code>. Exactly two links from the same "
                "chat include every post between them.",
                "စောင့်ဆိုင်းနေသောဖိုင် မရှိပါ။ Media ဖိုင်များကို forward လုပ်ပြီး /batch ပို့ပါ၊ "
                "သို့မဟုတ် <code>/batch link1 link2 link3</code> ကိုသုံးပါ။ Chat တစ်ခုတည်းမှ "
                "လင့်ခ်နှစ်ခုသာ ပေးပါက ကြားရှိ post အားလုံး ပါဝင်ပါမည်။",
            ))
        status = await message.reply(f"Creating a batch from {len(pending)} forwarded file(s)…")
        files = [{**item, "protect": protect_batch} for item in pending]
        try:
            await publish_batch(bot, message, status, files)
        except Exception:
            logger.exception("Could not publish forwarded batch")
            return await status.edit(GENERIC_ERROR)
        PENDING_BATCHES.pop(requester_id, None)
        return

    try:
        requested = [parse_batch_link(link) for link in link_texts]
    except ValueError:
        return await message.reply(bilingual(
            "One or more links are invalid. Use Telegram post links like:\n"
            "<code>/batch https://t.me/channel/10 https://t.me/channel/15 "
            "https://t.me/channel/22</code>",
            "လင့်ခ်တစ်ခု သို့မဟုတ် အများအပြား မမှန်ကန်ပါ။ အထက်ပါပုံစံအတိုင်း Telegram post လင့်ခ်များကို သုံးပါ။",
        ))

    resolved_chats = {}
    resolved = []
    try:
        for source_chat, message_id in requested:
            cache_key = str(source_chat).lower()
            if cache_key not in resolved_chats:
                resolved_chats[cache_key] = (await bot.get_chat(source_chat)).id
            resolved.append((resolved_chats[cache_key], message_id))
    except ChannelInvalid:
        return await message.reply(bilingual(
            "I cannot access one of those private chats. Add the bot there as an admin first.",
            "Private chat တစ်ခုကို ဝင်ရောက်၍ မရပါ။ Bot ကို ထို chat တွင် admin အဖြစ် အရင်ထည့်ပါ။",
        ))
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply(BATCH_INVALID)
    except Exception as error:
        logger.warning("Could not resolve batch source", exc_info=True)
        return await message.reply(f"I could not access one of those links: {error}")

    # Preserve the original two-link behavior: two posts in one chat define
    # an inclusive range. One link, three or more links, or links from
    # different chats select only those exact posts.
    is_range = len(resolved) == 2 and resolved[0][0] == resolved[1][0]
    status = await message.reply(bilingual(
        "Generating your batch link. A large range may take some time.",
        "Batch လင့်ခ်ကို ဖန်တီးနေပါသည်။ ဖိုင်အများအပြားရှိပါက အချိန်အနည်းငယ် ကြာနိုင်ပါသည်။",
    ))

    if is_range:
        chat_id = resolved[0][0]
        first_id, last_id = sorted((resolved[0][1], resolved[1][1]))
        if chat_id in FILE_STORE_CHANNEL:
            # Telegram limits deep-link payloads to 64 characters. A compact
            # protection flag keeps large channel IDs within that limit.
            protect_flag = "p" if protect_batch else "u"
            data = f"{first_id}_{last_id}_{chat_id}_{protect_flag}"
            encoded = base64.urlsafe_b64encode(data.encode("ascii")).decode().strip("=")
            return await status.edit(
                f"Here is your link https://t.me/{temp.U_NAME}?start=DSTORE-{encoded}"
            )

        total = last_id - first_id + 1
        outlist = []
        try:
            async for source_message in bot.iter_messages(chat_id, last_id, first_id):
                file_data = serialize_batch_message(source_message, protect_batch)
                if file_data:
                    outlist.append(file_data)
        except Exception:
            logger.exception("Could not read batch message range")
            return await status.edit(
                bilingual(
                    "I could not read that message range. Check the bot's access to the source chat.",
                    "ထိုမက်ဆေ့ချ်အပိုင်းကို ဖတ်၍မရပါ။ မူရင်း chat သို့ bot ဝင်ရောက်ခွင့် ရှိကြောင်း စစ်ဆေးပါ။",
                )
            )
        if not outlist:
            return await status.edit(bilingual(
                f"No media files were found in the {total}-message range.",
                f"မက်ဆေ့ချ် {total} ခုအတွင်း media ဖိုင် မတွေ့ပါ။",
            ))
    else:
        outlist = []
        for chat_id, message_id in resolved:
            try:
                source_message = await bot.get_messages(chat_id, message_id)
                file_data = serialize_batch_message(source_message, protect_batch)
                if file_data:
                    outlist.append(file_data)
            except Exception:
                logger.warning(
                    "Could not load message %s from %s",
                    message_id,
                    chat_id,
                    exc_info=True,
                )
        if not outlist:
            return await status.edit(bilingual(
                "None of the selected links contains accessible media.",
                "ရွေးချယ်ထားသောလင့်ခ်များတွင် ရယူနိုင်သည့် media မရှိပါ။",
            ))

    try:
        await publish_batch(bot, message, status, outlist)
    except Exception:
        logger.exception("Could not publish linked-message batch")
        await status.edit(GENERIC_ERROR)
