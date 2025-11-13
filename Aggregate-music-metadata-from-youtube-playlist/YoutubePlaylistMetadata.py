#!/usr/bin/env python3
"""
YouTube Playlist Metadata Extractor

This script extracts metadata from YouTube playlists and saves it to a CSV file.
It uses yt-dlp to fetch playlist information and provides progress tracking.
"""

import subprocess
import json
import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from tqdm import tqdm

# =============================================================================
# CONFIGURATION - Edit these variables before running the script
# =============================================================================
PLAYLIST_URL = "https://youtube.com/playlist?list=PLkuTuUy1lBRWtYYMTb6oWuQsmo6rVeFHh&si=_5HmvHJjk7Ek7ifs"
OUTPUT_FILE = "data/zahin_playlist.csv"
TIMEOUT_SECONDS = 30  # Timeout for each video fetch (in seconds)
# =============================================================================


class PlaylistMetadataExtractor:
    def __init__(self, playlist_url: str, output_file: str = "data/playlist.csv", timeout: int = 30):
        self.playlist_url = playlist_url
        self.output_file = output_file
        self.timeout = timeout
        self.total_songs = 0
        self.processed_songs = 0
        self.songs_with_details = 0
        self.songs_without_details = 0
        self.failed_songs = 0
        self.skipped_videos = []
        
    def extract_playlist_id(self, url: str) -> Optional[str]:
        """Extract playlist ID from YouTube URL."""
        if "list=" in url:
            return url.split("list=")[1].split("&")[0]
        return None
    
    def fetch_video_urls(self) -> Optional[List[str]]:
        """Fetch video URLs from playlist using yt-dlp."""
        print(f"🔍 Fetching video URLs from playlist...")
        
        try:
            # Get playlist info with video URLs only (fast operation)
            cmd = ["yt-dlp", "--flat-playlist", "--print", "url", self.playlist_url]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=self.timeout)
            
            if result.returncode != 0:
                print(f"❌ Error running yt-dlp: {result.stderr}")
                return None
                
            # Parse URLs from output
            urls = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            return urls
            
        except subprocess.TimeoutExpired:
            print(f"❌ Timeout ({self.timeout}s) while fetching playlist URLs")
            return None
        except subprocess.CalledProcessError as e:
            print(f"❌ Error running yt-dlp: {e}")
            return None
        except FileNotFoundError:
            print("❌ yt-dlp not found. Please install it with: pip install yt-dlp")
            return None

    def fetch_video_metadata(self, video_url: str) -> Optional[Dict]:
        """Fetch metadata for a single video with timeout."""
        try:
            cmd = ["yt-dlp", "-J", video_url]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=self.timeout)
            
            if result.returncode != 0:
                return None
                
            data = json.loads(result.stdout)
            return data
            
        except subprocess.TimeoutExpired:
            return None
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return None

    def fetch_playlist_data(self) -> Optional[List[Dict]]:
        """Fetch playlist data by processing videos individually."""
        # First, get all video URLs
        video_urls = self.fetch_video_urls()
        if not video_urls:
            return None
        
        self.total_songs = len(video_urls)
        print(f"✅ Found {self.total_songs} videos in playlist")
        
        entries = []
        failed_count = 0
        
        # Process each video individually with progress bar
        print(f"\n📥 Fetching metadata for {self.total_songs} videos...")
        progress_bar = tqdm(video_urls, desc="Fetching metadata", unit="video")
        
        for i, video_url in enumerate(progress_bar):
            try:
                # Update progress bar description
                progress_bar.set_description(f"Fetching video {i+1}/{self.total_songs}")
                
                # Fetch metadata for this video
                metadata = self.fetch_video_metadata(video_url)
                
                if metadata:
                    entries.append(metadata)
                else:
                    failed_count += 1
                    self.skipped_videos.append(video_url)
                    progress_bar.set_postfix({"Failed": failed_count})
                    
            except KeyboardInterrupt:
                print(f"\n⚠️ Interrupted by user. Processed {len(entries)} videos so far.")
                break
        
        progress_bar.close()
        
        if failed_count > 0:
            print(f"⚠️ Skipped {failed_count} videos due to errors or timeouts")
        
        return entries if entries else None
    
    def process_entry(self, entry: Dict) -> Tuple[str, str, str, str]:
        """Process a single playlist entry and extract metadata."""
        title = entry.get('title', '')
        artist = entry.get('artist', entry.get('uploader', ''))
        track = entry.get('track', '')
        album = entry.get('album', '')
        
        # Check if we have meaningful metadata
        has_details = bool(artist and (track or album))
        
        if has_details:
            self.songs_with_details += 1
        else:
            self.songs_without_details += 1
        
        self.processed_songs += 1
        
        return title, artist, track, album
    
    def save_to_csv(self, entries: List[Dict]) -> bool:
        """Save playlist entries to CSV file."""
        try:
            with open(self.output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow(['title', 'artist', 'track', 'album'])
                
                # Process entries with progress bar
                print(f"\n📝 Processing {len(entries)} songs...")
                
                for entry in tqdm(entries, desc="Processing songs", unit="song"):
                    title, artist, track, album = self.process_entry(entry)
                    writer.writerow([title, artist, track, album])
                
                return True
                
        except Exception as e:
            print(f"❌ Error writing to CSV: {e}")
            return False
    
    def print_statistics(self):
        """Print processing statistics."""
        print(f"\n📊 Processing Complete!")
        print(f"   • Total videos found: {self.total_songs}")
        print(f"   • Songs successfully processed: {self.processed_songs}")
        print(f"   • Songs with artist/track details: {self.songs_with_details}")
        print(f"   • Songs without detailed metadata: {self.songs_without_details}")
        print(f"   • Videos skipped (failed/timeout): {len(self.skipped_videos)}")
        print(f"   • Output saved to: {self.output_file}")
        
        if self.songs_without_details > 0 and self.processed_songs > 0:
            percentage = (self.songs_without_details / self.processed_songs) * 100
            print(f"   • ⚠️  {percentage:.1f}% of processed songs lack detailed metadata")
        
        if len(self.skipped_videos) > 0:
            print(f"   • ⚠️  {len(self.skipped_videos)} videos were skipped due to errors or timeouts")
    
    def run(self) -> bool:
        """Main execution method."""
        # Validate playlist URL
        playlist_id = self.extract_playlist_id(self.playlist_url)
        if not playlist_id:
            print("❌ Invalid YouTube playlist URL")
            return False
        
        # Fetch playlist data (now returns list of entries directly)
        entries = self.fetch_playlist_data()
        if not entries:
            print("❌ No entries found in playlist or all videos failed")
            return False
        
        print(f"✅ Successfully fetched metadata for {len(entries)} videos")
        
        # Save to CSV
        success = self.save_to_csv(entries)
        if not success:
            return False
        
        # Print statistics
        self.print_statistics()
        
        return True


def main():
    """Main function that uses global configuration variables."""
    print(f"🚀 YouTube Playlist Metadata Extractor")
    print(f"📁 Playlist URL: {PLAYLIST_URL}")
    print(f"💾 Output file: {OUTPUT_FILE}")
        
    # Validate output file path
    output_path = Path(OUTPUT_FILE)
    if output_path.exists():
        response = input(f"⚠️  File '{OUTPUT_FILE}' already exists. Overwrite? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Operation cancelled.")
            return False
    
    # Create and run extractor
    extractor = PlaylistMetadataExtractor(PLAYLIST_URL, OUTPUT_FILE, TIMEOUT_SECONDS)
    success = extractor.run()
    
    if success:
        print("🎉 Extraction completed successfully!")
        return True
    else:
        print("💥 Extraction failed!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)