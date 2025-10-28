#!/usr/bin/env python3
"""
Tests for the JSON file combiner module.

Tests cover:
- Path depth calculation
- File extraction from nested JSON
- Duplicate detection and removal
- Complete file combination workflow
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.combine import (
    calculate_path_depth,
    combine_json_files,
    extract_files_from_json,
    human_readable_size,
    remove_duplicates,
)


class TestCalculatePathDepth:
    """Test path depth calculation."""

    def test_root_file(self):
        """Test depth of file at root level."""
        assert calculate_path_depth("/file.txt") == 1

    def test_nested_file(self):
        """Test depth of nested file."""
        assert calculate_path_depth("/folder/file.txt") == 2
        assert calculate_path_depth("/a/b/file.txt") == 3
        assert calculate_path_depth("/a/b/c/d/file.txt") == 5

    def test_trailing_slash(self):
        """Test paths with trailing slashes."""
        assert calculate_path_depth("/folder/file.txt/") == 2

    def test_multiple_slashes(self):
        """Test handling of multiple slashes."""
        assert calculate_path_depth("///folder///file.txt///") == 2

    def test_empty_path(self):
        """Test empty path handling."""
        assert calculate_path_depth("") == 0
        assert calculate_path_depth("/") == 0


class TestHumanReadableSize:
    """Test human-readable size conversion."""

    def test_bytes(self):
        """Test byte conversion."""
        assert human_readable_size(500) == "500.00 B"

    def test_kilobytes(self):
        """Test kilobyte conversion."""
        assert human_readable_size(1024) == "1.00 KB"
        assert human_readable_size(1536) == "1.50 KB"

    def test_megabytes(self):
        """Test megabyte conversion."""
        assert human_readable_size(1048576) == "1.00 MB"
        assert human_readable_size(2097152) == "2.00 MB"

    def test_gigabytes(self):
        """Test gigabyte conversion."""
        assert human_readable_size(1073741824) == "1.00 GB"

    def test_zero(self):
        """Test zero bytes."""
        assert human_readable_size(0) == "0.00 B"


class TestExtractFilesFromJson:
    """Test file extraction from JSON structures."""

    def test_extract_single_file(self):
        """Test extracting a single file."""
        json_data = {
            "contents": [
                {
                    "name": "test.txt",
                    "path_display": "/test.txt",
                    "path_lower": "/test.txt",
                    "type": "file",
                    "content_hash": "abc123",
                    "size": 1024,
                    "id": "id:123",
                }
            ]
        }

        files = extract_files_from_json(json_data, "test.json")

        assert len(files) == 1
        assert files[0]["path_display"] == "/test.txt"
        assert files[0]["content_hash"] == "abc123"
        assert files[0]["size"] == 1024
        assert files[0]["depth"] == 1
        assert files[0]["source_file"] == "test.json"

    def test_extract_nested_files(self):
        """Test extracting files from nested structure."""
        json_data = {
            "contents": [
                {
                    "name": "folder",
                    "type": "folder",
                    "children": [
                        {
                            "name": "file1.txt",
                            "path_display": "/folder/file1.txt",
                            "type": "file",
                            "content_hash": "hash1",
                            "size": 100,
                        },
                        {
                            "name": "subfolder",
                            "type": "folder",
                            "children": [
                                {
                                    "name": "file2.txt",
                                    "path_display": "/folder/subfolder/file2.txt",
                                    "type": "file",
                                    "content_hash": "hash2",
                                    "size": 200,
                                }
                            ],
                        },
                    ],
                }
            ]
        }

        files = extract_files_from_json(json_data, "test.json")

        assert len(files) == 2
        assert files[0]["depth"] == 2
        assert files[1]["depth"] == 3

    def test_skip_folders(self):
        """Test that folders are not extracted."""
        json_data = {
            "contents": [
                {"name": "folder", "path_display": "/folder", "type": "folder"}
            ]
        }

        files = extract_files_from_json(json_data, "test.json")

        assert len(files) == 0

    def test_skip_files_without_hash(self):
        """Test that files without content_hash are skipped."""
        json_data = {
            "contents": [
                {
                    "name": "test.txt",
                    "path_display": "/test.txt",
                    "type": "file",
                    "size": 1024,
                }
            ]
        }

        files = extract_files_from_json(json_data, "test.json")

        assert len(files) == 0

    def test_skip_files_without_path(self):
        """Test that files without path are skipped."""
        json_data = {
            "contents": [{"name": "test.txt", "type": "file", "content_hash": "abc123"}]
        }

        files = extract_files_from_json(json_data, "test.json")

        assert len(files) == 0


class TestRemoveDuplicates:
    """Test duplicate file removal."""

    def test_no_duplicates(self):
        """Test with no duplicate files."""
        files = [
            {
                "path_display": "/file1.txt",
                "content_hash": "hash1",
                "size": 100,
                "depth": 1,
            },
            {
                "path_display": "/file2.txt",
                "content_hash": "hash2",
                "size": 200,
                "depth": 1,
            },
        ]

        unique_files, report = remove_duplicates(files)

        assert len(unique_files) == 2
        assert report["total_duplicate_files"] == 0
        assert report["total_wasted_bytes"] == 0

    def test_remove_duplicates_keep_shallowest(self):
        """Test that shallowest path is kept for duplicates."""
        files = [
            {
                "path_display": "/a/b/c/file.txt",
                "content_hash": "hash1",
                "size": 1000,
                "depth": 4,
            },
            {
                "path_display": "/a/file.txt",
                "content_hash": "hash1",
                "size": 1000,
                "depth": 2,
            },
            {
                "path_display": "/a/b/file.txt",
                "content_hash": "hash1",
                "size": 1000,
                "depth": 3,
            },
        ]

        unique_files, report = remove_duplicates(files)

        assert len(unique_files) == 1
        assert unique_files[0]["path_display"] == "/a/file.txt"
        assert unique_files[0]["depth"] == 2
        assert report["total_duplicate_files"] == 2
        assert report["total_wasted_bytes"] == 2000

    def test_multiple_duplicate_groups(self):
        """Test multiple groups of duplicates."""
        files = [
            {
                "path_display": "/file1_v1.txt",
                "content_hash": "hash1",
                "size": 100,
                "depth": 1,
            },
            {
                "path_display": "/a/file1_v2.txt",
                "content_hash": "hash1",
                "size": 100,
                "depth": 2,
            },
            {
                "path_display": "/file2_v1.txt",
                "content_hash": "hash2",
                "size": 200,
                "depth": 1,
            },
            {
                "path_display": "/b/file2_v2.txt",
                "content_hash": "hash2",
                "size": 200,
                "depth": 2,
            },
        ]

        unique_files, report = remove_duplicates(files)

        assert len(unique_files) == 2
        assert report["total_duplicate_files"] == 2
        assert report["total_wasted_bytes"] == 300
        assert report["unique_hashes_with_duplicates"] == 2

    def test_lexicographic_sorting_for_same_depth(self):
        """Test that lexicographic order is used when depths are equal."""
        files = [
            {
                "path_display": "/z_file.txt",
                "content_hash": "hash1",
                "size": 100,
                "depth": 1,
            },
            {
                "path_display": "/a_file.txt",
                "content_hash": "hash1",
                "size": 100,
                "depth": 1,
            },
        ]

        unique_files, report = remove_duplicates(files)

        assert len(unique_files) == 1
        assert unique_files[0]["path_display"] == "/a_file.txt"


class TestCombineJsonFiles:
    """Test complete JSON file combination workflow."""

    def test_combine_single_file(self):
        """Test combining a single JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test JSON file
            json_data = {
                "contents": [
                    {
                        "name": "test.txt",
                        "path_display": "/test.txt",
                        "type": "file",
                        "content_hash": "abc123",
                        "size": 1024,
                    }
                ]
            }

            json_file = Path(tmpdir) / "test.json"
            json_file.write_text(json.dumps(json_data))

            # Combine
            output_path, stats = combine_json_files(tmpdir, "all.json")

            # Verify output file exists
            assert Path(output_path).exists()

            # Verify statistics
            assert stats["source_files"] == 1
            assert stats["total_files_before"] == 1
            assert stats["total_files_after"] == 1
            assert stats["duplicate_report"]["total_duplicate_files"] == 0

            # Verify output content
            with open(output_path, "r") as f:
                output_data = json.load(f)

            assert len(output_data["files"]) == 1
            assert output_data["files"][0]["content_hash"] == "abc123"

    def test_combine_multiple_files_with_duplicates(self):
        """Test combining multiple JSON files with duplicates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create first JSON file
            json_data1 = {
                "contents": [
                    {
                        "name": "file1.txt",
                        "path_display": "/file1.txt",
                        "type": "file",
                        "content_hash": "hash1",
                        "size": 1000,
                    },
                    {
                        "name": "dup.txt",
                        "path_display": "/dup.txt",
                        "type": "file",
                        "content_hash": "hashDup",
                        "size": 500,
                    },
                ]
            }

            # Create second JSON file with duplicate
            json_data2 = {
                "contents": [
                    {
                        "name": "file2.txt",
                        "path_display": "/file2.txt",
                        "type": "file",
                        "content_hash": "hash2",
                        "size": 2000,
                    },
                    {
                        "name": "dup.txt",
                        "path_display": "/folder/dup.txt",
                        "type": "file",
                        "content_hash": "hashDup",
                        "size": 500,
                    },
                ]
            }

            json_file1 = Path(tmpdir) / "test1.json"
            json_file1.write_text(json.dumps(json_data1))

            json_file2 = Path(tmpdir) / "test2.json"
            json_file2.write_text(json.dumps(json_data2))

            # Combine
            output_path, stats = combine_json_files(tmpdir, "all.json")

            # Verify statistics
            assert stats["source_files"] == 2
            assert stats["total_files_before"] == 4
            assert stats["total_files_after"] == 3  # One duplicate removed
            assert stats["duplicate_report"]["total_duplicate_files"] == 1
            assert stats["duplicate_report"]["total_wasted_bytes"] == 500

            # Verify output content
            with open(output_path, "r") as f:
                output_data = json.load(f)

            assert len(output_data["files"]) == 3

            # Verify the shallow duplicate was kept
            dup_files = [
                f for f in output_data["files"] if f["content_hash"] == "hashDup"
            ]
            assert len(dup_files) == 1
            assert dup_files[0]["path_display"] == "/dup.txt"
            assert dup_files[0]["depth"] == 1

    def test_no_json_files_raises_error(self):
        """Test that missing JSON files raises FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                combine_json_files(tmpdir, "all.json")

    def test_invalid_directory_raises_error(self):
        """Test that invalid directory raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            combine_json_files("/nonexistent/directory", "all.json")

    def test_invalid_json_raises_error(self):
        """Test that invalid JSON raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create invalid JSON file
            json_file = Path(tmpdir) / "invalid.json"
            json_file.write_text("{ invalid json }")

            with pytest.raises(ValueError):
                combine_json_files(tmpdir, "all.json")
