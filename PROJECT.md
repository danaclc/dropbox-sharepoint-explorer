# Project-Specific Guidelines

> For general development standards, see `CLAUDE.md`

## Project Overview

Dropbox Public Link Explorer - Recursively explores Dropbox shared/public links and exports complete file/folder metadata to JSON.

## Architecture

### Core Components

- **DropboxExplorer**: Main class handling exploration logic
- **Session System**: Named exploration with state persistence for resumable operations
- **Token Management**: OAuth refresh token handling

### Sessions

A **session** is a named exploration of a Dropbox shared link. Understanding sessions is critical for development:

**What is a session?**
- A session represents one exploration task (one shared link + optional subfolder)
- Each session has a unique name (auto-generated hash or custom name via `-s` flag or `SESSION_NAME` env var)
- Session data is stored in a `.pkl` file (e.g., `checkpoint_abc123.pkl`)
- Sessions automatically save progress every 5 minutes (configurable via `CHECKPOINT_INTERVAL_SECONDS`)

**Session lifecycle:**
1. **Start**: User runs `explore` command
2. **Auto-save**: Progress saved periodically to session file
3. **Resume**: If interrupted, automatically resumes on next run
4. **Complete**: Session data can be extracted to JSON or kept for reference

**Key terminology:**
- Use "session" in all user-facing messages and documentation
- Internal variable names may still use "checkpoint" for historical reasons (acceptable)
- The session file is the `.pkl` file that stores progress
- Session name is the identifier (e.g., `checkpoint_abc123`)

### Key Design Decisions

1. **Session-based resumption**: Saves state every N seconds to enable recovery from interruptions
2. **Hierarchical structure**: Maintains parent-child relationships in exported JSON
3. **Flat list for sessions**: Stores all items in flat list for easier serialization/deserialization
4. **Atomic session writes**: Uses temp file + rename to ensure session file integrity

## Project-Specific Constants

```python
# Display and formatting
MAX_LINK_DISPLAY_LENGTH = 60
MAX_PATH_DISPLAY_LENGTH = 70
MAX_SAMPLE_FILES = 10

# Checkpoint configuration
CHECKPOINT_HASH_LENGTH = 12
DEFAULT_CHECKPOINT_INTERVAL = 300
DEFAULT_OUTPUT_DIR = "data"
```

## Key Methods

### DropboxExplorer

- `explore_shared_link()`: Main exploration loop with pagination
- `save_checkpoint()`: Atomic checkpoint persistence
- `load_checkpoint()`: Restore state from checkpoint
- `_process_entries()`: Recursive folder processing
- `rebuild_hierarchy_from_flat_list()`: Reconstruct tree from flat checkpoint data

### Utility Functions

- `generate_checkpoint_name()`: Deterministic hash-based naming
- `list_checkpoints()`: Discover available checkpoint files
- `select_checkpoint()`: Interactive checkpoint selection

## Command-Line Interface

```bash
-c, --continue    Auto-continue from checkpoint without prompting
-i, --inspect     Inspect checkpoint file and display statistics
-x, --extract     Extract checkpoint to JSON without re-exploring
-p, --path        Specify root folder path within shared link
-s, --session     Specify custom checkpoint/session name
```

## Testing Guidelines

### Critical Test Areas

1. **Checkpoint System**
   - Atomic writes (verify no corruption on interruption)
   - Deterministic naming (same inputs = same checkpoint name)
   - State restoration (checkpoint → explore → matches original)

2. **Hierarchy Rebuilding**
   - Flat list correctly reconstructs tree
   - Parent-child relationships preserved
   - Edge cases: root items, deep nesting, orphaned items

3. **Error Handling**
   - Restricted content (graceful skip)
   - Token expiration (auto-refresh)
   - Network failures (retry logic)

### Test Data

- Use mock Dropbox API responses
- Test with various folder structures (shallow, deep, wide)
- Include edge cases (empty folders, restricted items)

## Environment Configuration

Required variables:
- `DROPBOX_ACCESS_TOKEN` or `DROPBOX_REFRESH_TOKEN`
- `DROPBOX_SHARED_LINK`

Optional variables:
- `CHECKPOINT_INTERVAL_SECONDS` (default: 300)
- `OUTPUT_DIR` (default: "data")
- `ROOT_FOLDER` (default: root of shared link)
- `SESSION_NAME` (default: auto-generated hash)

## Output Format

### Checkpoint File (`.pkl`)
```python
{
    "timestamp": "ISO-8601 datetime",
    "shared_link": "URL",
    "root_folder": "path",
    "visited_paths": ["list", "of", "paths"],
    "restricted_items": [{"name": "...", "path": "...", "type": "..."}],
    "all_items": [{"metadata": "..."}]
}
```

### Export JSON
```json
{
  "timestamp": "ISO-8601 datetime",
  "statistics": {
    "total_files": 0,
    "total_folders": 0,
    "total_size": 0,
    "total_size_human": "0 B",
    "restricted_items": 0
  },
  "restricted": {
    "total_restricted": 0,
    "restricted_files": [],
    "restricted_folders": []
  },
  "contents": []
}
```

## Performance Considerations

- **Checkpoint interval**: Balance between safety and performance (default: 5 minutes)
- **API rate limits**: Dropbox has rate limits; handled by SDK with retries
- **Memory usage**: Flat list stored in memory; consider streaming for very large folders
- **Network resilience**: Retry logic for transient failures

## Known Limitations

1. **Restricted content**: Cannot access password-protected or permission-restricted items
2. **Memory constraints**: Very large shared folders (100k+ items) may require memory optimization
3. **Rate limiting**: Dropbox API rate limits may slow down exploration of massive folders

## Future Enhancements

- Incremental updates (detect changes since last scan)
- Parallel folder exploration
- Download file contents option
- Export to other formats (CSV, SQLite)
- Web UI for checkpoint inspection
