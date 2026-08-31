import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


os.environ.setdefault("API_ID", "123456")
os.environ.setdefault("API_HASH", "test-hash")
os.environ.setdefault("BOT_TOKEN", "123456:test-token")
os.environ.setdefault("DATABASE_URI", "mongodb://localhost")
os.environ.setdefault("ADMINS", "123456")
os.environ.setdefault("LOG_CHANNEL", "-100123456")

from database.pending_requests import request_token
from force_join import chat_member_is_joined
from plugins import fsub


class MembershipTests(unittest.TestCase):
    def test_accepts_member_admin_owner_and_present_restricted(self):
        for status in ("member", "administrator", "owner", "creator"):
            self.assertTrue(chat_member_is_joined(SimpleNamespace(status=status)))
        self.assertTrue(
            chat_member_is_joined(
                SimpleNamespace(status="restricted", is_member=True)
            )
        )

    def test_rejects_left_banned_and_absent_restricted(self):
        for status in ("left", "banned"):
            self.assertFalse(chat_member_is_joined(SimpleNamespace(status=status)))
        self.assertFalse(
            chat_member_is_joined(
                SimpleNamespace(status="restricted", is_member=False)
            )
        )

    def test_pending_token_is_short_and_stable(self):
        first = request_token(7, "movie-id", "checksub")
        self.assertEqual(first, request_token(7, "movie-id", "checksub"))
        self.assertEqual(len(first), 20)


class ForceJoinScreenTests(unittest.IsolatedAsyncioTestCase):
    async def test_movie_request_is_saved_before_join_screen(self):
        message = SimpleNamespace(
            chat=SimpleNamespace(id=7),
            from_user=SimpleNamespace(id=7),
            reply=AsyncMock(),
        )
        with (
            patch.object(fsub, "AUTH_CHANNEL", -100123),
            patch.object(fsub, "is_channel_member", AsyncMock(return_value=False)),
            patch.object(
                fsub,
                "get_required_channel_url",
                AsyncMock(return_value="https://t.me/filmxtest"),
            ),
            patch.object(
                fsub,
                "save_pending_request",
                AsyncMock(return_value="short-token"),
            ) as save,
        ):
            result = await fsub.ForceSub(
                SimpleNamespace(),
                message,
                file_id="movie-id",
                mode="checksubp",
            )

        self.assertFalse(result)
        save.assert_awaited_once_with(7, "movie-id", "checksubp")
        markup = message.reply.await_args.kwargs["reply_markup"]
        self.assertIn("Join Channel", markup.inline_keyboard[0][0].text)
        self.assertIn("ချန်နယ်", markup.inline_keyboard[0][0].text)
        self.assertEqual(
            markup.inline_keyboard[1][0].callback_data,
            "check_movie:short-token",
        )
