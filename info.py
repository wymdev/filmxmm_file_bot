import re
from os import environ

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


REQUIRED_ENV_VARS = (
    'API_ID',
    'API_HASH',
    'BOT_TOKEN',
    'DATABASE_URI',
    'ADMINS',
    'LOG_CHANNEL',
)

missing_env_vars = [name for name in REQUIRED_ENV_VARS if not environ.get(name, '').strip()]
if missing_env_vars:
    raise RuntimeError(
        'Missing required environment variables: ' + ', '.join(missing_env_vars)
    )


id_pattern = re.compile(r'^-?\d+$')


def is_enabled(value, default):
    normalized = str(value).strip().lower()
    if normalized in ["true", "yes", "1", "enable", "y"]:
        return True
    elif normalized in ["false", "no", "0", "disable", "n"]:
        return False
    return default


def get_int(name, default=None):
    value = environ.get(name, '')
    if not value.strip():
        if default is not None:
            return default
        raise RuntimeError(f'{name} must be set to an integer')
    try:
        return int(value)
    except ValueError as error:
        raise RuntimeError(f'{name} must be set to an integer') from error


def parse_peer_list(value):
    return [int(item) if id_pattern.fullmatch(item) else item for item in value.split()]


def parse_id_list(name, default=''):
    values = environ.get(name, default).split()
    try:
        return [int(value) for value in values]
    except ValueError as error:
        raise RuntimeError(f'{name} must contain only integer IDs') from error

# Bot information
SESSION = environ.get('SESSION', 'Media_search')
API_ID = get_int('API_ID')
API_HASH = environ['API_HASH'].strip()
BOT_TOKEN = environ['BOT_TOKEN'].strip()

# Bot settings
CACHE_TIME = get_int('CACHE_TIME', 300)
USE_CAPTION_FILTER = is_enabled(environ.get('USE_CAPTION_FILTER', 'False'), False)
PICS = (environ.get('PICS', 'https://te.legra.ph/file/119729ea3cdce4fefb6a1.jpg')).split()

# Admins, Channels & Users
ADMINS = parse_peer_list(environ['ADMINS'])
CHANNELS = parse_peer_list(environ.get('CHANNELS', ''))
auth_users = parse_peer_list(environ.get('AUTH_USERS', ''))
AUTH_USERS = (auth_users + ADMINS) if auth_users else []
AUTH_GROUPS = parse_id_list('AUTH_GROUP') or None

# MongoDB information
DATABASE_URI = environ['DATABASE_URI'].strip()
DATABASE_NAME = environ.get('DATABASE_NAME', 'FilmXBot')
COLLECTION_NAME = environ.get('COLLECTION_NAME', 'Telegram_files')

# FSUB
# REQUIRED_CHANNEL_ID is the clearer Phase 1/2 name.  AUTH_CHANNEL remains
# supported so existing deployments do not need to change immediately.
AUTH_CHANNEL = get_int(
    'REQUIRED_CHANNEL_ID',
    get_int('AUTH_CHANNEL', 0),
) or None
REQUIRED_CHANNEL_URL = environ.get('REQUIRED_CHANNEL_URL', '').strip()
PENDING_REQUEST_TTL_HOURS = get_int('PENDING_REQUEST_TTL_HOURS', 24)
# Set to False inside the bracket if you don't want to use Request Channel else set it to Channel ID
REQ_CHANNEL = get_int('REQ_CHANNEL', 0) or False
JOIN_REQS_DB = environ.get("JOIN_REQS_DB", '').strip() or DATABASE_URI

