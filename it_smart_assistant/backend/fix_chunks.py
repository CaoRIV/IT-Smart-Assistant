"""Script to fix duplicate files and incorrect subjects in chunks."""

import glob
import json
import os
from pathlib import Path

# Directory
PROCESSED_DIR = Path("knowledge_processed/bai_giang")

# Get all JSON files
files = list(PROCESSED_DIR.glob("*.json"))
print(f"Found {len(files)} files")

# Group by document base name (without hash)
doc_groups = {}
for f in files:
    # Extract base name (e.g., "giai-tich-chuong-1" from "giai-tich-chuong-1-12383e1d.json")
    base = f.stem.rsplit("-", 1)[0] if "-" in f.stem else f.stem
    if base not in doc_groups:
        doc_groups[base] = []
    doc_groups[base].append(f)

print("\n=== Deleting duplicates ===")
for base, file_list in doc_groups.items():
    if len(file_list) > 1:
        file_list.sort(key=lambda x: x.stat().st_mtime)
        keep = file_list[0]
        duplicates = file_list[1:]
        print(f"\n{base}:")
        print(f"  Keep: {keep.name}")
        for dup in duplicates:
            print(f"  Delete: {dup.name}")
            dup.unlink()


print("\n=== Fixing subjects ===")
remaining_files = list(PROCESSED_DIR.glob("*.json"))

for f in remaining_files:
    print(f"\nProcessing: {f.name}")
    
    with open(f, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    
    # Determine correct subject from filename
    filename_lower = f.stem.lower()
    
    if "giai-tich" in filename_lower or "bt-giai-tich" in filename_lower:
        correct_subject = "Toán"
    elif "vat-ly" in filename_lower or "ly" in filename_lower:
        correct_subject = "Vật lý"
    elif "hoa" in filename_lower:
        correct_subject = "Hóa học"
    elif "lap-trinh" in filename_lower or "csdl" in filename_lower:
        correct_subject = "Cơ sở dữ liệu"
    else:
        correct_subject = "Toán"  # Default for giải tích
    
    # Update all chunks
    updated = False
    for chunk in data.get("chunks", []):
        metadata = chunk.get("metadata", {})
        old_subject = metadata.get("subject", "Unknown")
        
        if old_subject != correct_subject:
            print(f"  Chunk {chunk.get('chunk_id', 'unknown')}: '{old_subject}' -> '{correct_subject}'")
            metadata["subject"] = correct_subject
            updated = True
    
    if updated:
        # Write back
        with open(f, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
        print(f"  Saved: {f.name}")
    else:
        print(f"  No changes needed")

print("\n=== Done! ===")
print(f"Remaining files: {len(list(PROCESSED_DIR.glob('*.json')))}")
