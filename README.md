# Dropbox Public Link Explorer

A robust Python tool to recursively explore Dropbox shared/public links and export complete file/folder metadata to JSON. Built with automatic session management, token refresh, and comprehensive error handling for production use.

## Features

- **Recursive Exploration** - Traverses entire directory trees from shared Dropbox links
- **Session Management** - Auto-saves progress periodically and resumes from interruptions
- **Token Auto-Refresh** - Never expires using OAuth refresh tokens for unlimited runtime
- **Comprehensive Export** - Exports file/folder structure, sizes, timestamps, content hashes to JSON
- **PDF Report Generation** - Create comprehensive PDF reports with statistics and charts
- **Duplicate File Detection** - Identify duplicate files and calculate recoverable storage space
- **JSON File Combiner** - Merge multiple JSON exports and remove duplicates by path depth
- **Graceful Error Handling** - Continues on restricted items, logs detailed errors
- **Production-Ready** - Atomic writes, crash recovery, structured logging with rotation

---

## Quick Start

Get up and running in 3 steps:

**1. Install**
```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
# or: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# Install dependencies
uv sync
```

**2. Setup Dropbox**
- Go to https://www.dropbox.com/developers/apps
- Create/select app → Enable `sharing.read` permission → Get App Key/Secret
- Run: `uv run src/get_refresh_token.py` (opens browser for authorization)
- Add your shared link to `.env`: `DROPBOX_SHARED_LINK=https://...`

**3. Run**
```bash
uv run explore
```

Done! The explorer handles session management, token refresh, and resume automatically.

---

## Installation Options

**Option 1: Using uv (Recommended)**
```bash
cd /path/to/explore
uv sync
uv run explore
```

**Option 2: Using pip**
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
explore
```

**Option 3: Direct Script (No Installation)**
```bash
uv pip install dropbox python-dotenv loguru
uv run python src/explore.py
```

---

## Usage

### Basic Exploration

```bash
# Start exploration (uses link from .env)
uv run explore

# Continue from previous session (auto-detected)
uv run explore -c

# Specify custom session name
uv run explore -s backup_2025

# Explore specific subdirectory
uv run explore -p /Documents/Project
```

### Session Management

```bash
# Continue from specific session
uv run explore -c mysession

# Inspect session stats without re-exploring
uv run explore -i mysession

# Extract session to JSON without re-exploring
uv run explore -x mysession

# Inspect with JSON output (for scripting)
uv run explore -i mysession -j
```

### Command-Line Options

| Option | Description |
|--------|-------------|
| `-c, --continue [SESSION]` | Continue from session (name or file) |
| `-i, --inspect [SESSION]` | Inspect session and show statistics |
| `-x, --extract [SESSION]` | Extract session to JSON |
| `-p, --path PATH` | Override ROOT_FOLDER - path within shared link |
| `-s, --session NAME` | Specify custom session name |
| `-j, --json` | Output inspection results as JSON (use with -i) |

### Additional Tools

**Generate PDF Report:**
```bash
# Generate report from all sessions
uv run report

# Custom output file and data directory
uv run report -o my_report.pdf -d /path/to/data
```

**Detect Duplicate Files:**
```bash
# Basic duplicate detection
uv run duplicates

# Save to JSON with pretty formatting
uv run duplicates -o duplicates.json --pretty

# Custom data directory
uv run duplicates -d /path/to/data --pretty
```

**Combine JSON Files:**
```bash
# Merge all JSON files and remove duplicates
uv run combine

# Custom output file
uv run combine -o combined.json

# Custom data directory
uv run combine -d /path/to/json/files
```

---

## How It Works

### Session System

The explorer automatically saves progress to session files (`.pkl`):

- **Auto-saves** every 5 minutes (configurable)
- **Atomic writes** ensure data integrity
- **Auto-resumes** on restart - no data loss
- **Preserves state**: visited paths, collected entries, restricted items

If interrupted (crash, Ctrl+C, power loss), just run again - it resumes automatically!

### Token Refresh

**Why use refresh tokens?**
- Access tokens expire after ~4 hours
- Refresh tokens **never expire**
- Auto-generates new access tokens as needed

**OAuth Flow:**
```
User → Authorize App → Get Auth Code → Exchange for Tokens
                                          ├─ Access Token (expires in 4h)
                                          └─ Refresh Token (never expires)
```

The explorer uses refresh tokens to create the Dropbox client. On authentication errors, it automatically refreshes and retries.

### Exploration Algorithm

1. Start at root folder (or specified path)
2. List all entries in current folder
3. For each entry:
   - **File**: Collect metadata (size, hash, timestamps)
   - **Folder**: Add to queue for exploration
4. Process queue recursively (DFS traversal)
5. Save session periodically
6. Handle errors gracefully (skip restricted items)
7. Export to JSON when complete

---

## Output Files

### File Structure

```
data/
├── {session_name}.pkl      # Session file (preserved after completion)
└── {session_name}.json     # Final JSON export

