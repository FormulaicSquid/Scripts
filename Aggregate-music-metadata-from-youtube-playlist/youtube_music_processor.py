#!/usr/bin/env python3
"""
YouTube Music Metadata Processor

A comprehensive script that processes YouTube playlists to extract, enhance, and organize
music metadata. This replaces multiple individual scripts with a single, well-structured
pipeline that follows good coding practices.

Features:
- Extract metadata from YouTube playlists (no downloads)
- Enhance metadata using MusicBrainz database
- Find original studio albums for tracks
- Sort results by artist and album
- Configurable pipeline steps
"""

import subprocess
import json
import csv
import re
import time
import requests
import argparse
import urllib3
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from tqdm import tqdm

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class Config:
    """Configuration settings."""
    rate_limit_delay: float = 1.0
    youtube_timeout: int = 30
    request_timeout: int = 15
    user_agent: str = "YouTubeMusicProcessor/1.0 (https://github.com/FormulaicSquid/Scripts)"


@dataclass 
class ProcessingStats:
    """Track processing statistics."""
    total_entries: int = 0
    successful: int = 0
    failed: int = 0
    albums_expanded: int = 0
    
    def increment(self, key: str, amount: int = 1) -> None:
        """Increment a counter."""
        if hasattr(self, key):
            setattr(self, key, getattr(self, key) + amount)
    
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_entries == 0:
            return 0.0
        return (self.successful / self.total_entries) * 100
    
    def print_summary(self, title: str, output_file: str = "") -> None:
        """Print processing summary."""
        print(f"\n📊 {title}")
        print(f"   • Total entries: {self.total_entries}")
        print(f"   • Successful: {self.successful}")
        print(f"   • Failed: {self.failed}")
        if self.albums_expanded > 0:
            print(f"   • Albums expanded: {self.albums_expanded}")
        if self.total_entries > 0:
            print(f"   • Success rate: {self.success_rate():.1f}%")
        if output_file:
            print(f"   • Output: {output_file}")


