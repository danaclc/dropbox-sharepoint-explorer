#!/usr/bin/env python3
"""
PDF Report Generator for Dropbox Explorer Sessions

Generates comprehensive PDF reports from .pkl session files including:
- Statistics for each directory
- File type distribution with charts
- Overall summary across all directories
"""

import argparse
import glob as glob_module
import json
import os
import pickle
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src import logger
from src.duplicates import find_duplicates
from src.explore import DropboxExplorer

# Constants
DEFAULT_OUTPUT_DIR = "data"


def load_session_stats(pkl_file: str) -> dict[str, Any]:
    """
    Load and analyze statistics from a session file.

    Args:
        pkl_file: Path to .pkl session file

    Returns:
        dict[str, Any]: Dictionary containing session statistics including:
            - session_name: Name of the session (filename without .pkl)
            - timestamp: ISO-8601 timestamp
            - shared_link: Dropbox shared link URL
            - root_folder: Root folder path
            - total_items: Total count of items
            - total_files: Count of files
            - total_folders: Count of folders
            - total_size: Total size in bytes
            - total_size_human: Human-readable size
            - unique_extensions: Count of unique file extensions
            - restricted_items: Count of restricted items
            - categories: List of file type categories with stats
    """
    logger.info(f"Loading session: {os.path.basename(pkl_file)}")

    try:
        with open(pkl_file, "rb") as f:
            checkpoint_data = pickle.load(f)

        # Extract basic information
        timestamp = checkpoint_data.get("timestamp", "Unknown")
        shared_link = checkpoint_data.get("shared_link", "Unknown")
        root_folder = checkpoint_data.get("root_folder", "")
        all_items = checkpoint_data.get("all_items", [])
        restricted_items = checkpoint_data.get("restricted_items", [])

        # Calculate statistics
        files = [item for item in all_items if item.get("type") == "file"]
        folders = [item for item in all_items if item.get("type") == "folder"]
        total_size = sum(item.get("size", 0) for item in files)

        # Collect file type categories
        extensions = set()
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

        # Extension to category mapping
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

        # Categorize files
        for file in files:
            name = file.get("name", "")
            file_size = file.get("size", 0)

            if "." in name:
                ext = name.rsplit(".", 1)[-1].lower()
                extensions.add(ext)
                category = ext_to_category.get(ext, "Other")
            else:
                extensions.add("(no extension)")
                category = "Other"

            category_stats[category]["count"] += 1
            category_stats[category]["size"] += file_size

        # Prepare category information
        categories_info = []
        for category, stats in category_stats.items():
            if stats["count"] > 0:
                cat_count = stats["count"]
                cat_size = stats["size"]
                cat_pct = (cat_count / len(files) * 100) if files else 0
                cat_size_pct = (cat_size / total_size * 100) if total_size else 0

                categories_info.append(
                    {
                        "category": category,
                        "file_count": cat_count,
                        "file_percentage": round(cat_pct, 1),
                        "total_size": cat_size,
                        "total_size_human": DropboxExplorer._human_readable_size(
                            cat_size
                        ),
                        "size_percentage": round(cat_size_pct, 1),
                    }
                )

        # Sort by file count descending
        categories_info.sort(key=lambda x: x["file_count"], reverse=True)

        return {
            "session_name": Path(pkl_file).stem,
            "pkl_file": pkl_file,
            "timestamp": timestamp,
            "shared_link": shared_link,
            "root_folder": root_folder if root_folder else "(root of shared link)",
            "total_items": len(all_items),
            "total_files": len(files),
            "total_folders": len(folders),
            "total_size": total_size,
            "total_size_human": DropboxExplorer._human_readable_size(total_size),
            "unique_extensions": len(extensions),
            "restricted_items": len(restricted_items),
            "categories": categories_info,
        }

    except Exception as e:
        logger.error(f"Error loading {pkl_file}: {e}")
        raise


