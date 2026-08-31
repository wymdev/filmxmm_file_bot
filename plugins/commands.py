import os
import io
import logging
import secrets
import asyncio
from functools import wraps
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from database.ia_filterdb import Media, get_file_details
from database.users_chats_db import db
from database.auto_delete_db import schedule_auto_delete
from database.mongo import RETRYABLE_MONGO_ERRORS
from info import CHANNELS, ADMINS, LOG_CHANNEL, PICS, BATCH_FILE_CAPTION, CUSTOM_FILE_CAPTION, PROTECT_CONTENT, MINI_APP_URL, REQUIRED_CHANNEL_URL
from utils import get_settings, get_size, save_group_settings, temp
from database.connections_mdb import active_connection
from plugins.fsub import ForceSub
from translations import (
    BATCH_EMPTY,
    BATCH_INVALID,
    BOT_NOT_IN_GROUP,
    DATABASE_UNAVAILABLE,
    DELETE_ALL_CONFIRM,
    DELETE_REPLY_REQUIRED,
    FILE_DELETED,
    FILE_NOT_IN_DATABASE,
    FILES_DELETED,
    NO_MESSAGES,
    NO_INPUT,
    NO_SUCH_FILE,
    NOT_CONNECTED,
    PREPARING_FILES,
    PROCESSING,
    SOURCE_UNAVAILABLE,
    UNSUPPORTED_FILE,
    bilingual,
)
import re
import json
import base64
logger = logging.getLogger(__name__)

BATCH_FILES = {}


def home_buttons():
    buttons = []
    if MINI_APP_URL:
        buttons.append(
            [
                InlineKeyboardButton(
                    "🎬 Open Movie App · ရုပ်ရှင် App",
                    web_app=WebAppInfo(url=MINI_APP_URL),
                )
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton('🔎 Search · ရှာရန်', switch_inline_query_current_chat=''),
            InlineKeyboardButton(
                '📢 Channel · ချန်နယ်',
                url=REQUIRED_CHANNEL_URL or 'https://t.me/filmxhub20',
            ),
        ]
    )
    buttons.append([InlineKeyboardButton('About · အကြောင်း', callback_data='about')])
    return buttons


def handle_database_errors(handler):
    @wraps(handler)
    async def wrapped(client, message):
        try:
            return await handler(client, message)
        except RETRYABLE_MONGO_ERRORS as error:
            logger.warning("MongoDB unavailable during /start: %s", error)
            return await message.reply(DATABASE_UNAVAILABLE)

    return wrapped


def _load_downloaded_batch(path):
    try:
        with open(path, encoding='utf-8') as file_data:
            return json.load(file_data)
    finally:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


async def _schedule_batch_delete(chat_id, sent_message):
    """Schedule deletion without treating a database hiccup as a send failure."""
    try:
        await schedule_auto_delete(chat_id, sent_message.id)
    except Exception:
        logger.warning(
            "Could not schedule auto-delete for batch message %s in chat %s",
            sent_message.id,
            chat_id,
            exc_info=True,
        )


