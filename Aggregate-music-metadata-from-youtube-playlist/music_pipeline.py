#!/usr/bin/env python3
"""
Music Metadata Pipeline

A comprehensive script that can extract YouTube playlist metadata, enhance it with
MusicBrainz data, find studio albums, and sort the results. This replaces the
individual scripts with a single, well-structured pipeline.
"""

import re
import argparse
import subprocess
import json
from typing import Dict, List, Optional
from tqdm import tqdm

# Local imports
from music_utils import MusicBrainzAPI, CSVProcessor, confirm_overwrite, Statistics, MusicTrack
from config import CONFIG


class TitleParser:
    """Parses YouTube video titles to extract artist and track information."""
    
    # Common patterns for parsing music titles
    PATTERNS = [
        # Artist - Track
        r'^(.+?)\s*-\s*(.+?)(?:\s*\(.*\))?(?:\s*\[.*\])?$',
        # Artist: Track
        r'^(.+?)\s*:\s*(.+?)(?:\s*\(.*\))?(?:\s*\[.*\])?$',
        # "Track" by Artist
        r'^["\'](.+?)["\'].*?by\s+(.+?)(?:\s*\(.*\))?(?:\s*\[.*\])?$',
        # Track - Artist (reverse)
        r'^(.+?)\s*-\s*(.+?)(?:\s*\(.*\))?(?:\s*\[.*\])?$'
    ]
    
    ALBUM_INDICATORS = ['full album', 'complete album', 'entire album', 'whole album']
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean text by removing extra whitespace and unwanted characters."""
        # Remove common prefixes/suffixes
        prefixes = ['official', 'music video', 'lyric video', 'audio', 'hd', 'hq']
        suffixes = ['official', 'music video', 'lyric video', 'audio', 'lyrics', 'hd', 'hq']
        
        text = text.strip()
        text_lower = text.lower()
        
        for prefix in prefixes:
            if text_lower.startswith(prefix):
                text = text[len(prefix):].strip()
                text_lower = text.lower()
        
        for suffix in suffixes:
            if text_lower.endswith(suffix):
                text = text[:-len(suffix)].strip()
                text_lower = text.lower()
        
        # Remove parentheses and brackets content
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'\[[^\]]*\]', '', text)
        
        return text.strip()
    
    @classmethod
    def parse_title(cls, title: str) -> Dict[str, str]:
        """Parse a YouTube title to extract artist, track, and album info."""
        original_title = title
        cleaned_title = cls.clean_text(title)
        
        # Check if it's a full album
        is_full_album = any(indicator in title.lower() for indicator in cls.ALBUM_INDICATORS)
        
        result = {
            'artist': '',
            'track': '',
            'album': '',
            'is_full_album': is_full_album,
            'original_title': original_title
        }
        
        # Try each pattern
        for pattern in cls.PATTERNS:
            match = re.match(pattern, cleaned_title)
            if match:
                if is_full_album:
                    # For albums, treat the second part as album name
                    result['artist'] = match.group(1).strip()
                    result['track'] = match.group(2).strip()  # This will be treated as album name
                else:
                    result['artist'] = match.group(1).strip()
                    result['track'] = match.group(2).strip()
                break
        
        return result


class YouTubeExtractor:
    """Extracts metadata from YouTube playlists."""
    
    def __init__(self, timeout: int = CONFIG.YOUTUBE_TIMEOUT):
        self.timeout = timeout
        self.stats = Statistics()
    
    def extract_playlist_urls(self, playlist_url: str) -> List[str]:
        """Extract video URLs from playlist."""
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
        """Extract metadata from a single video."""
        try:
            cmd = [
                "yt-dlp", "--print", "%(title)s|||%(uploader)s|||%(duration)s",
                "--no-download", video_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
            
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
    
    def extract_playlist(self, playlist_url: str, output_file: str) -> bool:
        """Extract full playlist metadata and save to CSV."""
        print(f"🔍 Extracting playlist metadata...")
        
        try:
            urls = self.extract_playlist_urls(playlist_url)
            self.stats.set('total_videos', len(urls))
            print(f"📖 Found {len(urls)} videos in playlist")
            
            results = []
            
            with tqdm(urls, desc="Extracting metadata", unit="video") as pbar:
                for url in pbar:
                    try:
                        metadata = self.extract_video_metadata(url)
                        if metadata and metadata['title']:
                            parsed = TitleParser.parse_title(metadata['title'])
                            results.append({
                                'title': metadata['title'],
                                'artist': parsed['artist'],
                                'track': parsed['track'],
                                'album': parsed.get('album', ''),
                                'uploader': metadata.get('uploader', ''),
                                'duration': metadata.get('duration', '')
                            })
                            self.stats.increment('successful')
                        else:
                            self.stats.increment('failed')
                        
                        pbar.set_postfix({
                            'Success': self.stats.get('successful'),
                            'Failed': self.stats.get('failed')
                        })
                        
                    except KeyboardInterrupt:
                        print(f"\n⚠️ Interrupted by user")
                        break
                    except Exception:
                        self.stats.increment('failed')
            
            # Save results
            if results:
                CSVProcessor.write_csv(output_file, results)
                print(f"\n📝 Saved {len(results)} entries to {output_file}")
                return True
            else:
                print("❌ No metadata extracted")
                return False
                
        except Exception as e:
            print(f"❌ Error extracting playlist: {e}")
            return False


class MetadataEnhancer:
    """Enhances metadata using MusicBrainz database."""
    
    def __init__(self, rate_limit: float = CONFIG.RATE_LIMIT_DELAY):
        self.api = MusicBrainzAPI(CONFIG.USER_AGENTS['metadata_enhancer'], rate_limit)
        self.stats = Statistics()
    
    def is_english_content(self, text: str) -> bool:
        """Check if text contains mostly English characters."""
        if not text:
            return False
        latin_chars = sum(1 for char in text if ord(char) < 256)
        non_latin_chars = len(text) - latin_chars
        return latin_chars >= non_latin_chars
    
    def enhance_entry(self, entry: Dict[str, str]) -> List[MusicTrack]:
        """Enhance a single entry with MusicBrainz data."""
        title = entry.get('title', '')
        existing_artist = entry.get('artist', '').strip()
        
        if not title:
            return [MusicTrack(track=title, artist=existing_artist)]
        
        parsed = TitleParser.parse_title(title)
        
        # Use existing artist if parsed artist is empty
        if not parsed['artist'] and existing_artist:
            parsed['artist'] = existing_artist
        
        if not parsed['artist']:
            self.stats.increment('failed')
            return [MusicTrack(track=title)]
        
        # Skip non-English content
        if not self.is_english_content(parsed['artist']) and not self.is_english_content(parsed['track']):
            self.stats.increment('failed')
            return [MusicTrack(track=parsed['track'], artist=parsed['artist'])]
        
        try:
            if parsed['is_full_album']:
                # Search for album
                data = self.api.search_album(parsed['artist'], parsed['track'])
                if data and 'releases' in data and data['releases']:
                    release = data['releases'][0]
                    tracks = self.api.get_album_tracks(release['id'])
                    if tracks:
                        self.stats.increment('albums_expanded')
                        self.stats.increment('successful')
                        return tracks
            else:
                # Search for individual track
                data = self.api.search_track(parsed['artist'], parsed['track'])
                if data and 'recordings' in data and data['recordings']:
                    recording = data['recordings'][0]
                    
                    # Extract artist name
                    artist_name = parsed['artist']
                    if 'artist-credit' in recording and recording['artist-credit']:
                        artist_name = recording['artist-credit'][0].get('name', parsed['artist'])
                    
                    # Extract album name
                    album_name = ''
                    if 'releases' in recording and recording['releases']:
                        album_name = recording['releases'][0].get('title', '')
                    
                    track_name = recording.get('title', parsed['track'])
                    
                    self.stats.increment('successful')
                    return [MusicTrack(track=track_name, artist=artist_name, album=album_name)]
        
        except Exception as e:
            print(f"  ⚠️ MusicBrainz error: {e}")
        
        # Return parsed data if no enhancement found
        self.stats.increment('failed')
        return [MusicTrack(track=parsed['track'], artist=parsed['artist'])]
    
    def enhance_csv(self, input_file: str, output_file: str) -> bool:
        """Enhance metadata in CSV file."""
        try:
            data = CSVProcessor.read_csv(input_file)
            CSVProcessor.validate_required_columns(data, ['title'])
            
            self.stats.set('total_entries', len(data))
            print(f"📖 Loaded {len(data)} entries from {input_file}")
            
            enhanced_tracks = []
            
            with tqdm(data, desc="Enhancing metadata", unit="entry") as pbar:
                for entry in pbar:
                    try:
                        tracks = self.enhance_entry(entry)
                        enhanced_tracks.extend(track.to_dict() for track in tracks)
                        
                        pbar.set_postfix({
                            'Enhanced': self.stats.get('successful'),
                            'Failed': self.stats.get('failed'),
                            'Albums': self.stats.get('albums_expanded')
                        })
                        
                    except KeyboardInterrupt:
                        print(f"\n⚠️ Interrupted by user")
                        break
                    except Exception as e:
                        print(f"  ❌ Error: {e}")
                        self.stats.increment('failed')
                        enhanced_tracks.append(entry)
            
            # Save results
            if enhanced_tracks:
                CSVProcessor.write_csv(output_file, enhanced_tracks)
                print(f"\n📝 Saved {len(enhanced_tracks)} tracks to {output_file}")
                return True
            else:
                print("❌ No enhanced data to save")
                return False
                
        except Exception as e:
            print(f"❌ Error enhancing metadata: {e}")
            return False


class StudioAlbumFinder:
    """Finds studio albums for tracks."""
    
    def __init__(self, rate_limit: float = CONFIG.RATE_LIMIT_DELAY):
        self.api = MusicBrainzAPI(CONFIG.USER_AGENTS['studio_album_finder'], rate_limit)
        self.stats = Statistics()
    
    def find_studio_album(self, artist: str, track: str) -> Optional[str]:
        """Find studio album for a track."""
        try:
            data = self.api.search_studio_album(artist, track)
            
            if data and 'release-groups' in data and data['release-groups']:
                release_group = data['release-groups'][0]
                return release_group.get('title', '')
            
            return None
            
        except Exception:
            return None
    
    def process_csv(self, input_file: str, output_file: str) -> bool:
        """Process CSV to find studio albums."""
        try:
            data = CSVProcessor.read_csv(input_file)
            CSVProcessor.validate_required_columns(data, ['track', 'artist'])
            
            self.stats.set('total_entries', len(data))
            already_had_albums = len([entry for entry in data if entry.get('album', '').strip()])
            self.stats.set('already_had_albums', already_had_albums)
            
            print(f"📖 Loaded {len(data)} entries from {input_file}")
            print(f"📀 {already_had_albums} entries already have album data")
            
            enhanced_data = []
            
            with tqdm(data, desc="Finding studio albums", unit="entry") as pbar:
                for entry in pbar:
                    try:
                        track = entry.get('track', '').strip()
                        artist = entry.get('artist', '').strip()
                        existing_album = entry.get('album', '').strip()
                        
                        result = entry.copy()
                        
                        if track and artist:
                            studio_album = self.find_studio_album(artist, track)
                            
                            if studio_album:
                                if existing_album and studio_album.lower() != existing_album.lower():
                                    result['album'] = f"{existing_album} / {studio_album}"
                                elif not existing_album:
                                    result['album'] = studio_album
                                self.stats.increment('successful')
                            else:
                                self.stats.increment('failed')
                        else:
                            self.stats.increment('failed')
                        
                        enhanced_data.append(result)
                        
                        pbar.set_postfix({
                            'Found': self.stats.get('successful'),
                            'Failed': self.stats.get('failed')
                        })
                        
                    except KeyboardInterrupt:
                        print(f"\n⚠️ Interrupted by user")
                        break
                    except Exception as e:
                        print(f"  ❌ Error: {e}")
                        enhanced_data.append(entry)
                        self.stats.increment('failed')
            
            # Save results
            if enhanced_data:
                CSVProcessor.write_csv(output_file, enhanced_data)
                print(f"\n📝 Saved {len(enhanced_data)} entries to {output_file}")
                return True
            else:
                print("❌ No data to save")
                return False
                
        except Exception as e:
            print(f"❌ Error finding studio albums: {e}")
            return False


class MusicSorter:
    """Sorts music CSV by artist and album."""
    
    @staticmethod
    def sort_key(entry: Dict[str, str]) -> tuple:
        """Generate sort key for an entry."""
        artist = entry.get('artist', '').strip().lower()
        album = entry.get('album', '').strip()
        track = entry.get('track', '').strip().lower()
        
        # Empty albums get sorted to bottom
        has_album = 0 if album else 1
        album_lower = album.lower() if album else ''
        
        return (artist, has_album, album_lower, track)
    
    @staticmethod
    def sort_csv(input_file: str, output_file: str) -> bool:
        """Sort CSV file by artist and album."""
        try:
            data = CSVProcessor.read_csv(input_file)
            CSVProcessor.validate_required_columns(data, ['artist'])
            
            print(f"📖 Loaded {len(data)} entries from {input_file}")
            print(f"🔄 Sorting by artist, then by album (empty albums last)...")
            
            sorted_data = sorted(data, key=MusicSorter.sort_key)
            
            CSVProcessor.write_csv(output_file, sorted_data)
            print(f"📝 Saved {len(sorted_data)} sorted entries to {output_file}")
            
            # Statistics
            artists = set(entry.get('artist', '').strip() for entry in sorted_data)
            albums = set(entry.get('album', '').strip() for entry in sorted_data if entry.get('album', '').strip())
            entries_without_albums = len([entry for entry in sorted_data if not entry.get('album', '').strip()])
            
            print(f"\n📊 Sorting Statistics:")
            print(f"   • Total entries: {len(sorted_data)}")
            print(f"   • Unique artists: {len(artists)}")
            print(f"   • Unique albums: {len(albums)}")
            print(f"   • Entries without albums: {entries_without_albums}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error sorting CSV: {e}")
            return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Music Metadata Pipeline')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract YouTube playlist metadata')
    extract_parser.add_argument('playlist_url', help='YouTube playlist URL')
    extract_parser.add_argument('--output', '-o', default=CONFIG.YOUTUBE_PLAYLIST_OUTPUT, help='Output CSV file')
    extract_parser.add_argument('--timeout', type=int, default=CONFIG.YOUTUBE_TIMEOUT, help='Timeout per video')
    
    # Enhance command
    enhance_parser = subparsers.add_parser('enhance', help='Enhance metadata with MusicBrainz')
    enhance_parser.add_argument('--input', '-i', default=CONFIG.YOUTUBE_PLAYLIST_OUTPUT, help='Input CSV file')
    enhance_parser.add_argument('--output', '-o', default=CONFIG.ENHANCED_METADATA_OUTPUT, help='Output CSV file')
    enhance_parser.add_argument('--rate-limit', '-r', type=float, default=CONFIG.RATE_LIMIT_DELAY, help='Rate limit (seconds)')
    
    # Studio albums command
    studio_parser = subparsers.add_parser('studio', help='Find studio albums')
    studio_parser.add_argument('--input', '-i', default=CONFIG.ENHANCED_METADATA_OUTPUT, help='Input CSV file')
    studio_parser.add_argument('--output', '-o', default=CONFIG.STUDIO_ALBUMS_OUTPUT, help='Output CSV file')
    studio_parser.add_argument('--rate-limit', '-r', type=float, default=CONFIG.RATE_LIMIT_DELAY, help='Rate limit (seconds)')
    
    # Sort command
    sort_parser = subparsers.add_parser('sort', help='Sort music CSV')
    sort_parser.add_argument('--input', '-i', default=CONFIG.STUDIO_ALBUMS_OUTPUT, help='Input CSV file')
    sort_parser.add_argument('--output', '-o', default=CONFIG.SORTED_MUSIC_OUTPUT, help='Output CSV file')
    
    # Pipeline command (run all steps)
    pipeline_parser = subparsers.add_parser('pipeline', help='Run complete pipeline')
    pipeline_parser.add_argument('playlist_url', help='YouTube playlist URL')
    pipeline_parser.add_argument('--rate-limit', '-r', type=float, default=CONFIG.RATE_LIMIT_DELAY, help='Rate limit (seconds)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return False
    
    # Execute commands
    success = True
    
    if args.command == 'extract':
        if not confirm_overwrite(args.output):
            return False
        extractor = YouTubeExtractor(args.timeout)
        success = extractor.extract_playlist(args.playlist_url, args.output)
        if success:
            extractor.stats.print_summary("YouTube Extraction Complete", args.output)
    
    elif args.command == 'enhance':
        if not confirm_overwrite(args.output):
            return False
        enhancer = MetadataEnhancer(args.rate_limit)
        success = enhancer.enhance_csv(args.input, args.output)
        if success:
            enhancer.stats.print_summary("Metadata Enhancement Complete", args.output)
    
    elif args.command == 'studio':
        if not confirm_overwrite(args.output):
            return False
        finder = StudioAlbumFinder(args.rate_limit)
        success = finder.process_csv(args.input, args.output)
        if success:
            finder.stats.print_summary("Studio Album Search Complete", args.output)
    
    elif args.command == 'sort':
        if not confirm_overwrite(args.output):
            return False
        success = MusicSorter.sort_csv(args.input, args.output)
    
    elif args.command == 'pipeline':
        print("🚀 Running complete music metadata pipeline...")
        
        # Step 1: Extract
        extractor = YouTubeExtractor()
        if not confirm_overwrite(CONFIG.YOUTUBE_PLAYLIST_OUTPUT):
            return False
        success = extractor.extract_playlist(args.playlist_url, CONFIG.YOUTUBE_PLAYLIST_OUTPUT)
        if not success:
            return False
        
        # Step 2: Enhance
        enhancer = MetadataEnhancer(args.rate_limit)
        success = enhancer.enhance_csv(CONFIG.YOUTUBE_PLAYLIST_OUTPUT, CONFIG.ENHANCED_METADATA_OUTPUT)
        if not success:
            return False
        
        # Step 3: Studio albums
        finder = StudioAlbumFinder(args.rate_limit)
        success = finder.process_csv(CONFIG.ENHANCED_METADATA_OUTPUT, CONFIG.STUDIO_ALBUMS_OUTPUT)
        if not success:
            return False
        
        # Step 4: Sort
        success = MusicSorter.sort_csv(CONFIG.STUDIO_ALBUMS_OUTPUT, CONFIG.SORTED_MUSIC_OUTPUT)
        
        if success:
            print("\n🎉 Complete pipeline finished successfully!")
            print(f"📝 Final output: {CONFIG.SORTED_MUSIC_OUTPUT}")
    
    return success


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)