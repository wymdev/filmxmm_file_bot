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


async def publish_batch(bot, message, status, files):
    """Store a batch manifest and edit the status with its deep link."""
    if not files:
        return await status.edit("No media files were found for this batch.")
    batch_file = io.BytesIO(json.dumps(files).encode("utf-8"))
    batch_file.name = f"batchmode_{message.from_user.id}.json"
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
    parts = message.text.split()
    cmd, link_texts = parts[0], parts[1:]
    protect_batch = cmd.lower().split("@", 1)[0] == "/pbatch"

    # Forwarded-media workflow: forward files first, then send /batch.
    if not link_texts:
        pending = PENDING_BATCHES.get(message.from_user.id, [])
        if not pending:
            return await message.reply(
                "Nothing is queued. Forward media files to me and then send /batch, "
                "or use <code>/batch link1 link2 link3</code>.\n\n"
                "With exactly two links from the same chat, every post between "
                "those links is included."
            )
        status = await message.reply(f"Creating a batch from {len(pending)} forwarded file(s)…")
        files = [{**item, "protect": protect_batch} for item in pending]
        try:
            await publish_batch(bot, message, status, files)
        except Exception:
            logger.exception("Could not publish forwarded batch")
            return await status.edit("I could not create the batch. Please try again.")
        PENDING_BATCHES.pop(message.from_user.id, None)
        return

    try:
        requested = [parse_batch_link(link) for link in link_texts]
    except ValueError:
        return await message.reply(
            "One or more links are invalid. Use Telegram post links like:\n"
            "<code>/batch https://t.me/channel/10 https://t.me/channel/15 "
            "https://t.me/channel/22</code>"
        )

    resolved_chats = {}
    resolved = []
    try:
        for source_chat, message_id in requested:
            cache_key = str(source_chat).lower()
            if cache_key not in resolved_chats:
                resolved_chats[cache_key] = (await bot.get_chat(source_chat)).id
            resolved.append((resolved_chats[cache_key], message_id))
    except ChannelInvalid:
        return await message.reply(
            "I cannot access one of those private chats. Add me there as an admin first."
        )
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply("One of the Telegram links is invalid.")
    except Exception as error:
        logger.warning("Could not resolve batch source", exc_info=True)
        return await message.reply(f"I could not access one of those links: {error}")

    # Preserve the original two-link behavior: two posts in one chat define
    # an inclusive range. One link, three or more links, or links from
    # different chats select only those exact posts.
    is_range = len(resolved) == 2 and resolved[0][0] == resolved[1][0]
    status = await message.reply(
        "Generating your batch link. This may take time for a large range."
    )

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
                "I could not read that message range. Check my access to the source chat."
            )
        if not outlist:
            return await status.edit(
                f"No media files were found in the {total}-message range."
            )
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
            return await status.edit(
                "None of the selected links contains accessible media."
            )

    try:
        await publish_batch(bot, message, status, outlist)
    except Exception:
        logger.exception("Could not publish linked-message batch")
        await status.edit("I could not create the batch. Please try again.")
