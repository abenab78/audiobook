#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utility script to clean filenames and directory names.
Removes special characters (smart quotes, curly apostrophes, straight quotes, commas)
and normalizes spacing and dashes according to user specifications.
"""

import os
import re
import sys
import argparse
import json


def clean_name(name):
    """
    Cleans a single filename or directory name based on user specifications:
    1. Replaces en/em/curly dashes with regular dash (-).
    2. Removes smart quotes (“ ”), curly apostrophes (’ ‘), and straight quotes (" ').
    3. Collapses multiple spaces in a row into a single space.
    4. Strips leading and trailing spaces.
    """
    # Replace en-dash (\u2013), em-dash (\u2014), hyphen-dash (\u2010), or horizontal bar (\u2015) with a regular hyphen
    cleaned = re.sub(r'[\u2010\u2013\u2014\u2015]', '-', name)
    
    # Characters to remove completely
    chars_to_remove = ['“', '”', '’', '‘', '"', "'"]
    for char in chars_to_remove:
        cleaned = cleaned.replace(char, '')
        
    # Collapse multiple consecutive whitespace characters (spaces, tabs, etc.) into a single space
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Strip leading/trailing spaces
    cleaned = cleaned.strip()
    
    return cleaned


def plan_renames(root_dir, recursive=False, rename_dirs=False):
    """
    Traverses the directory structure and plans renames.
    Uses bottom-up traversal to ensure deep files and directories are processed
    before their parent directories are renamed.
    
    Returns a list of dicts detailing the planned changes:
    [
        {
            "type": "file"|"directory",
            "original_path": "...",
            "original_name": "...",
            "new_name": "...",
            "new_path": "...",
            "changed": True|False
        },
        ...
    ]
    """
    planned_changes = []
    
    # We maintain a mapping of the directory path updates during the planning process
    # so we know the new paths of nested files if parent directories are planned to be renamed.
    dir_path_mapping = {}

    def get_current_parent_path(original_parent_path):
        """Resolves the new parent path if any ancestor directory was renamed in this plan."""
        parts = []
        curr = os.path.abspath(original_parent_path)
        while True:
            if curr in dir_path_mapping:
                # Reconstruct path using the renamed segments
                new_path = dir_path_mapping[curr]
                for p in reversed(parts):
                    new_path = os.path.join(new_path, p)
                return new_path
            
            parent, child = os.path.split(curr)
            if not child: # reached root
                break
            parts.append(child)
            curr = parent
            
        return original_parent_path

    if recursive:
        # bottom-up walk is critical to rename contents of a dir before the dir itself
        walk_generator = os.walk(root_dir, topdown=False)
    else:
        # For non-recursive, we just read the immediate contents of root_dir
        try:
            items = os.listdir(root_dir)
            files = [item for item in items if os.path.isfile(os.path.join(root_dir, item))]
            dirs = [item for item in items if os.path.isdir(os.path.join(root_dir, item))]
            walk_generator = [(root_dir, dirs, files)]
        except OSError as e:
            print(f"Error reading directory {root_dir}: {e}", file=sys.stderr)
            sys.exit(1)

    for dirpath, dirnames, filenames in walk_generator:
        # 1. Plan file renames in the current directory
        # Track existing file names in target folder (case-insensitive for Windows) to avoid collisions
        existing_files = set()
        for f in filenames:
            existing_files.add(f.lower())

        for filename in filenames:
            original_file_path = os.path.join(dirpath, filename)
            
            # Split extension to only clean the base name
            base, ext = os.path.splitext(filename)
            cleaned_base = clean_name(base)
            
            # Reconstruct and handle collisions
            if cleaned_base != base:
                # Check for collision
                new_filename = f"{cleaned_base}{ext}"
                if new_filename.lower() in existing_files and new_filename.lower() != filename.lower():
                    # Resolve collision by adding a suffix
                    counter = 1
                    while True:
                        candidate = f"{cleaned_base}_{counter}{ext}"
                        if candidate.lower() not in existing_files:
                            new_filename = candidate
                            break
                        counter += 1
                
                # Update existing files set
                existing_files.discard(filename.lower())
                existing_files.add(new_filename.lower())
                
                # Resolve the parent path (in case directory itself is changing)
                resolved_parent = get_current_parent_path(dirpath)
                
                planned_changes.append({
                    "type": "file",
                    "original_path": original_file_path,
                    "original_name": filename,
                    "new_name": new_filename,
                    "new_path": os.path.join(resolved_parent, new_filename),
                    "changed": True
                })
            else:
                planned_changes.append({
                    "type": "file",
                    "original_path": original_file_path,
                    "original_name": filename,
                    "new_name": filename,
                    "new_path": os.path.join(get_current_parent_path(dirpath), filename),
                    "changed": False
                })

        # 2. Plan directory renames
        if rename_dirs:
            existing_dirs = set(d.lower() for d in dirnames)
            
            for dirname in dirnames:
                original_dir_path = os.path.join(dirpath, dirname)
                cleaned_dirname = clean_name(dirname)
                
                if cleaned_dirname != dirname:
                    new_dirname = cleaned_dirname
                    if new_dirname.lower() in existing_dirs and new_dirname.lower() != dirname.lower():
                        counter = 1
                        while True:
                            candidate = f"{cleaned_dirname}_{counter}"
                            if candidate.lower() not in existing_dirs:
                                new_dirname = candidate
                                break
                            counter += 1
                            
                    existing_dirs.discard(dirname.lower())
                    existing_dirs.add(new_dirname.lower())
                    
                    resolved_parent = get_current_parent_path(dirpath)
                    new_dir_path = os.path.join(resolved_parent, new_dirname)
                    
                    # Record the mapping of original to new path for nested elements
                    dir_path_mapping[original_dir_path] = new_dir_path
                    
                    planned_changes.append({
                        "type": "directory",
                        "original_path": original_dir_path,
                        "original_name": dirname,
                        "new_name": new_dirname,
                        "new_path": new_dir_path,
                        "changed": True
                    })
                else:
                    resolved_parent = get_current_parent_path(dirpath)
                    new_dir_path = os.path.join(resolved_parent, dirname)
                    dir_path_mapping[original_dir_path] = new_dir_path
                    
                    planned_changes.append({
                        "type": "directory",
                        "original_path": original_dir_path,
                        "original_name": dirname,
                        "new_name": dirname,
                        "new_path": new_dir_path,
                        "changed": False
                    })
                    
    return planned_changes


def execute_renames(planned_changes):
    """
    Executes the planned renames on the filesystem.
    Returns a summary list of successful changes.
    """
    results = []
    
    # We filter only the items that actually changed
    to_rename = [item for item in planned_changes if item["changed"]]
    
    for item in to_rename:
        orig = item["original_path"]
        target = item["new_path"]
        
        # Ensure target parent directory exists before renaming
        target_parent = os.path.dirname(target)
        if not os.path.exists(target_parent):
            try:
                os.makedirs(target_parent, exist_ok=True)
            except OSError as e:
                print(f"Error creating directory {target_parent}: {e}", file=sys.stderr)
                item["error"] = f"Failed to create parent directory: {e}"
                item["success"] = False
                results.append(item)
                continue
                
        try:
            os.rename(orig, target)
            item["success"] = True
            print(f"Renamed: '{orig}' -> '{target}'")
        except OSError as e:
            print(f"Error renaming '{orig}' to '{target}': {e}", file=sys.stderr)
            item["success"] = False
            item["error"] = str(e)
            
        results.append(item)
        
    return results


def main():
    # Force UTF-8 encoding for standard output and error to prevent Windows encoding exceptions
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Clean filenames by removing special characters.")
    parser.add_argument("directory", help="The path to the folder containing files to clean.")
    parser.add_argument("--recursive", "-r", action="store_true", help="Traverse subdirectories recursively.")
    parser.add_argument("--rename-dirs", "-d", action="store_true", help="Also rename directories that have special characters.")
    parser.add_argument("--execute", "-x", action="store_true", help="Actually rename files (without this flag, it does a dry-run).")
    parser.add_argument("--output", "-o", help="Path to write the results as a JSON file.")
    
    args = parser.parse_args()
    
    target_dir = os.path.abspath(args.directory)
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        print(f"Error: Target directory '{target_dir}' does not exist or is not a directory.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Scanning: {target_dir}")
    print(f"Options: Recursive={args.recursive}, Rename Directories={args.rename_dirs}, Execute={args.execute}\n")
    
    planned = plan_renames(target_dir, recursive=args.recursive, rename_dirs=args.rename_dirs)
    
    changed_items = [item for item in planned if item["changed"]]
    
    if not changed_items:
        print("All filenames and directory names are already clean. No changes needed.")
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
        sys.exit(0)
        
    # Print preview
    print("Planned changes:")
    print(f"{'TYPE':<12} | {'ORIGINAL NAME':<50} | {'CLEANED NAME':<50}")
    print("-" * 120)
    for item in changed_items:
        orig_name = item["original_name"]
        new_name = item["new_name"]
        # Truncate for display if extremely long
        if len(orig_name) > 47:
            orig_name = orig_name[:44] + "..."
        if len(new_name) > 47:
            new_name = new_name[:44] + "..."
        print(f"{item['type'].upper():<12} | {orig_name:<50} | {new_name:<50}")
        
    print("-" * 120)
    print(f"Total items to change: {len(changed_items)}")
    
    execution_results = []
    if args.execute:
        print("\nApplying changes...")
        execution_results = execute_renames(planned)
        print("\nAll changes applied successfully!")
    else:
        print("\n*** DRY RUN ONLY *** Run with --execute or -x to apply these changes.")
        
    if args.output:
        output_data = execution_results if args.execute else changed_items
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2)
            print(f"\nResults written to: {args.output}")
        except OSError as e:
            print(f"Error writing output to {args.output}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