logs/
└── YYYYMMDD-HHMMSS.log     # Timestamped log files
```

### File Naming

Session names can be:
- **Custom** (via `-s` flag): `my_backup.pkl`, `my_backup.json`
- **From env var**: `project_scan.pkl`, `project_scan.json`
- **Auto-generated**: `session_abc123.pkl`, `session_abc123.json`

### JSON Export Structure

```json
{
  "timestamp": "2025-10-16T12:00:00",
  "statistics": {
    "total_files": 1234,
    "total_folders": 56,
    "total_size": 1073741824,
    "total_size_human": "1.00 GB",
    "restricted_items": 5
  },
  "restricted": {
    "total_restricted": 5,
    "restricted_files": [],
    "restricted_folders": [
      {
        "name": "Private Folder",
        "path": "/Documents/Private Folder",
        "type": "folder"
      }
    ]
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
          "server_modified": "2025-01-01T00:00:00Z",
          "content_hash": "abc123..."
        }
      ]
    }
  ]
}
```

**Note:** Restricted items are included in the main JSON file under the `"restricted"` key.

### Session Files

Session files (`.pkl`) contain:
- All collected entries
- Visited paths (avoids re-scanning)
- Shared link and root folder
- Restricted items tracking
- Timestamp of last save

Session files are **preserved after completion** and can be:
- Re-inspected with `-i` flag
- Re-exported with `-x` flag
- Used to resume exploration

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DROPBOX_ACCESS_TOKEN` | Yes* | - | Short-lived access token (~4 hours) |
| `DROPBOX_REFRESH_TOKEN` | No** | - | Refresh token (never expires) |
| `DROPBOX_APP_KEY` | No** | - | App key (for refresh) |
| `DROPBOX_APP_SECRET` | No** | - | App secret (for refresh) |
| `DROPBOX_SHARED_LINK` | Yes | - | Shared link to explore |
| `ROOT_FOLDER` | No | `""` | Path within shared link (override with `-p`) |
| `SESSION_NAME` | No | auto | Custom session name (override with `-s`) |
| `SESSION_INTERVAL_SECONDS` | No | `300` | Session save interval (seconds) |
| `OUTPUT_DIR` | No | `data` | Output directory for sessions and JSON |
| `LOG_LEVEL_CONSOLE` | No | `INFO` | Console log level |
| `LOG_LEVEL_FILE` | No | `DEBUG` | File log level |
| `LOG_DIR` | No | `logs` | Directory for log files |

\* Required if not using refresh token  
\** Recommended for long operations (prevents token expiration)

### Logging

The application uses **loguru** for structured, colored logging with UTC timestamps.

**Log Levels:**
- `NONE` - Disable logging
- `DEBUG` - Detailed debugging information
- `INFO` - General informational messages (default)
- `WARNING` - Warning messages (e.g., restricted items)
- `ERROR` - Error messages
- `CRITICAL` - Critical errors

**Features:**
- Colored console output
- UTC timestamps
- Automatic rotation at 100MB
- 30-day retention
- Automatic compression
- Thread-safe

**Example Configuration:**
```bash
LOG_LEVEL_CONSOLE=INFO    # Terminal output
LOG_LEVEL_FILE=DEBUG      # Saved to logs/
LOG_DIR=logs              # Log directory
```

**Disable Logging:**
```bash
LOG_LEVEL_CONSOLE=NONE    # No console output
LOG_LEVEL_FILE=NONE       # No log files
```

---

## Troubleshooting

### Token Expired

**Problem:** `expired_access_token` error after ~4 hours

**Solution:** Use refresh token (never expires)
```bash
uv run src/get_refresh_token.py
```

**Temporary fix:** Generate new access token at https://www.dropbox.com/developers/apps (expires in 4 hours)

### Lost Progress

**Problem:** Exploration was interrupted

**Solution:** Just run again - auto-resumes from session
```bash
uv run explore  # Automatically detects and resumes
```

### Permission Denied

**Problem:** `permission_denied` or `access_denied` error

**Check:**
1. App has `sharing.read` enabled (Permissions tab)
2. Shared link is public or you have access
3. Link hasn't expired
4. App has been authorized (`get_refresh_token.py`)

### Restricted Content Warnings

**Normal behavior.** Shared folders often have restricted items (password-protected or limited access).

These items are:
- Logged as warnings
- Included in JSON under `"restricted"` key
- Skipped during exploration (contents not accessible)
- Don't stop the scan - continues with accessible items

