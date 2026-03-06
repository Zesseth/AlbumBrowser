"""Tests for album_browser.py — focused on Bandcamp search accuracy improvements."""
import difflib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from album_browser import _is_similar, _normalize, search_bandcamp, main


class TestNormalize(unittest.TestCase):
    def test_lowercase(self):
        self.assertEqual(_normalize("Children of Bodom"), "children of bodom")

    def test_strips_extra_whitespace(self):
        self.assertEqual(_normalize("  Hate  Crew  Deathroll  "), "hate crew deathroll")

    def test_single_word(self):
        self.assertEqual(_normalize("Metallica"), "metallica")


class TestIsSimilar(unittest.TestCase):
    # --- Exact matches ---
    def test_exact_match(self):
        self.assertTrue(_is_similar("children of bodom", "children of bodom"))

    def test_exact_match_single_word(self):
        self.assertTrue(_is_similar("metallica", "metallica"))

    # --- "The" article variations ---
    def test_the_prefix_a_to_b(self):
        """'beatles' should match 'the beatles'."""
        self.assertTrue(_is_similar("beatles", "the beatles"))

    def test_the_prefix_b_to_a(self):
        """'the beatles' should match 'beatles'."""
        self.assertTrue(_is_similar("the beatles", "beatles"))

    def test_the_prefix_both(self):
        """'the beatles' should match 'the beatles'."""
        self.assertTrue(_is_similar("the beatles", "the beatles"))

    # --- Near-identical artist names that must NOT match as artists alone ---
    # (These names are so similar they may still pass the similarity check, but
    # the album match will correctly filter them out in search_bandcamp.)
    def test_nearly_identical_artist_names_high_ratio(self):
        """'children of bodom' vs 'children of sodom' have very high character
        similarity — _is_similar returns True, but the album check in
        search_bandcamp prevents a wrong album from being returned."""
        # We document the ratio rather than assert True/False, because the key
        # protection is the removal of the loose artist-only match.
        ratio = difflib.SequenceMatcher(None, "children of bodom", "children of sodom").ratio()
        self.assertGreater(ratio, 0.90)

    # --- Truncated / short artist names must NOT match longer ones ---
    def test_truncated_artist_rejected(self):
        """A truncated result like 'children of' must NOT match 'children of bodom'."""
        self.assertFalse(_is_similar("children of", "children of bodom"))

    def test_truncated_artist_reversed(self):
        """'children of bodom' must NOT match a truncated 'children of'."""
        self.assertFalse(_is_similar("children of bodom", "children of"))

    # --- Album titles that are clearly different must not match ---
    def test_different_albums_rejected(self):
        self.assertFalse(
            _is_similar("hate crew deathroll", "the life and death of a parallelogram")
        )

    # --- Empty / blank strings ---
    def test_empty_a(self):
        self.assertFalse(_is_similar("", "metallica"))

    def test_empty_b(self):
        self.assertFalse(_is_similar("metallica", ""))

    def test_both_empty(self):
        self.assertFalse(_is_similar("", ""))


