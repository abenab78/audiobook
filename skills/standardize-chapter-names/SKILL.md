---
name: standardize-chapter-names
description: >-
  Standardizes chapter and introduction filenames (e.g. padding single-digit chapters like 'Chapter 1' -> 'Chapter 01' and prepending '00 - ' to 'Introduction' files) to ensure correct alphabetical sorting. Runs strictly non-recursively.
---

# Standardize Chapter Names Skill

## Overview
This skill scans a target directory and renames files to ensure they sort in perfect alphabetical order in media players and file explorers. It:
- Formats single-digit chapter numbers (1-9) to always have a leading zero (e.g., `Chapter 1` $\rightarrow$ `Chapter 01`).
- Leaves double-digit chapter numbers (10+) untouched (e.g., `Chapter 10` remains unchanged).
- Prepends `00 - ` to `Introduction` files (e.g., `Introduction.mp3` $\rightarrow$ `00 - Introduction.mp3`) so they sort at the very top.
- Processes any file type starting with those keywords (e.g., `.mp3`, `.wav`, `.jpg`, `.txt`, `.log`), keeping matching track listings, album art, and logs synchronized.
- Operates strictly **non-recursively** in the target folder.
- Executes in safe **dry-run mode** by default.

## Dependencies
- `python` (Python 3.x, standard library only).

## Quick Start
To perform a dry-run standardization preview of a folder:
```bash
python scripts/standardize_filenames.py "c:/Users/abrah/OneDrive/Music/My Media/J. K. Rowling performance by Jim Dale/Book 3 - Harry Potter and the Prisoner of Azkaban"
```

To execute the renames on the files:
```bash
python scripts/standardize_filenames.py "c:/Users/abrah/OneDrive/Music/My Media/J. K. Rowling performance by Jim Dale/Book 3 - Harry Potter and the Prisoner of Azkaban" --execute
```

## CLI Arguments and Flags
The utility script is located at `scripts/standardize_filenames.py` and supports:

- `directory`: (Required, positional) Path to the target directory containing files to standardize.
- `--execute` / `-x`: (Optional flag) Perform the actual rename operations on disk. If omitted, runs in a dry-run preview mode.
- `--output` / `-o`: (Optional string) Path to write a JSON report of the execution.

## Common Safety Rules
1. **Collision Check**: If the target filename already exists (e.g., both `Chapter 1- Owl Post.mp3` and `Chapter 01- Owl Post.mp3` are present), the script will skip renaming that file and output a warning to prevent data overwriting.
2. **Casing Preservation**: The prefix casing (e.g., `Chapter` vs `chapter`, or `Introduction` vs `introduction`) is perfectly preserved when padding or prepending.
