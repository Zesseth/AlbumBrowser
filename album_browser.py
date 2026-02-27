import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from colorama import init, Fore, Style

init()  # Alustaa värituen (Windows/Linux/macOS)

AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma", ".opus", ".ape", ".alac", ".aiff", ".wv"}
LOSSLESS_FORMATS = {"FLAC", "APE", "WAV", "AIFF", "WV", "ALAC"}

BANDCAMP_SEARCH_URL = "https://bandcamp.com/search"
QOBUZ_SEARCH_URL = "https://www.qobuz.com/fi-en/search/albums"
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
REQUEST_TIMEOUT = 10
RATE_LIMIT = 2  # sekuntia pyyntöjen välillä


def get_audio_files(directory: Path) -> list[Path]:
    """Palauttaa kansion äänitiedostot aakkostettuina."""
    return sorted(
        [f for f in directory.iterdir() if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS],
        key=lambda f: f.name.lower()
    )


def format_file_size(size_bytes: int) -> str:
    """Muotoilee tavumäärän luettavaan muotoon."""
    if size_bytes >= 1_073_741_824:
        return f"{size_bytes / 1_073_741_824:.1f} GB"
    if size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.0f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.0f} KB"
    return f"{size_bytes} B"


def _normalize(text: str) -> str:
    """Normalisoi teksti vertailua varten (pienet kirjaimet, ylimääräiset välit pois)."""
    return " ".join(text.lower().split())


def _search_bandcamp(query: str, item_type: str) -> list[dict]:
    """Hakee Bandcampista ja palauttaa listan tuloksista.

    item_type: 'a' = albumit, 'b' = artistit/bändit
    Palauttaa listan: [{'name': str, 'artist': str, 'url': str, 'type': str}, ...]
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

        # Artistin nimi subheadista (albumi: "by Artisti", artisti: sijainti)
        artist = ""
        if item_type == "a" and subhead.lower().startswith("by "):
            artist = subhead[3:].strip()

        result_type = "album" if item_type == "a" else "artist"
        results.append({"name": name, "artist": artist, "url": url, "type": result_type})

    return results


def search_bandcamp(artist_name: str, album_name: str) -> tuple[str | None, str | None]:
    """Hakee Bandcampista albumin tai artistin sivun.

    Palauttaa (url, match_type) missä match_type on 'album', 'artist' tai None.
    Hakujärjestys: 1) albumihaku, 2) artistihaku.
    """
    artist_norm = _normalize(artist_name)
    album_norm = _normalize(album_name)

    # 1. Hae albumia
    query = f"{artist_name} {album_name}"
    results = _search_bandcamp(query, "a")

    for r in results:
        r_artist = _normalize(r["artist"])
        r_album = _normalize(r["name"])
        # Tarkista onko artisti ja albumin nimi riittävän lähellä
        if artist_norm in r_artist or r_artist in artist_norm:
            if album_norm in r_album or r_album in album_norm:
                return (r["url"], "album")

    # Löyhempi haku: pelkkä artisti-match albumihaussa
    for r in results:
        r_artist = _normalize(r["artist"])
        if artist_norm in r_artist or r_artist in artist_norm:
            return (r["url"], "album")

    time.sleep(RATE_LIMIT)

    # 2. Hae artistia
    results = _search_bandcamp(artist_name, "b")

    for r in results:
        r_name = _normalize(r["name"])
        if artist_norm in r_name or r_name in artist_norm:
            return (r["url"], "artist")

    # Palauta ensimmäinen artisti-tulos jos löytyy
    if results:
        return (results[0]["url"], "artist")

    return (None, None)


def _search_qobuz(query: str) -> list[dict]:
    """Hakee Qobuzin kaupasta albumeja.

    Palauttaa listan: [{'name': str, 'artist': str, 'url': str}, ...]
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

    # Albumilinkit löytyvät <a href="/fi-en/album/..."> elementeistä
    album_links = soup.find_all("a", href=lambda h: h and "/album/" in h)
    # Suodata otsikkolinkit (parent div sisältää 'min-w-0' luokan)
    title_links = [
        a for a in album_links
        if a.parent and "min-w-0" in (a.parent.get("class") or [])
    ]

    for a in title_links:
        album_name = a.get_text(strip=True)
        album_href = a.get("href", "")
        album_url = f"https://www.qobuz.com{album_href}" if album_href.startswith("/") else album_href

        # Etsi artistilinkki samasta containerista
        container = a.parent
        artist_links = (
            container.find_all("a", href=lambda h: h and "/interpreter/" in h)
            if container else []
        )
        artist_name = artist_links[0].get_text(strip=True) if artist_links else ""

        results.append({"name": album_name, "artist": artist_name, "url": album_url})

    return results


