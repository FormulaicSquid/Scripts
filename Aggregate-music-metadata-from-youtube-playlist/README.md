# YouTube Playlist Metadata Tools

A collection of Python scripts for extracting and enhancing metadata from YouTube playlists. These tools help you convert YouTube playlist data into properly formatted music metadata without downloading any files.

## Scripts

### 1. YoutubePlaylistMetadata.py
Extracts basic metadata from YouTube playlists without downloading any audio/video files. This script processes playlists video-by-video with timeout protection and error handling to ensure robust data extraction.

### 2. MetadataEnhancer.py  
Enhances the extracted metadata by querying the MusicBrainz music database to get accurate track, artist, and album information. Can automatically detect and expand full albums into individual tracks.

## Requirements

- Python 3.7+
- yt-dlp (YouTube metadata extraction)
- tqdm (progress bars)
- requests (HTTP API calls)
- ffmpeg (required by yt-dlp for video processing)

## Installation

1. **Install ffmpeg** (required by yt-dlp):
   ```bash
   # On macOS using Homebrew
   brew install ffmpeg
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Step 1: Extract YouTube Playlist Metadata

1. **Edit the configuration variables** in `YoutubePlaylistMetadata.py`:
   ```python
   PLAYLIST_URL = "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID"
   OUTPUT_FILE = "data/my_playlist.csv"
   TIMEOUT_SECONDS = 30  # Timeout per video
   ```

2. **Run the script**:
   ```bash
   python YoutubePlaylistMetadata.py
   ```

This creates a CSV with columns: `title`, `artist`, `track`, `album`

### Step 2: Enhance Metadata (Optional)

1. **Run the metadata enhancer**:
   ```bash
   python MetadataEnhancer.py --input data/my_playlist.csv --output data/enhanced_playlist.csv
   ```

This queries MusicBrainz to get proper metadata and can expand full albums into individual tracks.

## Features

### YoutubePlaylistMetadata.py
- ✅ **No file downloads** - metadata only
- ✅ **Individual video processing** - skips problematic videos
- ✅ **Timeout protection** - configurable timeout per video
- ✅ **Real-time progress** - shows current status
- ✅ **Interrupt handling** - save partial results with Ctrl+C
- ✅ **Error resilience** - continues processing despite individual failures

### MetadataEnhancer.py
- ✅ **Intelligent title parsing** - extracts artist/track from video titles using multiple patterns
- ✅ **Full album support** - automatically detects and expands albums into individual tracks  
- ✅ **MusicBrainz integration** - queries the free MusicBrainz music database
- ✅ **Content filtering** - skips non-English content for better results
- ✅ **Rate limiting** - respectful API usage with configurable delays
- ✅ **Progress tracking** - real-time statistics and progress bars
- ✅ **SSL handling** - works around certificate issues with music databases

## Configuration Options

### YoutubePlaylistMetadata.py
- `PLAYLIST_URL`: YouTube playlist URL
- `OUTPUT_FILE`: CSV output filename  
- `TIMEOUT_SECONDS`: Timeout per video (default: 30s)

### MetadataEnhancer.py
- `--input`: Input CSV file
- `--output`: Output CSV file
- `--rate-limit`: Seconds between API calls (default: 1.0)

## Output Formats

### YoutubePlaylistMetadata.py Output
```csv
title,artist,track,album
"Artist - Song Title",Artist,Song Title,Album Name
```

### MetadataEnhancer.py Output  
```csv
track,artist,album
"Proper Song Title","Proper Artist Name","Proper Album Name"
```

## Example Workflow

```bash
# 1. Extract playlist metadata (no downloads, metadata only)
python YoutubePlaylistMetadata.py

# 2. Enhance with proper metadata from MusicBrainz database
python MetadataEnhancer.py --input data/zahin_playlist.csv --output data/enhanced.csv --rate-limit 1.0

# 3. Review results
head data/enhanced.csv
```

## Success Rates

Based on testing with real playlists:
- **YouTube extraction**: ~98% success rate (skips only corrupted/private videos)
- **Metadata enhancement**: ~50-60% success rate (depends on title quality and MusicBrainz database coverage)
- **Album expansion**: Works best with clearly labeled "Full Album" titles

## Tips

- **Better source data** = better enhancement results - playlists with well-formatted titles work best
- Use **timeout settings** to avoid waiting indefinitely on problematic videos  
- **Rate limiting** respects MusicBrainz servers (1 req/sec recommended)
- **Album detection** automatically expands full albums into individual tracks when detected
- **Manual curation** may be needed for very obscure tracks or non-English content
- **Case sensitivity** matters - "ARTIST NAME" titles often fail, "Artist Name" works better