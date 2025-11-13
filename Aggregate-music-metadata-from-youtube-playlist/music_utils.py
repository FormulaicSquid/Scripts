#!/usr/bin/env python3
"""
Common utilities for music metadata processing scripts.

This module provides shared functionality for MusicBrainz API access,
CSV processing, and other common operations used across multiple scripts.
"""

import csv
import time
import requests
import urllib3
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class MusicTrack:
    """Data class for music track information."""
    track: str = ""
    artist: str = ""
    album: str = ""
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for CSV writing."""
        return {
            'track': self.track,
            'artist': self.artist,
            'album': self.album
        }


class MusicBrainzAPI:
    """Handles MusicBrainz API interactions with proper rate limiting and error handling."""
    
    def __init__(self, user_agent: str, rate_limit: float = 1.0):
        self.rate_limit = rate_limit
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
        self.session.verify = False  # Handle SSL certificate issues
        self.last_request_time = 0
    
    def _rate_limit_request(self):
        """Ensure proper rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit:
            time.sleep(self.rate_limit - time_since_last)
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, timeout: int = 15) -> Optional[Dict[str, Any]]:
        """Make a rate-limited request to MusicBrainz API."""
        self._rate_limit_request()
        
        base_urls = [
            "https://musicbrainz.org/ws/2/",
            "http://musicbrainz.org/ws/2/"  # Fallback
        ]
        
        for base_url in base_urls:
            try:
                full_url = url.replace("https://musicbrainz.org/ws/2/", base_url)
                response = self.session.get(full_url, timeout=timeout)
                if response.status_code == 200:
                    return response.json()
            except Exception:
                continue
        return None
    
    def search_track(self, artist: str, track: str, limit: int = 5) -> Optional[Dict[str, Any]]:
        """Search for a track recording."""
        query = f'artist:"{artist}" AND recording:"{track}"'
        url = f"https://musicbrainz.org/ws/2/recording/?query={query}&fmt=json&limit={limit}"
        return self._make_request(url)
    
    def search_studio_album(self, artist: str, track: str, limit: int = 5) -> Optional[Dict[str, Any]]:
        """Search for studio albums containing a track."""
        query = (f'artist:"{artist}" AND recording:"{track}" AND primarytype:album '
                f'AND NOT secondarytype:live AND NOT secondarytype:compilation '
                f'AND NOT secondarytype:soundtrack')
        url = f"https://musicbrainz.org/ws/2/release-group/?query={query}&fmt=json&limit={limit}"
        return self._make_request(url)
    
    def search_album(self, artist: str, album: str, limit: int = 5) -> Optional[Dict[str, Any]]:
        """Search for album releases."""
        query = f'artist:"{artist}" AND release:"{album}"'
        url = f"https://musicbrainz.org/ws/2/release/?query={query}&fmt=json&limit={limit}"
        return self._make_request(url)
    
    def get_album_tracks(self, release_id: str) -> List[MusicTrack]:
        """Get all tracks from a MusicBrainz release."""
        url = f"https://musicbrainz.org/ws/2/release/{release_id}?inc=recordings&fmt=json"
        data = self._make_request(url)
        
        tracks = []
        if data and 'media' in data:
            for medium in data['media']:
                if 'tracks' in medium:
                    for track in medium['tracks']:
                        artist_name = ""
                        if 'artist-credit' in data and data['artist-credit']:
                            artist_name = data['artist-credit'][0].get('name', '')
                        
                        tracks.append(MusicTrack(
                            track=track.get('title', ''),
                            artist=artist_name,
                            album=data.get('title', '')
                        ))
        return tracks


class CSVProcessor:
    """Handles CSV file operations with proper error handling."""
    
    @staticmethod
    def read_csv(file_path: str) -> List[Dict[str, str]]:
        """Read CSV file and return list of dictionaries."""
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return list(reader)
        except Exception as e:
            raise RuntimeError(f"Error reading CSV file: {e}")
    
    @staticmethod
    def write_csv(file_path: str, data: List[Dict[str, str]], fieldnames: Optional[List[str]] = None) -> None:
        """Write list of dictionaries to CSV file."""
        if not data:
            raise ValueError("No data to write")
        
        if fieldnames is None:
            fieldnames = list(data[0].keys())
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
        except Exception as e:
            raise RuntimeError(f"Error writing CSV file: {e}")
    
    @staticmethod
    def validate_required_columns(data: List[Dict[str, str]], required_columns: List[str]) -> None:
        """Validate that required columns exist in the data."""
        if not data:
            raise ValueError("No data to validate")
        
        missing_columns = [col for col in required_columns if col not in data[0]]
        if missing_columns:
            available_columns = list(data[0].keys())
            raise ValueError(f"Missing required columns: {missing_columns}. "
                           f"Available columns: {available_columns}")


def confirm_overwrite(file_path: str) -> bool:
    """Ask user confirmation before overwriting existing file."""
    if Path(file_path).exists():
        response = input(f"⚠️  File '{file_path}' already exists. Overwrite? (y/N): ")
        return response.lower() in ['y', 'yes']
    return True


def normalize_artist_name(artist: str) -> str:
    """Normalize artist name for consistent comparison."""
    return artist.strip().lower().replace("'", "").replace("-", "").replace(" ", "")


class Statistics:
    """Track and display processing statistics."""
    
    def __init__(self):
        self.counters = {}
    
    def increment(self, key: str, amount: int = 1) -> None:
        """Increment a counter."""
        self.counters[key] = self.counters.get(key, 0) + amount
    
    def get(self, key: str) -> int:
        """Get counter value."""
        return self.counters.get(key, 0)
    
    def set(self, key: str, value: int) -> None:
        """Set counter value."""
        self.counters[key] = value
    
    def print_summary(self, title: str, output_file: str = "") -> None:
        """Print statistics summary."""
        print(f"\n📊 {title}")
        for key, value in self.counters.items():
            print(f"   • {key}: {value}")
        
        if 'total_entries' in self.counters and 'successful' in self.counters:
            total = self.get('total_entries')
            successful = self.get('successful')
            if total > 0:
                success_rate = (successful / total) * 100
                print(f"   • Success rate: {success_rate:.1f}%")
        
        if output_file:
            print(f"   • Output saved to: {output_file}")