@dataclass
class MusicTrack:
    """Represents a music track with metadata."""
    title: str = ""
    artist: str = ""
    track: str = ""
    album: str = ""
    uploader: str = ""
    duration: str = ""
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for CSV output."""
        return {
            'title': self.title,
            'artist': self.artist, 
            'track': self.track,
            'album': self.album,
            'uploader': self.uploader,
            'duration': self.duration
        }


class TitleParser:
    """Utility class for parsing YouTube video titles."""
    
    # Patterns for extracting artist and track from titles
    PATTERNS = [
        r'^(.+?)\s*-\s*(.+?)(?:\s*\(.*\))?(?:\s*\[.*\])?$',  # Artist - Track
        r'^(.+?)\s*:\s*(.+?)(?:\s*\(.*\))?(?:\s*\[.*\])?$',  # Artist: Track
        r'^["\'](.+?)["\'].*?by\s+(.+?)(?:\s*\(.*\))?$',     # "Track" by Artist
    ]
    
    ALBUM_INDICATORS = ['full album', 'complete album', 'entire album', 'whole album']
    CLEANUP_TERMS = ['official', 'music video', 'lyric video', 'audio', 'hd', 'hq', 'lyrics']
    
    @classmethod
    def clean_title(cls, title: str) -> str:
        """Clean title by removing common prefixes/suffixes and unwanted content."""
        text = title.strip()
        text_lower = text.lower()
        
        # Remove common terms
        for term in cls.CLEANUP_TERMS:
            if text_lower.startswith(term):
                text = text[len(term):].strip()
                text_lower = text.lower()
            if text_lower.endswith(term):
                text = text[:-len(term)].strip()
                text_lower = text.lower()
        
        # Remove content in parentheses and brackets
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'\[[^\]]*\]', '', text)
        
        return text.strip()
    
    @classmethod
    def parse_title(cls, title: str) -> Tuple[str, str, bool]:
        """
        Parse title to extract artist and track.
        Returns: (artist, track, is_full_album)
        """
        cleaned_title = cls.clean_title(title)
        is_full_album = any(indicator in title.lower() for indicator in cls.ALBUM_INDICATORS)
        
        # Try each pattern
        for pattern in cls.PATTERNS:
            match = re.match(pattern, cleaned_title)
            if match:
                return match.group(1).strip(), match.group(2).strip(), is_full_album
        
        # If no pattern matches, return original
        return "", cleaned_title, is_full_album


class MusicBrainzAPI:
    """Handles MusicBrainz API interactions."""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': config.user_agent})
        self.session.verify = False  # Handle SSL issues
        self.last_request = 0
    
    def _rate_limit(self) -> None:
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request
        if elapsed < self.config.rate_limit_delay:
            time.sleep(self.config.rate_limit_delay - elapsed)
        self.last_request = time.time()
    
    def _make_request(self, url: str) -> Optional[Dict[str, Any]]:
        """Make rate-limited request to MusicBrainz."""
        self._rate_limit()
        
        base_urls = [
            "https://musicbrainz.org/ws/2/",
            "http://musicbrainz.org/ws/2/"
        ]
        
        for base_url in base_urls:
            try:
                full_url = url.replace("https://musicbrainz.org/ws/2/", base_url)
                response = self.session.get(full_url, timeout=self.config.request_timeout)
                if response.status_code == 200:
                    return response.json()
            except Exception:
                continue
        return None
    
    def search_track(self, artist: str, track: str) -> Optional[Dict[str, Any]]:
        """Search for track recording."""
        query = f'artist:"{artist}" AND recording:"{track}"'
        url = f"https://musicbrainz.org/ws/2/recording/?query={query}&fmt=json&limit=5"
        return self._make_request(url)
    
    def search_studio_album(self, artist: str, track: str) -> Optional[Dict[str, Any]]:
        """Search for studio albums containing a track."""
        query = (f'artist:"{artist}" AND recording:"{track}" AND primarytype:album '
                f'AND NOT secondarytype:live AND NOT secondarytype:compilation '
                f'AND NOT secondarytype:soundtrack')
        url = f"https://musicbrainz.org/ws/2/release-group/?query={query}&fmt=json&limit=5"
        return self._make_request(url)
    
    def search_album_release(self, artist: str, album: str) -> Optional[Dict[str, Any]]:
        """Search for album releases."""
        query = f'artist:"{artist}" AND release:"{album}"'
        url = f"https://musicbrainz.org/ws/2/release/?query={query}&fmt=json&limit=5"
        return self._make_request(url)
    
    def get_album_tracks(self, release_id: str) -> List[MusicTrack]:
        """Get tracks from a release."""
        url = f"https://musicbrainz.org/ws/2/release/{release_id}?inc=recordings&fmt=json"
        data = self._make_request(url)
        
        tracks = []
        if data and 'media' in data:
            album_title = data.get('title', '')
            artist_name = ''
            if 'artist-credit' in data and data['artist-credit']:
                artist_name = data['artist-credit'][0].get('name', '')
            
            for medium in data['media']:
                if 'tracks' in medium:
                    for track in medium['tracks']:
                        tracks.append(MusicTrack(
                            track=track.get('title', ''),
                            artist=artist_name,
                            album=album_title
                        ))
        return tracks


class YouTubePlaylistExtractor:
    """Extracts metadata from YouTube playlists."""
    
    def __init__(self, config: Config):
        self.config = config
        self.stats = ProcessingStats()
    
    def extract_playlist_urls(self, playlist_url: str) -> List[str]:
        """Get video URLs from playlist."""
        try:
            cmd = ["yt-dlp", "--flat-playlist", "--print", "url", playlist_url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                urls = [url.strip() for url in result.stdout.strip().split('\n') if url.strip()]
                return urls
            else:
                raise RuntimeError(f"yt-dlp failed: {result.stderr}")
        except Exception as e:
            raise RuntimeError(f"Failed to extract playlist URLs: {e}")
    
    def extract_video_metadata(self, video_url: str) -> Optional[Dict[str, str]]:
        """Extract metadata from single video."""
        try:
            cmd = [
                "yt-dlp", "--print", "%(title)s|||%(uploader)s|||%(duration)s",
                "--no-download", video_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                  timeout=self.config.youtube_timeout)
            
            if result.returncode == 0:
                parts = result.stdout.strip().split('|||')
                return {
                    'title': parts[0] if len(parts) > 0 else '',
                    'uploader': parts[1] if len(parts) > 1 else '',
                    'duration': parts[2] if len(parts) > 2 else ''
                }
            return None
        except Exception:
            return None
    
    def process_playlist(self, playlist_url: str) -> List[MusicTrack]:
        """Extract and parse playlist metadata."""
        print("🔍 Extracting playlist metadata...")
        
        urls = self.extract_playlist_urls(playlist_url)
        self.stats.total_entries = len(urls)
        print(f"📖 Found {len(urls)} videos in playlist")
        
        tracks = []
        
        with tqdm(urls, desc="Extracting metadata", unit="video") as pbar:
            for url in pbar:
                try:
                    metadata = self.extract_video_metadata(url)
                    if metadata and metadata['title']:
                        artist, track, is_album = TitleParser.parse_title(metadata['title'])
                        
                        tracks.append(MusicTrack(
                            title=metadata['title'],
                            artist=artist,
                            track=track,
                            uploader=metadata.get('uploader', ''),
                            duration=metadata.get('duration', '')
                        ))
                        self.stats.increment('successful')
                    else:
                        self.stats.increment('failed')
                    
                    pbar.set_postfix({
                        'Success': self.stats.successful,
                        'Failed': self.stats.failed
                    })
                    
                except KeyboardInterrupt:
                    print("\n⚠️ Interrupted by user")
                    break
                except Exception:
                    self.stats.increment('failed')
        
        return tracks


class MetadataEnhancer:
    """Enhances metadata using MusicBrainz."""
    
    def __init__(self, config: Config):
        self.api = MusicBrainzAPI(config)
        self.stats = ProcessingStats()
    
    def is_english_content(self, text: str) -> bool:
        """Check if text is mostly English characters."""
        if not text:
            return False
        latin_chars = sum(1 for char in text if ord(char) < 256)
        total_chars = len(text)
        return latin_chars >= (total_chars * 0.7)  # At least 70% latin characters
    
    def enhance_track(self, track: MusicTrack) -> List[MusicTrack]:
        """Enhance a single track with MusicBrainz data."""
        if not track.artist or not track.track:
            return [track]
        
        # Skip non-English content
        if not self.is_english_content(track.artist) or not self.is_english_content(track.track):
            return [track]
        
        try:
            # Check if it's a full album
            _, _, is_album = TitleParser.parse_title(track.title)
            
            if is_album:
                # Try to get album tracks
                data = self.api.search_album_release(track.artist, track.track)
                if data and 'releases' in data and data['releases']:
                    release = data['releases'][0]
                    album_tracks = self.api.get_album_tracks(release['id'])
                    if album_tracks:
                        self.stats.increment('albums_expanded')
                        self.stats.increment('successful')
                        return album_tracks
            else:
                # Search for individual track
                data = self.api.search_track(track.artist, track.track)
                if data and 'recordings' in data and data['recordings']:
                    recording = data['recordings'][0]
                    
                    # Extract enhanced metadata
                    artist_name = track.artist
                    if 'artist-credit' in recording and recording['artist-credit']:
                        artist_name = recording['artist-credit'][0].get('name', track.artist)
                    
                    track_name = recording.get('title', track.track)
                    
                    album_name = ''
                    if 'releases' in recording and recording['releases']:
                        album_name = recording['releases'][0].get('title', '')
                    
                    enhanced_track = MusicTrack(
                        title=track.title,
                        artist=artist_name,
                        track=track_name,
                        album=album_name,
                        uploader=track.uploader,
                        duration=track.duration
                    )
                    
                    self.stats.increment('successful')
                    return [enhanced_track]
        
        except Exception as e:
            print(f"  ⚠️ MusicBrainz error for {track.artist} - {track.track}: {e}")
        
        self.stats.increment('failed')
        return [track]
    
    def process_tracks(self, tracks: List[MusicTrack]) -> List[MusicTrack]:
        """Enhance multiple tracks."""
        print("🎵 Enhancing metadata with MusicBrainz...")
        
        self.stats.total_entries = len(tracks)
        enhanced_tracks = []
        
        with tqdm(tracks, desc="Enhancing metadata", unit="track") as pbar:
            for track in pbar:
                try:
                    result_tracks = self.enhance_track(track)
                    enhanced_tracks.extend(result_tracks)
                    
                    pbar.set_postfix({
                        'Enhanced': self.stats.successful,
                        'Failed': self.stats.failed,
                        'Albums': self.stats.albums_expanded
                    })
                    
                except KeyboardInterrupt:
                    print("\n⚠️ Interrupted by user")
                    break
                except Exception as e:
                    print(f"  ❌ Error: {e}")
                    enhanced_tracks.append(track)
                    self.stats.increment('failed')
        
        return enhanced_tracks


class StudioAlbumFinder:
    """Finds original studio albums for tracks."""
    
    def __init__(self, config: Config):
        self.api = MusicBrainzAPI(config)
        self.stats = ProcessingStats()
    
    def find_studio_album(self, track: MusicTrack) -> str:
        """Find studio album for a track."""
        if not track.artist or not track.track:
            return track.album
        
        try:
            data = self.api.search_studio_album(track.artist, track.track)
            if data and 'release-groups' in data and data['release-groups']:
                studio_album = data['release-groups'][0].get('title', '')
                if studio_album:
                    return studio_album
        except Exception:
            pass
        
        return track.album
    
    def process_tracks(self, tracks: List[MusicTrack]) -> List[MusicTrack]:
        """Find studio albums for tracks."""
        print("📀 Finding original studio albums...")
        
        self.stats.total_entries = len(tracks)
        result_tracks = []
        
        with tqdm(tracks, desc="Finding studio albums", unit="track") as pbar:
            for track in pbar:
                try:
                    original_album = track.album
                    studio_album = self.find_studio_album(track)
                    
                    # Create new track with studio album info
                    new_track = MusicTrack(
                        title=track.title,
                        artist=track.artist,
                        track=track.track,
                        album=studio_album,
                        uploader=track.uploader,
                        duration=track.duration
                    )
                    
                    # Combine albums if different
                    if original_album and studio_album and original_album.lower() != studio_album.lower():
                        new_track.album = f"{original_album} / {studio_album}"
                    
                    if studio_album and studio_album != original_album:
                        self.stats.increment('successful')
                    else:
                        self.stats.increment('failed')
                    
                    result_tracks.append(new_track)
                    
                    pbar.set_postfix({
                        'Found': self.stats.successful,
                        'Failed': self.stats.failed
                    })
                    
                except KeyboardInterrupt:
                    print("\n⚠️ Interrupted by user")
                    break
                except Exception as e:
                    print(f"  ❌ Error: {e}")
                    result_tracks.append(track)
                    self.stats.increment('failed')
        
        return result_tracks


class CSVManager:
    """Handles CSV file operations."""
    
    @staticmethod
    def save_tracks(tracks: List[MusicTrack], filename: str) -> bool:
        """Save tracks to CSV file."""
        if not tracks:
            print("❌ No tracks to save")
            return False
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                fieldnames = tracks[0].to_dict().keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows([track.to_dict() for track in tracks])
            
            print(f"📝 Saved {len(tracks)} tracks to {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving CSV: {e}")
            return False
    
    @staticmethod
    def load_tracks(filename: str) -> List[MusicTrack]:
        """Load tracks from CSV file."""
        if not Path(filename).exists():
            raise FileNotFoundError(f"File not found: {filename}")
        
        tracks = []
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tracks.append(MusicTrack(
                        title=row.get('title', ''),
                        artist=row.get('artist', ''),
                        track=row.get('track', ''),
                        album=row.get('album', ''),
                        uploader=row.get('uploader', ''),
                        duration=row.get('duration', '')
                    ))
            
            print(f"📖 Loaded {len(tracks)} tracks from {filename}")
            return tracks
            
        except Exception as e:
            raise RuntimeError(f"Error loading CSV: {e}")
    
    @staticmethod
    def sort_tracks(tracks: List[MusicTrack]) -> List[MusicTrack]:
        """Sort tracks by artist, then album, then track."""
        def sort_key(track: MusicTrack) -> Tuple[str, int, str, str]:
            artist = track.artist.lower().strip()
            album = track.album.strip()
            track_name = track.track.lower().strip()
            
            # Empty albums sorted last (1 > 0)
            has_album = 0 if album else 1
            album_lower = album.lower() if album else ''
            
            return (artist, has_album, album_lower, track_name)
        
        return sorted(tracks, key=sort_key)


def confirm_overwrite(filename: str) -> bool:
    """Ask user confirmation before overwriting file."""
    if Path(filename).exists():
        response = input(f"⚠️  File '{filename}' already exists. Overwrite? (y/N): ")
        return response.lower() in ['y', 'yes']
    return True


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description='YouTube Music Metadata Processor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s extract "https://youtube.com/playlist?list=..." -o data/playlist.csv
  %(prog)s enhance data/playlist.csv -o data/enhanced.csv
  %(prog)s studio data/enhanced.csv -o data/studio.csv  
  %(prog)s sort data/studio.csv -o data/sorted.csv
  %(prog)s pipeline "https://youtube.com/playlist?list=..." -o data/final.csv
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract YouTube playlist metadata')
    extract_parser.add_argument('playlist_url', help='YouTube playlist URL')
    extract_parser.add_argument('-o', '--output', default='data/playlist.csv', help='Output CSV file')
    extract_parser.add_argument('--timeout', type=int, default=30, help='Timeout per video (seconds)')
    
    # Enhance command
    enhance_parser = subparsers.add_parser('enhance', help='Enhance metadata with MusicBrainz')
    enhance_parser.add_argument('input_file', help='Input CSV file')
    enhance_parser.add_argument('-o', '--output', default='data/enhanced.csv', help='Output CSV file')
    enhance_parser.add_argument('-r', '--rate-limit', type=float, default=1.0, help='Rate limit (seconds)')
    
    # Studio albums command
    studio_parser = subparsers.add_parser('studio', help='Find original studio albums')
    studio_parser.add_argument('input_file', help='Input CSV file')
    studio_parser.add_argument('-o', '--output', default='data/studio.csv', help='Output CSV file')
    studio_parser.add_argument('-r', '--rate-limit', type=float, default=1.0, help='Rate limit (seconds)')
    
    # Sort command
    sort_parser = subparsers.add_parser('sort', help='Sort tracks by artist and album')
    sort_parser.add_argument('input_file', help='Input CSV file')
    sort_parser.add_argument('-o', '--output', default='data/sorted.csv', help='Output CSV file')
    
    # Complete pipeline command
    pipeline_parser = subparsers.add_parser('pipeline', help='Run complete processing pipeline')
    pipeline_parser.add_argument('playlist_url', help='YouTube playlist URL')
    pipeline_parser.add_argument('-o', '--output', default='data/final_music.csv', help='Final output CSV file')
    pipeline_parser.add_argument('-r', '--rate-limit', type=float, default=1.0, help='Rate limit (seconds)')
    pipeline_parser.add_argument('--skip-enhance', action='store_true', help='Skip MusicBrainz enhancement')
    pipeline_parser.add_argument('--skip-studio', action='store_true', help='Skip studio album search')
    pipeline_parser.add_argument('--keep-intermediate', action='store_true', help='Keep intermediate CSV files')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return False
    
    config = Config()
    if hasattr(args, 'rate_limit'):
        config.rate_limit_delay = args.rate_limit
    if hasattr(args, 'timeout'):
        config.youtube_timeout = args.timeout
    
    try:
        if args.command == 'extract':
            if not confirm_overwrite(args.output):
                return False
            
            extractor = YouTubePlaylistExtractor(config)
            tracks = extractor.process_playlist(args.playlist_url)
            success = CSVManager.save_tracks(tracks, args.output)
            
            if success:
                extractor.stats.print_summary("YouTube Extraction Complete", args.output)
            
            return success
        
        elif args.command == 'enhance':
            if not confirm_overwrite(args.output):
                return False
            
            tracks = CSVManager.load_tracks(args.input_file)
            enhancer = MetadataEnhancer(config)
            enhanced_tracks = enhancer.process_tracks(tracks)
            success = CSVManager.save_tracks(enhanced_tracks, args.output)
            
            if success:
                enhancer.stats.print_summary("Metadata Enhancement Complete", args.output)
            
            return success
        
        elif args.command == 'studio':
            if not confirm_overwrite(args.output):
                return False
            
            tracks = CSVManager.load_tracks(args.input_file)
            finder = StudioAlbumFinder(config)
            studio_tracks = finder.process_tracks(tracks)
            success = CSVManager.save_tracks(studio_tracks, args.output)
            
            if success:
                finder.stats.print_summary("Studio Album Search Complete", args.output)
            
            return success
        
        elif args.command == 'sort':
            if not confirm_overwrite(args.output):
                return False
            
            tracks = CSVManager.load_tracks(args.input_file)
            print("🔄 Sorting tracks by artist, album, and track...")
            sorted_tracks = CSVManager.sort_tracks(tracks)
            success = CSVManager.save_tracks(sorted_tracks, args.output)
            
            if success:
                # Print sorting statistics
                artists = set(t.artist for t in sorted_tracks if t.artist)
                albums = set(t.album for t in sorted_tracks if t.album)
                no_album = sum(1 for t in sorted_tracks if not t.album)
                
                print(f"\n📊 Sorting Complete")
                print(f"   • Total tracks: {len(sorted_tracks)}")
                print(f"   • Unique artists: {len(artists)}")
                print(f"   • Unique albums: {len(albums)}")
                print(f"   • Tracks without album: {no_album}")
                print(f"   • Output: {args.output}")
            
            return success
        
        elif args.command == 'pipeline':
            if not confirm_overwrite(args.output):
                return False
            
            print("🚀 Running complete music processing pipeline...\n")
            
            # Step 1: Extract
            print("Step 1/4: Extracting YouTube playlist")
            extractor = YouTubePlaylistExtractor(config)
            tracks = extractor.process_playlist(args.playlist_url)
            
            if not tracks:
                print("❌ No tracks extracted, stopping pipeline")
                return False
            
            extractor.stats.print_summary("Extraction Complete")
            
            if args.keep_intermediate:
                CSVManager.save_tracks(tracks, "data/01_extracted.csv")
            
            # Step 2: Enhance (optional)
            if not args.skip_enhance:
                print("\nStep 2/4: Enhancing metadata with MusicBrainz")
                enhancer = MetadataEnhancer(config)
                tracks = enhancer.process_tracks(tracks)
                enhancer.stats.print_summary("Enhancement Complete")
                
                if args.keep_intermediate:
                    CSVManager.save_tracks(tracks, "data/02_enhanced.csv")
            else:
                print("\nStep 2/4: Skipping metadata enhancement")
            
            # Step 3: Studio albums (optional)
            if not args.skip_studio:
                print("\nStep 3/4: Finding original studio albums")
                finder = StudioAlbumFinder(config)
                tracks = finder.process_tracks(tracks)
                finder.stats.print_summary("Studio Album Search Complete")
                
                if args.keep_intermediate:
                    CSVManager.save_tracks(tracks, "data/03_studio_albums.csv")
            else:
                print("\nStep 3/4: Skipping studio album search")
            
            # Step 4: Sort
            print("\nStep 4/4: Sorting final results")
            print("🔄 Sorting tracks by artist, album, and track...")
            sorted_tracks = CSVManager.sort_tracks(tracks)
            
            # Save final results
            success = CSVManager.save_tracks(sorted_tracks, args.output)
            
            if success:
                print(f"\n🎉 Pipeline completed successfully!")
                print(f"📝 Final output saved to: {args.output}")
                
                # Final statistics
                artists = set(t.artist for t in sorted_tracks if t.artist)
                albums = set(t.album for t in sorted_tracks if t.album)
                no_album = sum(1 for t in sorted_tracks if not t.album)
                
                print(f"\n📊 Final Results Summary")
                print(f"   • Total tracks: {len(sorted_tracks)}")
                print(f"   • Unique artists: {len(artists)}")
                print(f"   • Unique albums: {len(albums)}")
                print(f"   • Tracks without album: {no_album}")
            
            return success
    
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)