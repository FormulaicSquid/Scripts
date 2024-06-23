import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
from dotenv import load_dotenv

# Spotify API setup
load_dotenv()
spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
spotify_redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")


# Fetch YouTube playlist items from CSV
def get_playlists_from_csv(folder_path):
    playlists = {}

    # Iterate through each file in the folder
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.csv'):
            # Construct the full file path
            file_path = os.path.join(folder_path, file_name)
            with open(file_path, 'r') as file:
                first_line = file.readline().strip()
                if 'title' not in first_line:
                    # Remove first 5 lines, and make 6th line the headers of columns
                    lines = file.readlines()[4:]
                    with open(file_path, 'w') as file:
                        file.writelines(lines)
            # Get the playlist title from the file name (without extension)
            playlist_title = os.path.splitext(file_name)[0]
            # Read the CSV file
            df = pd.read_csv(file_path)
            # Assuming the song titles are in a column named 'title'
            if 'title' in df.columns:
                songs = df['title'].tolist()
                playlists[playlist_title] = songs
            else:
                print(f"Warning: 'title' column not found in {file_name}")

    return playlists


# Authentication for Spotify
def spotify_authenticate():
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=spotify_client_id,
        client_secret=spotify_client_secret,
        redirect_uri=spotify_redirect_uri,
        scope="playlist-modify-public"
    ))
    return sp


# Create Spotify playlist
def create_spotify_playlist(sp, name, description):
    user_id = sp.me()["id"]
    playlist = sp.user_playlist_create(user=user_id, name=name, public=True, description=description)
    return playlist["id"]


# Search and add songs to Spotify playlist
def add_songs_to_spotify_playlist(sp, playlist_id, songs):
    failed_songs = []
    for song in songs:
        results = sp.search(q=song, type='track', limit=1)
        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            sp.playlist_add_items(playlist_id, [track['id']])
        else:
            failed_songs.append(song)
    return failed_songs


def main(folder_path):
    youtube_playlists = get_playlists_from_csv(folder_path)
    sp = spotify_authenticate()
    # Iterate through the dictionary
    for playlist_name, youtube_songs in youtube_playlists.items():
        spotify_playlist_name = playlist_name
        spotify_playlist_description = f"Spotify playlist created from the YouTube playlist: {playlist_name}"
        spotify_playlist_id = create_spotify_playlist(sp, spotify_playlist_name, spotify_playlist_description)
        failed_songs = add_songs_to_spotify_playlist(sp, spotify_playlist_id, youtube_songs)

        if failed_songs:
            print(f"The following songs could not be transferred for {playlist_name}:")
            for song in failed_songs:
                print(song)
        else:
            print(f"All songs were successfully transferred for {playlist_name}!")


if __name__ == "__main__":
    folder_path = "./playlists/"
    main(folder_path)
