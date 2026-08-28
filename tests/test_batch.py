import base64
import json
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

from bot import Bot
from plugins import commands
from plugins.genlink import (
    PENDING_BATCHES,
    collect_forwarded_batch,
    gen_link_batch,
    parse_batch_link,
)


class BatchLinkTests(unittest.TestCase):
    def test_parses_public_and_private_post_links(self):
        self.assertEqual(
            parse_batch_link("https://t.me/TeamEvamaria/20?single"),
            ("TeamEvamaria", 20),
        )
        self.assertEqual(
            parse_batch_link("https://t.me/c/1234567890/42"),
            (-1001234567890, 42),
        )

    def test_rejects_non_post_links(self):
        with self.assertRaises(ValueError):
            parse_batch_link("https://example.com/channel/20")


class BatchGenerationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        PENDING_BATCHES.clear()

    async def test_accepts_extra_whitespace_and_reversed_endpoints(self):
        status = SimpleNamespace(edit=AsyncMock())
        message = SimpleNamespace(
            text=(
                "/batch   https://t.me/c/1234567890/20   "
                "https://t.me/c/1234567890/10"
            ),
            from_user=SimpleNamespace(id=7),
            reply=AsyncMock(return_value=status),
        )
        document = SimpleNamespace(
            file_id="file-id",
            file_name="movie.mkv",
            file_size=100,
        )
        source_message = SimpleNamespace(
            id=10,
            empty=False,
            service=False,
            media=SimpleNamespace(value="document"),
            document=document,
            caption="",
        )

        class FakeBot:
            def __init__(self):
                self.iter_args = None
                self.send_document = AsyncMock(return_value=SimpleNamespace(id=55))

            async def get_chat(self, chat_id):
                return SimpleNamespace(id=chat_id)

            async def iter_messages(self, chat_id, last_id, first_id):
                self.iter_args = (chat_id, last_id, first_id)
                yield source_message

        bot = FakeBot()
        with patch("plugins.genlink.temp.U_NAME", "test_bot", create=True):
            await gen_link_batch(bot, message)

        self.assertEqual(bot.iter_args, (-1001234567890, 20, 10))
        bot.send_document.assert_awaited_once()
        self.assertIn("Contains `1` files", status.edit.await_args.args[0])

    async def test_three_links_select_only_the_exact_messages(self):
        status = SimpleNamespace(edit=AsyncMock())
        message = SimpleNamespace(
            text=(
                "/batch https://t.me/c/1234567890/10 "
                "https://t.me/c/1234567890/20 "
                "https://t.me/c/1234567890/30"
            ),
            from_user=SimpleNamespace(id=7),
            reply=AsyncMock(return_value=status),
        )

        class FakeBot:
            def __init__(self):
                self.requested_ids = []
                self.send_document = AsyncMock(return_value=SimpleNamespace(id=55))

            async def get_chat(self, chat_id):
                return SimpleNamespace(id=chat_id)

            async def get_messages(self, chat_id, message_id):
                self.requested_ids.append(message_id)
                media = SimpleNamespace(
                    file_id=f"file-{message_id}",
                    file_name=f"{message_id}.mkv",
                    file_size=100,
                )
                return SimpleNamespace(
                    id=message_id,
                    empty=False,
                    service=False,
                    media=SimpleNamespace(value="document"),
                    document=media,
                    caption="",
                )

            async def iter_messages(self, *args):
                raise AssertionError("Three links must not be expanded as a range")
                yield

        bot = FakeBot()
        with patch("plugins.genlink.temp.U_NAME", "test_bot", create=True):
            await gen_link_batch(bot, message)

        self.assertEqual(bot.requested_ids, [10, 20, 30])
        manifest = bot.send_document.await_args.args[1]
        self.assertEqual(
            [item["file_id"] for item in json.loads(manifest.getvalue())],
            ["file-10", "file-20", "file-30"],
        )

    async def test_forwarded_media_then_batch_uses_the_queue(self):
        forwarded_media = SimpleNamespace(
            file_id="forwarded-file",
            file_name="forwarded.mkv",
            file_size=200,
        )
        forwarded = SimpleNamespace(
            id=1,
            from_user=SimpleNamespace(id=7),
            empty=False,
            service=False,
            media=SimpleNamespace(value="document"),
            document=forwarded_media,
            caption="Forwarded caption",
            reply=AsyncMock(),
        )
        await collect_forwarded_batch(None, forwarded)

        status = SimpleNamespace(edit=AsyncMock())
        command = SimpleNamespace(
            text="/pbatch",
            from_user=SimpleNamespace(id=7),
            reply=AsyncMock(return_value=status),
        )
        bot = SimpleNamespace(
            send_document=AsyncMock(return_value=SimpleNamespace(id=55))
        )
        with patch("plugins.genlink.temp.U_NAME", "test_bot", create=True):
            await gen_link_batch(bot, command)

        manifest = bot.send_document.await_args.args[1]
        stored = json.loads(manifest.getvalue())
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["file_id"], "forwarded-file")
        self.assertTrue(stored[0]["protect"])
        self.assertNotIn(7, PENDING_BATCHES)


