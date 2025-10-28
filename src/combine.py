#!/usr/bin/env python3
"""
JSON File Combiner for Dropbox Explorer.

Merges all JSON files in OUTPUT_DIR into a single all.json file.
Removes duplicate files based on content_hash, keeping only the file
at the shallowest path depth (closest to root).
"""

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.logger import configure_logging, get_logger

# Constants
DEFAULT_OUTPUT_DIR = "data"
DEFAULT_OUTPUT_FILE = "all.json"

# Initialize logger (will be configured in main)
logger = get_logger()


def calculate_path_depth(path: str) -> int:
    """
    Calculate the depth of a path (number of directory levels).

    Args:
        path: File path (e.g., "/folder1/folder2/file.txt")

    Returns:
        Depth as integer (number of path separators)

    Examples:
        >>> calculate_path_depth("/file.txt")
        1
        >>> calculate_path_depth("/folder/file.txt")
        2
        >>> calculate_path_depth("/a/b/c/file.txt")
        4
    """
    # Remove leading/trailing slashes and count remaining slashes + 1
    path = path.strip("/")
    if not path:
        return 0
    return path.count("/") + 1


def extract_files_from_json(
    json_data: dict[str, Any], source_file: str
) -> list[dict[str, Any]]:
    """
    Recursively extract all files from JSON data structure.

    Args:
        json_data: Parsed JSON data containing nested file/folder structure
        source_file: Name of the source JSON file

    Returns:
        List of file dictionaries with metadata including path, content_hash,
        size, depth, and source_file

    Examples:
        Files are extracted from nested "children" arrays and include:
        - path_display: Full file path
        - content_hash: Unique content identifier
        - size: File size in bytes
        - depth: Path depth (for duplicate resolution)
        - source_file: Origin JSON file
    """
    files = []

    def recurse_items(obj: Any, current_depth: int = 0) -> None:
        """Recursively traverse JSON structure to find files."""
        if isinstance(obj, dict):
            # Check if this is a file entry
            if obj.get("type") == "file":
                path = obj.get("path_display", obj.get("path", ""))
                content_hash = obj.get("content_hash")

                # Only include files with valid hash and path
                if content_hash and path:
                    # Calculate actual depth from path
                    depth = calculate_path_depth(path)

                    files.append(
                        {
                            "path_display": path,
                            "path_lower": obj.get("path_lower", path.lower()),
                            "content_hash": content_hash,
                            "size": obj.get("size", 0),
                            "name": obj.get("name", Path(path).name),
                            "id": obj.get("id", ""),
                            "depth": depth,
                            "source_file": source_file,
                        }
                    )

            # Recurse into children
            if "children" in obj and isinstance(obj["children"], list):
                for child in obj["children"]:
                    recurse_items(child, current_depth + 1)

        elif isinstance(obj, list):
            # Process list items
            for item in obj:
                recurse_items(item, current_depth)

    # Start recursion from contents or root
    if "contents" in json_data:
        recurse_items(json_data["contents"])
    else:
        recurse_items(json_data)

    logger.debug(f"Extracted {len(files)} files from {source_file}")
    return files


