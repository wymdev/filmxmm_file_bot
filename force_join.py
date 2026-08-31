import asyncio
import logging

from pyrogram import enums
from pyrogram.errors import FloodWait, PeerIdInvalid, UserNotParticipant

from info import ADMINS, AUTH_CHANNEL, REQ_CHANNEL, REQUIRED_CHANNEL_URL


logger = logging.getLogger(__name__)
_invite_link = None


def required_channel_id():
    return REQ_CHANNEL or AUTH_CHANNEL


def _status_name(status):
    return str(getattr(status, "value", status)).lower()


def chat_member_is_joined(member):
    status = _status_name(member.status)
    if status in {"member", "administrator", "owner", "creator"}:
        return True
    # Telegram can represent a still-present user as restricted.
    return status == "restricted" and bool(getattr(member, "is_member", False))


async def is_channel_member(bot, user_id):
    if int(user_id) in ADMINS:
        return True
    channel_id = required_channel_id()
    if not channel_id:
        return True
    try:
        member = await bot.get_chat_member(int(channel_id), int(user_id))
        return chat_member_is_joined(member)
    except (UserNotParticipant, PeerIdInvalid):
        return False
    except FloodWait as error:
        await asyncio.sleep(error.value)
        return await is_channel_member(bot, user_id)
    except Exception:
        logger.exception("Unable to check membership in %s", channel_id)
        return False


async def get_required_channel_url(bot):
    global _invite_link
    if REQUIRED_CHANNEL_URL:
        return REQUIRED_CHANNEL_URL
    if _invite_link:
        return _invite_link
    channel_id = required_channel_id()
    if not channel_id:
        return ""
    chat = await bot.get_chat(int(channel_id))
    if chat.username:
        _invite_link = f"https://t.me/{chat.username}"
    elif chat.invite_link:
        _invite_link = chat.invite_link
    else:
        _invite_link = (
            await bot.create_chat_invite_link(
                int(channel_id),
                creates_join_request=bool(REQ_CHANNEL),
            )
        ).invite_link
    return _invite_link


def set_required_channel_url(url):
    global _invite_link
    _invite_link = url
