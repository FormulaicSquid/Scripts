#!/usr/bin/env python3
"""
CSV Music Sorter

This script sorts a CSV file containing music metadata first by artist,
then by album within each artist. Entries with empty album fields are
sorted to the bottom within each artist's section.
"""

import csv
import argparse
from pathlib import Path
from typing import List, Dict

# =============================================================================
# CONFIGURATION - Edit these variables before running the script
# =============================================================================
INPUT_CSV = "data/studio_albums.csv"
OUTPUT_CSV = "data/sorted_music.csv"
# =============================================================================


class MusicSorter:
    def __init__(self, input_file: str, output_file: str):
        self.input_file = input_file
        self.output_file = output_file
    
    def sort_key(self, entry: Dict[str, str]) -> tuple:
        """
        Generate sort key for an entry.
        Returns tuple: (artist_lower, has_album, album_lower, track_lower)
        
        - artist_lower: Lowercase artist name for consistent sorting
        - has_album: 0 if album exists, 1 if empty (puts empty albums last)
        - album_lower: Lowercase album name for consistent sorting
        - track_lower: Lowercase track name for tie-breaking
        """
        artist = entry.get('artist', '').strip().lower()
        album = entry.get('album', '').strip()
        track = entry.get('track', '').strip().lower()
        
        # Empty albums get sorted to bottom (1 > 0)
        has_album = 0 if album else 1
        album_lower = album.lower() if album else ''
        
        return (artist, has_album, album_lower, track)
    
    def process_csv(self) -> bool:
        """Read, sort, and save the CSV file."""
        if not Path(self.input_file).exists():
            print(f"❌ Input file not found: {self.input_file}")
            return False
        
        # Read input CSV
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                data = list(reader)
        except Exception as e:
            print(f"❌ Error reading input file: {e}")
            return False
        
        if not data:
            print(f"❌ No data found in input file")
            return False
        
        print(f"📖 Loaded {len(data)} entries from {self.input_file}")
        
        # Validate that we have the expected columns
        required_columns = ['artist']
        missing_columns = [col for col in required_columns if col not in data[0]]
        if missing_columns:
            print(f"❌ Missing required columns: {missing_columns}")
            print(f"Available columns: {list(data[0].keys())}")
            return False
        
        # Sort the data
        print(f"🔄 Sorting by artist, then by album (empty albums last)...")
        sorted_data = sorted(data, key=self.sort_key)
        
        # Write sorted CSV
        try:
            fieldnames = data[0].keys()
            
            with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(sorted_data)
            
            print(f"📝 Saved {len(sorted_data)} sorted entries to {self.output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error writing output file: {e}")
            return False
    
    def print_preview(self, num_lines: int = 10):
        """Print a preview of the sorted data."""
        if not Path(self.output_file).exists():
            print(f"❌ Output file not found: {self.output_file}")
            return
        
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                data = list(reader)
            
            print(f"\n📋 Preview of first {min(num_lines, len(data))} sorted entries:")
            print("=" * 80)
            
            current_artist = None
            for i, entry in enumerate(data[:num_lines]):
                artist = entry.get('artist', '')
                album = entry.get('album', '')
                track = entry.get('track', '')
                
                # Print artist separator when artist changes
                if artist != current_artist:
                    if current_artist is not None:
                        print()  # Empty line between artists
                    current_artist = artist
                    print(f"🎤 {artist}")
                
                # Format album display
                album_display = album if album else "(No Album)"
                print(f"   📀 {album_display}")
                print(f"      🎵 {track}")
            
            if len(data) > num_lines:
                print(f"\n... and {len(data) - num_lines} more entries")
                
        except Exception as e:
            print(f"❌ Error reading preview: {e}")
    
    def print_statistics(self):
        """Print sorting statistics."""
        if not Path(self.output_file).exists():
            return
        
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                data = list(reader)
            
            # Count unique artists and albums
            artists = set(entry.get('artist', '').strip() for entry in data)
            albums = set(entry.get('album', '').strip() for entry in data if entry.get('album', '').strip())
            entries_without_albums = len([entry for entry in data if not entry.get('album', '').strip()])
            
            print(f"\n📊 Sorting Statistics:")
            print(f"   • Total entries: {len(data)}")
            print(f"   • Unique artists: {len(artists)}")
            print(f"   • Unique albums: {len(albums)}")
            print(f"   • Entries without albums: {entries_without_albums}")
            
        except Exception as e:
            print(f"❌ Error calculating statistics: {e}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Sort music CSV by artist then album')
    parser.add_argument('--input', '-i', default=INPUT_CSV, 
                       help='Input CSV file')
    parser.add_argument('--output', '-o', default=OUTPUT_CSV, 
                       help='Output CSV file')
    parser.add_argument('--preview', '-p', action='store_true',
                       help='Show preview of sorted data after sorting')
    parser.add_argument('--preview-lines', type=int, default=10,
                       help='Number of lines to show in preview (default: 10)')
    
    args = parser.parse_args()
    
    print(f"🚀 CSV Music Sorter")
    print(f"📖 Input file: {args.input}")
    print(f"💾 Output file: {args.output}")
    print(f"🔄 Sort order: Artist → Album (empty albums last) → Track")
    
    # Check if output file exists
    if Path(args.output).exists():
        response = input(f"⚠️  File '{args.output}' already exists. Overwrite? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Operation cancelled.")
            return False
    
    # Create and run sorter
    sorter = MusicSorter(args.input, args.output)
    success = sorter.process_csv()
    
    if success:
        sorter.print_statistics()
        
        if args.preview:
            sorter.print_preview(args.preview_lines)
        
        print("🎉 Sorting completed successfully!")
        return True
    else:
        print("💥 Sorting failed!")
        return False


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)