async def deliver_saved_batch(client, message, file_id, recipient_id=None):
    """Download and deliver a JSON-backed batch link."""
    recipient_id = recipient_id or message.chat.id
    sts = await client.send_message(recipient_id, PREPARING_FILES)
    msgs = BATCH_FILES.get(file_id)
    if msgs is None:
        try:
            post = await client.get_messages(LOG_CHANNEL, int(file_id))
            if not post or post.empty or not post.document:
                raise ValueError("Batch document is missing")
            file = await client.download_media(post.document)
            if not file:
                raise OSError("Batch document could not be downloaded")
            loop = asyncio.get_running_loop()
            msgs = await loop.run_in_executor(None, _load_downloaded_batch, file)
            if not isinstance(msgs, list) or not all(isinstance(item, dict) for item in msgs):
                raise ValueError("Invalid batch document")
        except Exception:
            logger.warning("Could not load batch %s", file_id, exc_info=True)
            await sts.edit(BATCH_INVALID)
            return False
        BATCH_FILES[file_id] = msgs

    sent_count = 0
    failed_count = 0
    for msg in msgs:
        title = msg.get("title")
        try:
            size = get_size(int(msg.get("size") or 0))
        except (TypeError, ValueError):
            size = ""
        original_caption = msg.get("caption") or (title or "")
        f_caption = original_caption
        if BATCH_FILE_CAPTION:
            try:
                f_caption = BATCH_FILE_CAPTION.format(
                    file_name=title or "",
                    file_size=size or "",
                    file_caption=original_caption,
                )
            except Exception:
                logger.warning("Could not format batch caption", exc_info=True)

        async def send(caption):
            return await client.send_cached_media(
                chat_id=recipient_id,
                file_id=msg.get("file_id"),
                caption=caption,
                protect_content=bool(msg.get("protect", False)),
            )

        try:
            try:
                sent_msg = await send(f_caption)
            except FloodWait as error:
                await asyncio.sleep(error.value)
                sent_msg = await send(f_caption)
            except Exception:
                # A custom template can exceed Telegram's caption limit or
                # contain invalid markup.  Preserve delivery with the original
                # caption when possible.
                if f_caption == original_caption:
                    raise
                logger.warning("Retrying batch item with its original caption", exc_info=True)
                sent_msg = await send(original_caption)
            sent_count += 1
            await _schedule_batch_delete(recipient_id, sent_msg)
        except Exception:
            failed_count += 1
            logger.warning("Could not send an item from batch %s", file_id, exc_info=True)
        await asyncio.sleep(1)

    if failed_count:
        await sts.edit(bilingual(
            f"Sent {sent_count} file(s). {failed_count} file(s) could not be sent.",
            f"ဖိုင် {sent_count} ခု ပို့ပြီးပါပြီ။ ဖိုင် {failed_count} ခုကို ပို့၍မရပါ။",
        ))
    elif sent_count:
        await sts.delete()
    else:
        await sts.edit(BATCH_EMPTY)
    return sent_count > 0


async def deliver_direct_store_batch(client, message, encoded_data, recipient_id=None):
    """Deliver a direct-store batch payload and report malformed links."""
    recipient_id = recipient_id or message.chat.id
    sts = await client.send_message(recipient_id, PREPARING_FILES)
    try:
        decoded = base64.urlsafe_b64decode(
            encoded_data + "=" * (-len(encoded_data) % 4)
        ).decode("ascii")
        try:
            first_id, last_id, chat_id, protect = decoded.split("_", 3)
        except ValueError:
            first_id, last_id, chat_id = decoded.split("_", 2)
            protect = "p" if PROTECT_CONTENT else "u"
        first_id, last_id, chat_id = int(first_id), int(last_id), int(chat_id)
        first_id, last_id = sorted((first_id, last_id))
    except (ValueError, UnicodeError):
        await sts.edit(BATCH_INVALID)
        return False

    sent_count = 0
    failed_count = 0
    try:
        async for msg in client.iter_messages(chat_id, last_id, first_id):
            if msg.empty:
                continue
            is_media = bool(msg.media)
            copy_kwargs = {
                "protect_content": protect in ("p", "/pbatch"),
            }
            original_caption = ""
            try:
                if is_media:
                    media = getattr(msg, msg.media.value)
                    original_caption = getattr(msg, "caption", "") or ""
                    if BATCH_FILE_CAPTION:
                        try:
                            f_caption = BATCH_FILE_CAPTION.format(
                                file_name=getattr(media, "file_name", "") or "",
                                file_size=get_size(getattr(media, "file_size", 0) or 0),
                                file_caption=original_caption,
                            )
                        except Exception:
                            logger.warning("Could not format direct batch caption", exc_info=True)
                            f_caption = original_caption
                    else:
                        f_caption = original_caption or getattr(media, "file_name", "")
                    copy_kwargs["caption"] = f_caption

                async def copy_message():
                    return await msg.copy(recipient_id, **copy_kwargs)

                try:
                    sent_msg = await copy_message()
                except FloodWait as error:
                    await asyncio.sleep(error.value)
                    sent_msg = await copy_message()
                except Exception:
                    if not is_media or copy_kwargs.get("caption") == original_caption:
                        raise
                    logger.warning(
                        "Retrying direct batch item with its original caption",
                        exc_info=True,
                    )
                    copy_kwargs["caption"] = original_caption
                    sent_msg = await copy_message()
                sent_count += 1
                if is_media:
                    await _schedule_batch_delete(recipient_id, sent_msg)
            except Exception:
                failed_count += 1
                logger.warning("Could not send direct batch item", exc_info=True)
            await asyncio.sleep(1)
    except Exception:
        logger.warning("Could not read direct batch source %s", chat_id, exc_info=True)
        await sts.edit(SOURCE_UNAVAILABLE)
        return False

    if failed_count:
        await sts.edit(bilingual(
            f"Sent {sent_count} message(s). {failed_count} message(s) could not be sent.",
            f"မက်ဆေ့ချ် {sent_count} ခု ပို့ပြီးပါပြီ။ မက်ဆေ့ချ် {failed_count} ခုကို ပို့၍မရပါ။",
        ))
    elif sent_count:
        await sts.delete()
    else:
        await sts.edit(NO_MESSAGES)
    return sent_count > 0


