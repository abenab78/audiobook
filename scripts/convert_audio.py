#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utility script to convert .wav files in a folder to 128kbps constant bitrate .mp3 files.
Does not recurse into subdirectories, runs sequentially, and supports dry-runs.
"""

import os
import sys
import argparse
import subprocess
import json


def check_ffmpeg():
    """
    Checks if ffmpeg is installed and available in the system PATH.
    Returns True if available, False otherwise.
    """
    try:
        # Run ffmpeg -version with a short timeout to check availability
        subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
        return True
    except (SubprocessError, FileNotFoundError, OSError):
        return False


def get_wav_files(directory):
    """
    Scans the immediate directory (non-recursively) for files ending in .wav.
    Returns a sorted list of absolute file paths.
    """
    wav_files = []
    try:
        for entry in os.scandir(directory):
            if entry.is_file() and entry.name.lower().endswith('.wav'):
                wav_files.append(os.path.abspath(entry.path))
    except OSError as e:
        print(f"Error scanning directory {directory}: {e}", file=sys.stderr)
        sys.exit(1)
        
    return sorted(wav_files)


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
                
            # Double-null termination is critical for SHFileOperationW
            buffer = file_path + '\0\0'
            
            fop = SHFILEOPSTRUCTW()
            fop.wFunc = 0x0003  # FO_DELETE
            fop.pFrom = buffer
            # FOF_ALLOWUNDO = 0x0040 (send to recycle bin)
            # FOF_NOCONFIRMATION = 0x0010 (suppress confirmation dialog)
            # FOF_NOERRORUI = 0x0400 (suppress error dialogs)
            fop.fFlags = 0x0040 | 0x0010 | 0x0400
            
            result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fop))
            if result == 0:
                return True
        except Exception:
            pass # Fallback to os.remove
            
    os.remove(file_path)
    return True


def get_audio_duration(filepath):
    """
    Queries the duration of an audio file using ffprobe.
    Returns the duration as a float in seconds, or None if ffprobe fails.
    """
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


def convert_file(wav_path, bitrate='128k', delete_original=False):
    """
    Converts a single WAV file to MP3 at the specified constant bitrate.
    Optionally deletes (recycles) the original WAV file upon successful completion,
    but only after verifying that the WAV and MP3 durations match.
    
    Returns a tuple: (success: bool, mp3_path: str or None, error_message: str or None)
    """
    base_dir, wav_filename = os.path.split(wav_path)
    base_name, _ = os.path.splitext(wav_filename)
    mp3_filename = f"{base_name}.mp3"
    mp3_path = os.path.join(base_dir, mp3_filename)
    
    cmd = [
        'ffmpeg',
        '-y',               # Overwrite existing output files
        '-i', wav_path,     # Input file
        '-codec:a', 'libmp3lame',
        '-b:a', bitrate,    # Constant Bitrate (CBR)
        mp3_path
    ]
    
    try:
        # Run conversion in a subprocess
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        if result.returncode != 0:
            return False, None, f"FFmpeg error (code {result.returncode}): {result.stderr.strip()}"
            
        # Post-conversion validation: check if the MP3 file was created and is non-empty
        if not os.path.exists(mp3_path) or os.path.getsize(mp3_path) == 0:
            return False, None, "MP3 file was not generated or is empty."
            
        # Optional: delete (recycle) the original WAV file after duration verification
        if delete_original:
            wav_dur = get_audio_duration(wav_path)
            mp3_dur = get_audio_duration(mp3_path)
            
            if wav_dur is None or mp3_dur is None:
                return True, mp3_path, "Conversion succeeded, but could not verify audio lengths. WAV file preserved."
                
            # Compare durations with a 0.1-second tolerance (standard MP3 padding cushion)
            if abs(wav_dur - mp3_dur) > 0.1:
                return True, mp3_path, f"Conversion succeeded, but audio lengths differ (WAV: {wav_dur:.3f}s, MP3: {mp3_dur:.3f}s). WAV file preserved."
                
            try:
                recycle_file(wav_path)
            except OSError as e:
                return True, mp3_path, f"Conversion succeeded, but failed to recycle original WAV: {e}"
                
        return True, mp3_path, None
        
    except Exception as e:
        return False, None, f"Exception during conversion: {e}"


def main():
    # Force UTF-8 encoding for standard output and error to prevent Windows encoding exceptions
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Convert WAV files to 128kbps constant bitrate MP3 files (non-recursive).")
    parser.add_argument("directory", help="The directory containing WAV files to convert.")
    parser.add_argument("--execute", "-x", action="store_true", help="Actually execute the conversions (defaults to dry-run preview).")
    parser.add_argument("--delete-original", "-d", action="store_true", help="Delete the original WAV file after successful conversion.")
    parser.add_argument("--bitrate", default="128k", help="Constant bitrate for MP3 files (default: 128k).")
    parser.add_argument("--output", "-o", help="Optional path to write a JSON report of the execution.")
    
    args = parser.parse_args()
    
    # 1. Validate Target Directory
    target_dir = os.path.abspath(args.directory)
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        print(f"Error: Target directory '{target_dir}' does not exist or is not a directory.", file=sys.stderr)
        sys.exit(1)
        
    # 2. Check for FFmpeg dependency
    if not check_ffmpeg():
        print("Error: FFmpeg is not installed or not found on the system PATH.", file=sys.stderr)
        print("Please install FFmpeg and add it to your system PATH to run this utility.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Scanning directory: {target_dir}")
    print(f"Options: Non-Recursive, Bitrate={args.bitrate}, Delete Original={args.delete_original}, Execute={args.execute}\n")
    
    # 3. Find target WAV files
    wav_files = get_wav_files(target_dir)
    
    if not wav_files:
        print("No .wav files found in the directory. Nothing to convert.")
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
        sys.exit(0)
        
    print(f"Found {len(wav_files)} WAV file(s) planned for conversion:")
    print(f"{'SOURCE FILE':<70} | {'PROPOSED OUTPUT':<30}")
    print("-" * 105)
    for wav_path in wav_files:
        base_dir, filename = os.path.split(wav_path)
        base_name, _ = os.path.splitext(filename)
        proposed_mp3 = f"{base_name}.mp3"
        
        # Display relative paths if possible for cleaner look
        rel_wav = os.path.relpath(wav_path, target_dir)
        print(f"{rel_wav:<70} | {proposed_mp3:<30}")
    print("-" * 105)
    
    if not args.execute:
        print("\n*** DRY RUN ONLY *** Run with --execute or -x to perform the actual conversion.")
        if args.output:
            dry_run_data = [
                {
                    "source": p,
                    "target": os.path.join(os.path.dirname(p), f"{os.path.splitext(os.path.basename(p))[0]}.mp3"),
                    "status": "planned"
                } for p in wav_files
            ]
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(dry_run_data, f, indent=2)
        sys.exit(0)
        
    # 4. Perform sequential conversion
    print("\nStarting conversion...")
    results = []
    success_count = 0
    failure_count = 0
    
    for idx, wav_path in enumerate(wav_files, 1):
        filename = os.path.basename(wav_path)
        print(f"[{idx}/{len(wav_files)}] Converting: '{filename}'... ", end="", flush=True)
        
        success, mp3_path, error_msg = convert_file(
            wav_path,
            bitrate=args.bitrate,
            delete_original=args.delete_original
        )
        
        if success:
            success_count += 1
            print("SUCCESS")
            if error_msg: # Warning logged during success (e.g. source delete failed)
                print(f"  Warning: {error_msg}")
            results.append({
                "source": wav_path,
                "target": mp3_path,
                "success": True,
                "error": error_msg
            })
        else:
            failure_count += 1
            print("FAILED")
            print(f"  Error: {error_msg}", file=sys.stderr)
            results.append({
                "source": wav_path,
                "target": None,
                "success": False,
                "error": error_msg
            })
            
    print(f"\nConversion complete! Success: {success_count}, Failed: {failure_count}")
    
    # 5. Write execution report
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            print(f"Results written to: {args.output}")
        except OSError as e:
            print(f"Error writing output to {args.output}: {e}", file=sys.stderr)
            
    # Exit with code 1 if any files failed to convert
    if failure_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