def remove_duplicates(
    files: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Remove duplicate files based on content_hash.

    When duplicates are found, keeps the file at the shallowest path depth
    (closest to root directory). Files without content_hash are kept.

    Args:
        files: List of file dictionaries with content_hash and depth

    Returns:
        Tuple of (unique_files, duplicate_report) where:
        - unique_files: List of deduplicated files
        - duplicate_report: Statistics about removed duplicates

    Algorithm:
        1. Group files by content_hash
        2. For each group with multiple files:
           - Sort by depth (ascending) then path (lexicographic)
           - Keep the first file (shallowest path)
           - Mark others as duplicates
    """
    # Group files by content_hash
    hash_to_files = defaultdict(list)

    for file_info in files:
        content_hash = file_info.get("content_hash")
        if content_hash:
            hash_to_files[content_hash].append(file_info)

    # Track statistics
    unique_files = []
    removed_files = []
    total_duplicate_files = 0
    total_wasted_bytes = 0

    logger.info(f"Analyzing {len(hash_to_files)} unique content hashes")

    for content_hash, file_group in hash_to_files.items():
        if len(file_group) == 1:
            # No duplicates, keep the file
            unique_files.append(file_group[0])
        else:
            # Multiple files with same hash - keep shallowest
            # Sort by depth first, then by path for deterministic results
            sorted_files = sorted(
                file_group, key=lambda f: (f["depth"], f["path_display"])
            )

            # Keep the first (shallowest) file
            keeper = sorted_files[0]
            unique_files.append(keeper)

            # Mark the rest as duplicates
            duplicates = sorted_files[1:]
            removed_files.extend(duplicates)

            # Calculate wasted space
            file_size = keeper["size"]
            duplicate_count = len(duplicates)
            wasted_bytes = file_size * duplicate_count

            total_duplicate_files += duplicate_count
            total_wasted_bytes += wasted_bytes

            logger.debug(
                f"Hash {content_hash[:16]}...: keeping {keeper['path_display']} "
                f"(depth {keeper['depth']}), removing {duplicate_count} duplicates"
            )

    logger.info(
        f"Removed {total_duplicate_files} duplicate files, "
        f"saving {human_readable_size(total_wasted_bytes)}"
    )

    duplicate_report = {
        "total_duplicate_files": total_duplicate_files,
        "total_wasted_bytes": total_wasted_bytes,
        "total_wasted_size": human_readable_size(total_wasted_bytes),
        "unique_hashes_with_duplicates": sum(
            1 for files in hash_to_files.values() if len(files) > 1
        ),
        "removed_files": [
            {
                "path": f["path_display"],
                "content_hash": f["content_hash"],
                "depth": f["depth"],
                "size": f["size"],
                "source_file": f["source_file"],
            }
            for f in removed_files
        ],
    }

    return unique_files, duplicate_report


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


def combine_json_files(data_dir: str, output_file: str) -> tuple[str, dict[str, Any]]:
    """
    Combine all JSON files in data directory into a single file.

    Merges all .json files in the specified directory, removes duplicates
    based on content_hash (keeping files at shallowest path depth), and
    writes the result to output_file.

    Args:
        data_dir: Directory containing JSON files
        output_file: Output file path for combined JSON

    Returns:
        Tuple of (output_path, statistics) where statistics contains:
        - source_files: Number of JSON files processed
        - total_files_before: Total files before deduplication
        - total_files_after: Total files after deduplication
        - total_size: Total size of unique files
        - duplicate_report: Details about removed duplicates

    Raises:
        FileNotFoundError: If data directory doesn't exist or contains no JSON files
        ValueError: If JSON files cannot be parsed
    """
    data_path = Path(data_dir)

    if not data_path.exists():
        logger.error(f"Data directory not found: {data_dir}")
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    # Find all .json files
    json_files = list(data_path.glob("*.json"))

    if not json_files:
        logger.error(f"No .json files found in {data_dir}")
        raise FileNotFoundError(f"No .json files found in {data_dir}")

    logger.info(f"Found {len(json_files)} JSON files in {data_dir}")

    # Extract all files from all JSON files
    all_files = []
    source_file_stats = {}

    for json_file in json_files:
        logger.info(f"Processing {json_file.name}")
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            files = extract_files_from_json(json_data, json_file.name)
            all_files.extend(files)

            # Track source file stats
            source_file_stats[json_file.name] = {
                "file_count": len(files),
                "total_size": sum(f["size"] for f in files),
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse {json_file.name}: {e}")
            raise ValueError(f"Invalid JSON in {json_file.name}: {e}")
        except Exception as e:
            logger.error(f"Error processing {json_file.name}: {e}")
            raise

    logger.info(f"Extracted {len(all_files)} total files from all sources")

    # Remove duplicates
    unique_files, duplicate_report = remove_duplicates(all_files)

    # Calculate statistics
    total_size = sum(f["size"] for f in unique_files)

    statistics = {
        "source_files": len(json_files),
        "source_file_stats": source_file_stats,
        "total_files_before": len(all_files),
        "total_files_after": len(unique_files),
        "total_size_bytes": total_size,
        "total_size": human_readable_size(total_size),
        "duplicate_report": duplicate_report,
    }

    # Create output structure
    output_data = {
        "metadata": {
            "description": "Combined file listing from all JSON sources",
            "source_files": [f.name for f in json_files],
            "statistics": statistics,
        },
        "files": unique_files,
    }

    # Write output file
    output_path = Path(data_dir) / output_file
    logger.info(f"Writing combined data to {output_path}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    logger.success(f"Successfully created {output_file}")
    return str(output_path), statistics


def main() -> None:
    """
    Main entry point for the JSON combiner.

    Configures logging, parses command-line arguments, combines JSON files,
    and outputs statistics about the merge and deduplication process.
    """
    parser = argparse.ArgumentParser(
        description="Combine all JSON files and remove duplicates"
    )
    parser.add_argument(
        "-d",
        "--data-dir",
        help=f"Directory containing JSON files (default: OUTPUT_DIR env or '{DEFAULT_OUTPUT_DIR}')",
        default=None,
    )
    parser.add_argument(
        "-o",
        "--output",
        help=f"Output filename (default: '{DEFAULT_OUTPUT_FILE}')",
        default=DEFAULT_OUTPUT_FILE,
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

    logger.info(f"Starting JSON file combination in: {data_dir}")

    try:
        # Combine JSON files
        output_path, statistics = combine_json_files(data_dir, args.output)

        # Print summary
        print(f"\n{'=' * 70}")
        print("JSON COMBINATION SUMMARY")
        print(f"{'=' * 70}")
        print(f"Source files processed:   {statistics['source_files']}")
        print(f"Total files found:        {statistics['total_files_before']:,}")
        print(f"Unique files kept:        {statistics['total_files_after']:,}")
        print(
            f"Duplicate files removed:  {statistics['duplicate_report']['total_duplicate_files']:,}"
        )
        print(f"Total unique file size:   {statistics['total_size']}")
        print(
            f"Space saved by dedup:     {statistics['duplicate_report']['total_wasted_size']}"
        )
        print(f"\nOutput file: {output_path}")
        print(f"{'=' * 70}\n")

        logger.info("Combination completed successfully")

    except Exception as e:
        logger.error(f"Failed to complete JSON combination: {e}")
        raise


if __name__ == "__main__":
    main()