async def deliver_single_file(client, request_id, recipient_id, protect=False):
    """Resolve one stored-media request and deliver it to a Telegram user."""
    file_id = request_id
    files_ = await get_file_details(file_id)
    if not files_:
        try:
            decoded = base64.urlsafe_b64decode(
                request_id + "=" * (-len(request_id) % 4)
            ).decode("ascii")
            _, file_id = decoded.split("_", 1)
        except Exception:
            return False
        files_ = await get_file_details(file_id)
    if not files_:
        return False

    media = files_[0]
    title = media.file_name
    size = get_size(media.file_size)
    caption = media.caption
    if CUSTOM_FILE_CAPTION:
        try:
            caption = CUSTOM_FILE_CAPTION.format(
                file_name="" if title in [None, "None"] else title,
                file_size="" if size is None else size,
                file_caption="" if caption is None else caption,
            )
        except Exception:
            logger.warning("Could not format the custom file caption", exc_info=True)
    if caption is None:
        caption = title or ""

    sent_msg = await client.send_cached_media(
        chat_id=recipient_id,
        file_id=media.file_id,
        caption=caption,
        protect_content=bool(protect),
    )
    try:
        await schedule_auto_delete(recipient_id, sent_msg.id)
    except Exception:
        logger.warning(
            "File delivered but auto-delete scheduling failed for message %s",
            sent_msg.id,
            exc_info=True,
        )
    return True


async def deliver_movie_request(client, request_id, recipient_id, mode="checksub"):
    """Single delivery entry point shared by deep links, joins, and Mini App."""
    request_id = str(request_id)
    if request_id.startswith("BATCH-"):
        return await deliver_saved_batch(
            client,
            None,
            request_id.split("-", 1)[1],
            recipient_id=recipient_id,
        )
    if request_id.startswith("DSTORE-"):
        return await deliver_direct_store_batch(
            client,
            None,
            request_id.split("-", 1)[1],
            recipient_id=recipient_id,
        )
    return await deliver_single_file(
        client,
        request_id,
        recipient_id,
        protect=mode in {"checksubp", "filep"},
    )


