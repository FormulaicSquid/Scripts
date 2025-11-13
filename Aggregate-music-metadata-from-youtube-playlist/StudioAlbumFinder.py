#!/usr/bin/env python3
"""
Studio Album Finder

This script takes a CSV file with track and artist data and finds the original
studio album names for each track. It uses MusicBrainz's built-in API filtering
to specifically request only studio albums, excluding live albums, compilations,
and soundtracks directly at the database level.
"""

import csv
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional
from tqdm import tqdm
import argparse
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =============================================================================
# CONFIGURATION - Edit these variables before running the script
# =============================================================================
INPUT_CSV = "data/enhanced_metadata.csv"
OUTPUT_CSV = "data/studio_albums.csv"
RATE_LIMIT_DELAY = 1.0  # Seconds between API calls to be respectful
# =============================================================================


class StudioAlbumFinder:
    def __init__(self, input_file: str, output_file: str, rate_limit: float = 1.0):
        self.input_file = input_file
        self.output_file = output_file
        self.rate_limit = rate_limit
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'StudioAlbumFinder/1.0 (https://github.com/example/studio-album-finder)'
        })
        # Disable SSL verification to handle certificate issues
        self.session.verify = False
        
        # Statistics
        self.total_entries = 0
        self.successful_lookups = 0
        self.failed_lookups = 0
        self.already_had_albums = 0
    
    def search_musicbrainz_for_studio_album(self, artist: str, track: str) -> Optional[str]:
        """Search MusicBrainz for the original studio album of a track using API filtering."""
        base_urls = [
            "https://musicbrainz.org/ws/2/",
            "http://musicbrainz.org/ws/2/"  # Fallback to HTTP if HTTPS fails
        ]
        
        for base_url in base_urls:
            try:
                # First, try to find the release group directly with filtering
                # This gets the canonical album information, not specific releases
                query = f'artist:"{artist}" AND recording:"{track}" AND primarytype:album AND NOT secondarytype:live AND NOT secondarytype:compilation AND NOT secondarytype:soundtrack'
                url = f"{base_url}release-group/?query={query}&fmt=json&limit=5"
                
                response = self.session.get(url, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'release-groups' in data and data['release-groups']:
                        # MusicBrainz has already filtered for us - just pick the first result
                        # which should be the most relevant studio album
                        release_group = data['release-groups'][0]
                        album_title = release_group.get('title', '')
                        
                        if album_title:
                            primary_type = release_group.get('primary-type', '')
                            secondary_types = release_group.get('secondary-types', [])
                            print(f"    📀 Found release group: {album_title} (Type: {primary_type})")
                            if secondary_types:
                                print(f"    🏷️ Secondary types: {', '.join(secondary_types)}")
                            return album_title
                
                # Fallback: If release-group search fails, try recording search with filtering
                query = f'artist:"{artist}" AND recording:"{track}"'
                url = f"{base_url}recording/?query={query}&fmt=json&limit=5&inc=releases+release-groups"
                
                response = self.session.get(url, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'recordings' in data and data['recordings']:
                        # Look through recordings to find studio albums
                        for recording in data['recordings']:
                            if 'releases' not in recording:
                                continue
                                
                            for release in recording['releases']:
                                release_group = release.get('release-group', {})
                                primary_type = release_group.get('primary-type', '').lower()
                                secondary_types = [t.lower() for t in release_group.get('secondary-types', [])]
                                
                                # Use MusicBrainz's own type classification
                                if (primary_type == 'album' and 
                                    'live' not in secondary_types and 
                                    'compilation' not in secondary_types and
                                    'soundtrack' not in secondary_types):
                                    
                                    album_title = release_group.get('title', '')
                                    if album_title:
                                        print(f"    📀 Found studio album: {album_title} (Type: {primary_type})")
                                        return album_title
                        
            except Exception as e:
                print(f"    ⚠️ MusicBrainz error: {e}")
                continue
        
        return None
    
    def process_entry(self, entry: Dict[str, str]) -> Dict[str, str]:
        """Process a single entry to find its studio album."""
        track = entry.get('track', '').strip()
        artist = entry.get('artist', '').strip()
        existing_album = entry.get('album', '').strip()
        
        result = entry.copy()  # Keep all original data
        
        if not track or not artist:
            print(f"  ⚠️ Missing track or artist data")
            return result
        
        print(f"🔍 Looking up studio album for: {artist} - {track}")
        
        # Rate limiting
        time.sleep(self.rate_limit)
        
        try:
            studio_album = self.search_musicbrainz_for_studio_album(artist, track)
            
            if studio_album:
                print(f"  ✅ Found studio album: {studio_album}")
                
                # Handle existing album data
                if existing_album:
                    # Add new album after existing one with separator
                    if studio_album.lower() != existing_album.lower():
                        result['album'] = f"{existing_album} / {studio_album}"
                        print(f"    📀 Combined: {result['album']}")
                    else:
                        result['album'] = existing_album  # Same album, keep original
                        print(f"    📀 Same as existing album")
                else:
                    result['album'] = studio_album
                
                self.successful_lookups += 1
                return result
            else:
                print(f"  ❌ No studio album found")
                self.failed_lookups += 1
                return result
                
        except Exception as e:
            print(f"  ❌ Error processing: {e}")
            self.failed_lookups += 1
            return result
    
    def process_csv(self) -> bool:
        """Process the input CSV and create enhanced output."""
        if not Path(self.input_file).exists():
            print(f"❌ Input file not found: {self.input_file}")
            return False
        
        # Read input CSV
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                input_data = list(reader)
        except Exception as e:
            print(f"❌ Error reading input file: {e}")
            return False
        
        # Validate required columns
        if not input_data:
            print(f"❌ No data found in input file")
            return False
        
        required_columns = ['track', 'artist']
        missing_columns = [col for col in required_columns if col not in input_data[0]]
        if missing_columns:
            print(f"❌ Missing required columns: {missing_columns}")
            return False
        
        self.total_entries = len(input_data)
        print(f"📖 Loaded {self.total_entries} entries from {self.input_file}")
        
        # Count entries that already have albums
        self.already_had_albums = len([entry for entry in input_data if entry.get('album', '').strip()])
        print(f"📀 {self.already_had_albums} entries already have album data")
        
        # Process each entry
        enhanced_data = []
        
        with tqdm(input_data, desc="Finding studio albums", unit="entry") as pbar:
            for entry in pbar:
                try:
                    result = self.process_entry(entry)
                    enhanced_data.append(result)
                    
                    # Update progress bar
                    pbar.set_postfix({
                        'Found': self.successful_lookups,
                        'Failed': self.failed_lookups
                    })
                    
                except KeyboardInterrupt:
                    print(f"\n⚠️ Interrupted by user. Processed {len(enhanced_data)} entries so far.")
                    break
                except Exception as e:
                    print(f"  ❌ Error processing entry: {e}")
                    enhanced_data.append(entry)  # Keep original data
                    self.failed_lookups += 1
        
        # Write output CSV
        try:
            if enhanced_data:
                fieldnames = enhanced_data[0].keys()
                
                with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(enhanced_data)
                
                print(f"\n📝 Saved {len(enhanced_data)} entries to {self.output_file}")
                return True
            else:
                print(f"❌ No data to save")
                return False
                
        except Exception as e:
            print(f"❌ Error writing output file: {e}")
            return False
    
    def print_statistics(self):
        """Print processing statistics."""
        print(f"\n📊 Studio Album Lookup Complete!")
        print(f"   • Total entries processed: {self.total_entries}")
        print(f"   • Entries with existing albums: {self.already_had_albums}")
        print(f"   • Successful studio album lookups: {self.successful_lookups}")
        print(f"   • Failed lookups: {self.failed_lookups}")
        if self.total_entries > 0:
            success_rate = (self.successful_lookups / self.total_entries) * 100
            print(f"   • Success rate: {success_rate:.1f}%")
        print(f"   • Output saved to: {self.output_file}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Find studio albums for tracks in CSV')
    parser.add_argument('--input', '-i', default=INPUT_CSV, help='Input CSV file')
    parser.add_argument('--output', '-o', default=OUTPUT_CSV, help='Output CSV file')
    parser.add_argument('--rate-limit', '-r', type=float, default=RATE_LIMIT_DELAY, 
                       help='Rate limit between API calls (seconds)')
    
    args = parser.parse_args()
    
    print(f"🚀 Studio Album Finder")
    print(f"📖 Input file: {args.input}")
    print(f"💾 Output file: {args.output}")
    print(f"⏱️ Rate limit: {args.rate_limit}s between requests")
    print(f"🎯 Target: Studio albums only (no live/compilation albums)")
    
    # Check if output file exists
    if Path(args.output).exists():
        response = input(f"⚠️  File '{args.output}' already exists. Overwrite? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Operation cancelled.")
            return False
    
    # Create and run finder
    finder = StudioAlbumFinder(args.input, args.output, args.rate_limit)
    success = finder.process_csv()
    
    if success:
        finder.print_statistics()
        print("🎉 Studio album lookup completed successfully!")
        return True
    else:
        print("💥 Studio album lookup failed!")
        return False


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)