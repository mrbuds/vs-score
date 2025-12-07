#!/usr/bin/env python3
"""
Script de concaténation des panoramas
Version simplifiée utilisant TableGenerator
"""

import os
import sys
from pathlib import Path

from table_generator import TableGenerator


def main():
    if len(sys.argv) != 2:
        print("Usage: python concat.py <folder_path>")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    
    if not os.path.isdir(folder_path):
        print(f"Error: {folder_path} is not a valid directory")
        sys.exit(1)
    
    print(f"Processing folder: {folder_path}")
    
    # Utiliser TableGenerator
    success, output_path, error = TableGenerator.generate_from_folder(folder_path)
    
    if success:
        print(f"✅ Success! Saved to: {output_path}")
    else:
        print(f"❌ Error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
