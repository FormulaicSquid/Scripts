# YouTube Playlist Metadata Extractor

A Python script that extracts metadata from YouTube playlists and saves it to a CSV file,

## Requirements

- Python 3.7+
- yt-dlp
- tqdm
- ffmpeg (for video/audio processing)

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

1. **Edit the configuration variables** in the script:
   ```python
   # Edit these variables at the top of YoutubePlaylistMetadata.py
   PLAYLIST_URL = "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID"
   OUTPUT_FILE = "my_playlist.csv"
   ```

2. **Run the script**:
   ```bash
   python YoutubePlaylistMetadata.py
   ```

### Configuration Variables

- `PLAYLIST_URL`: The YouTube playlist URL you want to extract metadata from
- `OUTPUT_FILE`: The name of the CSV file to save the results to

## Output Format

The script generates a CSV file with the following columns:
- `title`: Song title
- `artist`: Artist name (or uploader if artist not available)
- `track`: Track name (if available)
- `album`: Album name (if available)




This script replaces the following shell command:
```bash
yt-dlp -J "PLAYLIST_URL" | jq -r '.entries[] | [.title, .artist, .track, .album] | @csv' > playlist.csv
```