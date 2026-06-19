import logging
import logging.config
import asyncio

# Get logging configurations
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("imdbpy").setLevel(logging.ERROR)

from pyrogram import Client, __version__
from pyrogram.raw.all import layer
from database.ia_filterdb import Media
from database.users_chats_db import db
from database.auto_delete_db import ensure_auto_delete_indexes, get_expired_messages, remove_entry
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
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats
        await super().start()
        await Media.ensure_indexes()
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        self.username = '@' + me.username
        logging.info(f"{me.first_name} with for Pyrogram v{__version__} (Layer {layer}) started on {me.username}.")
        logging.info(LOG_STR)

        # Ensure auto-delete indexes and start the background cleanup loop
        await ensure_auto_delete_indexes()
        self._auto_delete_task = asyncio.create_task(self._auto_delete_loop())

        # Resolve Force Subscribe channel peer ID at startup to avoid PeerIdInvalid errors
        from info import AUTH_CHANNEL, REQ_CHANNEL
        for channel_id in [AUTH_CHANNEL, REQ_CHANNEL]:
            if channel_id:
                try:
                    await self.get_chat(int(channel_id))
                except Exception as e:
                    logging.warning(f"Failed to resolve channel {channel_id} by ID: {e}")
                    # Try username resolution fallback
                    if int(channel_id) == -1003922880580:
                        try:
                            await self.get_chat("@filmxhub20")
                            logging.info("Successfully resolved and cached channel @filmxhub20 peer.")
                        except Exception as err:
                            logging.error(f"Failed to resolve channel @filmxhub20 username: {err}")

    async def stop(self, *args):
        if hasattr(self, '_auto_delete_task'):
            self._auto_delete_task.cancel()
        await super().stop()
        logging.info("Bot stopped. Bye.")

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
                        logging.info(f"Auto-deleted msg {entry['message_id']} in chat {entry['chat_id']}")
                        # Send DMCA copyright notice after deletion
                        try:
                            await self.send_message(
                                chat_id=entry['chat_id'],
                                text=(
                                    "<b>⚠️ Copyright Notice</b>\n\n"
                                    "The file you requested has been <b>automatically deleted</b> "
                                    "due to <b>DMCA / Copyright</b> compliance.\n\n"
                                    "📌 <i>If you need the file again, please request it once more from the group.</i>\n\n"
                                    "🔒 <b>Note:</b> All files are auto-deleted after 5 hours to comply with copyright regulations."
                                ),
                                parse_mode='html'
                            )
                        except Exception as notify_err:
                            logging.warning(f"Failed to send DMCA notice to chat {entry['chat_id']}: {notify_err}")
                    except Exception as e:
                        logging.warning(f"Failed to auto-delete msg {entry['message_id']} in chat {entry['chat_id']}: {e}")
                    # Remove from queue regardless (message may already be deleted manually)
                    await remove_entry(entry['_id'])
            except Exception as e:
                logging.error(f"Error in auto-delete loop: {e}")
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
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current+new_diff+1)))
            for message in messages:
                yield message
                current += 1


app = Bot()
app.run()
