# Dropbox Public Link Explorer

Recursively explores Dropbox shared/public links and exports complete file/folder metadata to JSON.

**Key Features:**
- Automatic session system - resume from interruptions
- Token auto-refresh - no expiration errors
- Configurable intervals and output directory
- Handles large folders (tested 2+ hours)
- Graceful error handling

## What is a Session?

A **session** is a named exploration of a Dropbox shared link. Each session:
- Has a unique name (auto-generated or custom)
- Saves progress automatically (every 5 minutes by default)
- Can be resumed if interrupted
- Tracks all discovered files/folders
- Stores metadata in a `.pkl` file

**Use cases:**
- **Resume interrupted work**: Power loss, crashes, or Ctrl+C won't lose progress
- **Multiple explorations**: Use different session names (`-s`) for different shared links
- **Extract data later**: Use `-x` to export session data to JSON without re-scanning

---

## Quick Start

### 1. Install uv (if not already installed)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and runner - 10-100x faster than pip!

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

### 2. Install the Package

```bash
# Install dependencies and the package
uv sync

# Or with pip
pip install -e .
```

**Why uv?**
- 10-100x faster than pip
- No virtual environment hassle
- Handles dependencies automatically
- Consistent across machines

### 3. Setup Dropbox App

1. Go to https://www.dropbox.com/developers/apps
2. Create an app (or select existing)
3. **Permissions tab** → Enable `sharing.read` permission → Submit
4. **Settings tab** → Copy your App Key and App Secret

### 4. Get Refresh Token (One-Time Setup)

Run the helper script:
```bash
uv run src/get_refresh_token.py
```

**What it does:**
- Opens browser for Dropbox authorization
- Gets a refresh token that **never expires**
- Automatically updates your `.env` file

**You'll need:**
- App Key (from Settings tab)
- App Secret (from Settings tab, click "Show")

### 5. Run the Application

There are several ways to run the application:

#### Option 1: Using the console script (recommended)
```bash
# After installation, you can run:
uv run explore
```

#### Option 2: As a Python module
```bash
uv run python -m explore
```

#### Option 3: Direct script execution
```bash
uv run python src/explore.py
```

**The application will:**
- Save progress every 5 minutes (configurable)
- Auto-resume if interrupted
- Auto-refresh tokens (no expiration)
- Export results to JSON when complete

---

## Configuration

Edit the `.env` file to customize:

```bash
# Required
DROPBOX_ACCESS_TOKEN=your_access_token
DROPBOX_SHARED_LINK=https://www.dropbox.com/...

# Recommended: Refresh token (prevents expiration)
DROPBOX_REFRESH_TOKEN=your_refresh_token
DROPBOX_APP_KEY=your_app_key
DROPBOX_APP_SECRET=your_app_secret

# Optional: Customize behavior
SESSION_INTERVAL_SECONDS=300  # Save progress every 5 minutes
OUTPUT_DIR=data                   # Output directory

# Logging configuration
LOG_LEVEL_CONSOLE=INFO            # Console log level: NONE, DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL_FILE=DEBUG              # File log level: NONE, DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_DIR=logs                      # Log files directory
```

---

## Logging

The application uses **loguru** for structured, colored logging with UTC timestamps.

### Log Levels

You can configure separate log levels for console and file output:

- **NONE** - Disable logging
- **DEBUG** - Detailed information for debugging (file operations, skipped items)
- **INFO** - General informational messages (default for console)
- **WARNING** - Warning messages (restricted items, non-critical errors)
- **ERROR** - Error messages that don't stop execution
- **CRITICAL** - Critical errors

### Configuration

Set log levels in your `.env` file:

```bash
LOG_LEVEL_CONSOLE=INFO    # What you see in the terminal
LOG_LEVEL_FILE=DEBUG      # What gets saved to log files
LOG_DIR=logs              # Where log files are stored
```

### Log Files

- **Location**: `logs/` directory (or custom via `LOG_DIR`)
- **Naming**: `YYYYMMDD-HHMMSS.log` (e.g., `20251013-142756.log`)
- **Timestamps**: All timestamps are in UTC
- **Rotation**: Automatically rotates at 100MB
- **Retention**: Keeps logs for 30 days
- **Compression**: Old logs are compressed as `.zip`

### Features

