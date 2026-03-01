# Copilot Instructions for AlbumBrowser

## Project Overview

AlbumBrowser is a Python command-line tool that scans a local music library, classifies albums as lossless or lossy, and generates a shopping list with purchase links from Bandcamp and Qobuz for albums not yet in lossless format. The entire project lives in a single script: `album_browser.py`.

## Tech Stack

- **Language:** Python 3.10+
- **Dependencies:** `requests`, `beautifulsoup4`, `colorama`
- **No build step required** — run directly with `python3 album_browser.py`

## Running the Tool

```bash
# Install dependencies
pip install requests beautifulsoup4 colorama

# Basic usage
python3 album_browser.py "/path/to/Music"

# Skip Bandcamp/Qobuz searches or report generation
python3 album_browser.py "/path/to/Music" --no-bandcamp --no-qobuz --no-report
```

## Code Conventions

- **Type hints** are used on all function signatures, including `list[Path]`, `tuple[str | None, str | None]`, etc. (Python 3.10+ union syntax with `|`).
- **Docstrings** follow a concise one-liner or short block style describing what the function returns.
- **Private helpers** are prefixed with a single underscore (e.g., `_search_bandcamp`, `_normalize`).
- **Constants** are module-level ALL_CAPS (e.g., `AUDIO_EXTENSIONS`, `LOSSLESS_FORMATS`, `REQUEST_TIMEOUT`).
- **Color output** uses `colorama` (`Fore`, `Style`) for terminal output; always reset with `Style.RESET_ALL`.
- **Markdown output** is written line-by-line into a `lines: list[str]` then joined with `"\n".join(lines)`.

## Key Patterns

- **Audio format detection:** File extension (uppercased, stripped of leading dot) is compared against the `LOSSLESS_FORMATS` set.
- **Rate limiting:** A `time.sleep(RATE_LIMIT)` call separates HTTP requests to Bandcamp/Qobuz to avoid being blocked.
- **Search fallback:** Bandcamp is tried first; Qobuz is used as a fallback (or supplement when Bandcamp only returns an artist page).
- **Expected folder structure:** `Music / Artist / Album / tracks`. Loose audio files directly inside an artist folder are grouped under `(Loose tracks)`.
- **Report output:** Markdown report is saved to `MD/result.md` next to the script unless `--no-report` is passed.

## Project Structure

```
album_browser.py   # Main script — all logic lives here
README.md
LICENSE
```

## Testing

There is no automated test suite. Manual testing is done by pointing the script at a real or mock music directory. When adding new features, verify them by running the script against a sample directory tree.
