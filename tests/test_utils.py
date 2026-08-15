import os
import unittest
from types import SimpleNamespace


os.environ.setdefault('API_ID', '123456')
os.environ.setdefault('API_HASH', 'test-hash')
os.environ.setdefault('BOT_TOKEN', '123456:test-token')
os.environ.setdefault('DATABASE_URI', 'mongodb://localhost')
os.environ.setdefault('ADMINS', '123456')
os.environ.setdefault('LOG_CHANNEL', '-100123456')

from utils import get_file_id, get_size


class UtilityTests(unittest.TestCase):
    def test_get_file_id_uses_pyrogram_enum_value(self):
        photo = SimpleNamespace(file_id='photo-id')
        message = SimpleNamespace(media=True, photo=photo)

        result = get_file_id(message)

        self.assertIs(result, photo)
        self.assertEqual(result.message_type, 'photo')

    def test_get_size_stays_within_known_units(self):
        self.assertEqual(get_size(1024 ** 7), '1024.00 EB')
