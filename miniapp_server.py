import hashlib
import hmac
import html
import json
import logging
import re
import time
from pathlib import Path
from urllib.parse import parse_qsl

from aiohttp import web

from database.ia_filterdb import get_file_details, get_search_results
from database.miniapp_db import (
    add_favorite,
    get_profile,
    remove_favorite,
)
from database.pending_requests import claim_pending_request, save_pending_request
from force_join import get_required_channel_url, is_channel_member
from info import (
    BOT_TOKEN,
    MINI_APP_AUTH_MAX_AGE,
    MINI_APP_NAME,
    MINI_APP_URL,
    WEB_SERVER_ENABLED,
    WEB_SERVER_HOST,
    WEB_SERVER_PORT,
)
from translations import NO_SUCH_FILE, bilingual


logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).with_name("miniapp")
BOT_KEY = web.AppKey("bot")


def validate_init_data(init_data, bot_token=BOT_TOKEN, now=None, max_age=MINI_APP_AUTH_MAX_AGE):
    """Validate Telegram Mini App initData and return its trusted user."""
    if not init_data:
        raise ValueError("Missing Telegram init data")
    values = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = values.pop("hash", None)
    if not received_hash:
        raise ValueError("Missing init data hash")

    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise ValueError("Invalid Telegram init data")

    try:
        auth_date = int(values["auth_date"])
        user = json.loads(values["user"])
        user_id = int(user["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("Incomplete Telegram init data") from error

    current_time = int(time.time() if now is None else now)
    if auth_date > current_time + 60 or current_time - auth_date > max_age:
        raise ValueError("Expired Telegram init data")
    user["id"] = user_id
    return user


def _init_data_from_request(request):
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("tma "):
        return authorization[4:]
    return request.headers.get("X-Telegram-Init-Data", "")


@web.middleware
async def telegram_auth(request, handler):
    if request.path.startswith("/api/") and request.path != "/api/config":
        try:
            request["telegram_user"] = validate_init_data(_init_data_from_request(request))
        except ValueError as error:
            return web.json_response({"error": str(error)}, status=401)
    return await handler(request)


@web.middleware
async def cache_headers(request, handler):
    response = await handler(request)
    if request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=86400"
    elif request.path == "/" or request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def _movie_json(movie, favorite_ids=()):
    name = (movie.file_name or "").strip()
    if not name:
        plain_caption = html.unescape(
            re.sub(r"<[^>]+>", "", movie.caption or "")
        ).strip()
        name = next(
            (line.strip() for line in plain_caption.splitlines() if line.strip()),
            "Untitled Movie · အမည်မရှိသောရုပ်ရှင်",
        )[:160]
    lowered = name.lower()
    quality = next(
        (label for label in ("2160p", "1080p", "720p", "480p") if label in lowered),
        "HD",
    )
    return {
        "id": str(movie.id),
        "title": name,
        "quality": quality,
        "type": movie.file_type or "video",
        "size": int(movie.file_size or 0),
        "caption": movie.caption or "",
        "favorite": str(movie.id) in set(favorite_ids),
    }


async def _movies_for_ids(movie_ids, favorite_ids=()):
    movies = []
    for movie_id in movie_ids:
        details = await get_file_details(movie_id)
        if details:
            movies.append(_movie_json(details[0], favorite_ids))
    return movies


async def config_handler(request):
    bot = request.app[BOT_KEY]
    return web.json_response(
        {
            "name": MINI_APP_NAME,
            "bot_username": getattr(bot, "username", "").lstrip("@"),
            "mini_app_url": MINI_APP_URL,
        }
    )


async def session_handler(request):
    user = request["telegram_user"]
    profile = await get_profile(user["id"])
    return web.json_response(
        {
            "user": user,
            "favorite_ids": profile.get("favorites", []),
            "history_ids": profile.get("history", []),
        }
    )


async def movies_handler(request):
    user_id = request["telegram_user"]["id"]
    profile = await get_profile(user_id)
    query = request.query.get("q", "").strip()
    quality = request.query.get("quality", "").strip().lower()
    if quality in {"2160p", "1080p", "720p", "480p"}:
        query = f"{query} {quality}".strip()
    file_type = request.query.get("type", "").strip().lower()
    if file_type not in {"video", "document", "audio"}:
        file_type = None
    try:
        offset = max(0, int(request.query.get("offset", 0)))
    except ValueError:
        offset = 0
    movies, next_offset, total = await get_search_results(
        query,
        file_type=file_type,
        max_results=24,
        offset=offset,
        filter=True,
        include_caption=True,
    )
    return web.json_response(
        {
            "movies": [_movie_json(movie, profile.get("favorites", [])) for movie in movies],
            "next_offset": next_offset,
            "total": total,
        }
    )


async def movie_handler(request):
    movie_id = request.match_info["movie_id"]
    details = await get_file_details(movie_id)
    if not details:
        raise web.HTTPNotFound(text=NO_SUCH_FILE)
    profile = await get_profile(request["telegram_user"]["id"])
    return web.json_response(_movie_json(details[0], profile.get("favorites", [])))


async def favorites_handler(request):
    profile = await get_profile(request["telegram_user"]["id"])
    favorites = profile.get("favorites", [])
    return web.json_response({"movies": await _movies_for_ids(favorites, favorites)})


async def favorite_add_handler(request):
    movie_id = request.match_info["movie_id"]
    if not await get_file_details(movie_id):
        raise web.HTTPNotFound(text=NO_SUCH_FILE)
    await add_favorite(request["telegram_user"]["id"], movie_id)
    return web.json_response({"favorite": True})


async def favorite_remove_handler(request):
    await remove_favorite(
        request["telegram_user"]["id"],
        request.match_info["movie_id"],
    )
    return web.json_response({"favorite": False})


async def history_handler(request):
    profile = await get_profile(request["telegram_user"]["id"])
    favorite_ids = profile.get("favorites", [])
    return web.json_response(
        {"movies": await _movies_for_ids(profile.get("history", []), favorite_ids)}
    )


async def request_movie_handler(request):
    bot = request.app[BOT_KEY]
    user_id = request["telegram_user"]["id"]
    movie_id = request.match_info["movie_id"]
    if not await get_file_details(movie_id):
        raise web.HTTPNotFound(text=NO_SUCH_FILE)

    token = await save_pending_request(user_id, movie_id, "checksub")
    if not await is_channel_member(bot, user_id):
        return web.json_response(
            {
                "status": "join_required",
                "join_url": await get_required_channel_url(bot),
            }
        )

    pending = await claim_pending_request(token, user_id)
    if not pending:
        return web.json_response({"status": "already_processing"})

    from plugins.pending_delivery import deliver_claimed_request

    delivered = await deliver_claimed_request(bot, pending, announce=False)
    if not delivered:
        return web.json_response(
            {
                "error": bilingual(
                    "Movie delivery failed. Please try again.",
                    "ရုပ်ရှင်ပို့၍ မရပါ။ ထပ်မံကြိုးစားပါ။",
                )
            },
            status=500,
        )
    return web.json_response({"status": "delivered"})


async def index_handler(request):
    return web.FileResponse(STATIC_DIR / "index.html")


async def health_handler(request):
    return web.json_response({"ok": True})


def create_miniapp(bot):
    app = web.Application(middlewares=[telegram_auth, cache_headers])
    app[BOT_KEY] = bot
    app.router.add_get("/", index_handler)
    app.router.add_get("/health", health_handler)
    app.router.add_get("/api/config", config_handler)
    app.router.add_post("/api/session", session_handler)
    app.router.add_get("/api/movies", movies_handler)
    app.router.add_get("/api/movies/{movie_id}", movie_handler)
    app.router.add_post("/api/movies/{movie_id}/request", request_movie_handler)
    app.router.add_get("/api/favorites", favorites_handler)
    app.router.add_post("/api/favorites/{movie_id}", favorite_add_handler)
    app.router.add_delete("/api/favorites/{movie_id}", favorite_remove_handler)
    app.router.add_get("/api/history", history_handler)
    app.router.add_static("/static/", STATIC_DIR, name="miniapp-static")
    return app


async def start_miniapp_server(bot):
    if not WEB_SERVER_ENABLED:
        return None
    runner = web.AppRunner(create_miniapp(bot), access_log=logger)
    await runner.setup()
    site = web.TCPSite(runner, WEB_SERVER_HOST, WEB_SERVER_PORT)
    await site.start()
    logger.info("Mini App server listening on %s:%s", WEB_SERVER_HOST, WEB_SERVER_PORT)
    return runner