- **Colored console output** - Easy to read with color-coded log levels
- **UTC timestamps** - Consistent timezone regardless of system settings
- **Thread-safe** - Safe for concurrent operations
- **Structured logging** - Includes function name, line number, and context
- **File rotation** - Prevents log files from growing too large
- **Automatic cleanup** - Old logs are automatically removed

### Example Output

Console (colored with version display):
```
2025-10-13 14:27:56.123456 | INFO     | Dropbox Public Link Explorer v0.1.0
2025-10-13 14:27:56.234567 | INFO     | Accessing path: (root)
2025-10-13 14:27:57.345678 | INFO     | Exploring folder: /Documents
2025-10-13 14:27:58.456789 | WARNING  | Restricted access
```

The application displays its version on startup, which is automatically derived from Git tags using VCS-based versioning.

### Disabling Logging

To disable console or file logging, set the level to `NONE`:

```bash
LOG_LEVEL_CONSOLE=NONE    # No console output
LOG_LEVEL_FILE=NONE       # No log files
```

**Note**: Setting both to `NONE` will disable all logging except critical print statements that remain for backward compatibility.

---

## Fixing Common Issues

### `expired_access_token` Error

**Problem:** Token expired after ~4 hours.

**Solution:** Use refresh token (never expires)

```bash
uv run src/get_refresh_token.py
```

Follow the prompts. The script will update your `.env` automatically.

**Alternative (temporary fix):**
1. Go to https://www.dropbox.com/developers/apps
2. Generate new access token
3. Update `DROPBOX_ACCESS_TOKEN` in `.env`

WARNING: This expires in ~4 hours. Use refresh token for long operations.

---

### Resume After Interruption

If your script was interrupted (crash, Ctrl+C, power loss):

```bash
uv run explore
```

The script will automatically detect and resume from the session. No prompts or interaction needed - it's fully automated!

---

### Inspect Session Files

To view detailed information about a session file without running the full exploration:

```bash
# Inspect default session (uses SESSION_NAME or auto-generated)
uv run explore -i

# Inspect a specific session by session name
uv run explore -i -s my_session

# Inspect a specific session file
uv run explore -i session_abc123.pkl
```

**What it shows:**
- Session timestamp
- Shared link being explored
- Root folder path
- Items discovered (total, files, folders)
- Total size (bytes and human-readable)
- Restricted items (if any)
- Sample files (up to 10 with sizes and paths)

**Example output:**
```
2025-10-13 14:27:56.123456 | INFO     | Session Inspection Mode
2025-10-13 14:27:56.234567 | INFO     | Loading session: session_abc123.pkl
2025-10-13 14:27:56.345678 | INFO     | Path: /path/to/data/session_abc123.pkl
2025-10-13 14:27:56.456789 | INFO     | Session Statistics:
2025-10-13 14:27:56.567890 | INFO     | Timestamp: 2025-10-13T14:30:00
2025-10-13 14:27:56.678901 | INFO     | Shared Link: https://www.dropbox.com/...
2025-10-13 14:27:56.789012 | INFO     | Root Folder: /Documents/Project
2025-10-13 14:27:56.890123 | INFO     | Total items: 1,234 (987 files, 247 folders)
2025-10-13 14:27:56.901234 | INFO     | Visited paths: 250
2025-10-13 14:27:56.912345 | INFO     | Total Size: 5,368,709,120 bytes (5.00 GB)
```

---

### Alternative: Test Session (Legacy)

```bash
uv run tests/test_session.py
```

Shows:
- Session timestamp
- Number of visited paths
- Number of entries collected
- Sample paths

---

## Output Files

The script creates:

```
data/
├── session.pkl                    # Progress session (auto-deleted when done)
├── dropbox_metadata_YYYYMMDD_HHMMSS.json          # Main export
└── dropbox_metadata_YYYYMMDD_HHMMSS_restricted.json  # Restricted items
```

**Main JSON structure:**
```json
{
  "timestamp": "2025-10-10T12:00:00",
  "structure": "hierarchical",
  "statistics": {
    "total_files": 1234,
    "total_folders": 56,
    "total_size": 1073741824,
    "total_size_human": "1.00 GB",
    "restricted_items": 5
  },
  "contents": [
    {
      "name": "folder1",
      "type": "folder",
      "children": [
        {
          "name": "file1.txt",
          "type": "file",
          "size": 1024,
          "size_human": "1.00 KB",
          "server_modified": "2025-01-01T00:00:00"
        }
      ]
    }
  ]
}
```

