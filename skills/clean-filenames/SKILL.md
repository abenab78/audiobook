---
name: clean-filenames
description: >-
  Cleans filenames and directory names in a given folder by removing special characters, quotes, curly apostrophes, collapsing multiple spaces, and replacing en/em dashes with a standard hyphen. Works recursively and supports dry-runs.
---

# Clean Filenames Skill

## Overview
This skill cleans filenames and directory names inside a target directory to ensure they conform to a clean, filesystem-safe naming convention. It implements a Python utility script designed to:
- Remove smart quotes (`“`, `”`) and curly apostrophes (`’`, `‘`).
- Remove straight single quotes (`'`) and double quotes (`"`).
- Replace en/em dashes (`–`, `—`, `‐`) with a standard hyphen (`-`).
- Collapse multiple consecutive spaces into a single space.
- Optionally traverse subdirectories recursively and rename directories themselves using bottom-up traversal.
- Prevent file collisions by appending numerical suffixes (e.g. `_1`) if necessary.
- Perform safe **dry-runs** by default.

## Dependencies
- `python` (Python 3.x, no third-party packages required).

## Quick Start
To perform a dry-run check of filenames in a directory:
```bash
python scripts/clean_filenames.py "c:/Users/abrah/OneDrive/Music/My Media/J. K. Rowling performance by Jim Dale"
```

To run recursively and actually apply the renames:
```bash
python scripts/clean_filenames.py "c:/Users/abrah/OneDrive/Music/My Media/J. K. Rowling performance by Jim Dale" --recursive --rename-dirs --execute
```

## Utility Scripts

### Subcommands and Flags
The utility script is located at `scripts/clean_filenames.py` and supports the following arguments:

- `directory`: (Required, positional) Path to the target directory.
- `--recursive` / `-r`: (Optional flag) Scan subdirectories recursively.
- `--rename-dirs` / `-d`: (Optional flag) Rename matching folders in addition to files.
- `--execute` / `-x`: (Optional flag) Perform the actual rename operations. If omitted, the tool runs in a dry-run preview mode.
- `--output` / `-o`: (Optional string) Path to write a JSON report of the planned or executed renames.

### Example Console Preview Output:
```
Scanning: C:\Users\abrah\OneDrive\Music\My Media\J. K. Rowling performance by Jim Dale
Options: Recursive=True, Rename Directories=True, Execute=False

Planned changes:
TYPE         | ORIGINAL NAME                                      | CLEANED NAME
------------------------------------------------------------------------------------------------------------------------
FILE         | Chapter 1- “The Boy Who Lived”, Part 1.wav         | Chapter 1- The Boy Who Lived Part 1.wav
FILE         | Chapter 6- “The Journey From Platform...           | Chapter 6- The Journey From Platform...
DIRECTORY    | Book 1 - Harry Potter and the Sorcerer’s Stone    | Book 1 - Harry Potter and the Sorcerer’s Stone
------------------------------------------------------------------------------------------------------------------------
Total items to change: 3

*** DRY RUN ONLY *** Run with --execute or -x to apply these changes.
```

## Common Mistakes
1. **Executing Without Dry-Run**: Always run the tool without the `--execute` or `-x` flag first to verify the proposed renames in the printed preview table.
2. **Path Locks & Permissions**: Ensure target files are not currently open or locked in other software (such as an audio editor or media player) before running the renaming execution, as this can cause file system permission errors.
