import io
import json
import logging
import re

from pyrogram import filters, Client, enums
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, UsernameInvalid, UsernameNotModified
from info import ADMINS, LOG_CHANNEL, FILE_STORE_CHANNEL, PUBLIC_FILE_STORE
from utils import temp
import base64

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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

async def allowed(_, __, message):
    if PUBLIC_FILE_STORE:
        return True
    if message.from_user and message.from_user.id in ADMINS:
        return True
    return False

@Client.on_message(filters.command(['link', 'plink']) & filters.create(allowed))
async def gen_link_s(bot, message):
    replied = message.reply_to_message
    if not replied:
        return await message.reply('Reply to a message to get a shareable link.')
    file_type = replied.media
    if file_type not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
        return await message.reply("Reply to a supported media")
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
        return await message.reply("Failed to get file from database.")
        
    string = 'filep_' if message.text.lower().strip() == "/plink" else 'file_'
    string += str(file_doc.id)
    outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
    await message.reply(f"Here is your Link:\nhttps://t.me/{temp.U_NAME}?start={outstr}")
    
    
@Client.on_message(filters.command(['batch', 'pbatch']) & filters.create(allowed))
async def gen_link_batch(bot, message):
    links = message.text.split()
    if len(links) != 3:
        return await message.reply("Use correct format.\nExample <code>/batch https://t.me/TeamEvamaria/10 https://t.me/TeamEvamaria/20</code>.")
    cmd, first, last = links
    try:
        f_chat_id, f_msg_id = parse_batch_link(first)
        l_chat_id, l_msg_id = parse_batch_link(last)
    except ValueError:
        return await message.reply('Invalid link')

    if f_chat_id != l_chat_id:
        return await message.reply("Chat ids not matched.")

    # Users commonly paste the newest link first.  Process either order.
    f_msg_id, l_msg_id = sorted((f_msg_id, l_msg_id))
    try:
        chat_id = (await bot.get_chat(f_chat_id)).id
    except ChannelInvalid:
        return await message.reply('This may be a private channel / group. Make me an admin over there to index the files.')
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply('Invalid Link specified.')
    except Exception as e:
        return await message.reply(f'Errors - {e}')

    sts = await message.reply("Generating link for your message.\nThis may take time depending upon number of messages")
    protect_batch = cmd.lower().split("@", 1)[0] == "/pbatch"
    if chat_id in FILE_STORE_CHANNEL:
        # Telegram limits deep-link payloads to 64 characters.  A one-byte
        # protection flag keeps large channel IDs within that limit.
        protect_flag = "p" if protect_batch else "u"
        string = f"{f_msg_id}_{l_msg_id}_{chat_id}_{protect_flag}"
        b_64 = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
        return await sts.edit(f"Here is your link https://t.me/{temp.U_NAME}?start=DSTORE-{b_64}")

    FRMT = "Generating Link...\nTotal Messages: `{total}`\nDone: `{current}`\nRemaining: `{rem}`\nStatus: `{sts}`"

    outlist = []

    # file store without db channel
    og_msg = 0
    tot = 0
    total_messages = l_msg_id - f_msg_id + 1
    async for msg in bot.iter_messages(chat_id, l_msg_id, f_msg_id):
        tot += 1
        if msg.empty or msg.service:
            continue
        if not msg.media:
            # only media messages supported.
            continue
        try:
            file_type = msg.media
            file = getattr(msg, file_type.value)
            caption = getattr(msg, 'caption', '')
            if caption:
                caption = caption.html
            if file:
                file = {
                    "file_id": file.file_id,
                    "caption": caption,
                    "title": getattr(file, "file_name", ""),
                    "size": file.file_size,
                    "protect": protect_batch,
                }

                og_msg +=1
                outlist.append(file)
        except Exception:
            logger.warning("Could not serialize message %s", msg.id, exc_info=True)
        if tot % 20 == 0 or tot == total_messages:
            try:
                await sts.edit(FRMT.format(
                    total=total_messages,
                    current=tot,
                    rem=max(0, total_messages - tot),
                    sts="Saving Messages",
                ))
            except Exception:
                logger.debug("Could not update batch progress", exc_info=True)
    if not outlist:
        return await sts.edit("No media files were found in that message range.")
    batch_file = io.BytesIO(json.dumps(outlist).encode('utf-8'))
    batch_file.name = f"batchmode_{message.from_user.id}.json"
    post = await bot.send_document(
        LOG_CHANNEL,
        batch_file,
        file_name="Batch.json",
        caption="⚠️Generated for filestore.",
    )
    await sts.edit(f"Here is your link\nContains `{og_msg}` files.\n https://t.me/{temp.U_NAME}?start=BATCH-{post.id}")
