#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utility script to create a single M4B audiobook file from a directory of MP3 chapter files.
Dynamically extracts chapter durations using ffprobe, generates an FFMETADATA file with 
precise chapter markers in milliseconds, and transcodes the audio to 128kbps AAC.
Does not delete the original MP3 files. Runs strictly non-recursively.
"""

import os
import sys
import argparse
import subprocess
import json
import tempfile


def check_ffmpeg():
    """Checks if ffmpeg and ffprobe are available in the system PATH."""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
        subprocess.run(['ffprobe', '-version'], capture_output=True, text=True, timeout=5)
        return True
    except Exception:
        return False


def get_audio_duration(filepath):
    """Queries the exact duration of an audio file using ffprobe."""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        filepath
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception:
        pass
    return None


def get_mp3_files(directory):
    """
    Scans the immediate directory (non-recursively) for files ending in .mp3.
    Ignores any pre-existing .m4b or other extensions.
    Returns a sorted list of absolute file paths.
    """
    mp3_files = []
    try:
        for entry in os.scandir(directory):
            # Only pick .mp3 files and make sure we don't pick any temporary files or our own output if named .mp3
            if entry.is_file() and entry.name.lower().endswith('.mp3'):
                mp3_files.append(os.path.abspath(entry.path))
    except OSError as e:
        print(f"Error scanning directory {directory}: {e}", file=sys.stderr)
        sys.exit(1)
        
    return sorted(mp3_files)


def build_metadata_content(title, artist, chapters):
    """
    Generates the content for the FFMETADATA1 file containing global titles
    and the list of [CHAPTER] tags with START/END times in milliseconds.
    """
    lines = [
        ";FFMETADATA1",
        f"title={title}",
        f"artist={artist}",
        f"album={title}",
        f"genre=Audiobook",
        ""
    ]
    
    for ch in chapters:
        lines.append("[CHAPTER]")
        lines.append("TIMEBASE=1/1000")
        lines.append(f"START={ch['start_ms']}")
        lines.append(f"END={ch['end_ms']}")
        lines.append(f"title={ch['title']}")
        lines.append("")
        
    return "\n".join(lines)


def main():
    # Force UTF-8 encoding for standard output and error to prevent Windows encoding exceptions
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Create a single M4B audiobook file from a directory of MP3 chapter files.")
    parser.add_argument("directory", help="The directory containing the MP3 files.")
    parser.add_argument("--execute", "-x", action="store_true", help="Actually execute the transcoding and muxing (defaults to dry-run).")
    parser.add_argument("--bitrate", default="128k", help="Audio bitrate for the AAC stream (default: 128k).")
    parser.add_argument("--output", "-o", help="Optional path to write a JSON report of the execution.")
    
    args = parser.parse_args()
    
    target_dir = os.path.abspath(args.directory)
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        print(f"Error: Target directory '{target_dir}' does not exist or is not a directory.", file=sys.stderr)
        sys.exit(1)
        
    if not check_ffmpeg():
        print("Error: FFmpeg or FFprobe is not installed or not found on PATH.", file=sys.stderr)
        sys.exit(1)
        
    # Parse Title and Artist metadata based on folder names
    book_folder_name = os.path.basename(target_dir)
    parent_folder_name = os.path.basename(os.path.dirname(target_dir))
    
    # Clean up Title: e.g. "Book 3 - Harry Potter and the Prisoner of Azkaban" -> "Harry Potter and the Prisoner of Azkaban"
    if " - " in book_folder_name:
        book_title = book_folder_name.split(" - ", 1)[1].strip()
    else:
        book_title = book_folder_name
        
    # Artist: use parent folder if it exists, otherwise a sensible default
    book_artist = parent_folder_name if parent_folder_name else "J. K. Rowling performance by Jim Dale"
    
    print(f"Scanning directory: {target_dir}")
    print(f"Metadata Parsed: Title='{book_title}', Artist='{book_artist}'")
    print(f"Options: Non-Recursive, Bitrate={args.bitrate}, Execute={args.execute}\n")
    
    # Scan MP3 files in alphabetical order
    mp3_files = get_mp3_files(target_dir)
    
    if not mp3_files:
        print("No .mp3 files found in the directory. Nothing to transcode.")
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
        sys.exit(0)
        
    print(f"Found {len(mp3_files)} MP3 file(s) to compile in alphabetical order:")
    
    chapters = []
    current_offset_ms = 0
    
    for idx, path in enumerate(mp3_files, 1):
        filename = os.path.basename(path)
        dur = get_audio_duration(path)
        if dur is None:
            print(f"Error: Failed to query audio duration for file: {filename}", file=sys.stderr)
            sys.exit(1)
            
        dur_ms = int(round(dur * 1000))
        
        # Clean chapter title: "Chapter 01- Owl Post.mp3" -> "Chapter 01 - Owl Post"
        ch_title, _ = os.path.splitext(filename)
        # Beautify spacing around en-dashes/hyphens if present
        if "-" in ch_title and " - " not in ch_title:
            import re
            ch_title = re.sub(r"\s*-\s*", " - ", ch_title, count=1)
            
        chapters.append({
            "index": idx,
            "filename": filename,
            "path": path,
            "duration_s": dur,
            "start_ms": current_offset_ms,
            "end_ms": current_offset_ms + dur_ms,
            "title": ch_title
        })
        
        current_offset_ms += dur_ms
        
    # Print chapters and timing offsets
    print(f"{'#':<3} | {'CHAPTER TITLE':<50} | {'START TIME':<12} | {'DURATION':<10}")
    print("-" * 85)
    for ch in chapters:
        start_s = ch["start_ms"] / 1000.0
        m, s = divmod(start_s, 60)
        h, m = divmod(m, 60)
        time_str = f"{int(h):02d}:{int(m):02d}:{s:05.2f}"
        print(f"{ch['index']:<3} | {ch['title']:<50} | {time_str:<12} | {ch['duration_s']:<10.2f}s")
    print("-" * 85)
    
    output_filename = f"{book_folder_name}.m4b"
    output_path = os.path.join(target_dir, output_filename)
    
    # Total duration calculation
    total_s = current_offset_ms / 1000.0
    m, s = divmod(total_s, 60)
    h, m = divmod(m, 60)
    total_time_str = f"{int(h):02d}:{int(m):02d}:{s:05.2f}"
    print(f"Total Audiobook Length: {total_time_str} ({total_s:.2f} seconds)")
    print(f"Proposed Output Path: {output_path}\n")
    
    if not args.execute:
        print("*** DRY RUN ONLY *** Run with --execute or -x to execute the actual transcoding.")
        if args.output:
            dry_run_data = {
                "title": book_title,
                "artist": book_artist,
                "output_file": output_path,
                "total_duration_s": total_s,
                "chapters_count": len(chapters),
                "chapters": chapters,
                "status": "planned"
            }
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(dry_run_data, f, indent=2)
        sys.exit(0)
        
    # 1. Create temporary FFmpeg concat demuxer list
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_list:
            for ch in chapters:
                escaped_path = ch["path"].replace("\\", "/").replace("'", "'\\''")
                temp_list.write(f"file '{escaped_path}'\n")
            temp_list_path = temp_list.name
    except Exception as e:
        print(f"Error: Failed to create temporary concat demuxer file: {e}", file=sys.stderr)
        sys.exit(1)
        
    # 2. Create temporary FFMETADATA file
    metadata_content = build_metadata_content(book_title, book_artist, chapters)
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_meta:
            temp_meta.write(metadata_content)
            temp_meta_path = temp_meta.name
    except Exception as e:
        # clean up list file
        try:
            os.remove(temp_list_path)
        except OSError:
            pass
        print(f"Error: Failed to create temporary FFMETADATA file: {e}", file=sys.stderr)
        sys.exit(1)
        
    # 3. Compile FFmpeg command to transcode and mux
    print("Compiling M4B file (this may take a few moments for large audiobooks)...")
    cmd = [
        'ffmpeg',
        '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', temp_list_path,
        '-i', temp_meta_path,
        '-map', '0:a',
        '-map_metadata', '1',
        '-c:a', 'aac',
        '-b:a', args.bitrate,
        output_path
    ]
    
    try:
        # Run FFmpeg as a subprocess
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        # Clean up temporary files immediately
        try:
            os.remove(temp_list_path)
            os.remove(temp_meta_path)
        except OSError:
            pass
            
        if result.returncode != 0:
            print(f"FFmpeg Error (code {result.returncode}): {result.stderr.strip()}", file=sys.stderr)
            sys.exit(1)
            
        # Verify output file generated
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            print("Error: Output M4B file was not generated or is empty.", file=sys.stderr)
            sys.exit(1)
            
        # Validate output M4B duration
        m4b_dur = get_audio_duration(output_path)
        if m4b_dur is None:
            print("Warning: Conversion succeeded, but failed to verify final M4B duration.")
        else:
            diff = abs(total_s - m4b_dur)
            print(f"Verification:\n  Sum of parts: {total_s:.3f}s\n  M4B Duration: {m4b_dur:.3f}s\n  Difference: {diff:.3f}s")
            
        print(f"\nSUCCESS! Created M4B audiobook: {os.path.basename(output_path)}")
        print(f"All original MP3 files have been preserved in the directory.")
        
        if args.output:
            success_data = {
                "title": book_title,
                "artist": book_artist,
                "output_file": output_path,
                "total_duration_s": m4b_dur if m4b_dur else total_s,
                "chapters_count": len(chapters),
                "status": "success"
            }
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(success_data, f, indent=2)
                
        sys.exit(0)
        
    except Exception as e:
        # clean up files
        for p in [temp_list_path, temp_meta_path]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
        print(f"Exception during M4B compilation: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
