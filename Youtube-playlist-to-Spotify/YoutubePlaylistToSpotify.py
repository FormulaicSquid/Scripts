import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas
from dotenv import load_dotenv

# Spotify API setup, grab credentilas from .env file
load_dotenv()
spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
spotify_redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")


def remove_extra_info_from_csv(file_path):
    with open(file_path, 'r') as file:
        first_line = file.readline().strip()
        if 'title' not in first_line:
            lines = file.readlines()[4:]
            with open(file_path, 'w') as file:
                file.writelines(lines)


def get_a_single_playlist_from_a_single_csv(file_name):
    if file_name.endswith('.csv'):
        file_path = os.path.join(folder_path, file_name)
        remove_extra_info_from_csv(file_path)

        dataframe = pandas.read_csv(file_path)

        if 'title' in dataframe.columns:
            songs = dataframe['title'].tolist()
            return songs
        else:
            raise Exception(f"Error: 'title' column not found in {file_name}")


def get_playlists_from_multiple_csv(folder_path):
    playlists = {}

    for file_name in os.listdir(folder_path):
        playlist_title_without_file_extension = os.path.splitext(file_name)[0]
        playlists[playlist_title_without_file_extension] = get_a_single_playlist_from_a_single_csv(file_name)

    return playlists


def spotify_authenticate():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=spotify_client_id,
        client_secret=spotify_client_secret,
        redirect_uri=spotify_redirect_uri,
        scope="playlist-modify-public"
    ))


def create_spotify_playlist(spotify_instance, name, description):
    user_id = spotify_instance.me()["id"]
    playlist = spotify_instance.user_playlist_create(user=user_id, name=name, public=True, description=description)
    return playlist["id"]


def can_find_song_on_spotify(spotify_instance, song, playlist_id):
    results = spotify_instance.search(q=song, type='track', limit=1)
    if results['tracks']['items']:
        track = results['tracks']['items'][0]
        spotify_instance.playlist_add_items(playlist_id, [track['id']])
        return True
    else:
        return False


def add_songs_to_spotify_playlist(spotify_instance, playlist_id, songs):
    failed_songs = []
    for song in songs:
        if can_find_song_on_spotify(spotify_instance, song, playlist_id) is False:
            failed_songs.append(song)
    return failed_songs


def convert_youtube_playlist_to_spotify_playlist(spotify_instance, playlist_name, youtube_songs):
    spotify_playlist_name = playlist_name
    spotify_playlist_description = f"Spotify playlist created from the YouTube playlist: {playlist_name}"
    spotify_playlist_id = create_spotify_playlist(spotify_instance, spotify_playlist_name, spotify_playlist_description)
    failed_songs = add_songs_to_spotify_playlist(spotify_instance, spotify_playlist_id, youtube_songs)

    if failed_songs:
        print(f"The following songs could not be transferred for {playlist_name}:")
        for song in failed_songs:
            print(song)
    else:
        print(f"All songs were successfully transferred for {playlist_name}!")


def main(folder_path):
    youtube_playlists = get_playlists_from_multiple_csv(folder_path)
    spotify_instance = spotify_authenticate()

    for playlist_name, youtube_songs in youtube_playlists.items():
        convert_youtube_playlist_to_spotify_playlist(spotify_instance, playlist_name, youtube_songs)


if __name__ == "__main__":
    csv_folder = "./playlists/"
    main(csv_folder)
