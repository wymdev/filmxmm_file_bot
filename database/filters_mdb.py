import ast
import base64
import json
import logging

from pyrogram import enums
from pyrogram.types import InlineKeyboardButton

from database.mongo import create_motor_client
from info import DATABASE_URI, DATABASE_NAME

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

myclient = create_motor_client(DATABASE_URI)
mydb = myclient[DATABASE_NAME]

BUTTON_FIELDS = (
    'text',
    'callback_data',
    'url',
    'user_id',
    'switch_inline_query',
    'switch_inline_query_current_chat',
)


def _serialize_button(button):
    data = {}
    for field in BUTTON_FIELDS:
        value = getattr(button, field, None)
        if isinstance(value, bytes):
            value = {'bytes': base64.b64encode(value).decode('ascii')}
        if value is not None:
            data[field] = value
    return data


def serialize_buttons(buttons):
    if not buttons or buttons == "[]":
        return "[]"
    return json.dumps([
        [_serialize_button(button) for button in row]
        for row in buttons
    ])


def _deserialize_button(data):
    values = {}
    for field in BUTTON_FIELDS:
        value = data.get(field)
        if isinstance(value, dict) and set(value) == {'bytes'}:
            value = base64.b64decode(value['bytes'])
        if value is not None:
            values[field] = value
    if not values.get('text'):
        raise ValueError('Button text is required')
    return InlineKeyboardButton(**values)


def _legacy_button(call):
    if not isinstance(call, ast.Call):
        raise ValueError('Invalid legacy button')

    name = call.func
    while isinstance(name, ast.Attribute):
        if name.attr == 'InlineKeyboardButton':
            break
        name = name.value
    else:
        if not isinstance(name, ast.Name) or name.id != 'InlineKeyboardButton':
            raise ValueError('Invalid legacy button type')

    if call.args:
        raise ValueError('Legacy buttons must use named arguments')

    data = {}
    for keyword in call.keywords:
        if keyword.arg not in BUTTON_FIELDS:
            continue
        data[keyword.arg] = ast.literal_eval(keyword.value)
    return _deserialize_button(data)


def deserialize_buttons(value):
    if not value or value == "[]":
        return []

    try:
        payload = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        tree = ast.parse(value, mode='eval')
        if not isinstance(tree.body, ast.List):
            raise ValueError('Invalid legacy keyboard') from None
        return [
            [_legacy_button(button) for button in row.elts]
            for row in tree.body.elts
            if isinstance(row, ast.List)
        ]

    if not isinstance(payload, list):
        raise ValueError('Invalid keyboard payload')
    return [
        [_deserialize_button(button) for button in row]
        for row in payload
        if isinstance(row, list)
    ]



async def add_filter(grp_id, text, reply_text, btn, file, alert):
    mycol = mydb[str(grp_id)]
    # mycol.create_index([('text', 'text')])

    data = {
        'text':str(text),
        'reply':str(reply_text),
        'btn':serialize_buttons(btn),
        'file':str(file),
        'alert':str(alert)
    }

    try:
        await mycol.update_one({'text': str(text)},  {"$set": data}, upsert=True)
    except:
        logger.exception('Some error occured!', exc_info=True)
             
     
async def find_filter(group_id, name):
    mycol = mydb[str(group_id)]
    
    try:
        file = await mycol.find_one({"text": name})
        if not file:
            return None, None, None, None
        reply_text = file['reply']
        btn = file['btn']
        fileid = file['file']
        alert = file.get('alert')
        return reply_text, btn, alert, fileid
    except:
        return None, None, None, None


async def get_filters(group_id):
    mycol = mydb[str(group_id)]

    texts = []
    try:
        async for file in mycol.find():
            text = file['text']
            texts.append(text)
    except Exception:
        logger.exception('Could not load filters for group %s', group_id)
    return texts


async def delete_filter(message, text, group_id):
    mycol = mydb[str(group_id)]
    
    myquery = {'text':text }
    query = await mycol.count_documents(myquery)
    if query == 1:
        await mycol.delete_one(myquery)
        await message.reply_text(
            f"'`{text}`'  deleted. I'll not respond to that filter anymore.",
            quote=True,
            parse_mode=enums.ParseMode.MARKDOWN
        )
    else:
        await message.reply_text("Couldn't find that filter!", quote=True)


async def del_all(message, group_id, title):
    if str(group_id) not in await mydb.list_collection_names():
        await message.edit_text(f"Nothing to remove in {title}!")
        return

    mycol = mydb[str(group_id)]
    try:
        await mycol.drop()
        await message.edit_text(f"All filters from {title} has been removed")
    except:
        await message.edit_text("Couldn't remove all filters from group!")
        return


async def count_filters(group_id):
    mycol = mydb[str(group_id)]

    count = await mycol.count_documents({})
    return False if count == 0 else count


async def filter_stats():
    collections = await mydb.list_collection_names()

    if "CONNECTION" in collections:
        collections.remove("CONNECTION")

    totalcount = 0
    for collection in collections:
        mycol = mydb[collection]
        count = await mycol.count_documents({})
        totalcount += count

    totalcollections = len(collections)

    return totalcollections, totalcount
