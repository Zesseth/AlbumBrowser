import sys
import os
from pathlib import Path
from colorama import init, Fore, Style

init()  # Alustaa värituen (Windows/Linux/macOS)

AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma", ".opus", ".ape", ".alac", ".aiff", ".wv"}
LOSSLESS_FORMATS = {"FLAC", "APE", "WAV", "AIFF", "WV", "ALAC"}


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


def main():
    if len(sys.argv) < 2:
        print(f"{Fore.RED}Käyttö: python album_browser.py <musiikkikansion_polku>{Style.RESET_ALL}")
        print(f"Esim:  python album_browser.py \"C:\\Users\\Käyttäjä\\Music\"")
        return

    music_root = Path(sys.argv[1])

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
    total_tracks = 0

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

            # Häviötön = vihreä, häviöllinen = magenta
            is_lossless = any(fmt in LOSSLESS_FORMATS for fmt in formats)
            format_color = Fore.GREEN if is_lossless else Fore.MAGENTA

            print(
                f"     ├── 💿 {Fore.WHITE}{album_name}{Style.RESET_ALL}"
                f"  [{format_color}{format_str}{Style.RESET_ALL}]"
                f" ({len(tracks)} kpl, {size_str})"
            )

            # Kappaleet
            for i, track in enumerate(tracks):
                total_tracks += 1
                track_name = track.stem
                connector = "└── " if i == len(tracks) - 1 else "├── "
                print(f"     │      {Fore.LIGHTBLACK_EX}{connector}{Fore.LIGHTWHITE_EX}♪ {track_name}{Style.RESET_ALL}")

            print(f"     {Fore.LIGHTBLACK_EX}│{Style.RESET_ALL}")

        # Irralliset kappaleet (suoraan artistin kansiossa)
        if loose_files:
            total_albums += 1
            formats = sorted(set(f.suffix.lstrip(".").upper() for f in loose_files))
            print(
                f"     ├── 📁 {Fore.LIGHTYELLOW_EX}(Irrallisia kappaleita){Style.RESET_ALL}"
                f"  [{' / '.join(formats)}]"
            )

            for i, track in enumerate(loose_files):
                total_tracks += 1
                track_name = track.stem
                connector = "└── " if i == len(loose_files) - 1 else "├── "
                print(f"     │      {Fore.LIGHTBLACK_EX}{connector}{Fore.LIGHTWHITE_EX}♪ {track_name}{Style.RESET_ALL}")

            print(f"     {Fore.LIGHTBLACK_EX}│{Style.RESET_ALL}")

        print()

    # Yhteenveto
    print(f"{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗")
    print(f"║                        YHTEENVETO                           ║")
    print(f"╠══════════════════════════════════════════════════════════════╣{Style.RESET_ALL}")
    print(f"║  {Fore.YELLOW}Artisteja:  {total_artists:6}{Style.RESET_ALL}                                       ║")
    print(f"║  {Fore.WHITE}Albumeita:  {total_albums:6}{Style.RESET_ALL}                                       ║")
    print(f"║  {Fore.LIGHTWHITE_EX}Kappaleita: {total_tracks:6}{Style.RESET_ALL}                                       ║")
    print(f"{Fore.CYAN}╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
