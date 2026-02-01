#!/usr/bin/env python3
"""
Dropbox Public Link Explorer
Recursively explores a Dropbox folder accessible via a public/shared link
and retrieves all file and folder metadata.

IMPORTANT: To access OTHER people's shared Dropbox folders, your app needs:
1. The 'sharing.read' permission (not 'files.metadata.read')
2. A valid access token from your Dropbox app

The access token is from YOUR Dropbox account, but it allows you to read
OTHER people's PUBLIC shared links.
"""

# Standard library imports
import argparse
import glob as glob_module
import hashlib
import json
import os
import pickle
import sys
import time
from datetime import datetime
from typing import Any

# Third-party imports
import dropbox
from dotenv import load_dotenv
from dropbox.exceptions import ApiError, AuthError
from dropbox.files import FileMetadata, FolderMetadata

# Local imports
from src import logger

# Load environment variables from .env file
load_dotenv()


# Constants
MAX_LINK_DISPLAY_LENGTH = 60
MAX_PATH_DISPLAY_LENGTH = 70
CHECKPOINT_HASH_LENGTH = 12
MAX_SAMPLE_FILES = 10
DEFAULT_CHECKPOINT_INTERVAL = 300
DEFAULT_OUTPUT_DIR = "data"


class DropboxExplorer:
    """Explores Dropbox folders recursively via shared links."""

    def __init__(
        self,
        access_token: str,
        refresh_token: str | None = None,
        app_key: str | None = None,
        app_secret: str | None = None,
        checkpoint_interval: int = 300,
        output_dir: str = "data",
        checkpoint_name: str = "checkpoint",
    ):
        """
        Initialize the Dropbox explorer.

        Args:
            access_token: Dropbox API access token with sharing.read permission
            refresh_token: Dropbox refresh token for automatic token renewal
            app_key: Dropbox app key (required if using refresh token)
            app_secret: Dropbox app secret (required if using refresh token)
            checkpoint_interval: Seconds between checkpoint saves (default: 300)
            output_dir: Directory to save checkpoints and output (default: "data")
            checkpoint_name: Name for the checkpoint file (default: "checkpoint")
        """
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.app_key = app_key
        self.app_secret = app_secret
        self.dbx = self._create_client()
        self.visited_paths = set()
        self.restricted_items = []  # Track all restricted items
        self.all_items = []  # Flat list of all discovered items
        self.checkpoint_interval = checkpoint_interval
        self.output_dir = output_dir
        self.checkpoint_name = checkpoint_name
        self.last_checkpoint_time = time.time()
        self.checkpoint_file = os.path.join(output_dir, f"{checkpoint_name}.pkl")

    def _create_client(self) -> dropbox.Dropbox:
        """
        Create or refresh Dropbox client.

        Creates a Dropbox API client using either refresh token (preferred) or
        access token. Refresh tokens enable automatic token renewal, while
        access tokens may expire after ~4 hours.

        Returns:
            dropbox.Dropbox: Configured Dropbox API client instance
        """
        if self.refresh_token and self.app_key and self.app_secret:
            # Use refresh token for automatic token renewal
            return dropbox.Dropbox(
                oauth2_refresh_token=self.refresh_token,
                app_key=self.app_key,
                app_secret=self.app_secret,
            )
        else:
            # Use access token (may expire)
            return dropbox.Dropbox(self.access_token)

    def _refresh_client(self) -> None:
        """
        Refresh the Dropbox client if using refresh tokens.

        Attempts to refresh the Dropbox API client using refresh token credentials.
        If refresh tokens are not configured, raises an exception with instructions
        for the user to update their access token or configure refresh tokens.

        Raises:
            Exception: If refresh token is not available or configured
        """
        logger.info("Refreshing authentication...")
        if self.refresh_token and self.app_key and self.app_secret:
            self.dbx = self._create_client()
            logger.success("Authentication refreshed successfully")
        else:
            error_msg = "Token expired and no refresh token available. Please update your access token or configure refresh tokens."
            logger.warning(f"Cannot refresh - {error_msg}")
            raise Exception(error_msg)

    def _print_permission_error(self) -> None:
        """
        Print detailed permission error instructions.

        Displays comprehensive step-by-step instructions for resolving Dropbox
        app permission errors. This is typically called when the app lacks the
        required 'sharing.read' permission needed to access shared links.
        """
        logger.error(
            "Permission error! Your app is missing the 'sharing.read' permission."
        )
        logger.info("To fix this:")
        logger.info("  1. Go to https://www.dropbox.com/developers/apps")
        logger.info("  2. Select your app")
        logger.info("  3. Go to the 'Permissions' tab")
        logger.info(
            "  4. Enable 'sharing.read' (you may need to uncheck 'files.metadata.read')"
        )
        logger.info("  5. Click 'Submit' at the bottom")
        logger.info("  6. Generate a NEW access token in the 'Settings' tab")
        logger.info("  7. Update your .env file with the new token")

    def save_checkpoint(self, shared_link: str, root_folder: str) -> None:
        """
        Save current exploration state to checkpoint file.

        Persists the current exploration progress to a pickle file using an
        atomic write pattern (write to temp file, then rename). This ensures
        data integrity even if the process is interrupted during save.

        The checkpoint includes:
        - Timestamp of save
        - Shared link and root folder being explored
        - Set of visited paths (to avoid re-scanning)
        - List of restricted items encountered
        - Flat list of all discovered items

        Args:
            shared_link: Dropbox shared link URL being explored
            root_folder: Root folder path within the shared link
        """
        checkpoint_data = {
            "timestamp": datetime.now().isoformat(),
            "shared_link": shared_link,
            "root_folder": root_folder,
            "visited_paths": list(self.visited_paths),
            "restricted_items": self.restricted_items.copy(),
            "all_items": self.all_items.copy(),
        }

        os.makedirs(self.output_dir, exist_ok=True)
        temp_checkpoint = f"{self.checkpoint_file}.tmp"

        try:
            # Write to temp file first, then rename (atomic operation)
            with open(temp_checkpoint, "wb") as f:
                pickle.dump(checkpoint_data, f)
            os.replace(temp_checkpoint, self.checkpoint_file)
            self.last_checkpoint_time = time.time()
            logger.info(
                f"Checkpoint saved ({len(self.visited_paths)} paths visited, {len(self.all_items)} items discovered)"
            )
        except Exception as e:
            logger.warning(f"Failed to save session: {e}")

    def load_checkpoint(self) -> dict[str, Any] | None:
        """
        Load exploration state from checkpoint file if it exists.

        Attempts to restore the exploration state from a previously saved
        checkpoint file. If successful, updates the instance variables with
        the saved state (visited paths, restricted items, discovered items).

        Returns:
            dict[str, Any] | None: Checkpoint data dictionary containing:
                - timestamp: ISO-8601 timestamp of checkpoint
                - shared_link: Dropbox shared link URL
                - root_folder: Root folder path
                - visited_paths: List of previously visited paths
                - restricted_items: List of restricted items encountered
                - all_items: List of all discovered items
                Returns None if checkpoint file doesn't exist or loading fails.
        """
        if not os.path.exists(self.checkpoint_file):
            return None

        try:
            with open(self.checkpoint_file, "rb") as f:
                checkpoint_data = pickle.load(f)

            self.visited_paths = set(checkpoint_data.get("visited_paths", []))
            self.restricted_items = checkpoint_data.get("restricted_items", [])
            self.all_items = checkpoint_data.get("all_items", [])

            logger.info("Session loaded:")
            logger.info(f"  Timestamp: {checkpoint_data.get('timestamp', 'Unknown')}")
            logger.info(f"  Paths visited: {len(self.visited_paths)}")
            logger.info(f"  Items discovered: {len(self.all_items)}")
            logger.info(f"  Restricted items: {len(self.restricted_items)}")

            return checkpoint_data
        except Exception as e:
            logger.warning(f"Failed to load session: {e}")
            return None

    def should_save_checkpoint(self) -> bool:
        """
        Check if it's time to save a checkpoint.

        Compares the current time against the last checkpoint save time to
        determine if the configured checkpoint interval has elapsed.

        Returns:
            bool: True if checkpoint interval has elapsed, False otherwise
        """
        return (time.time() - self.last_checkpoint_time) >= self.checkpoint_interval

    def explore_shared_link(
        self,
        shared_link: str,
        path: str = "",
        root_folder: str = "",
    ) -> list[dict[str, Any]]:
        """
        Recursively explore a Dropbox shared link.

        Args:
            shared_link: The public Dropbox shared link URL
            path: The path within the shared link to explore (default: root)
            root_folder: The root folder being explored (for checkpointing)

        Returns:
            List of dictionaries containing file/folder metadata
        """
        # Skip if we've already FULLY explored this folder (from checkpoint)
        if path in self.visited_paths:
            logger.debug(f"Skipping fully explored folder: {path}")
            return []

        try:
            logger.info(f"Accessing path: {path if path else '(root)'}")

            result = self.dbx.files_list_folder(
                path=path, shared_link=dropbox.files.SharedLink(url=shared_link)
            )

            # Process entries with nested structure
            entries = self._process_entries(
                result.entries, shared_link, path, root_folder
            )

            # Mark this folder as fully explored AFTER we get its children
            self.visited_paths.add(path)

            # Save checkpoint if needed
            if self.should_save_checkpoint():
                self.save_checkpoint(shared_link, root_folder)

            # Handle pagination if there are more results
            while result.has_more:
                result = self.dbx.files_list_folder_continue(result.cursor)
                entries.extend(
                    self._process_entries(
                        result.entries, shared_link, path, root_folder
                    )
                )

                # Save checkpoint after pagination
                if self.should_save_checkpoint():
                    self.save_checkpoint(shared_link, root_folder)

        except AuthError as e:
            logger.error(f"Authentication error: {e}")
            logger.info("Attempting to refresh authentication...")
            try:
                self._refresh_client()
                # Retry the current operation
                logger.info("Retrying current operation...")
                self.visited_paths.remove(path)  # Remove so we can retry
                return self.explore_shared_link(shared_link, path, root_folder)
            except Exception as refresh_error:
                logger.error(f"Failed to refresh: {refresh_error}")
                raise

        except ApiError as e:
            error_msg = str(e).lower()

            # Handle restricted_content errors (very common in shared folders)
            if "restricted_content" in error_msg:
                logger.warning(f"Restricted access to: {path}")
                # Return empty list - the folder itself will be marked as restricted by the parent
                return []

            # For other errors, provide detailed feedback
            logger.error(f"Error accessing shared link at path '{path}': {e}")

            if "not_found" in error_msg:
                logger.error("The shared link or path was not found.")
            elif (
                "access_denied" in error_msg or "shared_link_access_denied" in error_msg
            ):
                logger.error("Access denied. Possible reasons:")
                logger.error(
                    "  - Password-protected, expired, or restricted to specific users"
                )
            elif "required scope" in error_msg:
                self._print_permission_error()

            return []

        return entries

    def _process_entries(
        self,
        entries: list,
        shared_link: str,
        parent_path: str = "",
        root_folder: str = "",
    ) -> list[dict[str, Any]]:
        """
        Process a list of Dropbox entries and recursively explore folders.
        Creates a nested/hierarchical structure.

        Args:
            entries: List of file/folder entries from Dropbox
            shared_link: The shared link URL for recursive exploration
            parent_path: The parent folder path for building hierarchy
            root_folder: Root folder for checkpointing

        Returns:
            List of metadata dictionaries with nested children
        """
        processed_entries = []

        for entry in entries:
            metadata = self._extract_metadata(entry)

            # Build full path
            if parent_path:
                full_path = f"{parent_path}/{entry.name}"
            else:
                full_path = f"/{entry.name}"

            # Override the null path_display and path_lower with our tracked path
            metadata["path_display"] = full_path
            metadata["path_lower"] = full_path.lower()

            # Add to flat list of all items (for checkpoint preservation)
            self.all_items.append(metadata.copy())

            # If it's a folder, recursively explore it and add children
            if isinstance(entry, FolderMetadata):
                logger.info(f"Exploring folder: {full_path}")
                metadata["children"] = []

                # Check if already fully explored (from checkpoint)
                if full_path not in self.visited_paths:
                    try:
                        # Get folder contents
                        result = self.dbx.files_list_folder(
                            path=full_path,
                            shared_link=dropbox.files.SharedLink(url=shared_link),
                        )

                        # Process children recursively
                        metadata["children"] = self._process_entries(
                            result.entries, shared_link, full_path, root_folder
                        )

                        # Mark as fully explored AFTER getting all children
                        self.visited_paths.add(full_path)

                        # Check if we should save checkpoint
                        if self.should_save_checkpoint():
                            self.save_checkpoint(shared_link, root_folder)

                        # Handle pagination
                        while result.has_more:
                            result = self.dbx.files_list_folder_continue(result.cursor)
                            metadata["children"].extend(
                                self._process_entries(
                                    result.entries,
                                    shared_link,
                                    full_path,
                                    root_folder,
                                )
                            )

                    except ApiError as e:
                        error_msg = str(e)
                        if "restricted_content" in error_msg.lower():
                            logger.warning("Restricted access")
                            metadata["restricted"] = True
                            # Mark as visited since we tried and can't access
                            self.visited_paths.add(full_path)
                            # Track this restricted item
                            self.restricted_items.append(
                                {
                                    "name": entry.name,
                                    "path": full_path,
                                    "type": "folder",
                                }
                            )
                        else:
                            logger.error(f"Error: {e}")
                            metadata["error"] = str(e)
                else:
                    logger.debug("Skipping fully explored folder")
                    metadata["already_visited"] = True

            elif isinstance(entry, FileMetadata):
                logger.debug(
                    f"File: {entry.name} ({self._human_readable_size(entry.size)})"
                )

            processed_entries.append(metadata)

        return processed_entries

    def _extract_metadata(self, entry) -> dict[str, Any]:
        """
        Extract metadata from a Dropbox entry.

        Args:
            entry: Dropbox FileMetadata or FolderMetadata object

        Returns:
            Dictionary containing the entry's metadata
        """
        metadata = {
            "name": entry.name,
            "path_display": entry.path_display,
            "path_lower": entry.path_lower,
            "type": "folder" if isinstance(entry, FolderMetadata) else "file",
        }

        # Add file-specific metadata
        if isinstance(entry, FileMetadata):
            metadata.update(
                {
                    "size": entry.size,
                    "size_human": self._human_readable_size(entry.size),
                    "client_modified": entry.client_modified.isoformat()
                    if entry.client_modified
                    else None,
                    "server_modified": entry.server_modified.isoformat()
                    if entry.server_modified
                    else None,
                    "rev": entry.rev,
                    "content_hash": entry.content_hash,
                    "id": entry.id,
                }
            )

            # Add media info if available
            if entry.media_info:
                metadata["media_info"] = str(entry.media_info)

        # Add folder-specific metadata
        elif isinstance(entry, FolderMetadata):
            metadata["id"] = entry.id

        return metadata

    @staticmethod
    def _human_readable_size(size: int) -> str:
        """Convert bytes to human-readable format."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    def _count_items(self, entries: list[dict[str, Any]]) -> tuple[int, int, int]:
        """
        Recursively count files and folders in nested structure.

        Traverses the hierarchical structure of entries to count the total
        number of files, folders, and cumulative size. Handles nested folders
        by recursively processing their children.

        Args:
            entries: List of entry dictionaries with nested 'children' for folders

        Returns:
            tuple[int, int, int]: A tuple containing:
                - file_count: Total number of files
                - folder_count: Total number of folders
                - total_size: Cumulative size of all files in bytes
        """
        file_count = 0
        folder_count = 0
        total_size = 0

        for entry in entries:
            if entry["type"] == "file":
                file_count += 1
                total_size += entry.get("size", 0)
            elif entry["type"] == "folder":
                folder_count += 1
                # Recursively count children
                if "children" in entry and entry["children"]:
                    child_files, child_folders, child_size = self._count_items(
                        entry["children"]
                    )
                    file_count += child_files
                    folder_count += child_folders
                    total_size += child_size

        return file_count, folder_count, total_size

    def rebuild_hierarchy_from_flat_list(self) -> list[dict[str, Any]]:
        """
        Rebuild hierarchical structure from flat list of items.

        Reconstructs the nested folder/file tree structure from the flat list
        of all discovered items. Uses path information (path_display or path_lower)
        to determine parent-child relationships. This is essential for resuming
        from checkpoints, as checkpoints store items in a flat list for easier
        serialization.

        Algorithm:
        1. Create a path->item mapping
        2. For each item, extract parent path from full path
        3. Add item to parent's children list
        4. Items without parents become root-level entries

        Returns:
            list[dict[str, Any]]: List of root-level entries, each potentially
                containing nested 'children' lists for folders
        """
        if not self.all_items:
            return []

        # Build a map of path -> item (with children list)
        path_map = {}
        for item in self.all_items:
            path = item.get("path_display") or item.get("path_lower", "")
            if path:
                # Create a copy with children list (if folder)
                item_copy = item.copy()
                if item_copy.get("type") == "folder":
                    item_copy["children"] = []
                path_map[path] = item_copy

        # Build parent-child relationships
        root_items = []
        for path, item in path_map.items():
            # Get parent path (everything before the last /)
            parts = path.rstrip("/").split("/")

            if len(parts) <= 2:  # Root level: "/" or "/name"
                root_items.append(item)
            else:
                # Find parent
                parent_path = "/".join(parts[:-1])
                if parent_path in path_map:
                    parent = path_map[parent_path]
                    if "children" not in parent:
                        parent["children"] = []
                    parent["children"].append(item)
                else:
                    # Parent not found - add to root as fallback
                    root_items.append(item)

        return root_items

    def get_restricted_summary(self) -> dict[str, Any]:
        """
        Get summary of all restricted items encountered during exploration.

        Analyzes the list of restricted items (items that couldn't be accessed
        due to permissions or passwords) and categorizes them by type (file or
        folder). Provides counts and detailed lists for reporting.

        Returns:
            dict[str, Any]: Dictionary containing:
                - total_restricted: Total count of restricted items
                - restricted_files: List of restricted file items
                - restricted_folders: List of restricted folder items
        """
        restricted_files = [
            item for item in self.restricted_items if item["type"] == "file"
        ]
        restricted_folders = [
            item for item in self.restricted_items if item["type"] == "folder"
        ]

        return {
            "total_restricted": len(self.restricted_items),
            "restricted_files": restricted_files,
            "restricted_folders": restricted_folders,
        }

    def export_to_json(self, entries: list[dict[str, Any]], output_file: str) -> None:
        """
        Export metadata to JSON file with hierarchical structure.

        Args:
            entries: List of metadata dictionaries (nested structure)
            output_file: Path to output JSON file
        """
        # Count items recursively
        file_count, folder_count, total_size = self._count_items(entries)

        # Get restricted items summary
        restricted_summary = self.get_restricted_summary()

        # Create output structure
        output = {
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                "total_files": file_count,
                "total_folders": folder_count,
                "total_size": total_size,
                "total_size_human": self._human_readable_size(total_size),
                "restricted_items": restricted_summary["total_restricted"],
            },
            "restricted": restricted_summary,
            "contents": entries,
        }

        # Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.success(f"Exported to {output_file}")
        logger.info(f"  Files: {file_count}")
        logger.info(f"  Folders: {folder_count}")
        logger.info(f"  Total size: {self._human_readable_size(total_size)}")
        if restricted_summary["total_restricted"] > 0:
            logger.warning(
                f"  Restricted: {restricted_summary['total_restricted']} items"
            )


def generate_checkpoint_name(shared_link: str, root_folder: str) -> str:
    """
    Generate a checkpoint name based on shared link and root folder.

    Creates a deterministic checkpoint name by hashing the combination of
    shared link URL and root folder path. The same inputs will always
    produce the same checkpoint name, enabling automatic session resumption.
    Uses SHA256 hash truncated to first 12 characters for uniqueness while
    maintaining readability.

    Args:
        shared_link: The Dropbox shared link URL
        root_folder: The root folder path within the shared link

    Returns:
        str: Checkpoint name in format 'checkpoint_XXXXXXXXXXXX' where X is hex
    """
    # Combine link and folder for unique identifier
    combined = f"{shared_link}|{root_folder}"
    # Create SHA256 hash and take first N characters
    hash_obj = hashlib.sha256(combined.encode("utf-8"))
    short_hash = hash_obj.hexdigest()[:CHECKPOINT_HASH_LENGTH]
    return f"checkpoint_{short_hash}"


def list_checkpoints(output_dir: str) -> list[dict[str, Any]]:
    """
    List all available checkpoint files in the output directory.

    Scans the output directory for checkpoint files matching the pattern
    'checkpoint_*.pkl', loads their metadata, and returns information about
    each checkpoint including timestamp, progress, and file location.
    Results are sorted by timestamp (most recent first).

    Args:
        output_dir: Directory containing checkpoint files

    Returns:
        list[dict[str, Any]]: List of checkpoint information dictionaries,
            each containing:
            - filepath: Full path to checkpoint file
            - filename: Basename of checkpoint file
            - timestamp: ISO-8601 timestamp of checkpoint
            - shared_link: Dropbox shared link being explored
            - root_folder: Root folder path within shared link
            - visited_paths: Number of paths visited
            - total_items: Total items discovered
    """
    checkpoint_pattern = os.path.join(output_dir, "checkpoint_*.pkl")
    checkpoint_files = glob_module.glob(checkpoint_pattern)

    checkpoints = []
    for filepath in checkpoint_files:
        try:
            with open(filepath, "rb") as f:
                data = pickle.load(f)

            checkpoints.append(
                {
                    "filepath": filepath,
                    "filename": os.path.basename(filepath),
                    "timestamp": data.get("timestamp", "Unknown"),
                    "shared_link": data.get("shared_link", "Unknown"),
                    "root_folder": data.get("root_folder", ""),
                    "visited_paths": len(data.get("visited_paths", [])),
                    "total_items": len(data.get("all_items", [])),
                }
            )
        except Exception as e:
            logger.warning(f"Warning: Could not read {filepath}: {e}")

    return sorted(checkpoints, key=lambda x: x["timestamp"], reverse=True)


def select_checkpoint(checkpoints: list[dict[str, Any]]) -> str | None:
    """
    Select the most recent checkpoint from available options.

    Automatically selects the most recent checkpoint (first in sorted list)
    and logs information about the selected checkpoint. If multiple checkpoints
    are available, logs a message indicating multiple sessions were found.

    Args:
        checkpoints: List of checkpoint information dictionaries (should be
            pre-sorted by timestamp with most recent first)

    Returns:
        str | None: Full filepath of most recent checkpoint, or None if no
            checkpoints available
    """
    if not checkpoints:
        return None

    # Always select the most recent checkpoint (first in sorted list)
    most_recent = checkpoints[0]

    if len(checkpoints) > 1:
        logger.info("Multiple sessions found, selecting most recent:")
    else:
        logger.info("Found session:")

    logger.info(f"  Filename: {most_recent['filename']}")
    logger.info(f"  Timestamp: {most_recent['timestamp']}")
    logger.info(
        f"  Progress: {most_recent['visited_paths']} paths, {most_recent['total_items']} items"
    )

    return most_recent["filepath"]


def determine_checkpoint_name(
    session_name_arg: str | None, shared_link: str, root_folder: str
) -> str:
    """
    Determine checkpoint name from session argument, environment variable, or auto-generate.

    Follows priority order:
    1. Session name from -s command-line flag (highest priority)
    2. SESSION_NAME environment variable
    3. Auto-generated hash-based name (lowest priority)

    This allows users to override the checkpoint name via CLI or environment,
    or rely on automatic deterministic naming based on the shared link and folder.

    Args:
        session_name_arg: Session name from -s flag (or None)
        shared_link: Dropbox shared link URL
        root_folder: Root folder path

    Returns:
        str: Checkpoint name to use (without .pkl extension)
    """
    if session_name_arg:
        logger.debug(f"Using session name from -s flag: {session_name_arg}")
        return session_name_arg

    session_from_env = os.getenv("SESSION_NAME", "").strip()
    if session_from_env:
        logger.debug(f"Using session name from .env: {session_from_env}")
        return session_from_env

    checkpoint_name = generate_checkpoint_name(shared_link, root_folder)
    logger.debug(f"Using auto-generated session name: {checkpoint_name}")
    return checkpoint_name


def main() -> None:
    """
    Main function to run the Dropbox explorer.

    Orchestrates the complete Dropbox shared link exploration workflow including:
    - Configuration loading from environment and command-line arguments
    - Logging setup
    - Authentication with Dropbox API
    - Session management (save/load/resume)
    - Recursive folder exploration
    - JSON export with statistics

    The function handles multiple modes of operation via command-line flags:
    - Normal exploration mode: Explores shared link and exports to JSON
    - Inspection mode (-i): Displays session statistics without exploring
    - Extraction mode (-x): Converts session to JSON without re-exploring
    - Continue mode (-c): Resumes from existing session

    Raises:
        SystemExit: Exits with code 1 on errors, 0 on success
    """

    # Configure logging from environment variables
    from src.logger import configure_logging

    console_level = os.getenv("LOG_LEVEL_CONSOLE", "INFO")
    file_level = os.getenv("LOG_LEVEL_FILE", "DEBUG")
    log_dir = os.getenv("LOG_DIR", "logs")

    configure_logging(
        console_level=console_level,
        file_level=file_level,
        log_dir=log_dir,
    )

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Dropbox Public Link Explorer - Recursively explores shared Dropbox folders"
    )
    parser.add_argument(
        "--provider",
        choices=["dropbox", "sharepoint"],
        default="dropbox",
        help="Data source to explore (default: dropbox).",
    )
    parser.add_argument(
        "-c",
        "--continue",
        dest="auto_continue",
        nargs="?",
        const=True,
        default=False,
        metavar="SESSION",
        help="Continue from session. Provide session name (e.g., 'mysession' or 'mysession.pkl') or use without argument for default session.",
    )
    parser.add_argument(
        "-x",
        "--extract",
        nargs="?",
        const=True,
        default=False,
        metavar="SESSION",
        help="Extract session to JSON. Provide session name (e.g., 'ACRD' or 'ACRD.pkl') or use without argument for default session.",
    )
    parser.add_argument(
        "-p",
        "--path",
        dest="root_folder",
        type=str,
        default=None,
        help="Override ROOT_FOLDER env var - specify path within shared link to explore",
    )
    parser.add_argument(
        "-s",
        "--session",
        dest="session_name",
        type=str,
        default=None,
        help="Specify session name (overrides SESSION_NAME env var and auto-generated name)",
    )
    parser.add_argument(
        "-i",
        "--inspect",
        nargs="?",
        const=True,
        default=False,
        metavar="SESSION",
        help="Inspect session and show statistics. Provide session name (e.g., 'ACRD' or 'ACRD.pkl') or use without argument for default session.",
    )
    parser.add_argument(
        "-j",
        "--json",
        dest="json_output",
        action="store_true",
        help="Output inspection results as JSON (use with -i flag)",
    )
    args = parser.parse_args()

    if args.provider == "sharepoint":
        from src.providers.sharepoint_graph import load_sp_config, SharePointGraphClient

        cfg = load_sp_config()
        client = SharePointGraphClient(cfg)

        logger.info("SharePoint: resolving site and drive…")
        site_id = client.resolve_site_id()
        drives = client.list_drives(site_id)

        drive_id = drives.get(cfg.drive_name)
        if not drive_id:
            logger.error(
                "SharePoint: drive '%s' not found. Available: %s",
                cfg.drive_name,
                ", ".join(sorted(drives.keys())),
            )
            return

        root_item = client.resolve_root_item(drive_id)
        root_id = root_item["id"]

        # Minimal export: flat list (paths) + basic metadata
        entries = []

        def walk(folder_id: str, parent_path: str) -> None:
            for item in client.iter_children(drive_id, folder_id):
                name = item.get("name", "")
                is_folder = "folder" in item
                path = f"{parent_path}/{name}".replace("//", "/")

                if is_folder:
                    entries.append({"type": "folder", "path": path})
                    walk(item["id"], path)
                else:
                    entries.append({
                        "type": "file",
                        "path": path,
                        "size": item.get("size"),
                        "lastModifiedDateTime": item.get("lastModifiedDateTime"),
                    })

        logger.info("SharePoint: crawling…")
        walk(root_id, "")

        # Write JSON next to other outputs (same output dir logic as Dropbox uses)
        import json
        from pathlib import Path

        out_dir = Path(os.environ.get("OUTPUT_DIR", "data"))
        out_dir.mkdir(parents=True, exist_ok=True)

        session_name = os.environ.get("SESSION_NAME", "sharepoint_session")
        out_path = out_dir / f"{session_name}.sharepoint.json"

        payload = {
            "source": "sharepoint",
            "site_id": site_id,
            "drive_name": cfg.drive_name,
            "root_folder": cfg.root_folder,
            "count": len(entries),
            "entries": entries,
        }

        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"SharePoint: wrote {out_path}")
        return

    # Configure logging from environment variables
    # Logging is now configured in __main__.py

    # Handle inspection mode (-i flag)
    if args.inspect:
        output_dir = os.getenv("OUTPUT_DIR", DEFAULT_OUTPUT_DIR)

        logger.info("Session Inspection Mode")

        # Get session file - from argument or use default
        checkpoint_file = None

        if isinstance(args.inspect, str):
            # Session file path provided as argument
            checkpoint_file = args.inspect

            # Auto-append .pkl extension if not present
            if not checkpoint_file.endswith(".pkl"):
                checkpoint_file += ".pkl"

            # If not an absolute path, treat it relative to output_dir
            if not os.path.isabs(checkpoint_file):
                checkpoint_file = os.path.join(output_dir, checkpoint_file)
            if not os.path.exists(checkpoint_file):
                logger.error(f"Session file not found: {checkpoint_file}")
                sys.exit(1)
        else:
            # No argument provided - use default session
            # Need to determine session name from environment
            shared_link = os.getenv("DROPBOX_SHARED_LINK", "")
            root_folder = os.getenv("ROOT_FOLDER", "").strip()
            if root_folder and not root_folder.startswith("/"):
                root_folder = "/" + root_folder

            checkpoint_name = determine_checkpoint_name(
                args.session_name, shared_link, root_folder
            )
            checkpoint_file = os.path.join(output_dir, f"{checkpoint_name}.pkl")

            if not os.path.exists(checkpoint_file):
                logger.error(f"Default session file not found: {checkpoint_file}")
                logger.info("Use -s <session_name> to specify a different session")
                sys.exit(1)

        try:
            logger.info(f"Loading session: {os.path.basename(checkpoint_file)}")
            logger.info(f"Path: {checkpoint_file}")

            with open(checkpoint_file, "rb") as f:
                checkpoint_data = pickle.load(f)

            # Extract basic information
            timestamp = checkpoint_data.get("timestamp", "Unknown")
            shared_link = checkpoint_data.get("shared_link", "Unknown")
            root_folder = checkpoint_data.get("root_folder", "")
            all_items = checkpoint_data.get("all_items", [])
            visited_paths = checkpoint_data.get("visited_paths", [])
            restricted_items = checkpoint_data.get("restricted_items", [])

            # Calculate statistics
            files = [item for item in all_items if item.get("type") == "file"]
            folders = [item for item in all_items if item.get("type") == "folder"]
            total_size = sum(item.get("size", 0) for item in files)

            # Collect unique file extensions and categorize them
            extensions = set()
            extension_categories = {
                "Image": set(),
                "Video": set(),
                "Audio": set(),
                "Document": set(),
                "Spreadsheet": set(),
                "Presentation": set(),
                "Archive": set(),
                "Code": set(),
                "Data": set(),
                "Executable": set(),
                "Other": set(),
            }

            # Track file counts and sizes per category
            category_stats = {
                "Image": {"count": 0, "size": 0},
                "Video": {"count": 0, "size": 0},
                "Audio": {"count": 0, "size": 0},
                "Document": {"count": 0, "size": 0},
                "Spreadsheet": {"count": 0, "size": 0},
                "Presentation": {"count": 0, "size": 0},
                "Archive": {"count": 0, "size": 0},
                "Code": {"count": 0, "size": 0},
                "Data": {"count": 0, "size": 0},
                "Executable": {"count": 0, "size": 0},
                "Other": {"count": 0, "size": 0},
            }

            # Define extension mappings
            ext_mapping = {
                "Image": [
                    "jpg",
                    "jpeg",
                    "png",
                    "gif",
                    "bmp",
                    "svg",
                    "webp",
                    "tiff",
                    "tif",
                    "ico",
                    "heic",
                    "heif",
                    "raw",
                    "cr2",
                    "nef",
                    "arw",
                ],
                "Video": [
                    "mp4",
                    "avi",
                    "mkv",
                    "mov",
                    "wmv",
                    "flv",
                    "webm",
                    "m4v",
                    "mpg",
                    "mpeg",
                    "3gp",
                    "m2ts",
                    "mts",
                ],
                "Audio": [
                    "mp3",
                    "wav",
                    "flac",
                    "aac",
                    "ogg",
                    "wma",
                    "m4a",
                    "opus",
                    "aiff",
                    "ape",
                    "alac",
                ],
                "Document": [
                    "pdf",
                    "doc",
                    "docx",
                    "txt",
                    "rtf",
                    "odt",
                    "tex",
                    "wpd",
                    "pages",
                    "md",
                    "markdown",
                ],
                "Spreadsheet": ["xls", "xlsx", "csv", "ods", "numbers", "tsv"],
                "Presentation": ["ppt", "pptx", "odp", "key"],
                "Archive": [
                    "zip",
                    "rar",
                    "7z",
                    "tar",
                    "gz",
                    "bz2",
                    "xz",
                    "tgz",
                    "tbz2",
                    "z",
                    "iso",
                    "dmg",
                ],
                "Code": [
                    "py",
                    "js",
                    "java",
                    "cpp",
                    "c",
                    "h",
                    "hpp",
                    "cs",
                    "php",
                    "rb",
                    "go",
                    "rs",
                    "swift",
                    "kt",
                    "ts",
                    "jsx",
                    "tsx",
                    "html",
                    "css",
                    "scss",
                    "sass",
                    "less",
                    "sql",
                    "sh",
                    "bash",
                    "r",
                    "m",
                    "scala",
                    "pl",
                    "lua",
                    "vim",
                ],
                "Data": [
                    "json",
                    "xml",
                    "yaml",
                    "yml",
                    "toml",
                    "ini",
                    "cfg",
                    "conf",
                    "log",
                    "dat",
                    "db",
                    "sqlite",
                    "mdb",
                    "accdb",
                ],
                "Executable": [
                    "exe",
                    "msi",
                    "app",
                    "deb",
                    "rpm",
                    "apk",
                    "dmg",
                    "pkg",
                    "bin",
                    "run",
                    "jar",
                    "bat",
                    "cmd",
                    "com",
                ],
            }

            # Reverse mapping for quick lookup
            ext_to_category = {}
            for category, exts in ext_mapping.items():
                for ext in exts:
                    ext_to_category[ext] = category

            for file in files:
                name = file.get("name", "")
                file_size = file.get("size", 0)

                if "." in name:
                    ext = name.rsplit(".", 1)[-1].lower()
                    extensions.add(ext)

                    # Categorize the extension
                    category = ext_to_category.get(ext, "Other")
                    extension_categories[category].add(ext)
                    category_stats[category]["count"] += 1
                    category_stats[category]["size"] += file_size
                else:
                    extensions.add("(no extension)")
                    extension_categories["Other"].add("(no extension)")
                    category_stats["Other"]["count"] += 1
                    category_stats["Other"]["size"] += file_size

            # Prepare category information for output
            categories_info = []
            for category in [
                "Image",
                "Video",
                "Audio",
                "Document",
                "Spreadsheet",
                "Presentation",
                "Archive",
                "Code",
                "Data",
                "Executable",
                "Other",
            ]:
                if extension_categories[category]:
                    sorted_exts = sorted(extension_categories[category])
                    cat_count = category_stats[category]["count"]
                    cat_size = category_stats[category]["size"]
                    cat_pct = (cat_count / len(files) * 100) if files else 0
                    cat_size_pct = (cat_size / total_size * 100) if total_size else 0

                    categories_info.append(
                        {
                            "category": category,
                            "extensions": sorted_exts,
                            "file_count": cat_count,
                            "file_percentage": round(cat_pct, 1),
                            "total_size": cat_size,
                            "total_size_human": DropboxExplorer._human_readable_size(
                                cat_size
                            ),
                            "size_percentage": round(cat_size_pct, 1),
                        }
                    )

            # Check if JSON output is requested
            if args.json_output:
                # Prepare restricted items info
                restricted_files = [
                    item for item in restricted_items if item.get("type") == "file"
                ]
                restricted_folders = [
                    item for item in restricted_items if item.get("type") == "folder"
                ]

                # Build JSON output
                json_output = {
                    "timestamp": timestamp,
                    "shared_link": shared_link,
                    "root_folder": root_folder
                    if root_folder
                    else "(root of shared link)",
                    "statistics": {
                        "total_items": len(all_items),
                        "total_files": len(files),
                        "total_folders": len(folders),
                        "visited_paths": len(visited_paths),
                        "total_size": total_size,
                        "total_size_human": DropboxExplorer._human_readable_size(
                            total_size
                        ),
                        "unique_extensions": len(extensions),
                        "restricted_items": len(restricted_items),
                        "restricted_files": len(restricted_files),
                        "restricted_folders": len(restricted_folders),
                    },
                    "categories": categories_info,
                }

                # Output JSON to stdout
                print(json.dumps(json_output, indent=2, ensure_ascii=False))
                sys.exit(0)

            # Display information (human-readable format)
            logger.info("Session Statistics:")
            logger.info(f"Timestamp: {timestamp}")
            logger.info(f"Shared Link: {shared_link}")
            logger.info(
                f"Root Folder: {root_folder if root_folder else '(root of shared link)'}"
            )
            logger.info(
                f"Total items: {len(all_items):,} ({len(files):,} files, {len(folders):,} folders)"
            )
            logger.info(f"Visited paths: {len(visited_paths):,}")
            logger.info(
                f"Total Size: {total_size:,} bytes ({DropboxExplorer._human_readable_size(total_size)})"
            )

            # Display unique file extensions by category
            if extensions:
                logger.info(f"Unique file extensions: {len(extensions):,}")
                logger.info("Extensions by category:")

                for cat_info in categories_info:
                    logger.info(
                        f"  {cat_info['category']}: {', '.join(cat_info['extensions'])}"
                    )
                    logger.info(
                        f"    Files: {cat_info['file_count']:,} ({cat_info['file_percentage']:.1f}%) | Size: {cat_info['total_size_human']} ({cat_info['size_percentage']:.1f}%)"
                    )

            if restricted_items:
                restricted_files = [
                    item for item in restricted_items if item.get("type") == "file"
                ]
                restricted_folders = [
                    item for item in restricted_items if item.get("type") == "folder"
                ]
                logger.info(
                    f"Restricted items: {len(restricted_items):,} ({len(restricted_files):,} files, {len(restricted_folders):,} folders)"
                )

            logger.success("Inspection complete!")
            sys.exit(0)

        except Exception as e:
            logger.error(f"Error inspecting session: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)

    # Handle extraction mode (-x flag)
    if args.extract:
        output_dir = os.getenv("OUTPUT_DIR", DEFAULT_OUTPUT_DIR)

        logger.info("Session Extraction Mode")

        # Get session file - from argument or use default
        checkpoint_file = None

        if isinstance(args.extract, str):
            # Session file path provided as argument
            checkpoint_file = args.extract

            # Auto-append .pkl extension if not present
            if not checkpoint_file.endswith(".pkl"):
                checkpoint_file += ".pkl"

            # If not an absolute path, treat it relative to output_dir
            if not os.path.isabs(checkpoint_file):
                checkpoint_file = os.path.join(output_dir, checkpoint_file)
            if not os.path.exists(checkpoint_file):
                logger.error(f"Session file not found: {checkpoint_file}")
                sys.exit(1)
        else:
            # No argument provided - use default session
            # Need to determine session name from environment
            shared_link = os.getenv("DROPBOX_SHARED_LINK", "")
            root_folder = os.getenv("ROOT_FOLDER", "").strip()
            if root_folder and not root_folder.startswith("/"):
                root_folder = "/" + root_folder

            checkpoint_name = determine_checkpoint_name(
                args.session_name, shared_link, root_folder
            )
            checkpoint_file = os.path.join(output_dir, f"{checkpoint_name}.pkl")

            if not os.path.exists(checkpoint_file):
                logger.error(f"Default session file not found: {checkpoint_file}")
                logger.info("Use -s <session_name> to specify a different session")
                sys.exit(1)

        try:
            logger.info(f"Loading session: {os.path.basename(checkpoint_file)}")
            with open(checkpoint_file, "rb") as f:
                checkpoint_data = pickle.load(f)

            logger.info(f"Timestamp: {checkpoint_data.get('timestamp', 'Unknown')}")
            logger.info(f"Total items: {len(checkpoint_data.get('all_items', []))}")


            # Create a temporary explorer instance (no API access needed)
            explorer = DropboxExplorer(
                access_token="dummy",  # Not needed for extraction
                checkpoint_interval=0,
                output_dir=output_dir,
            )

            # Load the session data
            explorer.all_items = checkpoint_data.get("all_items", [])
            explorer.restricted_items = checkpoint_data.get("restricted_items", [])

            # Rebuild hierarchy from flat list
            logger.info("Building hierarchy from session data...")
            entries = explorer.rebuild_hierarchy_from_flat_list()
            logger.info(f"Built {len(entries)} root-level entries")

            # Export to JSON using session name
            session_name = os.path.basename(checkpoint_file).replace(".pkl", "")
            output_file = os.path.join(output_dir, f"{session_name}.json")

            logger.info("Exporting to JSON...")
            explorer.export_to_json(entries, output_file)

            logger.success("Extraction complete!")
            sys.exit(0)

        except Exception as e:
            logger.error(f"Error extracting session: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)

    logger.info("Dropbox Public Link Explorer")

    # Get configuration from environment variables
    access_token = os.getenv("DROPBOX_ACCESS_TOKEN")
    refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN")
    app_key = os.getenv("DROPBOX_APP_KEY")
    app_secret = os.getenv("DROPBOX_APP_SECRET")

    if not access_token:
        logger.error("DROPBOX_ACCESS_TOKEN not found in .env file")
        logger.info("Setup instructions:")
        logger.info("  1. Go to https://www.dropbox.com/developers/apps")
        logger.info("  2. Create an app (or select existing)")
        logger.info("  3. In 'Permissions' tab, enable 'sharing.read'")
        logger.info("  4. In 'Settings' tab, generate an access token")
        logger.info("  5. Add to .env file: DROPBOX_ACCESS_TOKEN=your_token")
        logger.info("For long-running operations, consider using refresh tokens:")
        logger.info(
            "  - Set DROPBOX_REFRESH_TOKEN, DROPBOX_APP_KEY, and DROPBOX_APP_SECRET"
        )
        logger.info("  - This prevents token expiration during long operations")
        sys.exit(1)

    # Get output directory configuration
    output_dir = os.getenv("OUTPUT_DIR", DEFAULT_OUTPUT_DIR)
    checkpoint_interval = int(
        os.getenv("CHECKPOINT_INTERVAL_SECONDS", str(DEFAULT_CHECKPOINT_INTERVAL))
    )

    # Display configuration
    logger.info("Configuration:")
    logger.info(f"  Output directory: {output_dir}")
    logger.info(f"  Session save interval: {checkpoint_interval} seconds")
    if refresh_token:
        logger.info("  Using refresh token (auto-renewal enabled)")
    else:
        logger.warning("  Using access token only (may expire during long operations)")

    # Get shared link from environment variable
    shared_link = os.getenv("DROPBOX_SHARED_LINK")

    if not shared_link:
        logger.error("DROPBOX_SHARED_LINK not found in .env file")
        logger.info("Please add your shared link to the .env file:")
        logger.info("  DROPBOX_SHARED_LINK=https://www.dropbox.com/...")
        sys.exit(1)

    # Get root folder path (optional, defaults to root of shared link)
    # Command line argument takes precedence over environment variable
    if args.root_folder is not None:
        root_folder = args.root_folder.strip()
    else:
        root_folder = os.getenv("ROOT_FOLDER", "").strip()

    # Ensure path starts with / if not empty
    if root_folder and not root_folder.startswith("/"):
        root_folder = "/" + root_folder

    logger.info("Using shared link from .env")
    if root_folder:
        if args.root_folder is not None:
            logger.info(f"Starting from folder: {root_folder} (from -p flag)")
        else:
            logger.info(f"Starting from folder: {root_folder} (from .env)")
    else:
        logger.info("Starting from root of shared link")

    # Determine checkpoint name (priority: -s flag > SESSION_NAME env > auto-generated)
    if args.session_name:
        checkpoint_name = args.session_name
        logger.info(f"Session name: {checkpoint_name} (from -s flag)")
    else:
        session_from_env = os.getenv("SESSION_NAME", "").strip()
        if session_from_env:
            checkpoint_name = session_from_env
            logger.info(f"Session name: {checkpoint_name} (from .env)")
        else:
            checkpoint_name = generate_checkpoint_name(shared_link, root_folder)
            logger.info(f"Session name: {checkpoint_name} (auto-generated)")

    # Create explorer instance
    explorer = DropboxExplorer(
        access_token=access_token,
        refresh_token=refresh_token,
        app_key=app_key,
        app_secret=app_secret,
        checkpoint_interval=checkpoint_interval,
        output_dir=output_dir,
        checkpoint_name=checkpoint_name,
    )

    # Check for existing checkpoint
    checkpoint = explorer.load_checkpoint()
    should_resume = False

    # Handle -c flag with specific session file argument
    if isinstance(args.auto_continue, str):
        # -c was provided with a session file path
        checkpoint_file_arg = args.auto_continue

        # Auto-append .pkl extension if not present
        if not checkpoint_file_arg.endswith(".pkl"):
            checkpoint_file_arg += ".pkl"

        if not os.path.isabs(checkpoint_file_arg):
            checkpoint_file_arg = os.path.join(output_dir, checkpoint_file_arg)

        if not os.path.exists(checkpoint_file_arg):
            logger.error(f"Session file not found: {checkpoint_file_arg}")
            sys.exit(1)

        logger.info(
            f"Loading specified session: {os.path.basename(checkpoint_file_arg)}"
        )
        try:
            with open(checkpoint_file_arg, "rb") as f:
                checkpoint_data = pickle.load(f)

            # Use the shared_link and root_folder from the checkpoint
            shared_link = checkpoint_data.get("shared_link", "")
            root_folder = checkpoint_data.get("root_folder", "")

            if not shared_link:
                logger.error("Checkpoint does not contain shared_link information")
                sys.exit(1)

            logger.info(
                f"Using shared link from checkpoint: {shared_link[:MAX_LINK_DISPLAY_LENGTH]}..."
            )
            if root_folder:
                logger.info(f"Using root folder from checkpoint: {root_folder}")
            else:
                logger.info("Using root of shared link (from checkpoint)")

            explorer.visited_paths = set(checkpoint_data.get("visited_paths", []))
            explorer.restricted_items = checkpoint_data.get("restricted_items", [])
            explorer.all_items = checkpoint_data.get("all_items", [])
            explorer.checkpoint_file = checkpoint_file_arg
            explorer.checkpoint_name = os.path.basename(checkpoint_file_arg).replace(
                ".pkl", ""
            )

            logger.success(f"Loaded session: {os.path.basename(checkpoint_file_arg)}")
            should_resume = True
        except Exception as e:
            logger.error(f"Error loading session: {e}")
            sys.exit(1)

    elif checkpoint:
        logger.info("Session Found!")

        # Verify it's the same shared link and root folder
        checkpoint_link = checkpoint.get("shared_link", "")
        checkpoint_root = checkpoint.get("root_folder", "")

        if checkpoint_link != shared_link or checkpoint_root != root_folder:
            logger.warning("Session configuration mismatch!")
            logger.warning(
                f"Session link: {checkpoint_link[:MAX_LINK_DISPLAY_LENGTH]}..."
            )
            logger.warning(f"Current link: {shared_link[:MAX_LINK_DISPLAY_LENGTH]}...")
            logger.warning(f"Session root: {checkpoint_root}")
            logger.warning(f"Current root: {root_folder}")
            logger.warning("This session is for a different exploration.")
            logger.warning("Starting fresh exploration will replace this session.")

        # Automatically resume from session (default behavior)
        logger.info("Resuming from session")
        should_resume = True
    else:
        # No session found for current session name
        if args.auto_continue:
            # -c flag was used but no session exists
            # Check if there are other sessions available
            all_checkpoints = list_checkpoints(output_dir)

            if all_checkpoints:
                logger.warning(f"No session found for '{checkpoint_name}'")
                logger.info(f"However, {len(all_checkpoints)} other session(s) found.")
                logger.info("Automatically selecting most recent session...")

                # Automatically select the most recent checkpoint
                selected_checkpoint = select_checkpoint(all_checkpoints)

                if selected_checkpoint:
                    # Load the selected checkpoint
                    try:
                        with open(selected_checkpoint, "rb") as f:
                            checkpoint_data = pickle.load(f)

                        explorer.visited_paths = set(
                            checkpoint_data.get("visited_paths", [])
                        )
                        explorer.restricted_items = checkpoint_data.get(
                            "restricted_items", []
                        )
                        explorer.all_items = checkpoint_data.get("all_items", [])

                        # Update the explorer's checkpoint file to use this one
                        explorer.checkpoint_file = selected_checkpoint
                        explorer.checkpoint_name = os.path.basename(
                            selected_checkpoint
                        ).replace(".pkl", "")

                        logger.success(
                            f"Loaded checkpoint: {os.path.basename(selected_checkpoint)}"
                        )
                        should_resume = True
                    except Exception as e:
                        logger.error(f"Error loading session: {e}")
                        logger.info("Starting fresh exploration...")
                else:
                    logger.info("No session selected - starting fresh exploration")
            else:
                logger.info("No session found - starting fresh exploration")
        else:
            logger.info("No session found - starting fresh exploration")

    logger.info("Starting exploration...")

    try:
        if should_resume:
            # We already have items from checkpoint, just continue exploring
            logger.info(
                f"Resuming from checkpoint with {len(explorer.all_items)} items already discovered"
            )

        entries = explorer.explore_shared_link(
            shared_link, path=root_folder, root_folder=root_folder
        )

        # After exploration, rebuild hierarchy from flat list (includes checkpoint + new items)
        if explorer.all_items:
            logger.info(
                f"Building final hierarchy from {len(explorer.all_items)} items..."
            )
            entries = explorer.rebuild_hierarchy_from_flat_list()
            logger.info(f"Built {len(entries)} root-level entries")

    except KeyboardInterrupt:
        logger.warning("Interrupted by user!")
        logger.info("Saving session before exit...")
        explorer.save_checkpoint(shared_link, root_folder)
        logger.success("Session saved. Run the script again to resume.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error during exploration: {e}")
        logger.info("Attempting to save session...")
        try:
            explorer.save_checkpoint(shared_link, root_folder)
            logger.success("Session saved. Run the script again to resume.")
        except Exception as save_error:
            logger.warning(f"Failed to save session: {save_error}")
        sys.exit(1)

    if not entries:
        logger.error("No entries found or error occurred.")
        logger.info("Check the error messages above for details.")
        sys.exit(1)

    logger.success("Exploration complete!")

    # Display restricted items summary if any
    restricted_summary = explorer.get_restricted_summary()
    if restricted_summary["total_restricted"] > 0:
        logger.warning("Restricted Items Summary:")
        logger.warning(f"Folders: {len(restricted_summary['restricted_folders'])}")
        logger.warning(f"Files: {len(restricted_summary['restricted_files'])}")
        logger.info("The following items could not be accessed:")
        for item in restricted_summary["restricted_folders"][:10]:
            logger.info(f"  Folder: {item['path']}")
        for item in restricted_summary["restricted_files"][:10]:
            logger.info(f"  File: {item['path']}")

        remaining = restricted_summary["total_restricted"] - 20
        if remaining > 0:
            logger.info(f"  ... and {remaining} more (see JSON output for full list)")

    # Save final checkpoint before export to ensure .pkl contains everything
    logger.info("Saving final session before export...")
    explorer.save_checkpoint(shared_link, root_folder)

    # Export to JSON using session name
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{explorer.checkpoint_name}.json")

    explorer.export_to_json(entries, output_file)

    # Keep checkpoint file for reference (not deleted)
    if os.path.exists(explorer.checkpoint_file):
        logger.info(f"Session file preserved at: {explorer.checkpoint_file}")

    logger.success("Export complete!")


if __name__ == "__main__":
    main()
