---
name: create-m4b-audiobook
description: >-
  Compiles all sorted MP3 tracks inside a folder into a single .m4b audiobook file with dynamic millisecond-precision chapter markers using FFmpeg, while keeping original MP3 files intact.
---

# Create M4B Audiobook Skill

## Overview
This skill compiles a collection of zero-padded, alphabetically sorted `.mp3` chapter tracks inside an audiobook directory into a single, comprehensive `.m4b` audiobook container. It:
- Scans `.mp3` files and sorts them alphabetically (ensuring perfect sequential ordering of chapters and introductions).
- Extracts precise durations of each source track using `ffprobe`.
- Dynamically compiles a temporary `FFMETADATA1` file with **millisecond-accurate chapter markers** (`TIMEBASE=1/1000`).
- Invokes FFmpeg to transcode all MP3s and mux them into a single high-quality **128kbps AAC** `.m4b` file (`-c:a aac -b:a 128k`).
- Muxes interactive chapter listings so players (like Apple Books or Smart AudioBook Player) show titles and let readers easily skip tracks.
- Automatically preserves **100% of your original MP3 files** (strictly additive; no deletions).
- Operates strictly **non-recursively** in the target directory.
- Runs in safe **dry-run mode** by default.

## Dependencies
- `ffmpeg` and `ffprobe` (installed and globally available on system PATH).
- `python` (Python 3.x, standard library only).

## Quick Start

To perform a dry-run check of the planned M4B compilation (calculating offset timelines and showing the chapter index):
```bash
python scripts/create_m4b.py "c:/Users/abrah/OneDrive/Music/My Media/J. K. Rowling performance by Jim Dale/Book 1 - Harry Potter and the Sorcerers Stone"
```

To execute the M4B creation (transcoding audio and embedding chapter markers):
```bash
python scripts/create_m4b.py "c:/Users/abrah/OneDrive/Music/My Media/J. K. Rowling performance by Jim Dale/Book 1 - Harry Potter and the Sorcerers Stone" --execute
```

## CLI Arguments and Flags
The utility script is located at `scripts/create_m4b.py` and supports:

- `directory`: (Required, positional) Path to the target directory containing MP3 files.
- `--execute` / `-x`: (Optional flag) Perform the actual transcoding and chapter embedding. If omitted, runs in a dry-run preview mode.
- `--bitrate`: (Optional string, defaults to `128k`) Bitrate for the AAC audio stream.
- `--output` / `-o`: (Optional string) Path to write a JSON report of the execution.
