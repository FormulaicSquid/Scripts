import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# YouTube Data API setup
scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
youtube_client_secrets_file = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE")
youtube_api_service_name = "youtube"
youtube_api_version = "v3"

# Spotify API setup
spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
spotify_redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")


# Authentication for YouTube
def youtube_authenticate():
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        youtube_client_secrets_file, scopes)
    credentials = flow.run_console()
    youtube = googleapiclient.discovery.build(
        youtube_api_service_name, youtube_api_version, credentials=credentials)
    return youtube


# Fetch YouTube playlist items
def get_youtube_playlist_items(youtube, playlist_id):
    request = youtube.playlistItems().list(
        part="snippet",
        maxResults=50,
        playlistId=playlist_id
    )
    response = request.execute()
    songs = []
    for item in response["items"]:
        title = item["snippet"]["title"]
        songs.append(title)
    return songs


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


def main(youtube_playlist_id, spotify_playlist_name, spotify_playlist_description):
    youtube = youtube_authenticate()
    sp = spotify_authenticate()

    youtube_songs = get_youtube_playlist_items(youtube, youtube_playlist_id)
    spotify_playlist_id = create_spotify_playlist(sp, spotify_playlist_name, spotify_playlist_description)
    failed_songs = add_songs_to_spotify_playlist(sp, spotify_playlist_id, youtube_songs)

    if failed_songs:
        print("The following songs could not be transferred:")
        for song in failed_songs:
            print(song)
    else:
        print("All songs were successfully transferred!")


if __name__ == "__main__":
    youtube_playlist_id = "YOUR_YOUTUBE_PLAYLIST_ID"  # Replace with your YouTube playlist ID
    spotify_playlist_name = "Your Spotify Playlist Name"
    spotify_playlist_description = "Description for your Spotify playlist"

    main(youtube_playlist_id, spotify_playlist_name, spotify_playlist_description)