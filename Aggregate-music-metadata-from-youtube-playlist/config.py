#!/usr/bin/env python3
"""
Configuration settings for music metadata processing scripts.
"""

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Config:
    """Configuration settings for the music processing pipeline."""
    
    # File paths
    YOUTUBE_PLAYLIST_OUTPUT: str = "data/zahin_playlist.csv"
    ENHANCED_METADATA_OUTPUT: str = "data/enhanced_metadata.csv"
    STUDIO_ALBUMS_OUTPUT: str = "data/studio_albums.csv"
    SORTED_MUSIC_OUTPUT: str = "data/sorted_music.csv"
    
    # API settings
    RATE_LIMIT_DELAY: float = 1.0  # Seconds between API calls
    REQUEST_TIMEOUT: int = 15  # Seconds
    
    # YouTube extraction settings
    YOUTUBE_TIMEOUT: int = 30  # Seconds per video
    DEFAULT_PLAYLIST_URL: str = "https://youtube.com/playlist?list=PLkuTuUy1lBRWtYYMTb6oWuQsmo6rVeFHh&si=_5HmvHJjk7Ek7ifs"
    
    # User agent strings
    USER_AGENTS: Dict[str, str] = None
    
    def __post_init__(self):
        if self.USER_AGENTS is None:
            self.USER_AGENTS = {
                'metadata_enhancer': 'MetadataEnhancer/2.0 (https://github.com/FormulaicSquid/Scripts)',
                'studio_album_finder': 'StudioAlbumFinder/2.0 (https://github.com/FormulaicSquid/Scripts)',
                'youtube_extractor': 'YouTubePlaylistExtractor/2.0 (https://github.com/FormulaicSquid/Scripts)'
            }


# Global configuration instance
CONFIG = Config()