@Client.on_message(filters.command("start") & filters.incoming)
@handle_database_errors
async def start(client, message):
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        buttons = [
            [
                InlineKeyboardButton("Updates", url="https://t.me/filmxhub20"),
                InlineKeyboardButton("🍿 FilmX 🍿", url="https://t.me/filmxhub20")
            ]
            ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply(script.START_TXT.format(message.from_user.mention if message.from_user else message.chat.title, temp.U_NAME, temp.B_NAME), reply_markup=reply_markup)
        await asyncio.sleep(2) # 😢 https://github.com/EvamariaTG/EvaMaria/blob/master/plugins/p_ttishow.py#L17 😬 wait a bit, before checking.
        if not await db.get_chat(message.chat.id):
            total=await client.get_chat_members_count(message.chat.id)
            await client.send_message(LOG_CHANNEL, script.LOG_TEXT_G.format(message.chat.title, message.chat.id, total, "Unknown"))       
            await db.add_chat(message.chat.id, message.chat.title)
        return 
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(message.from_user.id, message.from_user.mention))
    if len(message.command) != 2:
        buttons = home_buttons()
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo=secrets.choice(PICS),
            caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return

    if len(message.command) == 2 and message.command[1] in ["subscribe", "error", "okay", "help", "start", "hehe"]:
        if message.command[1] == "subscribe":
            await ForceSub(client, message)
            return

        buttons = home_buttons()
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo=secrets.choice(PICS),
            caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return

    data = message.command[1]
    if data.startswith(("BATCH-", "DSTORE-")):
        # URL-safe base64 can itself contain underscores.  Keep batch
        # payloads intact for force-subscribe retries.
        kk, file_id = False, data
    else:
        kk, file_id = data.split("_", 1) if "_" in data else (False, False)
        if not file_id:
            file_id = data
    pre = ('checksubp' if kk == 'filep' else 'checksub') if kk else 'checksub'
 
    status = await ForceSub(client, message, file_id=file_id, mode=pre)
    if not status:
        return

    if not file_id:
        file_id = data

    try:
        delivered = await deliver_movie_request(
            client,
            file_id,
            message.from_user.id,
            mode=pre,
        )
    except Exception:
        logger.exception("Error delivering requested media")
        return await message.reply(NO_SUCH_FILE)
    if not delivered:
        return await message.reply(NO_SUCH_FILE)
                    

@Client.on_message(filters.command('channel') & filters.user(ADMINS))
async def channel_info(bot, message):
           
    """Send basic information of channel"""
    if isinstance(CHANNELS, (int, str)):
        channels = [CHANNELS]
    elif isinstance(CHANNELS, list):
        channels = CHANNELS
    else:
        raise ValueError("Unexpected type of CHANNELS")

    text = '📑 **Indexed channels/groups**\n'
    for channel in channels:
        chat = await bot.get_chat(channel)
        if chat.username:
            text += '\n@' + chat.username
        else:
            text += '\n' + chat.title or chat.first_name

    text += f'\n\n**Total:** {len(CHANNELS)}'

    if len(text) < 4096:
        await message.reply(text)
    else:
        file = io.BytesIO(text.encode('utf-8'))
        file.name = 'Indexed channels.txt'
        await message.reply_document(file)


@Client.on_message(filters.command('logs') & filters.user(ADMINS))
async def log_file(bot, message):
    """Send log file"""
    try:
        await message.reply_document('TelegramBot.log')
    except Exception as e:
        await message.reply(str(e))

@Client.on_message(filters.command('delete') & filters.user(ADMINS))
async def delete(bot, message):
    """Delete file from database"""
    reply = message.reply_to_message
    if reply and reply.media:
        msg = await message.reply(PROCESSING, quote=True)
    else:
        await message.reply(DELETE_REPLY_REQUIRED, quote=True)
        return

    for file_type in ("document", "video", "audio"):
        media = getattr(reply, file_type, None)
        if media is not None:
            break
    else:
        await msg.edit(UNSUPPORTED_FILE)
        return
    
    file_unique_id = getattr(media, "file_unique_id", media.file_id)

    result = await Media.collection.delete_one({
        'file_unique_id': file_unique_id,
    })
    if result.deleted_count:
        await msg.edit(FILE_DELETED)
    else:
        file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name)) if media.file_name else ""
        result = await Media.collection.delete_many({
            'file_name': file_name,
            'file_size': media.file_size,
            'mime_type': media.mime_type
            })
        if result.deleted_count:
            await msg.edit(FILE_DELETED)
        else:
            # files indexed before https://github.com/EvamariaTG/EvaMaria/commit/f3d2a1bcb155faf44178e5d7a685a1b533e714bf#diff-86b613edf1748372103e94cacff3b578b36b698ef9c16817bb98fe9ef22fb669R39 
            # have original file name.
            result = await Media.collection.delete_many({
                'file_name': media.file_name,
                'file_size': media.file_size,
                'mime_type': media.mime_type
            })
            if result.deleted_count:
                await msg.edit(FILE_DELETED)
            else:
                await msg.edit(FILE_NOT_IN_DATABASE)


