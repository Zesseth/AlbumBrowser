# AlbumBrowser

A command-line tool that scans your local music library, reports lossless vs. lossy albums, and generates a shopping list with purchase links from Bandcamp and Qobuz for any albums not yet in lossless format.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
  - [Linux](#linux)
  - [Windows](#windows)
  - [macOS](#macos)
- [Usage](#usage)
  - [Basic usage](#basic-usage)
  - [Options](#options)
  - [Expected folder structure](#expected-folder-structure)
- [Output](#output)
- [Reading the Markdown report](#reading-the-markdown-report)
- [Supported audio formats](#supported-audio-formats)

---

## Features

- Scans a music directory structured as `Artist / Album / tracks`
- Detects lossless formats: FLAC, APE, WAV, AIFF, WV, ALAC
- Flags non-lossless albums (MP3, AAC, OGG, etc.) with a warning
- Displays a summary table (total artists, albums, lossless/non-lossless counts)
- Searches Bandcamp first for purchase links; falls back to Qobuz when no Bandcamp match is found
- Generates a Markdown report (`MD/result.md`) with the full library overview

---

## Requirements

- **Python 3.10+**
- [requests](https://pypi.org/project/requests/)
- [beautifulsoup4](https://pypi.org/project/beautifulsoup4/)
- [colorama](https://pypi.org/project/colorama/)

---

## Installation

### Linux

1. **Install Python 3.10+** (most distributions already include it):

   ```bash
   # Debian / Ubuntu
   sudo apt update && sudo apt install python3 python3-pip

   # Fedora / RHEL
   sudo dnf install python3 python3-pip

   # Arch Linux
   sudo pacman -S python python-pip
   ```

2. **Clone or download this repository:**

   ```bash
   git clone https://github.com/Zesseth/AlbumBrowser.git
   cd AlbumBrowser
   ```

3. **Install dependencies:**

   ```bash
   pip3 install requests beautifulsoup4 colorama
   ```

   > **Tip:** Use a virtual environment to keep your system Python clean:
   > ```bash
   > python3 -m venv .venv
   > source .venv/bin/activate
   > pip install requests beautifulsoup4 colorama
   > ```

---

### Windows

1. **Install Python 3.10+** from [https://www.python.org/downloads/](https://www.python.org/downloads/).  
   During installation, check **"Add Python to PATH"**.

2. **Clone or download this repository:**

   ```powershell
   git clone https://github.com/Zesseth/AlbumBrowser.git
   cd AlbumBrowser
   ```

   Alternatively, download the ZIP from GitHub and extract it.

3. **Install dependencies** (in Command Prompt or PowerShell):

   ```powershell
   pip install requests beautifulsoup4 colorama
   ```

   > **Tip:** Use a virtual environment:
   > ```powershell
   > python -m venv .venv
   > .venv\Scripts\activate
   > pip install requests beautifulsoup4 colorama
   > ```

---

### macOS

1. **Install Python 3.10+.**  
   The recommended way is via [Homebrew](https://brew.sh/):

   ```bash
   brew install python
   ```

   Or download from [https://www.python.org/downloads/](https://www.python.org/downloads/).

2. **Clone or download this repository:**

   ```bash
   git clone https://github.com/Zesseth/AlbumBrowser.git
   cd AlbumBrowser
   ```

3. **Install dependencies:**

   ```bash
   pip3 install requests beautifulsoup4 colorama
   ```

   > **Tip:** Use a virtual environment:
   > ```bash
   > python3 -m venv .venv
   > source .venv/bin/activate
   > pip install requests beautifulsoup4 colorama
   > ```

---

## Usage

### Basic usage

**Linux / macOS:**
```bash
python3 album_browser.py "/path/to/your/Music"
```

**Windows (Command Prompt):**
```cmd
python album_browser.py "C:\Users\YourName\Music"
```

**Windows (PowerShell):**
```powershell
python album_browser.py "C:\Users\YourName\Music"
```

---

### Options

| Option | Description |
|:---|:---|
| `--no-bandcamp` | Skip Bandcamp search |
| `--no-qobuz` | Skip Qobuz search |
| `--no-report` | Skip Markdown report generation |
| `--all-album-links` | Fetch and display purchase links for **every** album inline, not just non-lossless ones. No separate shopping list is shown in this mode. |

**Examples:**

```bash
python album_browser.py "C:\Users\User\Music"
python album_browser.py ~/Music --no-bandcamp
python album_browser.py ~/Music --all-album-links
```

---

### Expected folder structure

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

Loose audio files placed directly inside an artist folder are grouped under **(Irrallisia kappaleita)**.

---

## Output

The tool prints a colour-coded tree of your library to the terminal and, unless `--no-report` is given, writes a Markdown summary to `MD/result.md` next to the script.

---

## Reading the Markdown report

After a successful run, a report is saved to **`MD/result.md`** next to `album_browser.py`.

The report contains:
- 🎤 **Artist sections** listing every album with format, track count, and size.
- 📊 **Summary table** with total artist, album, lossless, and non-lossless counts.
- 🛒 **Shopping list** of albums to upgrade, with a purchase link per entry (Bandcamp preferred, Qobuz as fallback).

**Ways to view the rendered Markdown:**

| Platform | Method |
|:---|:---|
| **GitHub** | Push the file to a repository — GitHub renders `.md` files automatically. |
| **VS Code** | Open `result.md`, then press `Ctrl+Shift+V` (Windows/Linux) or `Cmd+Shift+V` (macOS) for the built-in preview. |
| **Typora** | Open the file directly — Typora renders Markdown live. [typora.io](https://typora.io) |
| **Obsidian** | Add the `MD` folder to an Obsidian vault and open `result.md`. [obsidian.md](https://obsidian.md) |
| **Browser** | Use a browser extension such as *Markdown Viewer* (Chrome/Firefox) to open and render the file locally. |
| **Command line** | Install `glow` (`brew install glow` on macOS, or download from [github.com/charmbracelet/glow](https://github.com/charmbracelet/glow)) and run `glow MD/result.md`. |

> **Tip:** The shopping list contains clickable hyperlinks. These are only interactive in rendered Markdown viewers — plain-text editors will show the raw link syntax.

---

## Supported audio formats

| Format | Type |
|:---|:---|
| FLAC | ✅ Lossless |
| WAV | ✅ Lossless |
| AIFF | ✅ Lossless |
| ALAC (.alac) | ✅ Lossless |
| APE | ✅ Lossless |
| WavPack (.wv) | ✅ Lossless |
| MP3 | ⚠️ Lossy |
| M4A / AAC (.m4a / .aac) | ⚠️ Lossy |
| OGG | ⚠️ Lossy |
| WMA | ⚠️ Lossy |
| OPUS | ⚠️ Lossy |

---

## License

This project is licensed under the GPL-3.0 License. See [LICENSE](LICENSE) for details.
