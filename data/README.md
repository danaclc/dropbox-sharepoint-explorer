# Data Directory

This directory contains output files from the Dropbox explorer script.

## Files Generated

### Session Files (Checkpoints)
**Format**: `checkpoint_XXXXXXXXXXXX.pkl` or `{session_name}.pkl`

Binary pickle files that store exploration progress for resumable operations:
- Visited paths (to avoid re-scanning)
- All discovered items (flat list)
- Restricted items encountered
- Timestamp and configuration

**Purpose**: Enable session resumption after interruption. These files are automatically created and updated during exploration.

### JSON Export Files
**Format**: `checkpoint_XXXXXXXXXXXX.json` or `{session_name}.json`

Complete hierarchical structure of the explored Dropbox folder with:
- All accessible files and folders
- Full metadata (sizes, dates, IDs, content hashes)
- Nested structure showing parent-child relationships
- Statistics and restricted items summary

**Structure**:
```json
{
  "timestamp": "2025-10-15T19:30:00.123456",
  "statistics": {
    "total_files": 150,
    "total_folders": 45,
    "total_size": 5242880000,
    "total_size_human": "4.88 GB",
    "restricted_items": 23
  },
  "restricted": {
    "total_restricted": 23,
    "restricted_files": [
      {
        "name": "confidential.pdf",
        "path": "/HR/Documents/confidential.pdf",
        "type": "file"
      }
    ],
    "restricted_folders": [
      {
        "name": "Private",
        "path": "/HR/Private",
        "type": "folder"
      }
    ]
  },
  "contents": [
    {
      "name": "FolderName",
      "type": "folder",
      "path_display": "/FolderName",
      "path_lower": "/foldername",
      "id": "id:xxx",
      "children": [
        {
          "name": "file.pdf",
          "type": "file",
          "path_display": "/FolderName/file.pdf",
          "path_lower": "/foldername/file.pdf",
          "size": 1024000,
          "size_human": "1.00 MB",
          "server_modified": "2025-09-15T10:30:00",
          "client_modified": "2025-09-15T10:25:00",
          "rev": "abc123",
          "content_hash": "def456",
          "id": "id:yyy"
        }
      ]
    }
  ]
}
```

## Key Features

### 1. Session-Based Naming
Files are named based on:
- **Auto-generated**: `checkpoint_XXXXXXXXXXXX` (hash of shared link + root folder)
- **Custom**: Your specified session name via `-s` flag or `SESSION_NAME` env var

Examples:
- `checkpoint_a1b2c3d4e5f6.pkl` and `checkpoint_a1b2c3d4e5f6.json`
- `my_project.pkl` and `my_project.json`

### 2. Restricted Items Summary
The JSON export includes a `restricted` section with:
- Total count of restricted items
- Separate lists for restricted files and folders
- Full paths to identify location of inaccessible content

### 3. Complete Metadata
Each file entry includes:
- `name`: Filename
- `type`: "file" or "folder"
- `path_display`: Full path (original case)
- `path_lower`: Full path (lowercase)
- `size`: Size in bytes
- `size_human`: Human-readable size (e.g., "1.50 MB")
- `server_modified`: Server modification timestamp (ISO-8601)
- `client_modified`: Client modification timestamp (ISO-8601)
- `rev`: Dropbox revision ID
- `content_hash`: Dropbox content hash
- `id`: Dropbox file ID

### 4. Hierarchical Structure
Folders include a `children` array with nested items, preserving the complete directory tree structure.

## Usage

### Viewing the Data

**With Python**:
```python
import json

# Load metadata (use your actual filename)
with open('checkpoint_a1b2c3d4e5f6.json') as f:
    data = json.load(f)

# View statistics
print(f"Total files: {data['statistics']['total_files']}")
print(f"Total folders: {data['statistics']['total_folders']}")
print(f"Total size: {data['statistics']['total_size_human']}")
print(f"Restricted items: {data['statistics']['restricted_items']}")

# Navigate hierarchy
for item in data['contents']:
    print(f"{item['type']}: {item['name']}")
    if item['type'] == 'folder' and 'children' in item:
        for child in item['children']:
            print(f"  └─ {child['name']}")

# View restricted items
if data['restricted']['total_restricted'] > 0:
    print("\nRestricted folders:")
    for folder in data['restricted']['restricted_folders']:
        print(f"  - {folder['path']}")
```

**With jq (command line)**:
```bash
# View statistics
jq '.statistics' checkpoint_*.json

# Count restricted items
jq '.statistics.restricted_items' checkpoint_*.json

# List all restricted folder paths
jq '.restricted.restricted_folders[].path' checkpoint_*.json

# Find all PDFs
jq '.. | objects | select(.type=="file" and (.name | endswith(".pdf"))) | .name' checkpoint_*.json

# Get total size
jq '.statistics.total_size_human' checkpoint_*.json

# List all root-level items
jq '.contents[].name' checkpoint_*.json
```

### Inspecting Without Python/jq

Use the built-in inspection command:

```bash
# Inspect default session
uv run explore -i

# Inspect specific session
uv run explore -i my_session

# Get JSON output for scripting
uv run explore -i my_session -j
```

## File Lifecycle

1. **During Exploration**: `session.pkl` is created and updated every 5 minutes (configurable)
2. **After Completion**: `session.json` is exported with complete hierarchical data
3. **Session Preserved**: The `.pkl` file is kept for potential re-extraction or inspection

## Notes

- Session files (`.pkl`) enable resumable operations
- JSON files contain the same session name for easy correlation
- This directory is gitignored to keep data private
- Both `.pkl` and `.json` files use the same naming scheme
- Use `-s` flag or `SESSION_NAME` env var for custom session names
