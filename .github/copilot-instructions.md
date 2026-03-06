# Copilot Instructions for AlbumBrowser

AlbumBrowser is a Python command-line tool that scans a local music library, classifies albums as lossless or lossy, and generates a shopping list with purchase links from Bandcamp and Qobuz for albums not yet in lossless format. The entire project lives in a single script: `album_browser.py`.

## Code Standards

- **Language:** Python 3.10+ — use modern union syntax (`str | None`) instead of `Optional[str]`.
- **Type hints** are required on all function signatures, including `list[Path]`, `tuple[str | None, str | None]`, etc.
- **Docstrings** follow a concise one-liner or short block style describing what the function returns.
- **Private helpers** are prefixed with a single underscore (e.g., `_search_bandcamp`, `_normalize`).
- **Constants** are module-level `ALL_CAPS` (e.g., `AUDIO_EXTENSIONS`, `LOSSLESS_FORMATS`, `REQUEST_TIMEOUT`).
- **Color output** uses `colorama` (`Fore`, `Style`) for terminal output; always reset with `Style.RESET_ALL`.
- **Markdown output** is written line-by-line into a `lines: list[str]` then joined with `"\n".join(lines)`.

## Development Flow

- **Install:** `pip install requests beautifulsoup4 colorama`
- **Run:** `python3 album_browser.py "/path/to/Music"`
- **Run with flags:** `python3 album_browser.py "/path/to/Music" --no-bandcamp --no-qobuz --no-report`
- **Test:** There is no automated test suite. Manual testing is done by pointing the script at a real or mock music directory. When adding new features, verify them by running the script against a sample directory tree.

## Repository Structure

- `album_browser.py` — Main script; all logic lives here
- `README.md` — User-facing documentation
- `LICENSE` — MIT license

## Key Guidelines

1. **Audio format detection:** File extension (uppercased, stripped of leading dot) is compared against the `LOSSLESS_FORMATS` set.
2. **Rate limiting:** A `time.sleep(RATE_LIMIT)` call separates HTTP requests to Bandcamp/Qobuz to avoid being blocked.
3. **Search fallback:** Bandcamp is tried first; Qobuz is used as a fallback (or supplement when Bandcamp only returns an artist page).
4. **Expected folder structure:** `Music / Artist / Album / tracks`. Loose audio files directly inside an artist folder are grouped under `(Loose tracks)`.
5. **Report output:** Markdown report is saved to `MD/result.md` next to the script unless `--no-report` is passed.
6. Follow existing code structure and organization in `album_browser.py`.
7. Write clear, concise docstrings for any new functions.