# Others
LOG_CHANNEL = get_int('LOG_CHANNEL')
SUPPORT_CHAT = environ.get('SUPPORT_CHAT', 'VJ_Bot_Disscussion')
P_TTI_SHOW_OFF = is_enabled((environ.get('P_TTI_SHOW_OFF', "True")), False)
IMDB = is_enabled((environ.get('IMDB', "False")), True)
SINGLE_BUTTON = is_enabled((environ.get('SINGLE_BUTTON', "True")), False)
CUSTOM_FILE_CAPTION = environ.get("CUSTOM_FILE_CAPTION", """<b>{file_caption}\n\n⚠️ <b>Warning:</b> This file will be deleted automatically after 5 hours due to copyright. Please make sure to download it or forward it to your saved messages!</b>""")
BATCH_FILE_CAPTION = environ.get("BATCH_FILE_CAPTION", CUSTOM_FILE_CAPTION)
IMDB_TEMPLATE = environ.get("IMDB_TEMPLATE", "<b>Query: {query}</b> \n‌‌‌‌IMDb Data:\n\n🏷 Title: <a href={url}>{title}</a>\n🎭 Genres: {genres}\n📆 Year: <a href={url}/releaseinfo>{year}</a>\n🌟 Rating: <a href={url}/ratings>{rating}</a> / 10")
LONG_IMDB_DESCRIPTION = is_enabled(environ.get("LONG_IMDB_DESCRIPTION", "False"), False)
SPELL_CHECK_REPLY = is_enabled(environ.get("SPELL_CHECK_REPLY", "False"), True)
MAX_LIST_ELM = get_int('MAX_LIST_ELM', 0) or None
INDEX_REQ_CHANNEL = get_int('INDEX_REQ_CHANNEL', LOG_CHANNEL)
FILE_STORE_CHANNEL = parse_id_list('FILE_STORE_CHANNEL')
MELCOW_NEW_USERS = is_enabled((environ.get('MELCOW_NEW_USERS', "False")), True)
PROTECT_CONTENT = is_enabled((environ.get('PROTECT_CONTENT', "False")), False)
PUBLIC_FILE_STORE = is_enabled((environ.get('PUBLIC_FILE_STORE', "True")), True)

# Telegram Mini App / embedded HTTP server
MINI_APP_URL = environ.get('MINI_APP_URL', '').strip()
MINI_APP_NAME = environ.get('MINI_APP_NAME', 'FilmX').strip() or 'FilmX'
MINI_APP_AUTH_MAX_AGE = get_int('MINI_APP_AUTH_MAX_AGE', 86400)
WEB_SERVER_ENABLED = is_enabled(environ.get('WEB_SERVER_ENABLED', 'True'), True)
WEB_SERVER_HOST = environ.get('WEB_SERVER_HOST', '0.0.0.0').strip()
WEB_SERVER_PORT = get_int('PORT', get_int('WEB_SERVER_PORT', 8080))

LOG_STR = "Current Cusomized Configurations are:-\n"
LOG_STR += ("IMDB Results are enabled, Bot will be showing imdb details for you queries.\n" if IMDB else "IMBD Results are disabled.\n")
LOG_STR += ("P_TTI_SHOW_OFF found , Users will be redirected to send /start to Bot PM instead of sending file file directly\n" if P_TTI_SHOW_OFF else "P_TTI_SHOW_OFF is disabled files will be send in PM, instead of sending start.\n")
LOG_STR += ("SINGLE_BUTTON is Found, filename and files size will be shown in a single button instead of two separate buttons\n" if SINGLE_BUTTON else "SINGLE_BUTTON is disabled , filename and file_sixe will be shown as different buttons\n")
LOG_STR += (f"CUSTOM_FILE_CAPTION enabled with value {CUSTOM_FILE_CAPTION}, your files will be send along with this customized caption.\n" if CUSTOM_FILE_CAPTION else "No CUSTOM_FILE_CAPTION Found, Default captions of file will be used.\n")
LOG_STR += ("Long IMDB storyline enabled." if LONG_IMDB_DESCRIPTION else "LONG_IMDB_DESCRIPTION is disabled , Plot will be shorter.\n")
LOG_STR += ("Spell Check Mode Is Enabled, bot will be suggesting related movies if movie not found\n" if SPELL_CHECK_REPLY else "SPELL_CHECK_REPLY Mode disabled\n")
LOG_STR += (f"MAX_LIST_ELM Found, long list will be shortened to first {MAX_LIST_ELM} elements\n" if MAX_LIST_ELM else "Full List of casts and crew will be shown in imdb template, restrict them by adding a value to MAX_LIST_ELM\n")
LOG_STR += f"Your current IMDB template is {IMDB_TEMPLATE}"
