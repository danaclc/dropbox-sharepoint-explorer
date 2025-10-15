#!/usr/bin/env python3
"""
Test script to validate checkpoint functionality
"""

import pickle
import os

checkpoint_file = "data/checkpoint.pkl"

if os.path.exists(checkpoint_file):
    print("✅ Checkpoint file exists")

    with open(checkpoint_file, "rb") as f:
        checkpoint_data = pickle.load(f)

    print(f"\n📊 Checkpoint contents:")
    print(f"   Timestamp: {checkpoint_data.get('timestamp', 'N/A')}")
    print(f"   Shared link: {checkpoint_data.get('shared_link', 'N/A')[:60]}...")
    print(f"   Visited paths: {len(checkpoint_data.get('visited_paths', []))}")
    print(f"   Entries collected: {len(checkpoint_data.get('entries', []))}")

    if checkpoint_data.get("visited_paths"):
        print(f"\n📁 Sample visited paths:")
        for path in list(checkpoint_data["visited_paths"])[:5]:
            print(f"      {path}")

    print("\n✅ Checkpoint is valid and can be loaded!")
else:
    print("❌ No checkpoint file found")