---

## How It Works

### Session System

**Automatic saves:**
- Every N seconds (default: 300 = 5 minutes)
- After processing folders
- On errors or interruptions (Ctrl+C)

**What's saved:**
- All collected entries
- Visited paths (to avoid re-scanning)
- Shared link
- Timestamp

**Atomic writes:**
- Writes to temp file first
- Renames to session file (atomic operation)
- Ensures data integrity

**Auto-resume:**
- Detects session on startup
- Prompts to resume or start fresh
- Continues from last position

### Token Refresh

**Why refresh tokens?**
- Access tokens expire after ~4 hours
- Refresh tokens never expire
- Can generate new access tokens automatically

**How it works:**
1. Script uses refresh token to create Dropbox client
2. On `AuthError`, attempts to refresh authentication
3. Retries the failed operation
4. Saves session if refresh fails

**OAuth Flow:**
```
User → Authorize App → Get Auth Code → Exchange for Tokens
                                          ├─ Access Token (expires in 4h)
                                          └─ Refresh Token (never expires)
```

---

## Testing

Run comprehensive tests:

```bash
# Test session system
uv run tests/test_resume.py

# Check existing session
uv run tests/test_session.py
```

---

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DROPBOX_ACCESS_TOKEN` | Yes* | - | Short-lived access token |
| `DROPBOX_REFRESH_TOKEN` | No** | - | Refresh token (never expires) |
| `DROPBOX_APP_KEY` | No** | - | App key (needed for refresh) |
| `DROPBOX_APP_SECRET` | No** | - | App secret (needed for refresh) |
| `DROPBOX_SHARED_LINK` | Yes | - | Shared link to explore |
| `ROOT_FOLDER` | No | "" | Path within shared link to explore (can be overridden with `-p`) |
| `SESSION_NAME` | No | auto | Custom session/session name (can be overridden with `-s`) |
| `SESSION_INTERVAL_SECONDS` | No | 300 | Session save interval (seconds) |
| `OUTPUT_DIR` | No | data | Output directory for sessions and JSON |
| `LOG_LEVEL_CONSOLE` | No | INFO | Console log level (NONE, DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `LOG_LEVEL_FILE` | No | DEBUG | File log level (NONE, DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `LOG_DIR` | No | logs | Directory for log files |

\* Required if not using refresh token  
\** Recommended for long operations (prevents token expiration)

---

## Permissions Required

Your Dropbox app needs:
- `sharing.read` permission (NOT `files.metadata.read`)

**Why?** To access OTHER people's shared links, you need `sharing.read`.

**Setup:**
1. Go to https://www.dropbox.com/developers/apps
2. Select your app
3. **Permissions** tab
4. Enable **`sharing.read`**
5. Click **Submit**
6. Generate new token in **Settings** tab

---

## Troubleshooting

### "Module not found" errors

```bash
uv pip install dropbox python-dotenv requests
```

### "Permission denied" / "access_denied"

**Check permissions:**
1. App has `sharing.read` enabled
2. Shared link is public or you have access
3. Link hasn't expired

### "restricted_content" warnings

**Normal behavior.** Shared folders often have restricted items. These are:
- Logged in restricted items report
- Skipped silently
- Don't stop the scan

### Session not saving

**Check:**
- `OUTPUT_DIR` is writable
- Enough disk space
- `SESSION_INTERVAL_SECONDS` is set

**Test:**
```bash
uv run tests/test_resume.py
```

### Can't resume from session

**Possible causes:**
- Different shared link than original scan
- Session file corrupted
- Session file deleted

**Solution:**
- Say 'n' to resume prompt to start fresh
- Check `data/session.pkl` exists
- Run `uv run tests/test_session.py` to validate

---

## How to Get Refresh Token

### Automatic Method (Recommended)

```bash
uv run src/get_refresh_token.py
```

Walks you through the entire process.

### Manual Method

If you prefer to do it manually:

1. **Get App credentials:**
   - https://www.dropbox.com/developers/apps
   - Settings tab → Copy App Key and App Secret

2. **Get authorization code:**
   - Open URL (replace `YOUR_APP_KEY`):
   ```
   https://www.dropbox.com/oauth2/authorize?client_id=YOUR_APP_KEY&response_type=code&token_access_type=offline
   ```
   - Click "Allow"
   - Copy the authorization code

3. **Exchange for tokens:**
   ```bash
   curl https://api.dropbox.com/oauth2/token \
     -d code=YOUR_AUTH_CODE \
     -d grant_type=authorization_code \
     -d client_id=YOUR_APP_KEY \
     -d client_secret=YOUR_APP_SECRET
   ```

4. **Update `.env`:**
   ```bash
   DROPBOX_REFRESH_TOKEN=from_response
   DROPBOX_APP_KEY=your_app_key
   DROPBOX_APP_SECRET=your_app_secret
   ```

**Note:** `token_access_type=offline` is required to get a refresh token!

---

## Usage Examples

### Basic Usage

```bash
# With shared link in .env (using any of the three methods)
uv run explore
# or: uv run python -m explore
# or: uv run python src/explore.py

