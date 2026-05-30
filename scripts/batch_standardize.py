#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Batch script to run filename standardization across all Book 1 to 7 directories.
Supports dry-run preview by default and actual execution with --execute or -x.
"""

import os
import sys
import subprocess
import argparse


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Batch standardize chapter names across all audiobook folders.")
    parser.add_argument("--execute", "-x", action="store_true", help="Actually execute the renames (defaults to dry-run).")
    
    args = parser.parse_args()
    
    base_dir = r"c:\Users\abrah\OneDrive\Music\My Media\J. K. Rowling performance by Jim Dale"
    if not os.path.exists(base_dir):
        print(f"Error: Base directory '{base_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)
        
    # Get all Book directories
    try:
        book_dirs = sorted([
            d for d in os.listdir(base_dir) 
            if os.path.isdir(os.path.join(base_dir, d)) and d.lower().startswith("book ")
        ])
    except OSError as e:
        print(f"Error listing base directory: {e}", file=sys.stderr)
        sys.exit(1)
        
    if not book_dirs:
        print("No Book directories found in the base path.")
        sys.exit(0)
        
    print(f"Starting batch filename standardization in: {base_dir}")
    print(f"Execute renames: {args.execute}\n")
    
    for book in book_dirs:
        book_path = os.path.join(base_dir, book)
        print("=" * 80)
        print(f"PROCESSING: {book}")
        print("=" * 80)
        
        cmd = ["python", "scripts/standardize_filenames.py", book_path]
        if args.execute:
            cmd.append("--execute")
            
        # Run standardizer script as a subprocess
        subprocess.run(cmd, text=True)
        print()
        
    print("=" * 80)
    print("Batch processing job complete!")


if __name__ == "__main__":
    main()
