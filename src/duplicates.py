#!/usr/bin/env python3
"""
Duplicate File Detector for Dropbox Explorer.

Scans all .pkl session files in OUTPUT_DIR and identifies duplicate files
based on their content_hash metadata. Outputs a JSON report showing all
duplicate file groups and recoverable storage space.
"""

import argparse
import json
import os
import pickle
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.logger import configure_logging, get_logger

# Constants
DEFAULT_OUTPUT_DIR = "data"

# Initialize logger (will be configured in main)
logger = get_logger()


def human_readable_size(size_bytes: int) -> str:
    """
    Convert bytes to human-readable size string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string (e.g., "1.5 MB", "3.2 GB")

    Examples:
        >>> human_readable_size(1024)
        '1.00 KB'
        >>> human_readable_size(1048576)
        '1.00 MB'
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def extract_files_from_pkl(pkl_path: Path) -> list[dict[str, Any]]:
    """
    Extract file metadata from a .pkl session file.

    Args:
        pkl_path: Path to the .pkl file

    Returns:
        List of file metadata dictionaries containing path, content_hash,
        size, and source_pkl fields

    Raises:
        Exception: If the pickle file cannot be read or parsed
    """
    try:
        logger.debug(f"Reading session file: {pkl_path.name}")
        with open(pkl_path, "rb") as f:
            data = pickle.load(f)

        files = []

        # Handle the structure: data is a dict with metadata and items
        if isinstance(data, dict) and "all_items" in data:
            all_items = data["all_items"]
        elif isinstance(data, dict) and "items" in data:
            all_items = data["items"]
        else:
            # Assume it's a list of items
            all_items = data if isinstance(data, list) else []

        # Extract files from the items
        for item in all_items:
            if isinstance(item, dict):
                # Check if it's a file (has content_hash)
                if item.get("content_hash") and item.get("type") == "file":
                    files.append(
                        {
                            "path": item.get(
                                "path_display", item.get("path", "unknown")
                            ),
                            "content_hash": item["content_hash"],
                            "size": item.get("size", 0),
                            "source_pkl": pkl_path.name,
                        }
                    )

        logger.debug(f"Extracted {len(files)} files from {pkl_path.name}")
        return files

    except Exception as e:
        logger.warning(f"Failed to read {pkl_path.name}: {e}")
        return []


def find_duplicates(data_dir: str) -> dict[str, Any]:
    """
    Find duplicate files across all .pkl files in the data directory.

    Scans all .pkl session files in the specified directory and identifies
    files with identical content_hash values, indicating duplicate content.

    Args:
        data_dir: Directory containing .pkl files

    Returns:
        Dictionary containing duplicate file analysis with structure:
        {
            "summary": {
                "total_duplicate_files": int,
                "total_wasted_bytes": int,
                "total_wasted_size": str,
                "unique_hashes_with_duplicates": int,
                "scanned_pkl_files": int
            },
            "duplicate_groups": [...]
        }

    Raises:
        FileNotFoundError: If data directory doesn't exist or contains no .pkl files
    """
    data_path = Path(data_dir)

    if not data_path.exists():
        logger.error(f"Data directory not found: {data_dir}")
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    # Find all .pkl files
    pkl_files = list(data_path.glob("*.pkl"))

    if not pkl_files:
        logger.error(f"No .pkl files found in {data_dir}")
        raise FileNotFoundError(f"No .pkl files found in {data_dir}")

    logger.info(f"Scanning {len(pkl_files)} .pkl files in {data_dir}")

    # Hash -> list of file info
    hash_to_files = defaultdict(list)

    # Process each .pkl file
    for pkl_file in pkl_files:
        logger.info(f"Processing {pkl_file.name}")
        files = extract_files_from_pkl(pkl_file)

        for file_info in files:
            hash_to_files[file_info["content_hash"]].append(file_info)

    # Find duplicates (hashes with more than one file)
    duplicate_groups = []
    total_duplicate_files = 0
    total_wasted_bytes = 0

    logger.info("Analyzing duplicate groups")
    for content_hash, files in hash_to_files.items():
        if len(files) > 1:
            # This is a duplicate group
            file_size = files[0]["size"]  # All files with same hash have same size
            duplicate_count = len(files)
            wasted_bytes = file_size * (duplicate_count - 1)

            duplicate_groups.append(
                {
                    "content_hash": content_hash,
                    "duplicate_count": duplicate_count,
                    "file_size_bytes": file_size,
                    "file_size_human": human_readable_size(file_size),
                    "wasted_bytes": wasted_bytes,
                    "wasted_size_human": human_readable_size(wasted_bytes),
                    "file_paths": [f["path"] for f in files],
                }
            )

            total_duplicate_files += duplicate_count - 1  # Don't count the original
            total_wasted_bytes += wasted_bytes

    # Sort by wasted space (largest first)
    duplicate_groups.sort(key=lambda x: x["wasted_bytes"], reverse=True)

    logger.info(
        f"Found {len(duplicate_groups)} duplicate groups, "
        f"{total_duplicate_files} duplicate files, "
        f"{human_readable_size(total_wasted_bytes)} wasted space"
    )

    return {
        "summary": {
            "total_duplicate_files": total_duplicate_files,
            "total_wasted_bytes": total_wasted_bytes,
            "total_wasted_size": human_readable_size(total_wasted_bytes),
            "unique_hashes_with_duplicates": len(duplicate_groups),
            "scanned_pkl_files": len(pkl_files),
        },
        "duplicate_groups": duplicate_groups,
    }


def main() -> None:
    """
    Main entry point for the duplicate detector.

    Configures logging, parses command-line arguments, scans session files,
    and outputs duplicate file analysis in JSON format.
    """
    parser = argparse.ArgumentParser(
        description="Find duplicate files in Dropbox Explorer session files"
    )
    parser.add_argument(
        "-d",
        "--data-dir",
        help=f"Directory containing .pkl files (default: OUTPUT_DIR env or '{DEFAULT_OUTPUT_DIR}')",
        default=None,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output JSON file path (default: print to stdout)",
        default=None,
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    parser.add_argument(
        "--log-level-console",
        default=None,
        help="Console log level (NONE, DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    parser.add_argument(
        "--log-level-file",
        default=None,
        help="File log level (NONE, DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    args = parser.parse_args()

    # Configure logging
    console_level = (
        args.log_level_console or os.getenv("LOG_LEVEL_CONSOLE", "INFO")
    ).upper()
    file_level = (args.log_level_file or os.getenv("LOG_LEVEL_FILE", "DEBUG")).upper()

    configure_logging(console_level=console_level, file_level=file_level)

    # Determine data directory
    data_dir = args.data_dir or os.getenv("OUTPUT_DIR", DEFAULT_OUTPUT_DIR)

    logger.info(f"Starting duplicate file analysis in: {data_dir}")

    try:
        # Find duplicates
        result = find_duplicates(data_dir)

        # Print summary to console
        summary = result["summary"]
        print(f"\n{'=' * 60}")
        print("DUPLICATE FILE ANALYSIS SUMMARY")
        print(f"{'=' * 60}")
        print(f"Scanned PKL files:        {summary['scanned_pkl_files']}")
        print(f"Unique duplicate groups:  {summary['unique_hashes_with_duplicates']}")
        print(f"Total duplicate files:    {summary['total_duplicate_files']}")
        print(
            f"Total wasted space:       {summary['total_wasted_size']} ({summary['total_wasted_bytes']:,} bytes)"
        )
        print(f"{'=' * 60}\n")

        # Output JSON
        json_indent = 2 if args.pretty else None
        json_output = json.dumps(result, indent=json_indent)

        if args.output:
            output_path = Path(args.output)
            output_path.write_text(json_output, encoding="utf-8")
            logger.info(f"Results written to: {args.output}")
            print(f"Results written to: {args.output}")
        else:
            print(json_output)

        logger.info("Duplicate analysis completed successfully")

    except Exception as e:
        logger.error(f"Failed to complete duplicate analysis: {e}")
        raise


if __name__ == "__main__":
    main()