# Prompt will ask to use link from .env
```

### Command-Line Options

The explorer supports several command-line flags for different workflows. All these options work with any of the three run methods above (console script, module, or direct script).

```bash
# Continue from default session (auto-detected)
uv run explore -c

# Continue from specific session by name
uv run explore -c mysession

# Continue from specific session file
uv run explore -c mysession.pkl

# Inspect default session (view stats without exploring)
uv run explore -i

# Inspect specific session by name
uv run explore -i mysession

# Inspect with JSON output (for scripting)
uv run explore -i -j

# Extract default session to JSON without re-exploring
uv run explore -x

# Extract specific session by name
uv run explore -x mysession

# Specify a custom root folder path within the shared link
uv run explore -p /subfolder/path

# Specify a custom session name for new exploration
uv run explore -s my_custom_session

# Combine flags
uv run explore -s my_session -p /Documents
```

**Available Flags:**
- `-c, --continue [SESSION]` - Continue from session. Provide session name (e.g., 'mysession' or 'mysession.pkl') or use without argument for default session.
- `-i, --inspect [SESSION]` - Inspect session and show statistics. Provide session name (e.g., 'mysession' or 'mysession.pkl') or use without argument for default session.
- `-x, --extract [SESSION]` - Extract session to JSON. Provide session name (e.g., 'mysession' or 'mysession.pkl') or use without argument for default session.
- `-p, --path PATH` - Override ROOT_FOLDER env var - specify path within shared link to explore
- `-s, --session NAME` - Specify session name (overrides SESSION_NAME env var and auto-generated name)
- `-j, --json` - Output inspection results as JSON (use with -i flag)

### Long-Running Operation

```bash
# 1. Get refresh token (one-time)
uv run python src/get_refresh_token.py

# 2. Run the application
uv run explore

# Can run for days/weeks without issues!
```

### Resume After Crash

```bash
# Just run again - automatically resumes from session
uv run explore

# No prompts needed - fully automated!
```

### Custom Configuration

Edit `.env`:
```bash
# Save every minute
SESSION_INTERVAL_SECONDS=60

# Custom output directory
OUTPUT_DIR=my_backups

# Specify a custom session name
SESSION_NAME=my_custom_session