@Client.on_message(filters.command('deleteall') & filters.user(ADMINS))
async def delete_all_index(bot, message):
    await message.reply_text(
        DELETE_ALL_CONFIRM,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="YES", callback_data="autofilter_delete"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="CANCEL", callback_data="close_data"
                    )
                ],
            ]
        ),
        quote=True,
    )


@Client.on_callback_query(filters.regex(r'^autofilter_delete'))
async def delete_all_index_confirm(bot, message):
    await Media.collection.drop()
    await message.answer('Piracy Is Crime')
    await message.message.edit(FILES_DELETED)


@Client.on_message(filters.command('settings'))
async def settings(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(bilingual(
            f"Anonymous admins must use /connect {message.chat.id} in private chat.",
            f"Anonymous admin ဖြစ်သောကြောင့် private chat တွင် /connect {message.chat.id} ကို အသုံးပြုပါ။",
        ))
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text(BOT_NOT_IN_GROUP, quote=True)
                return
        else:
            await message.reply_text(NOT_CONNECTED, quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
            st.status != enums.ChatMemberStatus.ADMINISTRATOR
            and st.status != enums.ChatMemberStatus.OWNER
            and userid not in ADMINS
    ):
        return

    settings = await get_settings(grp_id)

    if settings is not None:
        buttons = [
            [
                InlineKeyboardButton(
                    'Filter Button',
                    callback_data=f'setgs#button#{settings["button"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    'Single' if settings["button"] else 'Double',
                    callback_data=f'setgs#button#{settings["button"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Bot PM',
                    callback_data=f'setgs#botpm#{settings["botpm"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["botpm"] else '❌ No',
                    callback_data=f'setgs#botpm#{settings["botpm"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'File Secure',
                    callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["file_secure"] else '❌ No',
                    callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'IMDB',
                    callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["imdb"] else '❌ No',
                    callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Spell Check',
                    callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["spell_check"] else '❌ No',
                    callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Welcome',
                    callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["welcome"] else '❌ No',
                    callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}',
                ),
            ],
        ]

        reply_markup = InlineKeyboardMarkup(buttons)

        await message.reply_text(
            text=f"<b>Change Your Settings for {title} As Your Wish ⚙</b>",
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode=enums.ParseMode.HTML,
            reply_to_message_id=message.id
        )



@Client.on_message(filters.command('set_template'))
async def save_template(client, message):
    sts = await message.reply(bilingual(
        "Checking the template…",
        "Template ကို စစ်ဆေးနေပါသည်…",
    ))
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(bilingual(
            f"Anonymous admins must use /connect {message.chat.id} in private chat.",
            f"Anonymous admin ဖြစ်သောကြောင့် private chat တွင် /connect {message.chat.id} ကို အသုံးပြုပါ။",
        ))
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text(BOT_NOT_IN_GROUP, quote=True)
                return
        else:
            await message.reply_text(NOT_CONNECTED, quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
            st.status != enums.ChatMemberStatus.ADMINISTRATOR
            and st.status != enums.ChatMemberStatus.OWNER
            and userid not in ADMINS
    ):
        return

    if len(message.command) < 2:
        return await sts.edit(NO_INPUT)
    template = message.text.split(" ", 1)[1]
    await save_group_settings(grp_id, 'template', template)
    await sts.edit(f"Successfully changed template for {title} to\n\n{template}")