### Session Not Saving

**Check:**
- `OUTPUT_DIR` is writable
- Sufficient disk space
- `SESSION_INTERVAL_SECONDS` is set in `.env`

### Can't Resume

**Possible causes:**
- Different shared link than original scan
- Session file corrupted
- Session file deleted

**Solution:** Delete the session file and start fresh
```bash
rm data/{session_name}.pkl
uv run explore
```

### Large Directories

**Tips for better performance:**
- Use `-p` flag to explore only subdirectories
- Increase `SESSION_INTERVAL_SECONDS` for fewer saves
- Check logs for restricted items (may slow scan)
- Ensure good network connection

### Module Not Found

**Solution:**
```bash
uv sync  # or: pip install -e .
```

---

## Additional Tools Details

### PDF Report Generator

Generate comprehensive PDF reports with statistics and visualizations.

**Features:**
- Overall summary across all directories
- Duplicate file analysis (top 10 largest groups)
- Individual directory statistics
- File type distribution (pie charts)
- Storage size by category (bar charts)
- Detailed category breakdowns

**Usage:**
```bash
# Basic usage
uv run report

# Custom options
uv run report -o my_report.pdf -d /path/to/data
```

**Options:**
- `-o, --output <filename>` - Output PDF filename (default: `dropbox_report.pdf`)
- `-d, --data-dir <directory>` - Directory with `.pkl` files (default: `OUTPUT_DIR`)

**File Categories:**
- Image, Video, Audio, Document, Spreadsheet, Presentation
- Archive, Code, Data, Executable, Other

### Duplicate File Detector

Identify duplicate files using Dropbox's cryptographic content hash.

**Features:**
- 100% accurate duplicate detection (content-based, not name-based)
- Total wasted space calculation
- Detailed duplicate groups sorted by size
- File paths for all copies
- JSON output for scripting

**Usage:**
```bash
# Console output
uv run duplicates

# Save to file with pretty formatting
uv run duplicates -o duplicates.json --pretty

# Custom data directory
uv run duplicates -d /path/to/data
```

**Options:**
- `-d, --data-dir <directory>` - Directory with `.pkl` files
- `-o, --output <file>` - Output JSON file (default: stdout)
- `--pretty` - Pretty-print JSON
- `--log-level-console <level>` - Console log level
- `--log-level-file <level>` - File log level

**Output Format:**
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
      "content_hash": "280539fdd34a5f7b61cf8ddadcf89ce...",
      "duplicate_count": 6,
      "file_size_bytes": 2393959844,
      "file_size_human": "2.23 GB",
      "wasted_bytes": 11969799220,
      "wasted_size_human": "11.15 GB",
      "file_paths": ["/path1", "/path2", ...]
    }
  ]
}
```

**Use Cases:**
- Storage cleanup - identify large duplicates
- Data deduplication planning
- Archive analysis
- Migration planning (calculate unique data size)
- Compliance checks

### JSON File Combiner

Merge multiple JSON export files into a single unified file with smart deduplication.

**Features:**
- Combines all JSON files from multiple explorations
- Removes duplicate files based on content hash
- Keeps files at shallowest path depth (closest to root)
- Comprehensive statistics and duplicate report
- Preserves all file metadata

**Usage:**
```bash
# Basic usage (merges all JSON in data/ directory)
uv run combine

# Custom options
uv run combine -o all.json -d /path/to/json/files
```

**Options:**
- `-d, --data-dir <directory>` - Directory with JSON files (default: `OUTPUT_DIR`)
- `-o, --output <filename>` - Output filename (default: `all.json`)
- `--log-level-console <level>` - Console log level
- `--log-level-file <level>` - File log level

**Output:**
```
======================================================================
JSON COMBINATION SUMMARY
======================================================================
Source files processed:   12
Total files found:        1,026,757
Unique files kept:        759,529
Duplicate files removed:  267,228
Total unique file size:   1.74 TB
Space saved by dedup:     254.39 GB

Output file: data/all.json
======================================================================
```

**How It Works:**
1. Scans all `.json` files in the data directory
2. Extracts all files from nested structures
3. Groups files by `content_hash`
4. For duplicates, keeps the file at the shallowest path depth
5. Outputs unified JSON with metadata and statistics

**Use Cases:**
- Combine exports from multiple shared links
- Create unified file catalog
- Identify cross-folder duplicates
- Calculate true unique data volume

See [docs/combine.md](docs/combine.md) for detailed documentation.

---

## License

This project is provided as-is for exploring Dropbox shared links. Use responsibly and in accordance with Dropbox's Terms of Service and API usage policies.


