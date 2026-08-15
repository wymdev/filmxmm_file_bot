import unittest

from pyrogram import utils as pyrogram_utils


class TelegramPeerTests(unittest.TestCase):
    def test_new_channel_ids_are_recognized(self):
        self.assertEqual(pyrogram_utils.get_peer_type(-1003922880580), 'channel')
        self.assertEqual(pyrogram_utils.get_peer_type(-1004425001338), 'channel')
