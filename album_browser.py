import difflib
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from colorama import init, Fore, Style

init()  # Initialize color support (Windows/Linux/macOS)

AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma", ".opus", ".ape", ".alac", ".aiff", ".wv"}
LOSSLESS_FORMATS = {"FLAC", "APE", "WAV", "AIFF", "WV", "ALAC"}

BANDCAMP_SEARCH_URL = "https://bandcamp.com/search"
QOBUZ_SEARCH_URL = "https://www.qobuz.com/fi-en/search/albums"
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
REQUEST_TIMEOUT = 10
RATE_LIMIT = 2  # seconds between requests


def get_audio_files(directory: Path) -> list[Path]:
    """Returns audio files in the directory, sorted alphabetically."""
    return sorted(
        [f for f in directory.iterdir() if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS],
        key=lambda f: f.name.lower()
    )


def format_file_size(size_bytes: int) -> str:
    """Formats a byte count into a human-readable string."""
    if size_bytes >= 1_073_741_824:
        return f"{size_bytes / 1_073_741_824:.1f} GB"
    if size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.0f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.0f} KB"
    return f"{size_bytes} B"


def _normalize(text: str) -> str:
    """Normalizes text for comparison (lowercase, strips extra whitespace)."""
    return " ".join(text.lower().split())


def _is_similar(a: str, b: str, threshold: float = 0.80) -> bool:
    """Returns True if two normalized strings are similar enough to be a match.

    Uses SequenceMatcher ratio, which correctly penalises short truncated strings
    (e.g. "children of" should NOT match "children of bodom").
    Also handles common "The Artist" vs "Artist" name variations.

    Args:
        a: First normalized string to compare.
        b: Second normalized string to compare.
        threshold: Minimum SequenceMatcher ratio (0.0–1.0) required for a match.
                   Defaults to 0.80 — high enough to reject short truncations
                   while accepting minor spelling differences.
    """
    if not a or not b:
        return False
    if a == b:
        return True
    # Handle leading "the " article variants (e.g. "beatles" == "the beatles")
    def _strip_the(s: str) -> str:
        return s[4:] if s.startswith("the ") else s
    if _strip_the(a) == _strip_the(b):
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= threshold


