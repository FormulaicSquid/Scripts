# Convert a Youtube Playlist to a Spotify Playlist

This script solves a very niche problem of converting a YouTube playlist to a Spotify playlist.
It uses a csv file containing the details of the videos in a Youtube playlist and the 
Spotify Web API to search for the corresponding Spotify tracks and add them to a new playlist.


## Getting the CSV with the Youtube Playlist

- Go to https://jolantahuba.github.io/YT-Backup/, and follow the instructions to get
a csv of the desired playlist.
- Save the csv file in the playlists folder, and give it an appropriate name.

## Create a `.env` File
Then, create a `.env` file in the root directory of your project. This file will store your API credentials and IDs.
The values you gather from the steps below will be plugged into this `.env` file.

```env
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=your_spotify_redirect_uri
```

## Spotify API Credentials

### 1. Create a Spotify Developer Account:
- Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/applications).
- Log in with your Spotify account and agree to the terms.

### 2. Create a New Application:
- Click on "Create an App".
- Fill in the necessary details (name, description, etc.).
- Once created, you will see your `Client ID` and `Client Secret`.

### 3. Set Redirect URI:
- In your Spotify app settings, add a redirect URI (e.g., `http://localhost:8888/callback`).
- You will use this redirect URI in your Spotify OAuth setup.

## Cleanup

Once you do all of these, and run the script, the script will let you know if
any of your songs were not found on Spotify.

Regardless of that, you will now have to do cleanup. As we are using the search function, sometimes
the API will add a different song than had a similar name or a similar-sounding artist. You will have to
manually go through the newly created playlist and remove any songs that are not the ones you wanted, and add in
the ones you wanted instead. Finally, if you had any songs that were not found, you will have to add them manually.