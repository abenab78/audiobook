#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utility script to merge segmented audiobook MP3 part files into single consolidated chapter files.
Only processes MP3 files, runs strictly non-recursively, verifies audio lengths, and recycles parts upon success.
"""

import os
import re
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


def recycle_file(file_path):
    """
    Moves a file to the Windows Recycle Bin using native shell32 API via ctypes.
    Falls back to standard os.remove if not on Windows or if ctypes fails.
    """
    file_path = os.path.abspath(file_path)
    if os.name == 'nt':
        try:
            import ctypes
            from ctypes import wintypes
            
            class SHFILEOPSTRUCTW(ctypes.Structure):
                _fields_ = [
                    ("hwnd", wintypes.HWND),
                    ("wFunc", wintypes.UINT),
                    ("pFrom", wintypes.LPCWSTR),
                    ("pTo", wintypes.LPCWSTR),
                    ("fFlags", wintypes.WORD),
                    ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", ctypes.c_void_p),
                    ("lpszProgressTitle", wintypes.LPCWSTR),
                ]
                
            buffer = file_path + '\0\0'
            
            fop = SHFILEOPSTRUCTW()
            fop.wFunc = 0x0003  # FO_DELETE
            fop.pFrom = buffer
            fop.fFlags = 0x0040 | 0x0010 | 0x0400  # FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_NOERRORUI
            
            result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fop))
            if result == 0:
                return True
        except Exception:
            pass
            
    os.remove(file_path)
    return True


def group_chapter_parts(directory):
    """
    Scans the directory (non-recursively) and groups files ending with ', Part [digits].mp3'.
    Returns a dict: { base_chapter_name: [(part_number, full_path), ...] }
    """
    groups = {}
    pattern = re.compile(r"^(.*?),\s*Part\s+(\d+)\.mp3$", re.IGNORECASE)
    
    try:
        for entry in os.scandir(directory):
            if entry.is_file() and entry.name.lower().endswith('.mp3'):
                match = pattern.match(entry.name)
                if match:
                    base_name = match.group(1).strip()
                    part_num = int(match.group(2))
                    full_path = os.path.abspath(entry.path)
                    
                    if base_name not in groups:
                        groups[base_name] = []
                    groups[base_name].append((part_num, full_path))
    except OSError as e:
        print(f"Error scanning directory {directory}: {e}", file=sys.stderr)
        sys.exit(1)
        
    # Sort parts of each chapter group by part number
    for base in groups:
        groups[base].sort(key=lambda x: x[0])
        
    return groups


def validate_contiguous_sequence(parts):
    """Checks if the part numbers form a contiguous sequence starting exactly at 1."""
    part_nums = [p[0] for p in parts]
    expected = list(range(1, len(parts) + 1))
    return part_nums == expected


def merge_group(base_name, parts, target_dir, tolerance=0.2):
    """
    Concatenates an MP3 group using FFmpeg's stream-copy demuxer.
    Performs duration sum verification. Moves parts to the Recycle Bin upon success.
    
    Returns a tuple: (success: bool, output_path: str or None, warning_message: str or None)
    """
    output_filename = f"{base_name}.mp3"
    output_path = os.path.join(target_dir, output_filename)
    
    # Check if target output file already exists
    if os.path.exists(output_path):
        return False, None, f"Target file '{output_filename}' already exists. Skipping to prevent overwriting."
        
    # Compute sum of durations of all parts
    part_durations = []
    for _, path in parts:
        dur = get_audio_duration(path)
        if dur is None:
            return False, None, f"Failed to query audio duration for part: '{os.path.basename(path)}'"
        part_durations.append(dur)
    total_parts_dur = sum(part_durations)
    
    # Create FFmpeg concat demuxer list in a temporary file
    # Use absolute paths with forward slashes for clean Windows compatibility in FFmpeg
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_list:
            for _, path in parts:
                escaped_path = path.replace("\\", "/").replace("'", "'\\''")
                temp_list.write(f"file '{escaped_path}'\n")
            temp_list_path = temp_list.name
    except Exception as e:
        return False, None, f"Failed to create temporary demux list file: {e}"
        
    cmd = [
        'ffmpeg',
        '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', temp_list_path,
        '-c', 'copy',  # Stream-copy (lossless concatenation, no re-encoding)
        output_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        # Clean up temporary list file immediately
        try:
            os.remove(temp_list_path)
        except OSError:
            pass
            
        if result.returncode != 0:
            return False, None, f"FFmpeg concatenation failed: {result.stderr.strip()}"
            
        # Verify output file generated
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            return False, None, "Merged MP3 file was not generated or is empty."
            
        # Verify audio duration of merged file
        merged_dur = get_audio_duration(output_path)
        if merged_dur is None:
            # Delete generated file if we cannot verify it
            try:
                os.remove(output_path)
            except OSError:
                pass
            return False, None, "Failed to query audio duration of merged MP3 file."
            
        # Dynamic tolerance calculation: 0.1s base + 0.05s per joint to account for standard MP3 frame padding
        dynamic_tolerance = max(tolerance, 0.1 + 0.05 * (len(parts) - 1))
        diff = abs(total_parts_dur - merged_dur)
        if diff > dynamic_tolerance:
            # Duration mismatch: remove generated file and fail
            try:
                os.remove(output_path)
            except OSError:
                pass
            return False, None, f"Duration verification failed! Parts sum: {total_parts_dur:.3f}s, Merged: {merged_dur:.3f}s, Diff: {diff:.3f}s (Tolerance: {dynamic_tolerance:.3f}s)."
            
        # Deletion (Recycle) Phase: all parts validated, move them to the Recycle Bin!
        recycle_errors = []
        for _, path in parts:
            try:
                recycle_file(path)
            except Exception as e:
                recycle_errors.append(f"Failed to recycle '{os.path.basename(path)}': {e}")
                
        warning_msg = ", ".join(recycle_errors) if recycle_errors else None
        return True, output_path, warning_msg
        
    except Exception as e:
        # Cleanup temp list if still exists
        if os.path.exists(temp_list_path):
            try:
                os.remove(temp_list_path)
            except OSError:
                pass
        return False, None, f"Exception during merge: {e}"


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Merge segmented MP3 chapter parts into single files sequentially.")
    parser.add_argument("directory", help="The directory containing MP3 part files to merge.")
    parser.add_argument("--execute", "-x", action="store_true", help="Actually execute the merges and recycles (defaults to dry-run).")
    parser.add_argument("--tolerance", type=float, default=0.2, help="Cushion tolerance in seconds for duration validation (default: 0.2s).")
    parser.add_argument("--output", "-o", help="Optional path to write a JSON report of the execution.")
    
    args = parser.parse_args()
    
    target_dir = os.path.abspath(args.directory)
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        print(f"Error: Target directory '{target_dir}' does not exist or is not a directory.", file=sys.stderr)
        sys.exit(1)
        
    if not check_ffmpeg():
        print("Error: FFmpeg or FFprobe is not installed or not found on PATH.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Scanning directory: {target_dir}")
    print(f"Options: Non-Recursive, Tolerance={args.tolerance}s, Execute={args.execute}\n")
    
    groups = group_chapter_parts(target_dir)
    
    if not groups:
        print("No segmented MP3 chapter part files found in the directory. Nothing to merge.")
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
        sys.exit(0)
        
    valid_groups = {}
    invalid_groups = {}
    
    for base, parts in groups.items():
        if len(parts) < 2:
            # Skip if a part file has no partners to merge
            continue
        if validate_contiguous_sequence(parts):
            valid_groups[base] = parts
        else:
            invalid_groups[base] = parts
            
    if not valid_groups and not invalid_groups:
        print("No valid multipart chapter sequences found.")
        sys.exit(0)
        
    if invalid_groups:
        print("WARNING: Found chapter sequences with sequence gaps (will be skipped):")
        for base, parts in invalid_groups.items():
            found_parts = ", ".join(f"Part {p[0]}" for p in parts)
            print(f" - '{base}': Found parts [{found_parts}] (Missing parts in contiguous series)")
        print()
        
    if not valid_groups:
        print("No valid contiguous chapter sequences found for merging.")
        sys.exit(0)
        
    print(f"Found {len(valid_groups)} chapter group(s) planned for merging:")
    for base, parts in valid_groups.items():
        print(f" - '{base}': {len(parts)} parts -> '{base}.mp3'")
    print("-" * 80)
    
    if not args.execute:
        print("\n*** DRY RUN ONLY *** Run with --execute or -x to perform the actual merges and clean-ups.")
        if args.output:
            dry_run_data = [
                {
                    "chapter": base,
                    "parts_count": len(parts),
                    "target": os.path.join(target_dir, f"{base}.mp3"),
                    "status": "planned"
                } for base, parts in valid_groups.items()
            ]
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(dry_run_data, f, indent=2)
        sys.exit(0)
        
    print("\nStarting merges...")
    results = []
    success_count = 0
    failure_count = 0
    
    for idx, (base, parts) in enumerate(valid_groups.items(), 1):
        print(f"[{idx}/{len(valid_groups)}] Merging: '{base}' ({len(parts)} parts)... ", end="", flush=True)
        
        success, out_path, warning_msg = merge_group(base, parts, target_dir, tolerance=args.tolerance)
        
        if success:
            success_count += 1
            print("SUCCESS")
            if warning_msg:
                print(f"  Warning: {warning_msg}")
            results.append({
                "chapter": base,
                "success": True,
                "output_file": out_path,
                "parts_merged": len(parts),
                "error": warning_msg
            })
        else:
            failure_count += 1
            print("FAILED")
            print(f"  Error: {out_path or warning_msg or 'Unknown merge error'}", file=sys.stderr)
            results.append({
                "chapter": base,
                "success": False,
                "output_file": None,
                "parts_merged": len(parts),
                "error": out_path or warning_msg
            })
            
    print(f"\nMerging complete! Success: {success_count}, Failed: {failure_count}")
    
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            print(f"Results written to: {args.output}")
        except OSError as e:
            print(f"Error writing output to {args.output}: {e}", file=sys.stderr)
            
    if failure_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
