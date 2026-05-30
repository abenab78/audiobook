---
name: convert-wav-to-mp3
description: >-
  Converts WAV files in a given directory to 128kbps constant bitrate MP3 files sequentially. Does not recurse into subdirectories, checks for FFmpeg availability, and supports dry-runs and moving original files to the Recycle Bin upon successful conversion.
---

# WAV to MP3 Conversion Skill

## Overview
This skill converts `.wav` audio files in a specified directory into standard **128kbps constant bitrate (CBR) `.mp3`** files. 

It implements a Python utility script designed to:
- Detect the presence of the system's `ffmpeg` library.
- Process WAV files sequentially (one-by-one) to maintain crystal-clear console logs.
- Perform safe **dry-runs** by default to let you review the files that will be processed.
- Preserve original `.wav` source files by default, providing an optional `--delete-original` flag to move source files to the Recycle Bin (on Windows) or delete them upon successful conversion.
- **Verify audio durations** prior to deletion (when `--delete-original` is specified) using `ffprobe`. If the source and output audio lengths differ by more than 0.1 seconds, the original WAV file is strictly preserved.
- Ignore subdirectories (non-recursive scanning of the target directory).
- Append results and statistics to a JSON execution report.

## Dependencies
- `ffmpeg` (must be installed on the system PATH).
- `python` (Python 3.x, no third-party packages required).

## Quick Start
To perform a dry-run check of WAV files in a folder:
```bash
python scripts/convert_audio.py "c:/Users/abrah/OneDrive/Music/My Media/J. K. Rowling performance by Jim Dale/Book 1 - Harry Potter and the Sorcerers Stone"
```

To execute the conversion sequentially:
```bash
python scripts/convert_audio.py "c:/Users/abrah/OneDrive/Music/My Media/J. K. Rowling performance by Jim Dale/Book 1 - Harry Potter and the Sorcerers Stone" --execute
```

To execute the conversion and safely delete the original WAV files:
```bash
python scripts/convert_audio.py "c:/Users/abrah/OneDrive/Music/My Media/J. K. Rowling performance by Jim Dale/Book 1 - Harry Potter and the Sorcerers Stone" --execute --delete-original
```

## Utility Scripts

### Arguments and Flags
The utility script is located at `scripts/convert_audio.py` and supports the following arguments:

- `directory`: (Required, positional) Path to the target directory containing WAV files.
- `--execute` / `-x`: (Optional flag) Perform the actual conversion operations. If omitted, the tool runs in a dry-run preview mode.
- `--delete-original` / `-d`: (Optional flag) Delete the original `.wav` file after successful conversion.
- `--bitrate`: (Optional string, defaults to `128k`) Adjust the constant bitrate output format (e.g. `192k` or `64k`).
- `--output` / `-o`: (Optional string) Path to write a JSON report of the execution.

## Common Mistakes
1. **FFmpeg Missing on PATH**: Ensure that `ffmpeg` is properly configured on your system environment variables. You can test it by running `ffmpeg` in your terminal.
2. **Deleting Source Files Early**: Do not use `--delete-original` unless you have verified your dry-runs and are fully comfortable removing the lossless source WAV files.
3. **Subdirectories expectation**: The tool is strictly non-recursive. If you want to convert WAV files across multiple directories, run the script on each folder individually.
