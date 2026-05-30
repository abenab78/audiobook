#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utility script to standardize chapter and introduction filenames:
- Pads single-digit chapter numbers (e.g., Chapter 1 -> Chapter 01).
- Prepends "00 - " to Introduction files.
- Strictly non-recursive, case-insensitive, and supports dry-run preview by default.
"""

import os
import re
import sys
import argparse
import json


def get_standardized_name(filename):
    """
    Checks if a filename matches our standardization criteria:
    - Chapter X -> Chapter 0X (where X is a single digit)
    - Introduction -> 00 - Introduction (case-insensitive)
    
    Returns the new filename string if it needs renaming, or None if it doesn't.
    """
    # 1. Check for single-digit Chapter padding
    chapter_match = re.match(r"^(Chapter)\s+(\d+)(.*)$", filename, re.IGNORECASE)
    if chapter_match:
        prefix = chapter_match.group(1)  # preserves 'Chapter' or 'chapter' casing
        num_str = chapter_match.group(2)
        rest = chapter_match.group(3)
        
        if len(num_str) == 1:
            return f"{prefix} 0{num_str}{rest}"
            
    # 2. Check for Introduction prepending
    if filename.lower().startswith("introduction"):
        return f"00 - {filename}"
        
    return None


def main():
    # Force UTF-8 encoding for standard output and error to prevent Windows encoding exceptions
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Standardize chapter and introduction filenames in a directory.")
    parser.add_argument("directory", help="The directory containing the files to standardize.")
    parser.add_argument("--execute", "-x", action="store_true", help="Actually execute the renames (defaults to dry-run preview).")
    parser.add_argument("--output", "-o", help="Optional path to write a JSON report of the execution.")
    
    args = parser.parse_args()
    
    target_dir = os.path.abspath(args.directory)
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        print(f"Error: Target directory '{target_dir}' does not exist or is not a directory.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Scanning directory: {target_dir}")
    print(f"Options: Non-Recursive, Execute={args.execute}\n")
    
    # Scan the folder non-recursively for files
    try:
        entries = sorted([e.name for e in os.scandir(target_dir) if e.is_file()])
    except OSError as e:
        print(f"Error scanning directory {target_dir}: {e}", file=sys.stderr)
        sys.exit(1)
        
    planned_renames = []
    
    for filename in entries:
        new_name = get_standardized_name(filename)
        if new_name:
            source_path = os.path.join(target_dir, filename)
            target_path = os.path.join(target_dir, new_name)
            planned_renames.append({
                "original": filename,
                "proposed": new_name,
                "source_path": source_path,
                "target_path": target_path
            })
            
    if not planned_renames:
        print("No files found requiring standardization.")
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
        sys.exit(0)
        
    print(f"Found {len(planned_renames)} file(s) that require standardization:")
    print(f"{'ORIGINAL FILENAME':<50} | {'PROPOSED FILENAME':<50} | {'STATUS':<20}")
    print("-" * 126)
    
    results = []
    success_count = 0
    failure_count = 0
    
    for item in planned_renames:
        orig = item["original"]
        prop = item["proposed"]
        src = item["source_path"]
        tgt = item["target_path"]
        
        if os.path.exists(tgt):
            # Target collision check
            status = "COLLISION (Skipped)"
            print(f"{orig:<50} | {prop:<50} | {status:<20}")
            results.append({
                "original": orig,
                "proposed": prop,
                "success": False,
                "status": "collision"
            })
            failure_count += 1
        elif not args.execute:
            status = "Dry-Run (Planned)"
            print(f"{orig:<50} | {prop:<50} | {status:<20}")
            results.append({
                "original": orig,
                "proposed": prop,
                "success": True,
                "status": "planned"
            })
        else:
            # Execute rename
            try:
                os.rename(src, tgt)
                status = "SUCCESS"
                print(f"{orig:<50} | {prop:<50} | {status:<20}")
                results.append({
                    "original": orig,
                    "proposed": prop,
                    "success": True,
                    "status": "renamed"
                })
                success_count += 1
            except Exception as e:
                status = f"FAILED: {e}"
                print(f"{orig:<50} | {prop:<50} | {status:<20}", file=sys.stderr)
                results.append({
                    "original": orig,
                    "proposed": prop,
                    "success": False,
                    "status": f"failed: {e}"
                })
                failure_count += 1
                
    print("-" * 126)
    if args.execute:
        print(f"Standardization complete! Success: {success_count}, Failed/Skipped: {failure_count}")
    else:
        print("*** DRY RUN ONLY *** Run with --execute or -x to execute the actual renames.")
        
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            print(f"Results report written to: {args.output}")
        except OSError as e:
            print(f"Error writing report to {args.output}: {e}", file=sys.stderr)
            
    if failure_count > 0 and args.execute:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
