import os
import unittest
from unittest.mock import AsyncMock, patch


os.environ.setdefault("API_ID", "123456")
os.environ.setdefault("API_HASH", "test-hash")
os.environ.setdefault("BOT_TOKEN", "123456:test-token")
os.environ.setdefault("DATABASE_URI", "mongodb://localhost")
os.environ.setdefault("ADMINS", "123456")
os.environ.setdefault("LOG_CHANNEL", "-100123456")

from database import ia_filterdb


class FakeCursor:
    def sort(self, *args):
        return self

    def skip(self, *args):
        return self

    def limit(self, *args):
        return self

    async def to_list(self, length):
        return []


class SearchQueryTests(unittest.IsolatedAsyncioTestCase):
    async def test_each_term_must_match_filename_or_caption(self):
        count = AsyncMock(return_value=0)
        with (
            patch.object(ia_filterdb.Media, "count_documents", count),
            patch.object(ia_filterdb.Media, "find", return_value=FakeCursor()),
        ):
            await ia_filterdb.get_search_results(
                '"Dune Part Two" 1080p',
                file_type="video",
                include_caption=True,
            )

        mongo_filter = count.await_args.args[0]
        self.assertEqual(len(mongo_filter["$and"]), 2)
        self.assertEqual(mongo_filter["file_type"], "video")
        self.assertIn("caption", mongo_filter["$and"][0]["$or"][1])

    async def test_search_terms_are_regex_escaped(self):
        count = AsyncMock(return_value=0)
        with (
            patch.object(ia_filterdb.Media, "count_documents", count),
            patch.object(ia_filterdb.Media, "find", return_value=FakeCursor()),
        ):
            await ia_filterdb.get_search_results(
                "movie.*",
                include_caption=True,
            )

        regex = count.await_args.args[0]["$or"][0]["file_name"]
        self.assertIn(r"\.\*", regex.pattern)

    async def test_exact_page_does_not_offer_an_empty_next_page(self):
        with (
            patch.object(
                ia_filterdb.Media,
                "count_documents",
                AsyncMock(return_value=24),
            ),
            patch.object(ia_filterdb.Media, "find", return_value=FakeCursor()),
        ):
            _, next_offset, total = await ia_filterdb.get_search_results(
                "",
                max_results=24,
            )

        self.assertEqual(total, 24)
        self.assertEqual(next_offset, "")
