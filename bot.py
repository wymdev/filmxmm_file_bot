import logging
import logging.config
import asyncio
from contextlib import suppress

# File logging is optional on read-only container filesystems.
try:
    logging.config.fileConfig('logging.conf')
except OSError as error:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True,
    )
    logging.warning("File logging is unavailable; using console logging only: %s", error)
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("imdbpy").setLevel(logging.ERROR)

from pyrogram import Client, __version__, enums
from pyrogram.errors import MessageIdInvalid
from pyrogram.raw.all import layer
from database.ia_filterdb import Media
from database.mongo import RETRYABLE_MONGO_ERRORS, retry_mongo_operation
from database.users_chats_db import db
from database.auto_delete_db import ensure_auto_delete_indexes, get_expired_messages, remove_entry
from database.pending_requests import ensure_pending_request_indexes
from database.miniapp_db import ensure_miniapp_indexes
from info import SESSION, API_ID, API_HASH, BOT_TOKEN, LOG_STR
from utils import temp
from typing import Union, Optional, AsyncGenerator
from pyrogram import types

class Bot(Client):

    def __init__(self):
        super().__init__(
            name=SESSION,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=500,
            plugins={"root": "plugins"},
            sleep_threshold=5,
        )

    async def start(self):
        ban_cache_loaded = True
        try:
            b_users, b_chats = await db.get_banned()
        except RETRYABLE_MONGO_ERRORS as error:
            ban_cache_loaded = False
            logging.warning(
                "Could not load banned users/chats from MongoDB at startup; "
                "continuing with empty ban caches: %s",
                error,
            )
            b_users, b_chats = [], []
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats
        await super().start()
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        self.username = '@' + me.username
        logging.info(f"{me.first_name} with for Pyrogram v{__version__} (Layer {layer}) started on {me.username}.")
        logging.info(LOG_STR)

        from miniapp_server import start_miniapp_server
        self._miniapp_runner = await start_miniapp_server(self)

        # Keep persisted maintenance state current for long-running processes.
        self._auto_delete_task = asyncio.create_task(
            self._auto_delete_loop(),
            name='auto-delete-loop',
        )
        self._ban_refresh_task = asyncio.create_task(
            self._ban_refresh_loop(initial_delay=30 if not ban_cache_loaded else 300),
            name='ban-refresh-loop',
        )
        self._database_maintenance_task = asyncio.create_task(
            self._database_maintenance_loop(),
            name='database-maintenance-loop',
        )

        # Resolve Force Subscribe channel peer ID at startup to avoid PeerIdInvalid errors
        from info import AUTH_CHANNEL, REQ_CHANNEL
        for channel_id in [AUTH_CHANNEL, REQ_CHANNEL]:
            if channel_id:
                try:
                    await self.get_chat(channel_id)
                except Exception:
                    logging.exception("Failed to resolve configured channel %s", channel_id)

        from info import MINI_APP_URL
        if MINI_APP_URL:
            try:
                await self.set_chat_menu_button(
                    menu_button=types.MenuButtonWebApp(
                        text="FilmX · ရုပ်ရှင်",
                        web_app=types.WebAppInfo(url=MINI_APP_URL),
                    )
                )
            except Exception:
                logging.exception("Failed to configure the Mini App menu button")

    async def stop(self, *args):
        tasks = [
            getattr(self, '_auto_delete_task', None),
            getattr(self, '_ban_refresh_task', None),
            getattr(self, '_database_maintenance_task', None),
        ]
        for task in filter(None, tasks):
            task.cancel()
        for task in filter(None, tasks):
            with suppress(asyncio.CancelledError):
                await task
        runner = getattr(self, '_miniapp_runner', None)
        if runner:
            await runner.cleanup()
        await super().stop(*args)
        logging.info("Bot stopped. Bye.")

    async def _ban_refresh_loop(self, initial_delay):
        """Refresh ban caches so startup fallbacks and remote changes recover."""
        await asyncio.sleep(initial_delay)
        while True:
            try:
                b_users, b_chats = await db.get_banned()
                temp.BANNED_USERS = b_users
                temp.BANNED_CHATS = b_chats
            except RETRYABLE_MONGO_ERRORS as error:
                logging.warning(
                    "Could not refresh banned users/chats from MongoDB: %s",
                    error,
                )
            except Exception:
                logging.exception("Unexpected error while refreshing banned users/chats")
            await asyncio.sleep(300)

    async def _database_maintenance_loop(self):
        """Create database indexes when MongoDB has a writable primary."""
        while True:
            try:
                await db.ensure_indexes()
                await retry_mongo_operation(
                    "media index initialization",
                    Media.ensure_indexes,
                )
                await ensure_auto_delete_indexes()
                await ensure_pending_request_indexes()
                await ensure_miniapp_indexes()
            except RETRYABLE_MONGO_ERRORS as error:
                logging.warning(
                    "MongoDB indexes are not ready; retrying in 5 minutes: %s",
                    error,
                )
                await asyncio.sleep(300)
            except Exception:
                logging.exception(
                    "Unexpected database index error; retrying in 5 minutes"
                )
                await asyncio.sleep(300)
            else:
                logging.info("MongoDB indexes are ready")
                return

    async def _auto_delete_loop(self):
        """Background loop that checks MongoDB every 5 minutes for expired messages and deletes them."""
        await asyncio.sleep(10)  # Wait a bit after startup
        while True:
            try:
                expired = await get_expired_messages()
                for entry in expired:
                    try:
                        await self.delete_messages(
                            chat_id=entry['chat_id'],
                            message_ids=entry['message_id']
                        )
                    except MessageIdInvalid:
                        logging.info(
                            "Auto-delete message %s in chat %s was already absent",
                            entry['message_id'],
                            entry['chat_id'],
                        )
                    except Exception:
                        logging.exception(
                            "Failed to auto-delete msg %s in chat %s; keeping it queued",
                            entry['message_id'],
                            entry['chat_id'],
                        )
                        continue
                    else:
                        logging.info(
                            "Auto-deleted msg %s in chat %s",
                            entry['message_id'],
                            entry['chat_id'],
                        )
                        try:
                            await self.send_message(
                                chat_id=entry['chat_id'],
                                text=(
                                    "<b>⏰ Time's up!</b>\n\n"
                                    "The file you got has been <b>auto-deleted</b> — that's just how we keep "
                                    "things copyright-safe.\n\n"
                                    "📌 <i>Need it again? Just request it once more from the channel.</i>\n\n"
                                    "🔒 <b>Note:</b> Every file auto-deletes 5 hours after delivery for copyright reasons.\n\n"
                                    "<b>🇲🇲 အချိန်ကုန်သွားပါပြီ!</b>\n\n"
                                    "သင်ရရှိထားတဲ့ ဖိုင်ကို <b>အလိုအလျောက် ဖျက်ပစ်လိုက်ပါပြီ</b> — မူပိုင်ခွင့်စည်းမျဉ်း လိုက်နာဖို့ လိုအပ်လို့ပါနော်။\n\n"
                                    "📌 <i>ထပ်လိုအပ်ရင် ချန်နယ်ကနေ ထပ်တောင်းလိုက်ရုံပါပဲ။</i>\n\n"
                                    "🔒 <b>မှတ်ချက်:</b> ဖိုင်တိုင်းကို ပို့ပြီး ၅ နာရီအကြာမှာ မူပိုင်ခွင့်အရ အလိုအလျောက် ဖျက်ပါတယ်နော်။"
                                ),
                                parse_mode=enums.ParseMode.HTML
                            )
                        except Exception:
                            logging.exception(
                                "Failed to send deletion notice to chat %s",
                                entry['chat_id'],
                            )
                    await remove_entry(entry['_id'])
            except RETRYABLE_MONGO_ERRORS as error:
                logging.warning("Auto-delete is waiting for MongoDB: %s", error)
            except Exception:
                logging.exception("Error in auto-delete loop")
            await asyncio.sleep(300)  # Check every 5 minutes
    
    async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0,
    ) -> Optional[AsyncGenerator["types.Message", None]]:
        """Iterate through a chat sequentially.
        This convenience method does the same as repeatedly calling :meth:`~pyrogram.Client.get_messages` in a loop, thus saving
        you from the hassle of setting up boilerplate code. It is useful for getting the whole chat messages with a
        single call.
        Parameters:
            chat_id (``int`` | ``str``):
                Unique identifier (int) or username (str) of the target chat.
                For your personal cloud (Saved Messages) you can simply use "me" or "self".
                For a contact that exists in your Telegram address book you can use his phone number (str).
                
            limit (``int``):
                Identifier of the last message to be returned.
                
            offset (``int``, *optional*):
                Identifier of the first message to be returned.
                Defaults to 0.
        Returns:
            ``Generator``: A generator yielding :obj:`~pyrogram.types.Message` objects.
        Example:
            .. code-block:: python
                for message in app.iter_messages("pyrogram", 1, 15000):
                    print(message.text)
        """
        # Telegram accepts at most 200 message IDs in one request.  The old
        # inclusive range requested 201 IDs and also started at the invalid ID
        # 0 when no offset was supplied.
        current = max(1, offset)
        while current <= limit:
            batch_end = min(current + 199, limit)
            messages = await self.get_messages(
                chat_id,
                list(range(current, batch_end + 1)),
            )
            for message in messages:
                yield message
            current = batch_end + 1


app = Bot()

if __name__ == "__main__":
    app.run()
