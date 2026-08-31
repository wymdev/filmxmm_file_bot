import hashlib
import hmac
import json
import os
import unittest
from types import SimpleNamespace
from urllib.parse import urlencode

from aiohttp.test_utils import TestClient, TestServer


os.environ.setdefault("API_ID", "123456")
os.environ.setdefault("API_HASH", "test-hash")
os.environ.setdefault("BOT_TOKEN", "123456:test-token")
os.environ.setdefault("DATABASE_URI", "mongodb://localhost")
os.environ.setdefault("ADMINS", "123456")
os.environ.setdefault("LOG_CHANNEL", "-100123456")

from miniapp_server import _movie_json, create_miniapp, validate_init_data


TOKEN = "123456:test-token"
NOW = 1_800_000_000


def signed_init_data(**overrides):
    values = {
        "auth_date": str(NOW),
        "query_id": "test-query",
        "user": json.dumps({"id": 42, "first_name": "Film"}, separators=(",", ":")),
    }
    values.update(overrides)
    check = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


class MiniAppAuthenticationTests(unittest.TestCase):
    def test_valid_init_data_returns_trusted_user(self):
        user = validate_init_data(signed_init_data(), TOKEN, now=NOW)
        self.assertEqual(user["id"], 42)
        self.assertEqual(user["first_name"], "Film")

    def test_tampered_init_data_is_rejected(self):
        data = signed_init_data().replace("Film", "Fake")
        with self.assertRaisesRegex(ValueError, "Invalid"):
            validate_init_data(data, TOKEN, now=NOW)

    def test_expired_init_data_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Expired"):
            validate_init_data(signed_init_data(), TOKEN, now=NOW + 90_000)


class MovieSerializationTests(unittest.TestCase):
    def test_caption_is_used_when_telegram_video_has_no_filename(self):
        movie = SimpleNamespace(
            id="movie-id",
            file_name="",
            file_type="video",
            file_size=100,
            caption="<b>Example Movie (2026)</b>\n1080p",
        )

        result = _movie_json(movie)

        self.assertEqual(result["title"], "Example Movie (2026)")

    def test_untitled_fallback_is_bilingual(self):
        movie = SimpleNamespace(
            id="movie-id",
            file_name=None,
            file_type="video",
            file_size=100,
            caption=None,
        )

        result = _movie_json(movie)

        self.assertIn("Untitled Movie", result["title"])
        self.assertIn("ရုပ်ရှင်", result["title"])


class MiniAppHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = TestClient(
            TestServer(create_miniapp(SimpleNamespace(username="@filmxtestbot")))
        )
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    async def test_frontend_and_health_are_served(self):
        health = await self.client.get("/health")
        self.assertEqual(health.status, 200)
        self.assertEqual(await health.json(), {"ok": True})

        page = await self.client.get("/")
        self.assertEqual(page.status, 200)
        self.assertIn("FilmX", await page.text())

        script = await self.client.get("/static/app.js")
        self.assertEqual(script.status, 200)
        self.assertIn("max-age", script.headers["Cache-Control"])

    async def test_movie_api_rejects_missing_telegram_init_data(self):
        response = await self.client.get("/api/movies")
        self.assertEqual(response.status, 401)