# Then run
uv run explore
```

---

## Features Overview

### Session System
- Auto-save progress periodically
- Resume from any interruption
- Atomic writes (data safety)
- Graceful Ctrl+C handling
- Auto-cleanup when done

### Token Management
- Refresh token support
- Auto-refresh on expiration
- Retry logic on auth errors
- Saves session before exit

### Error Handling
- Graceful degradation
- Detailed error messages
- Recovery instructions
- Continues on restricted items

### Output
- Hierarchical JSON structure
- Human-readable sizes
- Timestamps
- Statistics summary
- Restricted items report

### Configuration
- Everything via `.env`
- Sensible defaults
- No code changes needed

---

## Technical Details

### Implementation

**Language:** Python 3.12+  
**Dependencies:**
- `dropbox` - Dropbox SDK
- `python-dotenv` - Environment variables
- `loguru` - Advanced logging with colors and rotation

**Architecture:**
- `DropboxExplorer` class - Main functionality
- Session system - State persistence
- Token refresh - OAuth flow
- Recursive exploration - DFS traversal

**Key Methods:**
- `explore_shared_link()` - Main exploration loop
- `save_session()` - Persist state
- `load_session()` - Restore state
- `_refresh_client()` - Token refresh
- `_process_entries()` - Process files/folders

### File Structure

```
explore/
├── src/                    # Source code
│   ├── __main__.py         # Module entry point (python -m explore)
│   ├── explore.py          # Main script
│   ├── logger.py           # Logging configuration
│   └── get_refresh_token.py # Token helper
├── tests/                  # Test scripts
│   ├── test_session.py  # Session validator
│   └── test_resume.py      # System tests
├── data/                   # Output directory
│   ├── session_*.pkl    # Progress sessions
│   └── dropbox_metadata_*.json  # Exports
├── logs/                   # Log files directory
│   └── YYYYMMDD-HHMMSS.log # Timestamped log files
├── pyproject.toml          # Package configuration
├── .env                    # Configuration (git-ignored)
├── .env.example            # Configuration template
└── README.md               # This file
```

---

## Support

### Quick Reference

| Issue | Solution |
|-------|----------|
| Token expired | `uv run src/get_refresh_token.py` |
| Lost progress | Just run again (auto-resumes) |
| Module errors | `uv pip install dropbox python-dotenv requests` |
| Permission errors | Enable `sharing.read` in app settings |
| Session issues | `uv run tests/test_session.py` |

### Files to Check

- **`.env`** - Configuration
- **`data/session.pkl`** - Session state
- **Error messages** - Usually contain fix instructions

---

## Changelog

### Latest Version

**Added:**
- Session/resume system
- Refresh token support
- Configurable settings
- Helper script for token setup
- Comprehensive error handling
- Auto-retry on auth errors
- Graceful interruption handling

**Fixed:**
- Token expiration after 4 hours
- Lost progress on interruption
- Hardcoded output directory

**Improved:**
- User feedback and progress tracking
- Error messages with recovery steps
- Documentation and examples

---

## License

This script is provided as-is for exploring Dropbox shared links.

---

## Summary

**Before fixes:**
- Crashes after 4 hours (token expiration)
- Loses all progress on interruption
- No configuration options

**After fixes:**
- Runs indefinitely (refresh token)
- Auto-saves progress every 5 minutes
- Resumes automatically
- Fully configurable
- Production-ready

**Get started:**
```bash
uv sync                              # Install the package
uv run python src/get_refresh_token.py  # One-time setup
uv run explore                       # Run the application
```

That's it!

---

## Installation Methods

### Method 1: Using uv (recommended)

```bash
# Install dependencies and package
uv sync

# Run with console script
uv run explore

# Or run as module
uv run python -m explore
```

### Method 2: Using pip

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package
pip install -e .

# Run directly
explore

# Or as module
python -m explore
```

### Method 3: Direct script execution (no installation)

```bash
# Install dependencies only
uv pip install dropbox python-dotenv

# Run script directly
uv run python src/explore.py
```

---

## PDF Report Generator

Generate comprehensive PDF reports from session files with statistics and charts.

### Overview

The report generator processes all `.pkl` session files in the `OUTPUT_DIR` and creates a PDF report with:

- Overall summary across all directories
- **Duplicate file analysis** (automatically included)
- Individual directory statistics
- File type distribution charts (pie charts)
- Storage size by category charts (bar charts)
- Detailed category breakdowns with file counts and sizes

### Installation

The report generator requires additional dependencies:

```bash
uv sync
```

This will install:
- `matplotlib` - For generating charts
- `reportlab` - For PDF generation

### Usage

#### Basic Usage

Generate a report from all `.pkl` files in the default data directory:

```bash
uv run report
```

This will create `dropbox_report.pdf` in the `OUTPUT_DIR` (default: `data/`).

#### Custom Output File

Specify a custom output filename:

```bash
uv run report -o my_report.pdf
```

#### Custom Data Directory

Specify a different directory containing `.pkl` files:

```bash
uv run report -d /path/to/data -o custom_report.pdf
```

#### Command-Line Options

```
-o, --output <filename>     Output PDF filename (default: dropbox_report.pdf)
-d, --data-dir <directory>  Directory containing .pkl files (default: OUTPUT_DIR env or 'data')
```

### How It Works

The script follows these steps:

1. **Loads session data**: Reads all `.pkl` files from the specified directory
2. **Analyzes statistics**: For each session:
   - Counts files, folders, and total size
   - Categorizes files by type (Image, Video, Document, etc.)
   - Calculates file counts and storage per category