class MessageRangeTests(unittest.IsolatedAsyncioTestCase):
    async def test_iterator_uses_valid_200_message_chunks(self):
        class FakeClient:
            def __init__(self):
                self.calls = []

            async def get_messages(self, chat_id, message_ids):
                self.calls.append((chat_id, message_ids))
                return [SimpleNamespace(id=message_id) for message_id in message_ids]

        client = FakeClient()
        received = [
            message.id
            async for message in Bot.iter_messages(client, -100123, 450, 0)
        ]

        self.assertEqual(received, list(range(1, 451)))
        self.assertEqual([len(ids) for _, ids in client.calls], [200, 200, 50])
        self.assertEqual(client.calls[0][1][0], 1)
        self.assertEqual(client.calls[-1][1][-1], 450)

    async def test_iterator_includes_both_range_endpoints(self):
        class FakeClient:
            async def get_messages(self, chat_id, message_ids):
                return [SimpleNamespace(id=message_id) for message_id in message_ids]

        received = [
            message.id
            async for message in Bot.iter_messages(FakeClient(), "channel", 20, 10)
        ]
        self.assertEqual(received, list(range(10, 21)))


class BatchDeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        commands.BATCH_FILES.clear()

    async def test_start_keeps_underscores_in_batch_payload_for_force_sub(self):
        data = "DSTORE-ab_cd_ef"
        message = SimpleNamespace(
            chat=SimpleNamespace(type=commands.enums.ChatType.PRIVATE),
            from_user=SimpleNamespace(id=99, first_name="User", mention="User"),
            command=["start", data],
        )
        client = SimpleNamespace()

        with (
            patch.object(commands.db, "is_user_exist", AsyncMock(return_value=True)),
            patch.object(commands, "ForceSub", AsyncMock(return_value=False)) as force_sub,
        ):
            await commands.start(client, message)

        force_sub.assert_awaited_once_with(
            client,
            message,
            file_id=data,
            mode="checksub",
        )

    async def test_missing_batch_document_returns_expired_message(self):
        status = SimpleNamespace(edit=AsyncMock(), delete=AsyncMock())
        client = SimpleNamespace(
            send_message=AsyncMock(return_value=status),
            get_messages=AsyncMock(
                return_value=SimpleNamespace(empty=True, document=None)
            ),
        )

        await commands.deliver_saved_batch(
            client,
            SimpleNamespace(chat=SimpleNamespace(id=99)),
            "123",
        )

        status.edit.assert_awaited_once_with(
            "This batch link is invalid or has expired."
        )

    async def test_custom_caption_failure_retries_original_caption(self):
        commands.BATCH_FILES["123"] = [
            {
                "file_id": "cached-file",
                "title": "movie.mkv",
                "size": 100,
                "caption": "Original caption",
                "protect": True,
            }
        ]
        status = SimpleNamespace(edit=AsyncMock(), delete=AsyncMock())
        sent = SimpleNamespace(id=77)
        client = SimpleNamespace(
            send_message=AsyncMock(return_value=status),
            send_cached_media=AsyncMock(
                side_effect=[RuntimeError("bad formatted caption"), sent]
            ),
        )

        with (
            patch.object(commands, "BATCH_FILE_CAPTION", "<b>{file_caption}</b>"),
            patch.object(commands, "schedule_auto_delete", AsyncMock()) as schedule,
            patch.object(commands.asyncio, "sleep", AsyncMock()),
        ):
            await commands.deliver_saved_batch(
                client,
                SimpleNamespace(chat=SimpleNamespace(id=99)),
                "123",
            )

        self.assertEqual(client.send_cached_media.await_count, 2)
        self.assertEqual(
            client.send_cached_media.await_args_list[1].kwargs["caption"],
            "Original caption",
        )
        schedule.assert_awaited_once_with(99, 77)
        status.delete.assert_awaited_once()

    async def test_compact_direct_store_payload_preserves_protection(self):
        raw = "10_20_-1003922880580_p"
        payload = base64.urlsafe_b64encode(raw.encode("ascii")).decode().rstrip("=")
        self.assertLessEqual(len(f"DSTORE-{payload}"), 64)

        copied = SimpleNamespace(id=88)
        source_message = SimpleNamespace(
            empty=False,
            media=None,
            copy=AsyncMock(return_value=copied),
        )
        status = SimpleNamespace(edit=AsyncMock(), delete=AsyncMock())

        class FakeClient:
            send_message = AsyncMock(return_value=status)

            async def iter_messages(self, chat_id, last_id, first_id):
                self.iter_args = (chat_id, last_id, first_id)
                yield source_message

        client = FakeClient()
        with patch.object(commands.asyncio, "sleep", AsyncMock()):
            await commands.deliver_direct_store_batch(
                client,
                SimpleNamespace(chat=SimpleNamespace(id=99)),
                payload,
            )

        self.assertEqual(client.iter_args, (-1003922880580, 20, 10))
        source_message.copy.assert_awaited_once_with(
            99,
            protect_content=True,
        )
        status.delete.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
