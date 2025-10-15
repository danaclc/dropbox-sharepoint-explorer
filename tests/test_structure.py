# Quick test to show the JSON structure
import json

sample_data = {
    "timestamp": "2025-10-09T19:05:00",
    "structure": "hierarchical",
    "statistics": {
        "total_files": 150,
        "total_folders": 45,
        "total_size": 5242880000,
        "total_size_human": "4.88 GB"
    },
    "contents": [
        {
            "name": "Compta",
            "type": "folder",
            "id": "id:123",
            "children": [
                {
                    "name": "Factures.xlsx",
                    "type": "file",
                    "size": 2048000,
                    "size_human": "2.00 MB",
                    "server_modified": "2025-09-15T10:30:00",
                    "client_modified": "2025-09-15T10:25:00"
                },
                {
                    "name": "Archive",
                    "type": "folder",
                    "id": "id:456",
                    "children": [
                        {
                            "name": "2024.zip",
                            "type": "file",
                            "size": 104857600,
                            "size_human": "100.00 MB",
                            "server_modified": "2024-12-31T23:59:59"
                        }
                    ]
                }
            ]
        },
        {
            "name": "Documents",
            "type": "folder",
            "id": "id:789",
            "restricted": True,
            "children": []
        }
    ]
}

print(json.dumps(sample_data, indent=2))