def compute_overall_stats(all_session_stats: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compute overall statistics across all sessions.

    Args:
        all_session_stats: List of session statistics dictionaries

    Returns:
        dict[str, Any]: Overall statistics including aggregated category data
    """
    # Aggregate category data across all sessions
    overall_categories = {}

    for session_stats in all_session_stats:
        for cat in session_stats["categories"]:
            category_name = cat["category"]
            if category_name not in overall_categories:
                overall_categories[category_name] = {"count": 0, "size": 0}

            overall_categories[category_name]["count"] += cat["file_count"]
            overall_categories[category_name]["size"] += cat["total_size"]

    # Calculate totals
    total_files = sum(cat["count"] for cat in overall_categories.values())
    total_size = sum(cat["size"] for cat in overall_categories.values())

    # Prepare category information with percentages
    categories_info = []
    for category, stats in overall_categories.items():
        cat_count = stats["count"]
        cat_size = stats["size"]
        cat_pct = (cat_count / total_files * 100) if total_files else 0
        cat_size_pct = (cat_size / total_size * 100) if total_size else 0

        categories_info.append(
            {
                "category": category,
                "file_count": cat_count,
                "file_percentage": round(cat_pct, 1),
                "total_size": cat_size,
                "total_size_human": DropboxExplorer._human_readable_size(cat_size),
                "size_percentage": round(cat_size_pct, 1),
            }
        )

    # Sort by file count descending
    categories_info.sort(key=lambda x: x["file_count"], reverse=True)

    return {
        "total_files": total_files,
        "total_size": total_size,
        "total_size_human": DropboxExplorer._human_readable_size(total_size),
        "categories": categories_info,
    }


def generate_category_chart(
    stats_dict: dict[str, Any], output_path: str, title: str = "File Type Distribution"
) -> None:
    """
    Generate a pie chart for file type categories with improved aesthetics.

    Args:
        stats_dict: Statistics dictionary (session or overall)
        output_path: Path to save the chart image
        title: Chart title
    """
    categories = stats_dict.get("categories", [])

    if not categories:
        logger.warning(f"No categories to chart for {title}")
        return

    # Extract data for pie chart (all categories, not just top 10)
    labels = [cat["category"] for cat in categories]
    sizes = [cat["file_count"] for cat in categories]
    percentages = [cat["file_percentage"] for cat in categories]

    # Define colors for better aesthetics
    colors_palette = [
        "#FF6B6B",
        "#4ECDC4",
        "#45B7D1",
        "#FFA07A",
        "#98D8C8",
        "#F7DC6F",
        "#BB8FCE",
        "#85C1E2",
        "#F8B739",
        "#52B788",
        "#AED9E0",
    ]

    # Create pie chart with improved styling
    fig, ax = plt.subplots(figsize=(12, 10))

    # Custom autopct function to show percentage only for slices >= 2%
    def autopct_format(pct):
        return f"{pct:.1f}%" if pct >= 2 else ""

    wedges, texts, autotexts = ax.pie(
        sizes,
        autopct=autopct_format,
        startangle=90,
        colors=colors_palette[: len(labels)],
        textprops={"fontsize": 10, "weight": "bold"},
        pctdistance=0.85,
        labeldistance=1.05,  # Distance of labels from center
    )

    # Improve label positioning and readability
    for i, (wedge, text, autotext) in enumerate(zip(wedges, texts, autotexts)):
        # Make percentage text white for better visibility
        autotext.set_color("white")
        autotext.set_fontsize(9)

        # Get the angle for this wedge
        angle = (wedge.theta2 + wedge.theta1) / 2.0

        # For small slices (< 5%), use leader lines and move labels outside
        if percentages[i] < 5:
            # Position label further out with leader line
            x = 1.3 * plt.np.cos(plt.np.radians(angle))
            y = 1.3 * plt.np.sin(plt.np.radians(angle))

            # Set smaller font for small slices
            text.set_fontsize(8)
            text.set_position((x, y))

            # Add a line from pie edge to label
            connectionstyle = "arc3,rad=0.1"
            text.set_bbox(
                dict(
                    boxstyle="round,pad=0.3",
                    facecolor="white",
                    edgecolor="gray",
                    alpha=0.8,
                )
            )

            # Draw connection line
            pie_x = 1.0 * plt.np.cos(plt.np.radians(angle))
            pie_y = 1.0 * plt.np.sin(plt.np.radians(angle))
            ax.plot(
                [pie_x, x],
                [pie_y, y],
                color="gray",
                linewidth=0.5,
                linestyle="--",
                alpha=0.6,
            )
        else:
            # Normal size labels
            text.set_fontsize(10)

        # Set the label text with percentage for context
        text.set_text(f"{labels[i]}\n({percentages[i]:.1f}%)")

    ax.set_title(title, fontsize=16, weight="bold", pad=20)
    plt.axis("equal")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.debug(f"Generated chart: {output_path}")


def generate_size_chart(
    stats_dict: dict[str, Any], output_path: str, title: str = "Storage by Category"
) -> None:
    """
    Generate a bar chart for storage size by category with improved aesthetics.

    Args:
        stats_dict: Statistics dictionary (session or overall)
        output_path: Path to save the chart image
        title: Chart title
    """
    categories = stats_dict.get("categories", [])

    if not categories:
        logger.warning(f"No categories to chart for {title}")
        return

    # Extract data for bar chart (sorted by size)
    sorted_by_size = sorted(categories, key=lambda x: x["total_size"], reverse=True)
    labels = [cat["category"] for cat in sorted_by_size]
    sizes_gb = [cat["total_size"] / (1024**3) for cat in sorted_by_size]

    # Create bar chart with improved styling
    fig, ax = plt.subplots(figsize=(12, 7))

    # Use gradient colors
    colors_gradient = plt.cm.viridis(plt.np.linspace(0.3, 0.9, len(labels)))

    bars = ax.bar(
        labels, sizes_gb, color=colors_gradient, edgecolor="black", linewidth=0.5
    )

    ax.set_xlabel("Category", fontsize=12, weight="bold")
    ax.set_ylabel("Storage Size (GB)", fontsize=12, weight="bold")
    ax.set_title(title, fontsize=16, weight="bold", pad=20)
    ax.tick_params(axis="x", rotation=45)
    plt.setp(ax.get_xticklabels(), ha="right", fontsize=10)

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        label_text = f"{height:.2f}" if height >= 0.01 else f"{height:.3f}"
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            label_text,
            ha="center",
            va="bottom",
            fontsize=9,
            weight="bold",
        )

    # Add grid for better readability
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.debug(f"Generated size chart: {output_path}")


def build_pdf_report(
    all_session_stats: list[dict[str, Any]],
    output_pdf: str,
    charts_dir: str,
    duplicate_data: dict[str, Any] | None = None,
) -> None:
    """
    Build a comprehensive PDF report from session statistics.

    Args:
        all_session_stats: List of session statistics dictionaries
        output_pdf: Path to output PDF file
        charts_dir: Directory containing chart images
        duplicate_data: Optional duplicate file analysis data from find_duplicates()
    """
    logger.info(f"Building PDF report: {output_pdf}")

    doc = SimpleDocTemplate(output_pdf, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Custom styles with better hierarchy
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=26,
        spaceAfter=20,
        textColor=colors.HexColor("#2C3E50"),
        alignment=1,  # Center
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=18,
        spaceAfter=15,
        spaceBefore=10,
        textColor=colors.HexColor("#34495E"),
    )
    subheading_style = ParagraphStyle(
        "CustomSubheading",
        parent=styles["Heading3"],
        fontSize=14,
        spaceAfter=10,
        spaceBefore=8,
        textColor=colors.HexColor("#7F8C8D"),
    )
    normal_style = styles["Normal"]

    # Title page
    story.append(Paragraph("Dropbox Directory Statistics Report", title_style))
    story.append(
        Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ParagraphStyle("DateStyle", parent=normal_style, alignment=1, fontSize=10),
        )
    )
    story.append(Spacer(1, 0.5 * inch))

    # Overall Summary
    total_files = sum(s["total_files"] for s in all_session_stats)
    total_folders = sum(s["total_folders"] for s in all_session_stats)
    total_size = sum(s["total_size"] for s in all_session_stats)
    total_size_human = DropboxExplorer._human_readable_size(total_size)

    story.append(Paragraph("Overall Summary", heading_style))
    summary_data = [
        ["Metric", "Value"],
        ["Total Directories Analyzed", str(len(all_session_stats))],
        ["Total Files", f"{total_files:,}"],
        ["Total Folders", f"{total_folders:,}"],
        ["Total Storage", total_size_human],
    ]

    summary_table = Table(summary_data, colWidths=[3 * inch, 3 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495E")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("TOPPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ECF0F1")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#BDC3C7")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F8F9FA")],
                ),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 0.4 * inch))

    # Compute and display overall file type breakdown
    overall_stats = compute_overall_stats(all_session_stats)

    story.append(Paragraph("Overall File Type Breakdown", subheading_style))
    overall_category_data = [["Category", "Files", "% Files", "Size", "% Size"]]
    for cat in overall_stats["categories"]:
        overall_category_data.append(
            [
                cat["category"],
                f"{cat['file_count']:,}",
                f"{cat['file_percentage']:.1f}%",
                cat["total_size_human"],
                f"{cat['size_percentage']:.1f}%",
            ]
        )

    overall_category_table = Table(
        overall_category_data,
        colWidths=[1.5 * inch, 1 * inch, 1 * inch, 1.5 * inch, 1 * inch],
    )
    overall_category_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495E")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("TOPPADDING", (0, 0), (-1, 0), 12),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#BDC3C7")),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F8F9FA")],
                ),
            ]
        )
    )
    story.append(overall_category_table)
    story.append(Spacer(1, 0.3 * inch))

    # Add overall charts side-by-side with KeepTogether
    overall_category_chart = os.path.join(charts_dir, "overall_category.png")
    overall_size_chart = os.path.join(charts_dir, "overall_size.png")

    if os.path.exists(overall_category_chart) and os.path.exists(overall_size_chart):
        from reportlab.platypus import Image

        # Both charts vertically on same page - reduced sizes to fit
        chart_section = [
            Paragraph("Overall File Type Distribution", subheading_style),
            Image(overall_category_chart, width=5 * inch, height=3.8 * inch),
            Spacer(1, 0.15 * inch),
            Paragraph("Overall Storage by Category", subheading_style),
            Image(overall_size_chart, width=5 * inch, height=2.5 * inch),
        ]
        story.append(KeepTogether(chart_section))
    elif os.path.exists(overall_category_chart):
        from reportlab.platypus import Image

        chart_section = [
            Paragraph("Overall File Type Distribution", subheading_style),
            Image(overall_category_chart, width=5.5 * inch, height=4.5 * inch),
            Spacer(1, 0.2 * inch),
        ]
        story.append(KeepTogether(chart_section))
    elif os.path.exists(overall_size_chart):
        from reportlab.platypus import Image

        chart_section = [
            Paragraph("Overall Storage by Category", subheading_style),
            Image(overall_size_chart, width=5.5 * inch, height=3.5 * inch),
        ]
        story.append(KeepTogether(chart_section))

    # Add duplicate file analysis if available
    if duplicate_data:
        story.append(PageBreak())
        story.append(Paragraph("Duplicate File Analysis", heading_style))
        story.append(Spacer(1, 0.2 * inch))

        # Duplicate summary
        dup_summary = duplicate_data["summary"]
        dup_summary_data = [
            ["Metric", "Value"],
            ["Scanned Session Files", f"{dup_summary['scanned_pkl_files']:,}"],
            [
                "Unique Files with Duplicates",
                f"{dup_summary['unique_hashes_with_duplicates']:,}",
            ],
            ["Total Duplicate Files", f"{dup_summary['total_duplicate_files']:,}"],
            [
                "Total Wasted Space",
                f"{dup_summary['total_wasted_size']} ({dup_summary['total_wasted_bytes']:,} bytes)",
            ],
        ]

        dup_summary_table = Table(dup_summary_data, colWidths=[3 * inch, 3 * inch])
        dup_summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E74C3C")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("TOPPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FADBD8")),
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#BDC3C7")),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#FEF5E7")],
                    ),
                ]
            )
        )
        story.append(dup_summary_table)
        story.append(Spacer(1, 0.3 * inch))

        # Top 10 duplicate groups by wasted space
        story.append(Paragraph("Top 10 Largest Duplicate Groups", subheading_style))
        story.append(Spacer(1, 0.1 * inch))

        top_duplicates = duplicate_data["duplicate_groups"][:10]
        if top_duplicates:
            dup_detail_data = [
                ["Rank", "Copies", "File Size", "Wasted Space", "Sample Path"]
            ]
            for rank, dup_group in enumerate(top_duplicates, 1):
                # Get first path as sample (truncate if too long)
                sample_path = dup_group["file_paths"][0]
                if len(sample_path) > 60:
                    sample_path = "..." + sample_path[-57:]

                dup_detail_data.append(
                    [
                        str(rank),
                        str(dup_group["duplicate_count"]),
                        dup_group["file_size_human"],
                        dup_group["wasted_size_human"],
                        sample_path,
                    ]
                )

            dup_detail_table = Table(
                dup_detail_data,
                colWidths=[0.5 * inch, 0.7 * inch, 1 * inch, 1.3 * inch, 3 * inch],
            )
            dup_detail_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E74C3C")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (3, -1), "CENTER"),
                        ("ALIGN", (4, 0), (4, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 9),
                        ("FONTSIZE", (0, 1), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("TOPPADDING", (0, 0), (-1, 0), 12),
                        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#BDC3C7")),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#FEF5E7")],
                        ),
                    ]
                )
            )
            story.append(dup_detail_table)
        else:
            story.append(Paragraph("No duplicate files found.", normal_style))

    # Add page break before individual directory details
    story.append(PageBreak())

    # Individual directory reports
    for idx, session_stats in enumerate(all_session_stats, 1):
        story.append(
            Paragraph(
                f"Directory {idx}: {session_stats['session_name']}", heading_style
            )
        )

        # Directory info table
        info_data = [
            ["Metric", "Value"],
            ["Timestamp", session_stats["timestamp"]],
            ["Root Folder", session_stats["root_folder"]],
            ["Total Items", f"{session_stats['total_items']:,}"],
            ["Files", f"{session_stats['total_files']:,}"],
            ["Folders", f"{session_stats['total_folders']:,}"],
            ["Storage Size", session_stats["total_size_human"]],
            ["Unique Extensions", str(session_stats["unique_extensions"])],
            ["Restricted Items", str(session_stats["restricted_items"])],
        ]

        info_table = Table(info_data, colWidths=[2.5 * inch, 3.5 * inch])
        info_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495E")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("TOPPADDING", (0, 0), (-1, 0), 12),
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#BDC3C7")),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#F8F9FA")],
                    ),
                ]
            )
        )
        story.append(info_table)
        story.append(Spacer(1, 0.3 * inch))

        # Category breakdown table
        if session_stats["categories"]:
            story.append(Paragraph("File Type Breakdown", subheading_style))
            category_data = [["Category", "Files", "% Files", "Size", "% Size"]]
            for cat in session_stats["categories"]:
                category_data.append(
                    [
                        cat["category"],
                        f"{cat['file_count']:,}",
                        f"{cat['file_percentage']:.1f}%",
                        cat["total_size_human"],
                        f"{cat['size_percentage']:.1f}%",
                    ]
                )

            category_table = Table(
                category_data,
                colWidths=[1.5 * inch, 1 * inch, 1 * inch, 1.5 * inch, 1 * inch],
            )
            category_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495E")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("TOPPADDING", (0, 0), (-1, 0), 12),
                        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#BDC3C7")),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#F8F9FA")],
                        ),
                    ]
                )
            )
            story.append(category_table)
            story.append(Spacer(1, 0.3 * inch))

        # Add charts side-by-side with KeepTogether to prevent page breaks
        chart_file = os.path.join(
            charts_dir, f"{session_stats['session_name']}_category.png"
        )
        size_chart_file = os.path.join(
            charts_dir, f"{session_stats['session_name']}_size.png"
        )

        if os.path.exists(chart_file) and os.path.exists(size_chart_file):
            from reportlab.platypus import Image

            # Both charts vertically on same page - reduced sizes to fit
            chart_section = [
                Paragraph("File Type Distribution", subheading_style),
                Image(chart_file, width=5 * inch, height=3.8 * inch),
                Spacer(1, 0.15 * inch),
                Paragraph("Storage by Category", subheading_style),
                Image(size_chart_file, width=5 * inch, height=2.5 * inch),
            ]
            story.append(KeepTogether(chart_section))
        elif os.path.exists(chart_file):
            from reportlab.platypus import Image

            chart_section = [
                Paragraph("File Type Distribution", subheading_style),
                Image(chart_file, width=5.5 * inch, height=4.5 * inch),
                Spacer(1, 0.2 * inch),
            ]
            story.append(KeepTogether(chart_section))
        elif os.path.exists(size_chart_file):
            from reportlab.platypus import Image

            chart_section = [
                Paragraph("Storage by Category", subheading_style),
                Image(size_chart_file, width=5.5 * inch, height=3.5 * inch),
            ]
            story.append(KeepTogether(chart_section))

        # Add page break between directories (except after the last one)
        if idx < len(all_session_stats):
            story.append(PageBreak())

    # Build PDF
    doc.build(story)
    logger.success(f"PDF report generated: {output_pdf}")


def main() -> None:
    """
    Main function to generate PDF reports from session files.

    Processes all .pkl files in OUTPUT_DIR, generates statistics and charts,
    and creates a comprehensive PDF report with individual directory details
    and an overall summary.
    """
    # Configure logging
    from src.logger import configure_logging

    console_level = os.getenv("LOG_LEVEL_CONSOLE", "INFO")
    file_level = os.getenv("LOG_LEVEL_FILE", "DEBUG")
    log_dir = os.getenv("LOG_DIR", "logs")

    configure_logging(
        console_level=console_level,
        file_level=file_level,
        log_dir=log_dir,
    )

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Generate PDF reports from Dropbox Explorer session files"
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_pdf",
        type=str,
        default="dropbox_report.pdf",
        help="Output PDF filename (default: dropbox_report.pdf)",
    )
    parser.add_argument(
        "-d",
        "--data-dir",
        dest="data_dir",
        type=str,
        default=None,
        help="Directory containing .pkl files (default: OUTPUT_DIR env or 'data')",
    )
    args = parser.parse_args()

    # Determine data directory
    data_dir = args.data_dir or os.getenv("OUTPUT_DIR", DEFAULT_OUTPUT_DIR)

    if not os.path.exists(data_dir):
        logger.error(f"Data directory not found: {data_dir}")
        sys.exit(1)

    logger.info("Dropbox Directory Statistics Report Generator")
    logger.info(f"Data directory: {data_dir}")

    # Find all .pkl files
    pkl_pattern = os.path.join(data_dir, "*.pkl")
    pkl_files = sorted(glob_module.glob(pkl_pattern))

    if not pkl_files:
        logger.error(f"No .pkl files found in {data_dir}")
        sys.exit(1)

    logger.info(f"Found {len(pkl_files)} session file(s)")

    # Load statistics from all sessions
    all_session_stats = []
    for pkl_file in pkl_files:
        try:
            stats = load_session_stats(pkl_file)
            all_session_stats.append(stats)
        except Exception as e:
            logger.warning(f"Skipping {pkl_file}: {e}")

    if not all_session_stats:
        logger.error("No valid session files to process")
        sys.exit(1)

    logger.success(f"Loaded statistics from {len(all_session_stats)} session(s)")

    # Create temporary directory for charts
    charts_dir = os.path.join(data_dir, ".charts")
    os.makedirs(charts_dir, exist_ok=True)

    # Generate charts for each session
    logger.info("Generating individual directory charts...")
    for session_stats in all_session_stats:
        chart_path = os.path.join(
            charts_dir, f"{session_stats['session_name']}_category.png"
        )
        size_chart_path = os.path.join(
            charts_dir, f"{session_stats['session_name']}_size.png"
        )

        try:
            generate_category_chart(
                session_stats,
                chart_path,
                f"File Type Distribution - {session_stats['session_name']}",
            )
            generate_size_chart(
                session_stats,
                size_chart_path,
                f"Storage by Category - {session_stats['session_name']}",
            )
        except Exception as e:
            logger.warning(
                f"Failed to generate charts for {session_stats['session_name']}: {e}"
            )

    # Generate overall charts
    logger.info("Generating overall summary charts...")
    overall_stats = compute_overall_stats(all_session_stats)
    overall_category_chart = os.path.join(charts_dir, "overall_category.png")
    overall_size_chart = os.path.join(charts_dir, "overall_size.png")

    try:
        generate_category_chart(
            overall_stats, overall_category_chart, "Overall File Type Distribution"
        )
        generate_size_chart(
            overall_stats, overall_size_chart, "Overall Storage by Category"
        )
    except Exception as e:
        logger.warning(f"Failed to generate overall charts: {e}")

    # Run duplicate file analysis
    logger.info("Running duplicate file analysis...")
    duplicate_data = None
    try:
        duplicate_data = find_duplicates(data_dir)
        logger.success(
            f"Duplicate analysis complete: {duplicate_data['summary']['unique_hashes_with_duplicates']} "
            f"duplicate groups found, {duplicate_data['summary']['total_wasted_size']} wasted space"
        )
    except Exception as e:
        logger.warning(
            f"Failed to analyze duplicates, continuing without duplicate data: {e}"
        )

    # Generate PDF report
    output_pdf = os.path.join(data_dir, args.output_pdf)
    try:
        build_pdf_report(all_session_stats, output_pdf, charts_dir, duplicate_data)
    except Exception as e:
        logger.error(f"Failed to generate PDF report: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Clean up charts directory (optional)
    try:
        import shutil

        shutil.rmtree(charts_dir)
        logger.debug(f"Cleaned up temporary charts directory: {charts_dir}")
    except Exception:
        pass

    logger.success("Report generation complete!")


if __name__ == "__main__":
    main()
