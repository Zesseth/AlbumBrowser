# AlbumBrowser

A command-line tool that scans your local music library, reports lossless vs. lossy albums, and generates a shopping list with purchase links from Bandcamp and Qobuz for any albums not yet in lossless format.

## Features

- Scans a music directory structured as `Artist / Album / tracks`
- Detects lossless formats: FLAC, APE, WAV, AIFF, WV, ALAC
- Flags non-lossless albums (MP3, AAC, OGG, etc.) with a warning
- Displays a summary table (total artists, albums, lossless/non-lossless counts)
- Searches Bandcamp and Qobuz for purchase links for non-lossless albums
- Generates a Markdown report (`MD/result.md`) with the full library overview

## Requirements

- Python 3.10+
- [requests](https://pypi.org/project/requests/)
- [beautifulsoup4](https://pypi.org/project/beautifulsoup4/)
- [colorama](https://pypi.org/project/colorama/)

Install dependencies:

```bash
pip install requests beautifulsoup4 colorama
```

## Usage

```bash
python album_browser.py <music_folder_path> [--no-bandcamp] [--no-qobuz] [--no-report] [--all-links]
```

### Options

| Option | Description |
|:---|:---|
| `--no-bandcamp` | Skip Bandcamp search |
| `--no-qobuz` | Skip Qobuz search |
| `--no-report` | Skip Markdown report generation |
| `--all-links` | Fetch and display purchase links for **all** albums (lossless and non-lossless) inline in the album listing |

### Example

```bash
python album_browser.py "C:\Users\User\Music"
python album_browser.py ~/Music --no-bandcamp
python album_browser.py ~/Music --all-links
```

## Expected folder structure

```
Music/
├── Artist Name/
│   ├── Album Title/
│   │   ├── 01 - Track.flac
│   │   └── 02 - Track.flac
│   └── Another Album/
│       └── 01 - Track.mp3
└── Another Artist/
    └── ...
```

Loose audio files placed directly inside an artist folder are grouped under **(Loose tracks)**.

## Output

The tool prints a colour-coded tree of your library to the terminal and, unless `--no-report` is given, writes a Markdown summary to `MD/result.md` next to the script.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
