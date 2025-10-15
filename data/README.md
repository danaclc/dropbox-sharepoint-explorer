# Data Directory

This directory contains all output files from the Dropbox explorer script.

## Files Generated

### Main Metadata File
**Format**: `dropbox_metadata_YYYYMMDD_HHMMSS.json`

Contains the complete hierarchical structure of the Dropbox folder with:
- All accessible files and folders
- Full metadata (sizes, dates, IDs)
- Nested structure showing parent-child relationships
- `restricted` flag on all items (true/false)

**Structure**:
```json
{
  "timestamp": "2025-10-09T19:30:00",
  "structure": "hierarchical",
  "statistics": {
    "total_files": 150,
    "total_folders": 45,
    "total_size": 5242880000,
    "total_size_human": "4.88 GB",
    "restricted_items": 23
  },
  "contents": [
    {
      "name": "FolderName",
      "type": "folder",
      "restricted": false,
      "id": "id:xxx",
      "children": [
        {
          "name": "file.pdf",
          "type": "file",
          "restricted": false,
          "size": 1024000,
          "size_human": "1.00 MB",
          "server_modified": "2025-09-15T10:30:00",
          "client_modified": "2025-09-15T10:25:00"
        }
      ]
    }
  ]
}
```

### Restricted Items Report
**Format**: `dropbox_metadata_YYYYMMDD_HHMMSS_restricted.json`

A separate file listing all items you don't have access to:

**Structure**:
```json
{
  "timestamp": "2025-10-09T19:30:00",
  "total_restricted": 23,
  "restricted_files": [
    {
      "name": "confidential.pdf",
      "path": "HR/Documents/confidential.pdf",
      "type": "file",
      "id": "id:yyy"
    }
  ],
  "restricted_folders": [
    {
      "name": "Private",
      "path": "HR/Private",
      "type": "folder",
      "id": "id:zzz"
    }
  ],
  "all_restricted": [...]
}
```

## Key Features

### 1. Restricted Flag
Every item in the main metadata has a `"restricted"` field:
- `"restricted": false` - You have access, metadata is complete
- `"restricted": true` - Access denied, limited metadata available

### 2. Complete Paths
The restricted report shows full paths to help identify:
- Where restricted content is located
- The hierarchy of inaccessible items
- Which departments/areas have limited access

### 3. Statistics
Quick overview of:
- Total files and folders (including nested)
- Total size of accessible content
- Number of restricted items

## Usage

### Viewing the Data

**With Python**:
```python
import json

# Load main metadata
with open('dropbox_metadata_20251009_193000.json') as f:
    data = json.load(f)

print(f"Total files: {data['statistics']['total_files']}")
print(f"Total size: {data['statistics']['total_size_human']}")

# Navigate hierarchy
for item in data['contents']:
    if not item['restricted']:
        print(f"Accessible: {item['name']}")
```

**With jq (command line)**:
```bash
# Count restricted items
jq '.statistics.restricted_items' dropbox_metadata_*.json

# List all restricted folder names
jq '.restricted_folders[].name' dropbox_metadata_*_restricted.json

# Find all PDFs
jq '.. | objects | select(.type=="file" and (.name | endswith(".pdf"))) | .name' dropbox_metadata_*.json
```

## Notes

- Files are timestamped to track different exploration runs
- This directory is gitignored to keep data private
- Both files are generated together for each run
- If no restricted items exist, the restricted report is not created