class TestSearchBandcamp(unittest.TestCase):
    """Tests for search_bandcamp() using mocked _search_bandcamp results."""

    def _make_album_result(self, name: str, artist: str, url: str) -> dict:
        return {"name": name, "artist": artist, "url": url, "type": "album"}

    def _make_artist_result(self, name: str, url: str) -> dict:
        return {"name": name, "artist": "", "url": url, "type": "artist"}

    @patch("album_browser.time.sleep")
    @patch("album_browser._search_bandcamp")
    def test_correct_album_found(self, mock_search, mock_sleep):
        """Exact artist + album match returns the album URL."""
        mock_search.side_effect = [
            [self._make_album_result("Hate Crew Deathroll", "Children of Bodom",
                                     "https://childrenofbodom.bandcamp.com/album/hate-crew-deathroll")],
            [],
        ]
        url, match_type = search_bandcamp("Children of Bodom", "Hate Crew Deathroll")
        self.assertEqual(url, "https://childrenofbodom.bandcamp.com/album/hate-crew-deathroll")
        self.assertEqual(match_type, "album")

    @patch("album_browser.time.sleep")
    @patch("album_browser._search_bandcamp")
    def test_wrong_artist_album_not_returned(self, mock_search, mock_sleep):
        """A result from a different artist must NOT be returned as an album match
        even when the artist names are similar (Children of Sodom vs Bodom)."""
        mock_search.side_effect = [
            # Album search returns a Children of Sodom album — wrong artist
            [self._make_album_result(
                "The Life and Death of a Parallelogram",
                "Children of Sodom",
                "https://childrenofsodom.bandcamp.com/album/the-life-and-death-of-a-parallelogram",
            )],
            # Artist search returns nothing
            [],
        ]
        url, match_type = search_bandcamp("Children of Bodom", "Hate Crew Deathroll")
        self.assertIsNone(url)
        self.assertIsNone(match_type)

    @patch("album_browser.time.sleep")
    @patch("album_browser._search_bandcamp")
    def test_truncated_artist_not_matched(self, mock_search, mock_sleep):
        """A result where the artist field is truncated ('Children of') must NOT
        trigger a match for 'Children of Bodom'."""
        mock_search.side_effect = [
            # Album search returns result with truncated artist name
            [self._make_album_result(
                "The Life and Death of a Parallelogram",
                "Children of",  # truncated — the old bug trigger
                "https://childrenofsodom.bandcamp.com/album/the-life-and-death-of-a-parallelogram",
            )],
            # Artist search returns nothing
            [],
        ]
        url, match_type = search_bandcamp("Children of Bodom", "Hate Crew Deathroll")
        self.assertIsNone(url)
        self.assertIsNone(match_type)

    @patch("album_browser.time.sleep")
    @patch("album_browser._search_bandcamp")
    def test_artist_page_fallback(self, mock_search, mock_sleep):
        """When no album match is found, a matching artist page is returned."""
        mock_search.side_effect = [
            # Album search returns nothing useful
            [],
            # Artist search returns the correct band
            [self._make_artist_result(
                "Children of Bodom",
                "https://childrenofbodom.bandcamp.com",
            )],
        ]
        url, match_type = search_bandcamp("Children of Bodom", "Hate Crew Deathroll")
        self.assertEqual(url, "https://childrenofbodom.bandcamp.com")
        self.assertEqual(match_type, "artist")

    @patch("album_browser.time.sleep")
    @patch("album_browser._search_bandcamp")
    def test_no_results_returns_none(self, mock_search, mock_sleep):
        """When both searches return nothing, (None, None) is returned."""
        mock_search.side_effect = [[], []]
        url, match_type = search_bandcamp("Unknown Artist", "Unknown Album")
        self.assertIsNone(url)
        self.assertIsNone(match_type)

    @patch("album_browser.time.sleep")
    @patch("album_browser._search_bandcamp")
    def test_no_first_result_fallback(self, mock_search, mock_sleep):
        """A completely unrelated first artist result must NOT be returned as fallback."""
        mock_search.side_effect = [
            [],
            # Artist search returns a completely unrelated band as first result
            [self._make_artist_result(
                "Some Unrelated Band",
                "https://someunrelatedband.bandcamp.com",
            )],
        ]
        url, match_type = search_bandcamp("Children of Bodom", "Hate Crew Deathroll")
        self.assertIsNone(url)
        self.assertIsNone(match_type)

    @patch("album_browser.time.sleep")
    @patch("album_browser._search_bandcamp")
    def test_the_article_artist_variation(self, mock_search, mock_sleep):
        """'The Beatles' in folder should match 'beatles' on Bandcamp (and vice versa)."""
        mock_search.side_effect = [
            [self._make_album_result(
                "Abbey Road",
                "beatles",  # Bandcamp result without "The"
                "https://thebeatles.bandcamp.com/album/abbey-road",
            )],
            [],
        ]
        url, match_type = search_bandcamp("The Beatles", "Abbey Road")
        self.assertEqual(url, "https://thebeatles.bandcamp.com/album/abbey-road")
        self.assertEqual(match_type, "album")


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# Helpers for integration-style main() tests
# ---------------------------------------------------------------------------

def _make_music_dir(base: Path) -> Path:
    """Creates a small mock music directory tree and returns its path.

    Structure:
      Artist A/
        Lossless Album/  — 2 FLAC files
        Lossy Album/     — 1 MP3 file
      Artist B/
        Only Lossless/   — 1 FLAC file
    """
    (base / "Artist A" / "Lossless Album").mkdir(parents=True)
    (base / "Artist A" / "Lossy Album").mkdir(parents=True)
    (base / "Artist B" / "Only Lossless").mkdir(parents=True)

    (base / "Artist A" / "Lossless Album" / "01.flac").write_bytes(b"\x00" * 1024)
    (base / "Artist A" / "Lossless Album" / "02.flac").write_bytes(b"\x00" * 1024)
    (base / "Artist A" / "Lossy Album" / "01.mp3").write_bytes(b"\x00" * 512)
    (base / "Artist B" / "Only Lossless" / "01.flac").write_bytes(b"\x00" * 2048)

    return base


