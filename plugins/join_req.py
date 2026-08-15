#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) @AlbertEinsteinTG

from logging import getLogger
from pyrogram import Client, filters, enums
from pyrogram.types import ChatJoinRequest
from database.join_reqs import join_reqs
from info import ADMINS, REQ_CHANNEL


logger = getLogger(__name__)

@Client.on_chat_join_request(filters.chat(REQ_CHANNEL if REQ_CHANNEL else "self"))
async def handle_join_request(client, join_req: ChatJoinRequest):

    if join_reqs.is_active():
        user_id = join_req.from_user.id
        first_name = join_req.from_user.first_name
        username = join_req.from_user.username
        date = join_req.date

        await join_reqs.add_user(
            user_id=user_id,
            first_name=first_name,
            username=username,
            date=date
        )


@Client.on_message(filters.command("totalrequests") & filters.private & filters.user(ADMINS))
async def total_requests(client, message):

    if join_reqs.is_active():
        total = await join_reqs.get_all_users_count()
        await message.reply_text(
            text=f"Total Requests: {total}",
            parse_mode=enums.ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )


@Client.on_message(filters.command("purgerequests") & filters.private & filters.user(ADMINS))
async def purge_requests(client, message):
    
    if join_reqs.is_active():
        await join_reqs.delete_all_users()
        await message.reply_text(
            text="Purged All Requests.",
            parse_mode=enums.ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
