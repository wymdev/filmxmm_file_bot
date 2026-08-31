import os
import unittest
from unittest.mock import AsyncMock, patch

from pymongo.errors import NotPrimaryError


os.environ.setdefault('API_ID', '123456')
os.environ.setdefault('API_HASH', 'test-hash')
os.environ.setdefault('BOT_TOKEN', '123456:test-token')
os.environ.setdefault('DATABASE_URI', 'mongodb://localhost')
os.environ.setdefault('ADMINS', '123456')
os.environ.setdefault('LOG_CHANNEL', '-100123456')

import bot
from plugins.commands import handle_database_errors
from translations import DATABASE_UNAVAILABLE


class DatabaseMaintenanceTests(unittest.IsolatedAsyncioTestCase):
    async def test_index_initialization_recovers_in_background(self):
        user_indexes = AsyncMock(
            side_effect=[NotPrimaryError('temporary election'), None]
        )
        media_indexes = AsyncMock()
        auto_delete_indexes = AsyncMock()
        pending_indexes = AsyncMock()
        miniapp_indexes = AsyncMock()

        with (
            patch.object(bot.db, 'ensure_indexes', user_indexes),
            patch.object(bot.Media, 'ensure_indexes', media_indexes),
            patch.object(bot, 'ensure_auto_delete_indexes', auto_delete_indexes),
            patch.object(bot, 'ensure_pending_request_indexes', pending_indexes),
            patch.object(bot, 'ensure_miniapp_indexes', miniapp_indexes),
            patch.object(bot.asyncio, 'sleep', AsyncMock()),
        ):
            await bot.Bot._database_maintenance_loop(object())

        self.assertEqual(user_indexes.await_count, 2)
        media_indexes.assert_awaited_once()
        auto_delete_indexes.assert_awaited_once()
        pending_indexes.assert_awaited_once()
        miniapp_indexes.assert_awaited_once()

    async def test_start_handler_reports_database_outage(self):
        async def failing_handler(client, message):
            raise NotPrimaryError('temporary election')

        reply = AsyncMock()
        message = unittest.mock.Mock(reply=reply)

        result = await handle_database_errors(failing_handler)(None, message)

        self.assertIs(result, reply.return_value)
        reply.assert_awaited_once_with(DATABASE_UNAVAILABLE)