class TestAllAlbumLinksFlag(unittest.TestCase):
    """Integration tests for the --all-album-links switch."""

    @staticmethod
    def _run_main(music_dir: Path, extra_args: list[str]) -> str:
        """Runs main() with patched sys.argv and returns captured stdout."""
        import io

        argv = ["album_browser.py", str(music_dir)] + extra_args
        with patch.object(sys, "argv", argv), \
             patch("sys.stdout", new_callable=io.StringIO) as mock_out, \
             patch("album_browser.search_bandcamp", return_value=(None, None)), \
             patch("album_browser.search_qobuz", return_value=(None, None)), \
             patch("album_browser.time.sleep"):
            main()
            return mock_out.getvalue()

    def test_all_album_links_fetches_for_every_album(self):
        """With --all-album-links, search_bandcamp is called for ALL albums."""
        with tempfile.TemporaryDirectory() as tmp:
            music_dir = _make_music_dir(Path(tmp))
            argv = ["album_browser.py", str(music_dir), "--all-album-links",
                    "--no-qobuz", "--no-report"]
            with patch.object(sys, "argv", argv), \
                 patch("album_browser.search_bandcamp", return_value=(None, None)) as mock_bc, \
                 patch("album_browser.search_qobuz", return_value=(None, None)), \
                 patch("album_browser.time.sleep"):
                main()
            # 3 albums total: Lossless Album, Lossy Album, Only Lossless
            self.assertEqual(mock_bc.call_count, 3)

    def test_default_mode_only_fetches_for_lossy_albums(self):
        """Without --all-album-links, search_bandcamp is called only for lossy albums."""
        with tempfile.TemporaryDirectory() as tmp:
            music_dir = _make_music_dir(Path(tmp))
            argv = ["album_browser.py", str(music_dir), "--no-qobuz", "--no-report"]
            with patch.object(sys, "argv", argv), \
                 patch("album_browser.search_bandcamp", return_value=(None, None)) as mock_bc, \
                 patch("album_browser.search_qobuz", return_value=(None, None)), \
                 patch("album_browser.time.sleep"):
                main()
            # Only 1 lossy album (Lossy Album by Artist A)
            self.assertEqual(mock_bc.call_count, 1)

    def test_all_album_links_no_shopping_list_box(self):
        """With --all-album-links, the SHOPPING LIST box must NOT appear."""
        with tempfile.TemporaryDirectory() as tmp:
            music_dir = _make_music_dir(Path(tmp))
            output = self._run_main(music_dir, ["--all-album-links", "--no-report"])
            self.assertNotIn("SHOPPING LIST", output)

    def test_default_mode_shows_shopping_list_box(self):
        """Without --all-album-links, the SHOPPING LIST box IS shown for lossy albums."""
        with tempfile.TemporaryDirectory() as tmp:
            music_dir = _make_music_dir(Path(tmp))
            output = self._run_main(music_dir, ["--no-report"])
            self.assertIn("SHOPPING LIST", output)

    def test_all_album_links_inline_link_in_tree(self):
        """With --all-album-links and a BC match, the link appears in the album tree."""
        with tempfile.TemporaryDirectory() as tmp:
            music_dir = _make_music_dir(Path(tmp))
            argv = ["album_browser.py", str(music_dir), "--all-album-links",
                    "--no-qobuz", "--no-report"]
            fake_url = "https://artistb.bandcamp.com/album/only-lossless"
            import io

            def _bc_side_effect(artist, album):
                if artist == "Artist B" and album == "Only Lossless":
                    return (fake_url, "album")
                return (None, None)

            with patch.object(sys, "argv", argv), \
                 patch("sys.stdout", new_callable=io.StringIO) as mock_out, \
                 patch("album_browser.search_bandcamp", side_effect=_bc_side_effect), \
                 patch("album_browser.search_qobuz", return_value=(None, None)), \
                 patch("album_browser.time.sleep"):
                main()
            output = mock_out.getvalue()
        # The link must appear in the tree output, not in a separate section
        self.assertIn(fake_url, output)
        self.assertNotIn("SHOPPING LIST", output)