3. **Detects duplicates**: Automatically scans for duplicate files across all sessions (see [Duplicate File Detector](#duplicate-file-detector))
4. **Generates charts**: Creates visualizations:
   - Pie charts for file type distribution (by count)
   - Bar charts for storage size by category
5. **Builds PDF report**: Assembles a comprehensive report with:
   - Title page with overall summary
   - Duplicate file analysis section with top 10 largest duplicate groups
   - Individual pages for each directory with tables and charts

### Implementation Details

#### File Type Categories

Files are automatically categorized into:

- **Image**: jpg, png, gif, svg, etc.
- **Video**: mp4, avi, mkv, mov, etc.
- **Audio**: mp3, wav, flac, aac, etc.
- **Document**: pdf, doc, docx, txt, etc.
- **Spreadsheet**: xls, xlsx, csv, etc.
- **Presentation**: ppt, pptx, odp, key
- **Archive**: zip, rar, 7z, tar, gz, etc.
- **Code**: py, js, java, cpp, html, css, etc.
- **Data**: json, xml, yaml, sql, db, etc.
- **Executable**: exe, msi, app, deb, rpm, etc.
- **Other**: Unrecognized file types

#### Direct Import

The script imports the `explore` module directly rather than spawning shell processes:

```python
from src.explore import DropboxExplorer

# Use DropboxExplorer methods like _human_readable_size()
```

This provides:
- Better performance (no subprocess overhead)
- Type safety and IDE support
- Direct access to utility functions

#### Output Structure

The generated PDF includes:

1. **Title Page**
   - Report title
   - Generation timestamp
   - Overall summary table

2. **Directory Pages** (one per `.pkl` file)
   - Directory information table
   - File type breakdown table
   - File distribution pie chart
   - Storage size bar chart

#### Temporary Files

Charts are temporarily saved to `<data_dir>/.charts/` during generation and automatically cleaned up after the PDF is created.

### Examples

#### Generate report for all directories:

```bash
cd /Users/mesca/Documents/Pro/Missions/TTH/code/explore
uv run report -o dropbox_statistics.pdf
```

#### Generate report with custom data directory:

```bash
uv run report -d ~/my_dropbox_data -o analysis_report.pdf
```

### Code Quality

The script follows all guidelines from `CLAUDE.md`:

- Comprehensive docstrings (NumPy style)
- Full type hints
- Structured logging with loguru
- Clear variable names
- Single responsibility functions
- Proper error handling

### Troubleshooting

#### No .pkl files found

```
ERROR: No .pkl files found in data
```

**Solution**: Ensure you've run `uv run explore` to create session files first, or specify the correct directory with `-d`.

#### Missing dependencies

```
ModuleNotFoundError: No module named 'matplotlib'
```

**Solution**: Run `uv sync` to install all dependencies.

#### Permission errors

```
ERROR: Failed to generate PDF report: [Errno 13] Permission denied
```

**Solution**: Ensure you have write permissions to the output directory.

#### Session File Compatibility

The report generator is compatible with all session files created by the `explore` command. It uses the `-i -j` inspection functionality internally to extract statistics without re-exploring Dropbox.

---

## Duplicate File Detector

Identify duplicate files across all session files and calculate recoverable storage space.

> **Note:** Duplicate detection is automatically included in the [PDF Report Generator](#pdf-report-generator). Use this standalone tool when you need detailed JSON output or want to analyze duplicates separately.

### Overview

The duplicate detector scans all `.pkl` session files in the `OUTPUT_DIR` and identifies duplicate files based on their `content_hash` metadata. This helps you:

- Find identical files stored in multiple locations
- Calculate total wasted storage space
- Identify the largest duplicate files for cleanup priority
- Generate detailed JSON reports of all duplicates

### Usage

#### Basic Usage

Scan for duplicates in the default data directory:

```bash
uv run duplicates
```

This will output a summary and JSON report to stdout.

#### Save Results to File

Generate a JSON report file:

```bash
uv run duplicates -o duplicates_report.json
```

#### Pretty-Print JSON

Format JSON output for readability:

```bash
uv run duplicates --pretty
```

#### Custom Data Directory

Specify a different directory containing `.pkl` files:

```bash
uv run duplicates -d /path/to/data -o report.json
```

#### Command-Line Options

```
-d, --data-dir <directory>              Directory containing .pkl files (default: OUTPUT_DIR env or 'data')
-o, --output <file>                     Output JSON file path (default: print to stdout)
--pretty                                Pretty-print JSON output
--log-level-console <level>             Console log level (NONE, DEBUG, INFO, WARNING, ERROR, CRITICAL)
--log-level-file <level>                File log level (NONE, DEBUG, INFO, WARNING, ERROR, CRITICAL)
```

### How It Works

The duplicate detector:

1. **Scans session files**: Reads all `.pkl` files from the specified directory
2. **Extracts file metadata**: Collects file paths, content hashes, and sizes
3. **Identifies duplicates**: Groups files by their `content_hash` (Dropbox's file fingerprint)
4. **Calculates waste**: Determines recoverable space for each duplicate group
5. **Generates report**: Outputs JSON with summary statistics and detailed duplicate groups

### Output Format

The JSON report has the following structure:

```json
{
  "summary": {
    "total_duplicate_files": 555014,
    "total_wasted_bytes": 703119450459,
    "total_wasted_size": "654.83 GB",
    "unique_hashes_with_duplicates": 209903,
    "scanned_pkl_files": 13
  },
  "duplicate_groups": [
    {
      "content_hash": "280539fdd34a5f7b61cf8ddadcf89ce1531f2ecf6783f89447714ac9df0d2b6b",
      "duplicate_count": 6,
      "file_size_bytes": 2393959844,
      "file_size_human": "2.23 GB",
      "wasted_bytes": 11969799220,
      "wasted_size_human": "11.15 GB",
      "file_paths": [
        "/path/to/file1.zip",
        "/path/to/file2.zip",
        ...
      ]
    },
    ...
  ]
}
```

#### Summary Fields

- `total_duplicate_files`: Total number of duplicate copies (excluding originals)
- `total_wasted_bytes`: Total recoverable storage space in bytes
- `total_wasted_size`: Human-readable total wasted space
- `unique_hashes_with_duplicates`: Number of unique files that have duplicates
- `scanned_pkl_files`: Number of session files analyzed

#### Duplicate Group Fields

- `content_hash`: Dropbox content hash identifying the file
- `duplicate_count`: Number of copies of this file
- `file_size_bytes`: Size of one instance in bytes
- `file_size_human`: Human-readable file size
- `wasted_bytes`: Recoverable space for this group (file_size × (duplicate_count - 1))
- `wasted_size_human`: Human-readable wasted space
- `file_paths`: List of all paths where this file appears

### Examples

#### Generate duplicate report with pretty formatting:

```bash
cd /Users/mesca/Documents/Pro/Missions/TTH/code/explore
uv run duplicates --pretty -o data/duplicates.json
```

#### Scan custom directory:

```bash
uv run duplicates -d ~/my_dropbox_data --pretty
```

#### Silent mode (only JSON output):

```bash
uv run duplicates --log-level-console NONE -o report.json
```

### Understanding Content Hash

Dropbox's `content_hash` is a cryptographic hash that uniquely identifies file content:

- Files with identical content have the same hash, regardless of name or location
- Even if a file is renamed or moved, its hash remains the same
- Different files will have different hashes (with extremely high probability)
- This makes it perfect for identifying true duplicates vs. files with similar names

### Use Cases

1. **Storage Cleanup**: Identify large duplicate files consuming significant space
2. **Data Deduplication**: Find files that can be replaced with links or references
3. **Archive Analysis**: Understand redundancy in archived project folders
4. **Migration Planning**: Calculate actual unique data size before migration
5. **Compliance**: Ensure no duplicate copies of sensitive files exist

### Code Quality

The script follows all guidelines from `CLAUDE.md`:

- Comprehensive docstrings (NumPy style)
- Full type hints
- Structured logging with loguru
- Clear variable names
- Single responsibility functions
- Proper error handling

### Troubleshooting

#### No .pkl files found

```
ERROR: No .pkl files found in data
```

**Solution**: Ensure you've run `uv run explore` to create session files first, or specify the correct directory with `-d`.

#### Large datasets

For very large session files (100k+ files), the analysis may take several minutes. Progress is logged to help track the operation.

#### Memory usage

The tool loads all file metadata into memory. For extremely large datasets (1M+ files), ensure you have sufficient RAM available.
