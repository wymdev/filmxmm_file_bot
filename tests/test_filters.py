import os
import unittest


os.environ.setdefault('API_ID', '123456')
os.environ.setdefault('API_HASH', 'test-hash')
os.environ.setdefault('BOT_TOKEN', '123456:test-token')
os.environ.setdefault('DATABASE_URI', 'mongodb://localhost')
os.environ.setdefault('ADMINS', '123456')
os.environ.setdefault('LOG_CHANNEL', '-100123456')

from pyrogram.types import InlineKeyboardButton

from database.filters_mdb import deserialize_buttons, serialize_buttons


class ButtonSerializationTests(unittest.TestCase):
    def test_json_round_trip(self):
        buttons = [[
            InlineKeyboardButton('Website', url='https://example.com'),
            InlineKeyboardButton('Action', callback_data=b'action'),
        ]]

        restored = deserialize_buttons(serialize_buttons(buttons))

        self.assertEqual(restored[0][0].text, 'Website')
        self.assertEqual(restored[0][0].url, 'https://example.com')
        self.assertEqual(restored[0][1].callback_data, b'action')

    def test_legacy_button_format_is_supported(self):
        legacy = (
            "[[pyrogram.types.InlineKeyboardButton("
            "text='Website', url='https://example.com')]]"
        )

        restored = deserialize_buttons(legacy)

        self.assertEqual(restored[0][0].url, 'https://example.com')

    def test_arbitrary_python_is_rejected(self):
        with self.assertRaises(ValueError):
            deserialize_buttons("__import__('os').system('echo unsafe')")
