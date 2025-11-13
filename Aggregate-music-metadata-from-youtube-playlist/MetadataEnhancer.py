#!/usr/bin/env python3
"""
Music Metadata Enhancer

This script takes a CSV file with YouTube video titles and enhances the metadata
by querying the MusicBrainz database. It can handle both individual tracks and full albums,
expanding albums into individual tracks.
"""

import re
import argparse
from typing import Dict, List
from tqdm import tqdm

# Local imports
from music_utils import MusicBrainzAPI, CSVProcessor, confirm_overwrite, Statistics, MusicTrack
from config import CONFIG


class MetadataEnhancer:
    """Enhances YouTube playlist metadata using MusicBrainz database."""
    
    def __init__(self, input_file: str, output_file: str, rate_limit: float = CONFIG.RATE_LIMIT_DELAY):
        self.input_file = input_file
        self.output_file = output_file
        self.api = MusicBrainzAPI(CONFIG.USER_AGENTS['metadata_enhancer'], rate_limit)
        self.stats = Statistics()
        
    def is_english_content(self, text: str) -> bool:
        """Check if text contains mostly English characters."""
        if not text:
            return False
        latin_chars = sum(1 for char in text if ord(char) < 256)
        non_latin_chars = len(text) - latin_chars
        return latin_chars >= non_latin_chars
        
    def clean_title(self, title: str) -> str:
        """Clean and normalize video titles for better matching."""
        # Remove common YouTube artifacts
        patterns_to_remove = [
            r'\[OFFICIAL.*?\]', r'\(OFFICIAL.*?\)', r'\[Official.*?\]', r'\(Official.*?\)',
            r'\[FULL.*?\]', r'\(FULL.*?\)', r'\[Full.*?\]', r'\(Full.*?\)',
            r'\[HD\]', r'\(HD\)', r'\[HQ\]', r'\(HQ\)',
            r'\[Lyrics?\]', r'\(Lyrics?\)', r'\[Official.*?Video\]', r'\(Official.*?Video\)',
            r'\[Music Video\]', r'\(Music Video\)', r'\[Audio\]', r'\(Audio\)',
            r'【.*?】', r'「.*?」',  # Japanese brackets
            r'OFFICIAL VIDEO', r'OFFICIAL MUSIC VIDEO', r'MUSIC VIDEO',
            r'LYRIC VIDEO', r'OFFICIAL AUDIO', r'OFFICIAL LYRIC VIDEO'
        ]
        
        cleaned = title
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Clean up extra spaces and normalize
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = re.sub(r'\s*-\s*', ' - ', cleaned)  # Normalize separators
        
        return cleaned
    
    def parse_title(self, title: str) -> Dict[str, str]:
        """Parse video title to extract artist, track, and album information."""
        cleaned = self.clean_title(title)
        
        # Initialize result
        result = {'artist': '', 'track': '', 'album': '', 'is_full_album': False}
        
        # Check if it's a full album
        album_indicators = [
            r'full album', r'complete album', r'entire album', r'whole album',
            r'\(album\)', r'\[album\]', r'full cd', r'complete cd'
        ]
        
        for indicator in album_indicators:
            if re.search(indicator, cleaned, re.IGNORECASE):
                result['is_full_album'] = True
                break
        
        # Common patterns for artist - track
        patterns = [
            r'^([^-]+?)\s*-\s*(.+)$',  # Artist - Track
            r'^(.+?)\s*:\s*(.+)$',     # Artist : Track
            r'^(.+?)\s*–\s*(.+)$',     # Artist – Track (em dash)
            r'^(.+?)\s*—\s*(.+)$',     # Artist — Track (em dash)
        ]
        
        for pattern in patterns:
            match = re.match(pattern, cleaned)
            if match:
                result['artist'] = match.group(1).strip()
                result['track'] = match.group(2).strip()
                break
        
        # If no pattern matched, use the whole title as track
        if not result['artist'] and not result['track']:
            result['track'] = cleaned
        
        return result
    
    def is_english_content(self, text: str) -> bool:
        """Check if text contains meaningful English content."""
        if not text:
            return False
        
        # Count non-Latin characters
        non_latin_chars = sum(1 for char in text if char.isalpha() and ord(char) > 127)
        latin_chars = sum(1 for char in text if char.isalpha() and ord(char) <= 127)
        
        # If more than 50% non-Latin, consider it non-English
        if latin_chars + non_latin_chars == 0:
            return False
        
        return latin_chars >= non_latin_chars
    
    def search_musicbrainz(self, artist: str, track: str = None, album: str = None) -> Optional[Dict]:
        """Search MusicBrainz for track or album information."""
        base_urls = [
            "https://musicbrainz.org/ws/2/",
            "http://musicbrainz.org/ws/2/"  # Fallback to HTTP if HTTPS fails
        ]
        
        for base_url in base_urls:
            try:
                if track:
                    query = f'artist:"{artist}" AND recording:"{track}"'
                    url = f"{base_url}recording/?query={query}&fmt=json&limit=5"
                else:
                    query = f'artist:"{artist}"'
                    if album:
                        query += f' AND release:"{album}"'
                    url = f"{base_url}release/?query={query}&fmt=json&limit=5"
                
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if (track and 'recordings' in data and data['recordings']) or \
                       (not track and 'releases' in data and data['releases']):
                        return data
                
            except Exception:
                continue
        
        return None
    
    def find_best_recording(self, recordings: List[Dict]) -> Optional[Dict]:
        """Find the best recording from a list, preferring studio versions over live."""
        if not recordings:
            return None
        
        # Score recordings based on quality indicators
        scored_recordings = []
        for recording in recordings:
            score = 0
            title = recording.get('title', '').lower()
            
            # Prefer recordings that don't have live/remix indicators
            if 'live' not in title and 'remix' not in title and 'demo' not in title:
                score += 10
            
            # Boost score if it has releases (albums)
            if recording.get('releases'):
                score += 5
                
                # Check if any releases are studio albums
                for release in recording['releases']:
                    release_title = release.get('title', '').lower()
                    if 'live' not in release_title and 'compilation' not in release_title:
                        score += 5
                        break
            
            scored_recordings.append((score, recording))
        
        # Return the highest scored recording
        scored_recordings.sort(key=lambda x: x[0], reverse=True)
        return scored_recordings[0][1]
    
    def find_best_album_from_releases(self, releases: List[Dict]) -> str:
        """Find the best album name from a list of releases, preferring studio albums."""
        if not releases:
            return ''
        
        # Score releases based on quality indicators
        scored_releases = []
        for release in releases:
            score = 0
            title = release.get('title', '')
            title_lower = title.lower()
            
            # Prefer studio albums over live/compilation
            if 'live' not in title_lower:
                score += 10
            if 'compilation' not in title_lower and 'greatest hits' not in title_lower:
                score += 5
            if 'best of' not in title_lower and 'collection' not in title_lower:
                score += 5
            if 'remix' not in title_lower and 'demo' not in title_lower:
                score += 3
            
            # Prefer releases with reasonable dates (not too old compilations)
            date = release.get('date', '')
            if date and len(date) >= 4:
                try:
                    year = int(date[:4])
                    # Prefer releases from 1960-2025 (reasonable music era)
                    if 1960 <= year <= 2025:
                        score += 2
                except:
                    pass
            
            scored_releases.append((score, title))
        
        # Return the highest scored release title
        if scored_releases:
            scored_releases.sort(key=lambda x: x[0], reverse=True)
            return scored_releases[0][1]
        
        return releases[0].get('title', '') if releases else ''
    
    def find_best_release(self, releases: List[Dict]) -> Optional[Dict]:
        """Find the best release from a list, preferring studio albums over live/compilation."""
        if not releases:
            return None
        
        # Score releases based on quality indicators
        scored_releases = []
        for release in releases:
            score = 0
            title = release.get('title', '').lower()
            
            # Check release group primary type
            release_group = release.get('release-group', {})
            primary_type = release_group.get('primary-type', '').lower()
            
            # Strongly prefer Albums over other types
            if primary_type == 'album':
                score += 20
            elif primary_type in ['ep', 'single']:
                score += 5  # Less preferred but acceptable
            elif primary_type == 'compilation':
                score -= 10  # Avoid compilations
            
            # Check title for quality indicators
            if 'live' not in title:
                score += 10
            if 'compilation' not in title and 'greatest hits' not in title:
                score += 8
            if 'best of' not in title and 'collection' not in title:
                score += 5
            if 'remix' not in title and 'demo' not in title and 'bootleg' not in title:
                score += 3
            
            # Prefer releases with reasonable dates
            date = release.get('date', '')
            if date and len(date) >= 4:
                try:
                    year = int(date[:4])
                    if 1960 <= year <= 2025:
                        score += 2
                    # Slightly prefer more recent releases if they're studio albums
                    if year >= 1970 and primary_type == 'album':
                        score += 1
                except:
                    pass
            
            # Check country (prefer major markets for original releases)
            country = release.get('country', '')
            if country in ['US', 'GB', 'DE', 'JP', 'CA', 'AU']:
                score += 1
            
            scored_releases.append((score, release))
        
        # Return the highest scored release
        if scored_releases:
            scored_releases.sort(key=lambda x: x[0], reverse=True)
            return scored_releases[0][1]
        
        return releases[0]  # Fallback to first release
    
    def get_album_tracks(self, release_id: str) -> List[Dict[str, str]]:
        """Get all tracks from a MusicBrainz release."""
        base_urls = [
            f"https://musicbrainz.org/ws/2/release/{release_id}?inc=recordings&fmt=json",
            f"http://musicbrainz.org/ws/2/release/{release_id}?inc=recordings&fmt=json"
        ]
        
        for url in base_urls:
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    tracks = []
                    
                    if 'media' in data:
                        for medium in data['media']:
                            if 'tracks' in medium:
                                for track in medium['tracks']:
                                    tracks.append({
                                        'track': track.get('title', ''),
                                        'artist': data.get('artist-credit', [{}])[0].get('name', '') if data.get('artist-credit') else '',
                                        'album': data.get('title', '')
                                    })
                    
                    return tracks
            except Exception:
                continue
        
        return []
    
    def enhance_metadata(self, original_data: Dict[str, str]) -> List[Dict[str, str]]:
        """Enhance metadata for a single entry."""
        title = original_data['title']
        existing_artist = original_data.get('artist', '').strip()
        
        print(f"\n🔍 Processing: {title[:60]}...")
        
        # Parse the title
        parsed = self.parse_title(title)
        
        # Use existing artist if available and parsed artist is empty
        if not parsed['artist'] and existing_artist:
            parsed['artist'] = existing_artist
        
        # If we still don't have an artist, skip
        if not parsed['artist']:
            print(f"  ❌ No artist found")
            self.failed_lookups += 1
            return [{'track': title, 'artist': '', 'album': ''}]
        
        # Skip if no English content
        if not self.is_english_content(parsed['artist']) and not self.is_english_content(parsed['track']):
            print(f"  ⚠️ Non-English content, using parsed data")
            self.failed_lookups += 1
            return [{'track': parsed['track'], 'artist': parsed['artist'], 'album': ''}]
        
        # Rate limiting
        time.sleep(self.rate_limit)
        
        # Try MusicBrainz first
        try:
            if parsed['is_full_album']:
                print(f"  📀 Searching for full album...")
                data = self.search_musicbrainz(parsed['artist'], album=parsed['track'])
                
                if data and 'releases' in data and data['releases']:
                    # Find the best release (prefer studio albums over live/compilation)
                    best_release = self.find_best_release(data['releases'])
                    if best_release:
                        tracks = self.get_album_tracks(best_release['id'])
                        if tracks:
                            print(f"  ✅ Found {len(tracks)} tracks in album: {best_release['title']}")
                            print(f"    📀 Release type: {best_release.get('release-group', {}).get('primary-type', 'Unknown')}")
                            self.album_expansions += 1
                            self.successful_enhancements += 1
                            self.musicbrainz_hits += 1
                            return tracks
            else:
                # Search for individual track
                data = self.search_musicbrainz(parsed['artist'], track=parsed['track'])
                
                if data and 'recordings' in data and data['recordings']:
                    # Find the best recording (prefer studio albums over live/compilation)
                    best_recording = self.find_best_recording(data['recordings'])
                    if best_recording:
                        recording = best_recording
                        artist_name = recording.get('artist-credit', [{}])[0].get('name', parsed['artist']) if recording.get('artist-credit') else parsed['artist']
                        track_name = recording.get('title', parsed['track'])
                        
                        # Find the best album from this recording's releases
                        album_name = self.find_best_album_from_releases(recording.get('releases', []))
                        
                        print(f"  ✅ Enhanced via MusicBrainz: {artist_name} - {track_name}")
                        if album_name:
                            print(f"    📀 Album: {album_name}")
                        self.successful_enhancements += 1
                        self.musicbrainz_hits += 1
                        return [{'track': track_name, 'artist': artist_name, 'album': album_name}]
        
        except Exception as e:
            print(f"  ⚠️ MusicBrainz error: {e}")
        
        # If no database match found, return parsed data
        print(f"  ⚠️ No match found, using parsed data")
        self.failed_lookups += 1
        return [{'track': parsed['track'], 'artist': parsed['artist'], 'album': ''}]
    
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
        
        self.total_entries = len(input_data)
        print(f"📖 Loaded {self.total_entries} entries from {self.input_file}")
        
        # Process each entry
        enhanced_tracks = []
        
        with tqdm(input_data, desc="Enhancing metadata", unit="entry") as pbar:
            for entry in pbar:
                try:
                    tracks = self.enhance_metadata(entry)
                    enhanced_tracks.extend(tracks)
                    
                    # Update progress bar
                    pbar.set_postfix({
                        'Enhanced': self.successful_enhancements,
                        'Failed': self.failed_lookups,
                        'Albums': self.album_expansions
                    })
                    
                except KeyboardInterrupt:
                    print(f"\n⚠️ Interrupted by user. Processed {len(enhanced_tracks)} tracks so far.")
                    break
                except Exception as e:
                    print(f"  ❌ Error processing entry: {e}")
                    self.failed_lookups += 1
                    enhanced_tracks.append({'track': entry['title'], 'artist': '', 'album': ''})
        
        # Write output CSV
        try:
            with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['track', 'artist', 'album'])
                
                for track in enhanced_tracks:
                    writer.writerow([track['track'], track['artist'], track['album']])
            
            print(f"\n📝 Saved {len(enhanced_tracks)} tracks to {self.output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error writing output file: {e}")
            return False
    
    def print_statistics(self):
        """Print processing statistics."""
        print(f"\n📊 Processing Complete!")
        print(f"   • Total entries processed: {self.total_entries}")
        print(f"   • Successful enhancements: {self.successful_enhancements}")
        print(f"     - MusicBrainz hits: {self.musicbrainz_hits}")
        print(f"   • Albums expanded: {self.album_expansions}")
        print(f"   • Failed lookups: {self.failed_lookups}")
        
        if self.total_entries > 0:
            success_rate = (self.successful_enhancements / self.total_entries) * 100
            print(f"   • Success rate: {success_rate:.1f}%")
        
        print(f"   • Output saved to: {self.output_file}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Enhance music metadata from YouTube playlist CSV')
    parser.add_argument('--input', '-i', default=INPUT_CSV, help='Input CSV file')
    parser.add_argument('--output', '-o', default=OUTPUT_CSV, help='Output CSV file')
    parser.add_argument('--rate-limit', '-r', type=float, default=RATE_LIMIT_DELAY, 
                       help='Rate limit between API calls (seconds)')
    
    args = parser.parse_args()
    
    print(f"🚀 Music Metadata Enhancer")
    print(f"📖 Input file: {args.input}")
    print(f"💾 Output file: {args.output}")
    print(f"⏱️ Rate limit: {args.rate_limit}s between requests")
    
    # Check if output file exists
    if Path(args.output).exists():
        response = input(f"⚠️  File '{args.output}' already exists. Overwrite? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Operation cancelled.")
            return False
    
    # Create and run enhancer
    enhancer = MetadataEnhancer(args.input, args.output, args.rate_limit)
    success = enhancer.process_csv()
    
    if success:
        enhancer.print_statistics()
        print("🎉 Enhancement completed successfully!")
        return True
    else:
        print("💥 Enhancement failed!")
        return False


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)