def _search_bandcamp(query: str, item_type: str) -> list[dict]:
    """Searches Bandcamp and returns a list of results.

    item_type: 'a' = albums, 'b' = artists/bands
    Returns a list: [{'name': str, 'artist': str, 'url': str, 'type': str}, ...]
    """
    params = {"q": query, "item_type": item_type, "page": 1}
    try:
        resp = requests.get(
            BANDCAMP_SEARCH_URL,
            params=params,
            headers=HTTP_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for li in soup.select(".result-items li"):
        heading_el = li.select_one(".heading")
        url_el = li.select_one(".itemurl a")
        subhead_el = li.select_one(".subhead")

        if not heading_el or not url_el:
            continue

        name = heading_el.get_text(strip=True)
        url = url_el.get_text(strip=True) if url_el else ""
        subhead = subhead_el.get_text(strip=True) if subhead_el else ""

        # Artist name from subhead (album: "by Artist", artist: location)
        artist = ""
        if item_type == "a" and subhead.lower().startswith("by "):
            artist = subhead[3:].strip()

        result_type = "album" if item_type == "a" else "artist"
        results.append({"name": name, "artist": artist, "url": url, "type": result_type})

    return results


def search_bandcamp(artist_name: str, album_name: str) -> tuple[str | None, str | None]:
    """Searches Bandcamp for an album or artist page.

    Returns (url, match_type) where match_type is 'album', 'artist', or None.
    Search order: 1) album search, 2) artist search.
    """
    artist_norm = _normalize(artist_name)
    album_norm = _normalize(album_name)

    # 1. Search for album — require BOTH artist AND album to match
    query = f"{artist_name} {album_name}"
    results = _search_bandcamp(query, "a")

    for r in results:
        r_artist = _normalize(r["artist"])
        r_album = _normalize(r["name"])
        if _is_similar(artist_norm, r_artist) and _is_similar(album_norm, r_album):
            return (r["url"], "album")

    time.sleep(RATE_LIMIT)

    # 2. Search for artist
    results = _search_bandcamp(artist_name, "b")

    for r in results:
        r_name = _normalize(r["name"])
        if _is_similar(artist_norm, r_name):
            return (r["url"], "artist")

    return (None, None)


def _search_qobuz(query: str) -> list[dict]:
    """Searches the Qobuz store for albums.

    Returns a list: [{'name': str, 'artist': str, 'url': str}, ...]
    """
    search_url = f"{QOBUZ_SEARCH_URL}/{requests.utils.quote(query)}"
    try:
        resp = requests.get(
            search_url,
            headers=HTTP_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    # Album links are found in <a href="/fi-en/album/..."> elements
    album_links = soup.find_all("a", href=lambda h: h and "/album/" in h)
    # Filter for title links (parent div contains the 'min-w-0' class)
    title_links = [
        a for a in album_links
        if a.parent and "min-w-0" in (a.parent.get("class") or [])
    ]

    for a in title_links:
        album_name = a.get_text(strip=True)
        album_href = a.get("href", "")
        album_url = f"https://www.qobuz.com{album_href}" if album_href.startswith("/") else album_href

        # Find artist link in the same container
        container = a.parent
        artist_links = (
            container.find_all("a", href=lambda h: h and "/interpreter/" in h)
            if container else []
        )
        artist_name = artist_links[0].get_text(strip=True) if artist_links else ""

        results.append({"name": album_name, "artist": artist_name, "url": album_url})

    return results


def search_qobuz(artist_name: str, album_name: str) -> tuple[str | None, str | None]:
    """Searches Qobuz for an album page.

    Returns (url, match_type) where match_type is 'album' or None.
    """
    artist_norm = _normalize(artist_name)
    album_norm = _normalize(album_name)

    query = f"{artist_name} {album_name}"
    results = _search_qobuz(query)

    # Exact match: artist + album
    for r in results:
        r_artist = _normalize(r["artist"])
        r_album = _normalize(r["name"])
        if (artist_norm in r_artist or r_artist in artist_norm) and \
           (album_norm in r_album or r_album in album_norm):
            return (r["url"], "album")

    # Looser match: artist-only match
    for r in results:
        r_artist = _normalize(r["artist"])
        if artist_norm in r_artist or r_artist in artist_norm:
            return (r["url"], "album")

    return (None, None)


def _build_link_suffix(
    bc: tuple[str | None, str | None] | None,
    qb: tuple[str | None, str | None] | None,
    *,
    qobuz_supplement_only: bool = False,
) -> str:
    """Returns a formatted purchase-link string to append to an album terminal line.

    When qobuz_supplement_only is True (shopping list mode), Qobuz is only appended
    when Bandcamp returned an artist-page match or no match at all.
    When False (all-album-links mode), Qobuz is appended whenever a URL is available.
    """
    suffix = ""
    bc_url, bc_match = bc if bc else (None, None)
    qb_url = qb[0] if qb else None

    if bc_url:
        if bc_match == "album":
            suffix += f"  {Fore.CYAN}🔗 BC: {bc_url}{Style.RESET_ALL}"
        else:
            suffix += f"  {Fore.CYAN}🔗 BC: {bc_url} (artist){Style.RESET_ALL}"
            if qobuz_supplement_only and qb_url:
                suffix += f"  {Fore.GREEN}🔗 Qobuz: {qb_url}{Style.RESET_ALL}"
    else:
        if qobuz_supplement_only and qb_url:
            suffix += f"  {Fore.GREEN}🔗 Qobuz: {qb_url}{Style.RESET_ALL}"

    if not qobuz_supplement_only and qb_url:
        suffix += f"  {Fore.GREEN}🔗 Qobuz: {qb_url}{Style.RESET_ALL}"

    return suffix


def generate_markdown_report(
    script_dir: Path,
    music_root: Path,
    artists_data: list[dict],
    total_artists: int,
    total_albums: int,
    total_lossless: int,
    total_non_lossless: int,
    shopping_list: list[tuple],
    bandcamp_results: dict,
    qobuz_results: dict,
) -> Path:
    """Generates a Markdown report to MD/result.md."""
    md_dir = script_dir / "MD"
    md_dir.mkdir(exist_ok=True)
    md_path = md_dir / "result.md"

    lines = []
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Header
    lines.append("# 🎵 Music Library")
    lines.append("")
    lines.append(f"> Scanned: **{now}**  ")
    lines.append(f"> Path: `{music_root}`")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Artists and albums
    for artist_info in artists_data:
        artist_name = artist_info["name"]
        lines.append(f"## 🎤 {artist_name}")
        lines.append("")

        for album in artist_info["albums"]:
            name = album["name"]
            fmt = album["format_str"]
            count = album["track_count"]
            size = album["size_str"]
            is_lossless = album["all_lossless"]
            is_loose = album.get("is_loose", False)

            icon = "📁" if is_loose else "💿"
            if is_lossless:
                status = "✅"
                fmt_display = f"**{fmt}**"
            else:
                lossy = ", ".join(album["lossy_fmts"])
                status = f"⚠️ *Non-lossless: {lossy}*"
                fmt_display = f"`{fmt}`"

            lines.append(f"- {icon} **{name}** — {fmt_display} — {count} tracks, {size} {status}")

        lines.append("")

    # Summary
    lines.append("---")
    lines.append("")
    lines.append("## 📊 Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|:---|---:|")
    lines.append(f"| 🎤 Artists | **{total_artists}** |")
    lines.append(f"| 💿 Albums | **{total_albums}** |")
    lines.append(f"| ✅ Lossless | **{total_lossless}** |")
    lines.append(f"| ⚠️ Non-lossless | **{total_non_lossless}** |")
    lines.append("")

    # Shopping list
    if shopping_list:
        lines.append("---")
        lines.append("")
        lines.append("## 🛒 Shopping List — Albums to Get in Lossless")
        lines.append("")
        lines.append("| # | Artist | Album | Format | Bandcamp | Qobuz |")
        lines.append("|---:|:---|:---|:---:|:---|:---|")

        bc_found = 0
        qb_found = 0

        for i, (artist, album, lossy_fmts) in enumerate(shopping_list, 1):
            fmt_str = ", ".join(lossy_fmts)

            # Find purchase links
            bc_link = "—"
            qb_link = "—"
            bc = bandcamp_results.get((artist, album))
            qb = qobuz_results.get((artist, album))
            if bc and bc[0]:
                url, match_type = bc
                suffix = " (artist)" if match_type != "album" else ""
                bc_link = f"[🔗 Bandcamp{suffix}]({url})"
                bc_found += 1
            if qb and qb[0]:
                qb_link = f"[🔗 Qobuz]({qb[0]})"
                qb_found += 1

            lines.append(f"| {i} | **{artist}** | {album} | `{fmt_str}` | {bc_link} | {qb_link} |")

        lines.append("")
        lines.append(f"> **Total {len(shopping_list)}** albums to acquire in lossless format.  ")
        if bandcamp_results:
            lines.append(f"> Bandcamp links found: **{bc_found}** / {len(shopping_list)}  ")
        if qobuz_results:
            lines.append(f"> Qobuz links found: **{qb_found}** / {len(shopping_list)}")
        lines.append("")
    else:
        lines.append("")
        lines.append("> ✅ **All albums are in lossless format!**")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def main():
    # Parse flags
    args = sys.argv[1:]
    no_bandcamp = "--no-bandcamp" in args
    no_qobuz = "--no-qobuz" in args
    no_report = "--no-report" in args
    all_album_links = "--all-album-links" in args
    args = [a for a in args if a not in ("--no-bandcamp", "--no-qobuz", "--no-report", "--all-album-links")]

    if len(args) < 1:
        print(f"{Fore.RED}Usage: python album_browser.py <music_folder_path> [--no-bandcamp] [--no-qobuz] [--no-report] [--all-album-links]{Style.RESET_ALL}")
        print(f"Example: python album_browser.py \"C:\\Users\\User\\Music\"")
        print(f"         --no-bandcamp      Skip Bandcamp search")
        print(f"         --no-qobuz         Skip Qobuz search")
        print(f"         --no-report        Skip MD report generation")
        print(f"         --all-album-links  Fetch and show links for every album inline (not just non-lossless)")
        return

    music_root = Path(args[0])

    if not music_root.exists():
        print(f"{Fore.RED}Directory not found: {music_root}{Style.RESET_ALL}")
        return

    print(f"{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗")
    print(f"║                    🎵  MUSIC LIBRARY  🎵                    ║")
    print(f"╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")
    print()

    artist_dirs = sorted(
        [d for d in music_root.iterdir() if d.is_dir()],
        key=lambda d: d.name.lower()
    )

    total_artists = 0
    total_albums = 0
    total_lossless = 0
    total_non_lossless = 0
    shopping_list = []
    artists_data = []  # Collect data for MD report

    for artist_dir in artist_dirs:
        artist_name = artist_dir.name
        album_dirs = sorted(
            [d for d in artist_dir.iterdir() if d.is_dir()],
            key=lambda d: d.name.lower()
        )
        loose_files = get_audio_files(artist_dir)

        if not album_dirs and not loose_files:
            continue

        total_artists += 1
        current_artist = {"name": artist_name, "albums": []}
        if not all_album_links:
            print(f"  {Fore.YELLOW}🎤 {artist_name}{Style.RESET_ALL}")

        for album_dir in album_dirs:
            album_name = album_dir.name
            tracks = get_audio_files(album_dir)

            if not tracks:
                continue

            total_albums += 1

            # Determine album formats
            formats = sorted(set(f.suffix.lstrip(".").upper() for f in tracks))
            format_str = " / ".join(formats)

            # Calculate total album size
            total_size = sum(f.stat().st_size for f in tracks)
            size_str = format_file_size(total_size)

            # Determine lossless and lossy formats
            lossless_fmts = [fmt for fmt in formats if fmt in LOSSLESS_FORMATS]
            lossy_fmts = [fmt for fmt in formats if fmt not in LOSSLESS_FORMATS]
            all_lossless = len(lossy_fmts) == 0

            if all_lossless:
                format_color = Fore.GREEN
                total_lossless += 1
            else:
                format_color = Fore.MAGENTA
                total_non_lossless += 1
                shopping_list.append((artist_name, album_name, lossy_fmts))

            # Collect album data for report
            current_artist["albums"].append({
                "name": album_name,
                "format_str": format_str,
                "track_count": len(tracks),
                "size_str": size_str,
                "all_lossless": all_lossless,
                "lossy_fmts": lossy_fmts,
                "is_loose": False,
            })

            # Album row
            line = (
                f"     ├── 💿 {Fore.WHITE}{album_name}{Style.RESET_ALL}"
                f"  [{format_color}{format_str}{Style.RESET_ALL}]"
                f" ({len(tracks)} tracks, {size_str})"
            )
            if not all_lossless:
                line += f"  {Fore.RED}⚠️  Non-lossless: {', '.join(lossy_fmts)}{Style.RESET_ALL}"
            if not all_album_links:
                print(line)

        # Loose tracks (directly in the artist folder)
        if loose_files:
            total_albums += 1
            formats = sorted(set(f.suffix.lstrip(".").upper() for f in loose_files))
            format_str = " / ".join(formats)
            lossy_fmts = [fmt for fmt in formats if fmt not in LOSSLESS_FORMATS]
            all_lossless = len(lossy_fmts) == 0

            total_size = sum(f.stat().st_size for f in loose_files)
            size_str = format_file_size(total_size)

            if all_lossless:
                format_color = Fore.GREEN
                total_lossless += 1
            else:
                format_color = Fore.MAGENTA
                total_non_lossless += 1
                shopping_list.append((artist_name, "(Loose tracks)", lossy_fmts))

            # Collect loose tracks data for report
            current_artist["albums"].append({
                "name": "(Loose tracks)",
                "format_str": format_str,
                "track_count": len(loose_files),
                "size_str": size_str,
                "all_lossless": all_lossless,
                "lossy_fmts": lossy_fmts,
                "is_loose": True,
            })

            line = (
                f"     ├── 📁 {Fore.LIGHTYELLOW_EX}(Loose tracks){Style.RESET_ALL}"
                f"  [{format_color}{format_str}{Style.RESET_ALL}]"
                f" ({len(loose_files)} tracks, {size_str})"
            )
            if not all_lossless:
                line += f"  {Fore.RED}⚠️  Non-lossless: {', '.join(lossy_fmts)}{Style.RESET_ALL}"
            if not all_album_links:
                print(line)

        artists_data.append(current_artist)
        if not all_album_links:
            print()

    # --all-album-links: fetch links for every album then print the full tree with inline links
    if all_album_links:
        all_links: dict[tuple[str, str], dict] = {}
        all_album_entries: list[tuple[str, str]] = []
        for artist_info in artists_data:
            for album in artist_info["albums"]:
                all_album_entries.append((artist_info["name"], album["name"]))

        if all_album_entries and not (no_bandcamp and no_qobuz):
            print()
            print(f"  {Fore.CYAN}🔍 Fetching links for all albums...{Style.RESET_ALL}")
            for i, (artist, album) in enumerate(all_album_entries, 1):
                print(
                    f"  {Fore.CYAN}   ({i}/{len(all_album_entries)}) {artist} – {album}...{Style.RESET_ALL}",
                    end="", flush=True,
                )

                found = False
                bc_artist_only = False
                all_links[(artist, album)] = {"bc": (None, None), "qb": (None, None)}

                if not no_bandcamp:
                    url, match_type = search_bandcamp(artist, album)
                    all_links[(artist, album)]["bc"] = (url, match_type)
                    if url:
                        if match_type == "album":
                            print(f" {Fore.GREEN}💿 BC found!{Style.RESET_ALL}")
                            found = True
                        else:
                            print(f" {Fore.GREEN}🎤 BC artist{Style.RESET_ALL}", end="", flush=True)
                            bc_artist_only = True

                if (not found or bc_artist_only) and not no_qobuz:
                    if not no_bandcamp:
                        time.sleep(RATE_LIMIT)
                    url, match_type = search_qobuz(artist, album)
                    all_links[(artist, album)]["qb"] = (url, match_type)
                    if url:
                        print(f" {Fore.GREEN}💿 Qobuz found!{Style.RESET_ALL}")
                        found = True
                    elif bc_artist_only:
                        print()
                        found = True
                elif bc_artist_only:
                    print()
                    found = True

                if not found:
                    print(f" {Fore.RED}❌{Style.RESET_ALL}")

                if i < len(all_album_entries):
                    time.sleep(RATE_LIMIT)

        # Print full tree with inline links
        print()
        for artist_info in artists_data:
            artist_name = artist_info["name"]
            print(f"  {Fore.YELLOW}🎤 {artist_name}{Style.RESET_ALL}")
            for album in artist_info["albums"]:
                name = album["name"]
                format_str = album["format_str"]
                track_count = album["track_count"]
                size_str = album["size_str"]
                all_lossless = album["all_lossless"]
                lossy_fmts = album["lossy_fmts"]
                is_loose = album.get("is_loose", False)

                format_color = Fore.GREEN if all_lossless else Fore.MAGENTA
                icon = "📁" if is_loose else "💿"
                name_color = Fore.LIGHTYELLOW_EX if is_loose else Fore.WHITE

                line = (
                    f"     ├── {icon} {name_color}{name}{Style.RESET_ALL}"
                    f"  [{format_color}{format_str}{Style.RESET_ALL}]"
                    f" ({track_count} tracks, {size_str})"
                )
                if not all_lossless:
                    line += f"  {Fore.RED}⚠️  Non-lossless: {', '.join(lossy_fmts)}{Style.RESET_ALL}"

                links = all_links.get((artist_name, name))
                if links:
                    line += _build_link_suffix(links["bc"], links["qb"])
                print(line)
            print()

    # Summary
    print(f"{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗")
    print(f"║                          SUMMARY                            ║")
    print(f"╠══════════════════════════════════════════════════════════════╣{Style.RESET_ALL}")
    print(f"║  {Fore.YELLOW}Artists:         {total_artists:6}{Style.RESET_ALL}                                  ║")
    print(f"║  {Fore.WHITE}Albums:          {total_albums:6}{Style.RESET_ALL}                                  ║")
    print(f"║  {Fore.GREEN}Lossless:        {total_lossless:6}{Style.RESET_ALL}                                  ║")
    print(f"║  {Fore.MAGENTA}Non-lossless:    {total_non_lossless:6}{Style.RESET_ALL}                                  ║")
    print(f"{Fore.CYAN}╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")

    # Shopping list
    bandcamp_results: dict = {}
    qobuz_results: dict = {}

    if all_album_links:
        # Links were already fetched for every album; derive report-compatible dicts
        bandcamp_results = {k: v["bc"] for k, v in all_links.items()}
        qobuz_results = {k: v["qb"] for k, v in all_links.items()}
    elif shopping_list:
        # Fetch purchase links for shopping list albums
        if not no_bandcamp or not no_qobuz:
            print()
            print(f"  {Fore.CYAN}🔍 Searching for purchase links...{Style.RESET_ALL}")
            for i, (artist, album, _) in enumerate(shopping_list, 1):
                print(
                    f"  {Fore.CYAN}   ({i}/{len(shopping_list)}) {artist} – {album}...{Style.RESET_ALL}",
                    end="", flush=True,
                )

                found = False
                bc_artist_only = False

                # 1. Bandcamp search
                if not no_bandcamp:
                    url, match_type = search_bandcamp(artist, album)
                    bandcamp_results[(artist, album)] = (url, match_type)
                    if url:
                        if match_type == "album":
                            print(f" {Fore.GREEN}💿 BC found!{Style.RESET_ALL}")
                            found = True
                        else:
                            # Artist page only — not a confirmed album match
                            print(f" {Fore.GREEN}🎤 BC artist{Style.RESET_ALL}", end="", flush=True)
                            bc_artist_only = True

                # 2. Qobuz search (fallback OR supplement for artist-only BC hit)
                if (not found or bc_artist_only) and not no_qobuz:
                    if not no_bandcamp:
                        time.sleep(RATE_LIMIT)
                    url, match_type = search_qobuz(artist, album)
                    qobuz_results[(artist, album)] = (url, match_type)
                    if url:
                        print(f" {Fore.GREEN}💿 Qobuz found!{Style.RESET_ALL}")
                        found = True
                    elif bc_artist_only:
                        # Qobuz didn't find it either, keep BC artist link
                        print()
                        found = True
                elif bc_artist_only:
                    print()
                    found = True

                if not found:
                    print(f" {Fore.RED}❌{Style.RESET_ALL}")

                if i < len(shopping_list):
                    time.sleep(RATE_LIMIT)

        print()
        print(f"{Fore.RED}╔══════════════════════════════════════════════════════════════╗")
        print(f"║        🛒  SHOPPING LIST – Albums to Get in Lossless        ║")
        print(f"╠══════════════════════════════════════════════════════════════╣{Style.RESET_ALL}")
        for artist, album, lossy_fmts in shopping_list:
            fmt_str = ', '.join(lossy_fmts)
            line = f"  {Fore.YELLOW}{artist}{Style.RESET_ALL} – {Fore.WHITE}{album}{Style.RESET_ALL}  [{Fore.MAGENTA}{fmt_str}{Style.RESET_ALL}]"

            # Add purchase links
            bc = bandcamp_results.get((artist, album))
            qb = qobuz_results.get((artist, album))
            line += _build_link_suffix(bc, qb, qobuz_supplement_only=True)

            print(line)
        print(f"{Fore.RED}╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")

        bc_found = sum(1 for v in bandcamp_results.values() if v[0]) if bandcamp_results else 0
        qb_found = sum(1 for v in qobuz_results.values() if v[0]) if qobuz_results else 0
        print(f"\n  {Fore.RED}Total {len(shopping_list)} albums to acquire in lossless format.{Style.RESET_ALL}")
        if bandcamp_results:
            print(f"  {Fore.CYAN}Bandcamp links found: {bc_found}/{len(shopping_list)}{Style.RESET_ALL}")
        if qobuz_results:
            print(f"  {Fore.GREEN}Qobuz links found: {qb_found}/{len(shopping_list) - bc_found}{Style.RESET_ALL}")
    else:
        print(f"\n  {Fore.GREEN}✅ All albums are in lossless format!{Style.RESET_ALL}")

    # Generate MD report
    if not no_report:
        script_dir = Path(__file__).resolve().parent
        md_path = generate_markdown_report(
            script_dir=script_dir,
            music_root=music_root,
            artists_data=artists_data,
            total_artists=total_artists,
            total_albums=total_albums,
            total_lossless=total_lossless,
            total_non_lossless=total_non_lossless,
            shopping_list=shopping_list,
            bandcamp_results=bandcamp_results,
            qobuz_results=qobuz_results,
        )
        print(f"\n  {Fore.CYAN}📝 Report saved: {md_path}{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
