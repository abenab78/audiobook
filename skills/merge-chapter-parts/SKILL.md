---
name: merge-chapter-parts
description: >-
  Merges segmented MP3 chapter part files (e.g. ', Part 1.mp3' ... ', Part N.mp3') into single consolidated chapter files. Checks sequence contiguity, verifies duration sums, and recycles part files upon success. Runs strictly non-recursively.
---

# Merge Chapter Parts Skill

## Overview
This skill merges segmented chapter MP3 part files inside a given folder into a single unified chapter MP3 file. It implements a Python utility script designed to:
- Group `.mp3` files ending with `, Part [digits].mp3`.
- Verify **contiguous sequence alignment** starting exactly at Part 1 (e.g., skips merging and preserves files if any intermediate parts are missing).
- Perform a **lossless stream copy concatenation** (`-c copy`) via FFmpeg, ensuring zero audio quality loss and ultra-fast merge execution times.
- Validate **audio duration alignment** (checks if the sum of durations of all parts matches the merged file's duration within a `0.2` seconds tolerance threshold).
- Automatically move the original part files to the **Recycle Bin** on Windows upon a successful merge and validation.
- Run strictly **non-recursively** to protect subdirectories.
- Execute in safe **dry-run mode** by default.

## Dependencies
- `ffmpeg` and `ffprobe` (must be installed on the system PATH).
- `python` (Python 3.x, no third-party packages required).

## Quick Start
To perform a dry-run check of chapter part files in a folder:
```bash
python scripts/merge_chapters.py "c:/Users/abrah/OneDrive/Music/My Media/J. K. Rowling performance by Jim Dale/Book 1 - Harry Potter and the Sorcerers Stone"
```

To execute the merges and safely recycle the source parts:
```bash
python scripts/merge_chapters.py "c:/Users/abrah/OneDrive/Music/My Media/J. K. Rowling performance by Jim Dale/Book 1 - Harry Potter and the Sorcerers Stone" --execute
```

## Utility Scripts

### Arguments and Flags
The utility script is located at `scripts/merge_chapters.py` and supports the following arguments:

- `directory`: (Required, positional) Path to the target directory containing MP3 part files.
- `--execute` / `-x`: (Optional flag) Perform the actual merge and Recycle Bin cleanup operations. If omitted, the tool runs in a dry-run preview mode.
- `--tolerance`: (Optional float, defaults to `0.2`s) Cushion tolerance in seconds for duration validation.
- `--output` / `-o`: (Optional string) Path to write a JSON report of the execution.

## Common Mistakes
1. **Sequence Gaps**: If any parts are missing from a chapter sequence (e.g. you have Part 1 and Part 3, but Part 2 was deleted), the tool will skip merging that chapter for safety. Ensure all part files are present in the directory.
2. **Output File Already Exists**: If a merged output file (e.g., `Chapter 1.mp3`) already exists, the tool will skip merging to prevent accidental overwrites. Clean up or rename the destination file first.
