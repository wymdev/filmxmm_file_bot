#!/usr/bin/env python3

import asyncio
import logging

from pyrogram import Client, enums
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from database.pending_requests import save_pending_request
from force_join import (
    get_required_channel_url,
    is_channel_member,
    set_required_channel_url,
)
from info import ADMINS, AUTH_CHANNEL, REQ_CHANNEL
from translations import FORCE_JOIN_TEXT, JOIN_LOOKUP_FAILED


logger = logging.getLogger(__name__)


async def ForceSub(
    bot: Client,
    update: Message,
    file_id: str = False,
    mode="checksub",
):
    """Verify membership and remember the requested file when it is missing."""
    user_id = update.from_user.id
    if user_id in ADMINS or not (AUTH_CHANNEL or REQ_CHANNEL):
        return True

    if await is_channel_member(bot, user_id):
        return True

    try:
        invite_link = await get_required_channel_url(bot)
    except FloodWait as error:
        await asyncio.sleep(error.value)
        return await ForceSub(bot, update, file_id=file_id, mode=mode)
    except Exception:
        logger.exception("Unable to create the force-join invite link")
        await update.reply(JOIN_LOOKUP_FAILED)
        return False

    token = None
    if file_id and str(file_id) not in {"False", "subscribe"}:
        token = await save_pending_request(user_id, str(file_id), mode)

    buttons = [[InlineKeyboardButton("📢 Join Channel · ချန်နယ်ဝင်ရန်", url=invite_link)]]
    if token:
        buttons.append(
            [
                InlineKeyboardButton(
                    "✅ Get Movie · ရုပ်ရှင်ရယူရန်",
                    callback_data=f"check_movie:{token}",
                )
            ]
        )

    # Callback queries have .message rather than .chat. New Phase 1 buttons no
    # longer rely on this path, but keeping the distinction preserves old links.
    target = update if hasattr(update, "chat") else update.message
    await target.reply(
        text=FORCE_JOIN_TEXT,
        quote=True,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML,
    )
    return False


def set_global_invite(url: str):
    """Backward-compatible alias used by older deployments/tests."""
    set_required_channel_url(url)
