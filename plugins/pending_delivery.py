import logging

from pyrogram import Client, filters

from database.miniapp_db import add_history
from database.pending_requests import (
    claim_next_pending_request,
    claim_pending_request,
    mark_pending_delivered,
    release_pending_request,
)
from force_join import chat_member_is_joined, is_channel_member, required_channel_id
from translations import (
    JOIN_REQUIRED_ALERT,
    MEMBERSHIP_VERIFIED,
    MEMBERSHIP_VERIFIED_SHORT,
    REQUEST_FINISHED,
)


logger = logging.getLogger(__name__)


async def deliver_claimed_request(client, pending, announce=True):
    """Deliver one atomically claimed request and finalize its state."""
    from plugins.commands import deliver_movie_request

    user_id = pending["user_id"]
    token = pending["_id"]
    try:
        if announce:
            await client.send_message(
                user_id,
                MEMBERSHIP_VERIFIED,
            )
        delivered = await deliver_movie_request(
            client,
            pending["request_id"],
            user_id,
            mode=pending.get("mode", "checksub"),
        )
        if not delivered:
            raise ValueError("The requested movie no longer exists")
        await mark_pending_delivered(token)
        await add_history(user_id, pending["request_id"])
        return True
    except Exception as error:
        logger.exception("Pending movie delivery failed for token %s", token)
        await release_pending_request(token, error)
        return False


@Client.on_callback_query(filters.regex(r"^check_movie:"), group=-1)
async def check_pending_movie(client, query):
    token = query.data.split(":", 1)[1]
    if not await is_channel_member(client, query.from_user.id):
        await query.answer(JOIN_REQUIRED_ALERT, show_alert=True)
        query.stop_propagation()
        return

    pending = await claim_pending_request(token, query.from_user.id)
    if not pending:
        await query.answer(
            REQUEST_FINISHED,
            show_alert=True,
        )
        query.stop_propagation()
        return

    await query.answer(MEMBERSHIP_VERIFIED_SHORT)
    try:
        await query.message.edit_text(
            MEMBERSHIP_VERIFIED
        )
    except Exception:
        logger.debug("Could not edit the force-join prompt", exc_info=True)
    await deliver_claimed_request(client, pending, announce=False)
    query.stop_propagation()


_channel_filter = (
    filters.chat(required_channel_id()) if required_channel_id() else filters.chat("self")
)


@Client.on_chat_member_updated(_channel_filter)
async def deliver_after_join(client, update):
    member = update.new_chat_member
    if not member or not chat_member_is_joined(member):
        return

    user_id = member.user.id
    # Deliver every distinct movie the user requested while they were outside
    # the channel. Atomic claims prevent the fallback callback racing this loop.
    while True:
        pending = await claim_next_pending_request(user_id)
        if not pending:
            break
        if not await deliver_claimed_request(client, pending, announce=True):
            break
