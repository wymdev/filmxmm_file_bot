import unittest
from unittest.mock import AsyncMock, patch

from pymongo.errors import NotPrimaryError

from database.mongo import retry_mongo_operation


class MongoRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_transient_error_is_retried(self):
        attempts = 0

        async def operation():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise NotPrimaryError('temporary election')
            return 'ok'

        with patch('database.mongo.asyncio.sleep', new=AsyncMock()):
            result = await retry_mongo_operation('test operation', operation)

        self.assertEqual(result, 'ok')
        self.assertEqual(attempts, 3)

    async def test_invalid_retry_count_is_rejected(self):
        async def operation():
            return None

        with self.assertRaises(ValueError):
            await retry_mongo_operation('test operation', operation, retries=0)
