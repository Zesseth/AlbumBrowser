# AlbumBrowser

A command-line Python tool that scans your local music library, identifies which albums are in lossless vs. lossy formats, builds a prioritised shopping list for lossless upgrades, and automatically searches **Bandcamp** and **Qobuz** for purchase links. Results are written to the terminal in a colour-coded tree view and saved as a neatly formatted Markdown report.

---

## Table of Contents

- [What it does](#what-it-does)
- [Requirements](#requirements)
- [Installation](#installation)
  - [Linux](#linux)
  - [Windows](#windows)
  - [macOS](#macos)
- [Usage](#usage)
  - [Basic usage](#basic-usage)
  - [Optional flags](#optional-flags)
  - [Expected folder structure](#expected-folder-structure)
- [Reading the Markdown report](#reading-the-markdown-report)
- [Supported audio formats](#supported-audio-formats)

---

## What it does

1. **Scans** a music library directory that follows the `Music / Artist / Album` folder convention.
2. **Detects** audio file formats for every album (MP3, FLAC, WAV, AAC, etc.).
3. **Flags** albums that contain lossy formats (⚠️) and those that are fully lossless (✅).
4. **Prints** a colour-coded tree to the terminal showing every artist and album with format, track count, and total size.
5. **Builds a shopping list** of albums that need a lossless upgrade.
6. **Searches Bandcamp and Qobuz** automatically and attaches purchase links to each shopping-list entry.
7. **Generates a Markdown report** (`MD/result.md`) that contains the full library overview, a summary table, and the shopping list with clickable links.

---

## Requirements

- **Python 3.10 or newer**
- The following third-party Python packages:

| Package | Purpose |
|:---|:---|
| `requests` | HTTP requests to Bandcamp / Qobuz |
| `beautifulsoup4` | HTML parsing of search results |
| `colorama` | Cross-platform coloured terminal output |

---

## Installation

### Linux

1. **Install Python 3.10+** (most distributions already have it):

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

The script will:
- Print a colour-coded library tree to the terminal.
- Search Bandcamp and Qobuz for any albums that need a lossless upgrade.
- Save a Markdown report to `MD/result.md` (relative to the script's location).

---

### Optional flags

| Flag | Description |
|:---|:---|
| `--no-bandcamp` | Skip the Bandcamp search (faster run) |
| `--no-qobuz` | Skip the Qobuz search (faster run) |
| `--no-report` | Do not generate the `MD/result.md` Markdown report |

**Examples:**

```bash
# Scan without any web searches
python3 album_browser.py "/path/to/Music" --no-bandcamp --no-qobuz

# Scan and search only Qobuz, skip the report
python3 album_browser.py "/path/to/Music" --no-bandcamp --no-report
```

---

### Expected folder structure

AlbumBrowser expects your music library to be organised as follows:

```
Music/
├── Artist Name/
│   ├── Album Title/
│   │   ├── 01 - Track Title.flac
│   │   ├── 02 - Track Title.flac
│   │   └── ...
│   └── Another Album/
│       ├── 01 - Track Title.mp3
│       └── ...
└── Another Artist/
    └── ...
```

Audio files placed **directly inside an artist folder** (without an album sub-folder) are listed as *"(Loose tracks)"* in the report.

---

## Reading the Markdown report

After a successful run, a report is saved to **`MD/result.md`** next to `album_browser.py`.

The report contains:
- 🎤 **Artist sections** listing every album with format, track count, and size.
- 📊 **Summary table** with total artist, album, lossless, and non-lossless counts.
- 🛒 **Shopping list** of albums to upgrade, with direct Bandcamp / Qobuz purchase links.

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
| ALAC (.m4a) | ✅ Lossless |
| APE | ✅ Lossless |
| WavPack (.wv) | ✅ Lossless |
| MP3 | ⚠️ Lossy |
| AAC (.m4a / .aac) | ⚠️ Lossy |
| OGG | ⚠️ Lossy |
| WMA | ⚠️ Lossy |
| OPUS | ⚠️ Lossy |

---

## License

See [LICENSE](LICENSE) for details.