def search_qobuz(artist_name: str, album_name: str) -> tuple[str | None, str | None]:
    """Hakee Qobuzista albumin sivun.

    Palauttaa (url, match_type) missä match_type on 'album' tai None.
    """
    artist_norm = _normalize(artist_name)
    album_norm = _normalize(album_name)

    query = f"{artist_name} {album_name}"
    results = _search_qobuz(query)

    # Tarkka haku: artisti + albumi
    for r in results:
        r_artist = _normalize(r["artist"])
        r_album = _normalize(r["name"])
        if (artist_norm in r_artist or r_artist in artist_norm) and \
           (album_norm in r_album or r_album in album_norm):
            return (r["url"], "album")

    # Löyhempi haku: pelkkä artisti-match
    for r in results:
        r_artist = _normalize(r["artist"])
        if artist_norm in r_artist or r_artist in artist_norm:
            return (r["url"], "album")

    return (None, None)


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
    """Generoi Markdown-raportin MD/result.md tiedostoon."""
    md_dir = script_dir / "MD"
    md_dir.mkdir(exist_ok=True)
    md_path = md_dir / "result.md"

    lines = []
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Otsikko
    lines.append("# 🎵 Musiikkikirjasto")
    lines.append("")
    lines.append(f"> Skannaus: **{now}**  ")
    lines.append(f"> Polku: `{music_root}`")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Artistit ja albumit
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
                status = f"⚠️ *Ei-lossless: {lossy}*"
                fmt_display = f"`{fmt}`"

            lines.append(f"- {icon} **{name}** — {fmt_display} — {count} kpl, {size} {status}")

        lines.append("")

    # Yhteenveto
    lines.append("---")
    lines.append("")
    lines.append("## 📊 Yhteenveto")
    lines.append("")
    lines.append("| Mittari | Määrä |")
    lines.append("|:---|---:|")
    lines.append(f"| 🎤 Artisteja | **{total_artists}** |")
    lines.append(f"| 💿 Albumeita | **{total_albums}** |")
    lines.append(f"| ✅ Lossless | **{total_lossless}** |")
    lines.append(f"| ⚠️ Ei-lossless | **{total_non_lossless}** |")
    lines.append("")

    # Ostoslista
    if shopping_list:
        lines.append("---")
        lines.append("")
        lines.append("## 🛒 Ostoslista — Hankittava lossless-versio")
        lines.append("")
        lines.append("| # | Artisti | Albumi | Formaatti | Linkki |")
        lines.append("|---:|:---|:---|:---:|:---|")

        bc_found = 0
        qb_found = 0

        for i, (artist, album, lossy_fmts) in enumerate(shopping_list, 1):
            fmt_str = ", ".join(lossy_fmts)

            # Etsi linkki
            link_str = "—"
            bc = bandcamp_results.get((artist, album))
            if bc and bc[0]:
                url, match_type = bc
                suffix = " (artisti)" if match_type != "album" else ""
                link_str = f"[🔗 Bandcamp{suffix}]({url})"
                bc_found += 1
            else:
                qb = qobuz_results.get((artist, album))
                if qb and qb[0]:
                    url, _ = qb
                    link_str = f"[🔗 Qobuz]({url})"
                    qb_found += 1

            lines.append(f"| {i} | **{artist}** | {album} | `{fmt_str}` | {link_str} |")

        lines.append("")
        lines.append(f"> **Yhteensä {len(shopping_list)}** albumia hankittavana lossless-formaatissa.  ")
        if bandcamp_results:
            lines.append(f"> Bandcamp-linkkejä löytyi: **{bc_found}** / {len(shopping_list)}  ")
        if qobuz_results:
            lines.append(f"> Qobuz-linkkejä löytyi: **{qb_found}** / {len(shopping_list) - bc_found}")
        lines.append("")
    else:
        lines.append("")
        lines.append("> ✅ **Kaikki albumit ovat lossless-formaatissa!**")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def main():
    # Tarkista liput
    args = sys.argv[1:]
    no_bandcamp = "--no-bandcamp" in args
    no_qobuz = "--no-qobuz" in args
    no_report = "--no-report" in args
    args = [a for a in args if a not in ("--no-bandcamp", "--no-qobuz", "--no-report")]

    if len(args) < 1:
        print(f"{Fore.RED}Käyttö: python album_browser.py <musiikkikansion_polku> [--no-bandcamp] [--no-qobuz] [--no-report]{Style.RESET_ALL}")
        print(f"Esim:  python album_browser.py \"C:\\Users\\Käyttäjä\\Music\"")
        print(f"       --no-bandcamp  Ohittaa Bandcamp-haun")
        print(f"       --no-qobuz     Ohittaa Qobuz-haun")
        print(f"       --no-report    Ohittaa MD-raportin generoinnin")
        return

    music_root = Path(args[0])

    if not music_root.exists():
        print(f"{Fore.RED}Kansiota ei löydy: {music_root}{Style.RESET_ALL}")
        return

    print(f"{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗")
    print(f"║                    🎵  MUSIIKKIKIRJASTO  🎵                 ║")
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
    artists_data = []  # Datan keräys MD-raporttia varten

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
        print(f"  {Fore.YELLOW}🎤 {artist_name}{Style.RESET_ALL}")

        for album_dir in album_dirs:
            album_name = album_dir.name
            tracks = get_audio_files(album_dir)

            if not tracks:
                continue

            total_albums += 1

            # Selvitä albumin formaatit
            formats = sorted(set(f.suffix.lstrip(".").upper() for f in tracks))
            format_str = " / ".join(formats)

            # Laske albumin kokonaiskoko
            total_size = sum(f.stat().st_size for f in tracks)
            size_str = format_file_size(total_size)

            # Selvitä häviöttömät ja häviölliset formaatit
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

            # Kerää albumidata raporttia varten
            current_artist["albums"].append({
                "name": album_name,
                "format_str": format_str,
                "track_count": len(tracks),
                "size_str": size_str,
                "all_lossless": all_lossless,
                "lossy_fmts": lossy_fmts,
                "is_loose": False,
            })

            # Albumirivi
            line = (
                f"     ├── 💿 {Fore.WHITE}{album_name}{Style.RESET_ALL}"
                f"  [{format_color}{format_str}{Style.RESET_ALL}]"
                f" ({len(tracks)} kpl, {size_str})"
            )
            if not all_lossless:
                line += f"  {Fore.RED}⚠️  Ei-lossless: {', '.join(lossy_fmts)}{Style.RESET_ALL}"
            print(line)

        # Irralliset kappaleet (suoraan artistin kansiossa)
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
                shopping_list.append((artist_name, "(Irrallisia kappaleita)", lossy_fmts))

            # Kerää irrallisten kappaleiden data raporttia varten
            current_artist["albums"].append({
                "name": "(Irrallisia kappaleita)",
                "format_str": format_str,
                "track_count": len(loose_files),
                "size_str": size_str,
                "all_lossless": all_lossless,
                "lossy_fmts": lossy_fmts,
                "is_loose": True,
            })

            line = (
                f"     ├── 📁 {Fore.LIGHTYELLOW_EX}(Irrallisia kappaleita){Style.RESET_ALL}"
                f"  [{format_color}{format_str}{Style.RESET_ALL}]"
                f" ({len(loose_files)} kpl, {size_str})"
            )
            if not all_lossless:
                line += f"  {Fore.RED}⚠️  Ei-lossless: {', '.join(lossy_fmts)}{Style.RESET_ALL}"
            print(line)

        artists_data.append(current_artist)
        print()

    # Yhteenveto
    print(f"{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗")
    print(f"║                        YHTEENVETO                           ║")
    print(f"╠══════════════════════════════════════════════════════════════╣{Style.RESET_ALL}")
    print(f"║  {Fore.YELLOW}Artisteja:       {total_artists:6}{Style.RESET_ALL}                                  ║")
    print(f"║  {Fore.WHITE}Albumeita:       {total_albums:6}{Style.RESET_ALL}                                  ║")
    print(f"║  {Fore.GREEN}Lossless:        {total_lossless:6}{Style.RESET_ALL}                                  ║")
    print(f"║  {Fore.MAGENTA}Ei-lossless:     {total_non_lossless:6}{Style.RESET_ALL}                                  ║")
    print(f"{Fore.CYAN}╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")

    # Ostoslista
    if shopping_list:
        # Hae Bandcamp-linkit ostoslistan albumeille
        bandcamp_results = {}
        qobuz_results = {}
        if not no_bandcamp or not no_qobuz:
            print()
            print(f"  {Fore.CYAN}🔍 Haetaan ostolinkkejä...{Style.RESET_ALL}")
            for i, (artist, album, _) in enumerate(shopping_list, 1):
                print(
                    f"  {Fore.CYAN}   ({i}/{len(shopping_list)}) {artist} – {album}...{Style.RESET_ALL}",
                    end="", flush=True,
                )

                found = False

                # 1. Bandcamp-haku
                if not no_bandcamp:
                    url, match_type = search_bandcamp(artist, album)
                    bandcamp_results[(artist, album)] = (url, match_type)
                    if url:
                        tag = "💿" if match_type == "album" else "🎤"
                        print(f" {Fore.GREEN}{tag} BC löytyi!{Style.RESET_ALL}")
                        found = True

                # 2. Qobuz-fallback (jos Bandcampista ei löytynyt)
                if not found and not no_qobuz:
                    if not no_bandcamp:
                        time.sleep(RATE_LIMIT)
                    url, match_type = search_qobuz(artist, album)
                    qobuz_results[(artist, album)] = (url, match_type)
                    if url:
                        print(f" {Fore.GREEN}💿 Qobuz löytyi!{Style.RESET_ALL}")
                        found = True

                if not found:
                    print(f" {Fore.RED}❌{Style.RESET_ALL}")

                if i < len(shopping_list):
                    time.sleep(RATE_LIMIT)

        print()
        print(f"{Fore.RED}╔══════════════════════════════════════════════════════════════╗")
        print(f"║          🛒  OSTOSLISTA – Hankittava lossless-versio        ║")
        print(f"╠══════════════════════════════════════════════════════════════╣{Style.RESET_ALL}")
        for artist, album, lossy_fmts in shopping_list:
            fmt_str = ', '.join(lossy_fmts)
            line = f"  {Fore.YELLOW}{artist}{Style.RESET_ALL} – {Fore.WHITE}{album}{Style.RESET_ALL}  [{Fore.MAGENTA}{fmt_str}{Style.RESET_ALL}]"

            # Lisää Bandcamp-linkki jos löytyi
            bc = bandcamp_results.get((artist, album))
            if bc and bc[0]:
                url, match_type = bc
                if match_type == "album":
                    line += f"  {Fore.CYAN}🔗 BC: {url}{Style.RESET_ALL}"
                else:
                    line += f"  {Fore.CYAN}🔗 BC: {url} (artisti){Style.RESET_ALL}"
            else:
                # Lisää Qobuz-linkki jos löytyi (fallback)
                qb = qobuz_results.get((artist, album))
                if qb and qb[0]:
                    url, _ = qb
                    line += f"  {Fore.GREEN}🔗 Qobuz: {url}{Style.RESET_ALL}"

            print(line)
        print(f"{Fore.RED}╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")

        bc_found = sum(1 for v in bandcamp_results.values() if v[0]) if bandcamp_results else 0
        qb_found = sum(1 for v in qobuz_results.values() if v[0]) if qobuz_results else 0
        print(f"\n  {Fore.RED}Yhteensä {len(shopping_list)} albumia hankittavana lossless-formaatissa.{Style.RESET_ALL}")
        if bandcamp_results:
            print(f"  {Fore.CYAN}Bandcamp-linkkejä löytyi: {bc_found}/{len(shopping_list)}{Style.RESET_ALL}")
        if qobuz_results:
            print(f"  {Fore.GREEN}Qobuz-linkkejä löytyi: {qb_found}/{len(shopping_list) - bc_found}{Style.RESET_ALL}")
    else:
        print(f"\n  {Fore.GREEN}✅ Kaikki albumit ovat lossless-formaatissa!{Style.RESET_ALL}")

    # Generoi MD-raportti
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
            bandcamp_results=bandcamp_results if shopping_list else {},
            qobuz_results=qobuz_results if shopping_list else {},
        )
        print(f"\n  {Fore.CYAN}📝 Raportti tallennettu: {md_path}{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
