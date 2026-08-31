from pyrogram import filters, Client, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.connections_mdb import add_connection, all_connections, if_active, delete_connection
from info import ADMINS
from translations import BOT_NOT_IN_GROUP, GENERIC_ERROR, bilingual
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


@Client.on_message((filters.private | filters.group) & filters.command('connect'))
async def addconnection(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Use /connect {message.chat.id} in PM")
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        try:
            cmd, group_id = message.text.split(" ", 1)
        except:
            await message.reply_text(
                "<b>Enter the correct format:</b>\n\n"
                "<code>/connect groupid</code>\n\n"
                "<i>Add this bot to your group and use <code>/id</code> to get the group ID.</i>\n\n"
                "<b>🇲🇲 ပုံစံမှန်ဖြင့် ထည့်ပါ:</b>\n\n"
                "<code>/connect groupid</code>\n\n"
                "<i>Bot ကို group ထဲထည့်ပြီး group ID ရယူရန် <code>/id</code> ကို အသုံးပြုပါ။</i>",
                quote=True
            )
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        group_id = message.chat.id

    try:
        st = await client.get_chat_member(group_id, userid)
        if (
                st.status != enums.ChatMemberStatus.ADMINISTRATOR
                and st.status != enums.ChatMemberStatus.OWNER
                and userid not in ADMINS
        ):
            await message.reply_text(bilingual(
                "You must be an administrator in that group.",
                "သင်သည် ထို group ၏ admin ဖြစ်ရပါမည်။",
            ), quote=True)
            return
    except Exception as e:
        logger.exception(e)
        await message.reply_text(
            bilingual(
                "Invalid group ID. If it is correct, make sure the bot is present in the group.",
                "Group ID မမှန်ကန်ပါ။ ID မှန်ပါက bot သည် group ထဲတွင် ရှိကြောင်း စစ်ဆေးပါ။",
            ),
            quote=True,
        )

        return
    try:
        st = await client.get_chat_member(group_id, "me")
        if st.status == enums.ChatMemberStatus.ADMINISTRATOR:
            ttl = await client.get_chat(group_id)
            title = ttl.title

            addcon = await add_connection(str(group_id), str(userid))
            if addcon:
                await message.reply_text(
                    bilingual(
                        f"Successfully connected to **{title}**. You can now manage it from my private chat.",
                        f"**{title}** နှင့် အောင်မြင်စွာ ချိတ်ဆက်ပြီးပါပြီ။ ယခု bot private chat မှ စီမံနိုင်ပါသည်။",
                    ),
                    quote=True,
                    parse_mode=enums.ParseMode.MARKDOWN
                )
                if chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
                    await client.send_message(
                        userid,
                        f"Connected to **{title}** !",
                        parse_mode=enums.ParseMode.MARKDOWN
                    )
            else:
                await message.reply_text(
                    bilingual(
                        "You're already connected to this chat.",
                        "ဤ chat နှင့် ချိတ်ဆက်ပြီးသားဖြစ်ပါသည်။",
                    ),
                    quote=True
                )
        else:
            await message.reply_text(BOT_NOT_IN_GROUP, quote=True)
    except Exception as e:
        logger.exception(e)
        await message.reply_text(GENERIC_ERROR, quote=True)
        return


@Client.on_message((filters.private | filters.group) & filters.command('disconnect'))
async def deleteconnection(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Use /connect {message.chat.id} in PM")
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        await message.reply_text(bilingual(
            "Use /connections to view or disconnect groups.",
            "ချိတ်ဆက်ထားသော group များကို ကြည့်ရန် သို့မဟုတ် ဖြုတ်ရန် /connections ကို သုံးပါ။",
        ), quote=True)

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        group_id = message.chat.id

        st = await client.get_chat_member(group_id, userid)
        if (
                st.status != enums.ChatMemberStatus.ADMINISTRATOR
                and st.status != enums.ChatMemberStatus.OWNER
                and userid not in ADMINS
        ):
            return

        delcon = await delete_connection(str(userid), str(group_id))
        if delcon:
            await message.reply_text("Successfully disconnected from this chat", quote=True)
        else:
            await message.reply_text(bilingual(
                "This chat is not connected. Use /connect to connect it.",
                "ဤ chat ကို မချိတ်ဆက်ရသေးပါ။ ချိတ်ဆက်ရန် /connect ကို သုံးပါ။",
            ), quote=True)


@Client.on_message(filters.private & filters.command(["connections"]))
async def connections(client, message):
    userid = message.from_user.id

    groupids = await all_connections(str(userid))
    if groupids is None:
        await message.reply_text(
            "There are no active connections!! Connect to some groups first.",
            quote=True
        )
        return
    buttons = []
    for groupid in groupids:
        try:
            ttl = await client.get_chat(int(groupid))
            title = ttl.title
            active = await if_active(str(userid), str(groupid))
            act = " - ACTIVE" if active else ""
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{title}{act}", callback_data=f"groupcb:{groupid}:{act}"
                    )
                ]
            )
        except Exception:
            logger.debug("Could not load connected group %s", groupid, exc_info=True)
    if buttons:
        await message.reply_text(
            "Your connected group details ;\n\n",
            reply_markup=InlineKeyboardMarkup(buttons),
            quote=True
        )
    else:
        await message.reply_text(
            "There are no active connections!! Connect to some groups first.",
            quote=True
        )
