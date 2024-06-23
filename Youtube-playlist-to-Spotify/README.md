# Setting Up API Credentials and IDs for YouTube and Spotify

To get the necessary API credentials and IDs for YouTube and Spotify, follow these steps:

## Create a `.env` File
First, create a `.env` file in the root directory of your project. This file will store your API credentials and IDs. The values you gather from the steps below will be plugged into this `.env` file.

## YouTube Data API Credentials

### 1. Create a Project in Google Cloud Console:
- Go to the [Google Cloud Console](https://console.cloud.google.com/).
- Click on the project drop-down and select "New Project".
- Give your project a name and create it.

### 2. Enable the YouTube Data API v3:
- With your project selected, go to the [API Library](https://console.cloud.google.com/apis/library).
- Search for "YouTube Data API v3" and enable it for your project.

### 3. Create OAuth 2.0 Credentials:
- Go to the [Credentials page](https://console.cloud.google.com/apis/credentials).
- Click on "Create Credentials" and select "OAuth 2.0 Client IDs".
- Configure the consent screen if prompted.
- Choose "Desktop app" as the application type.
- Once created, you can download the `client_secret.json` file. This file contains your OAuth 2.0 credentials.

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

## YouTube Playlist ID

The playlist ID can be found in the URL of the YouTube playlist. For example, in the URL `https://www.youtube.com/playlist?list=PL4cUxeGkcC9i4g-QLrjMH6KegEStFhZjX`, the playlist ID is `PL4cUxeGkcC9i4g-QLrjMH6KegEStFhZjX`.

## Script Configuration

Replace the placeholders in the script with your actual credentials and IDs. Add these values to your `.env` file:

```env
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=your_spotify_redirect_uri
YOUTUBE_CLIENT_SECRETS_FILE=path/to/your/client_secret.json
```


How to get your Youtube Playlists in text.

Go to Google Takeout https://takeout.google.com/
Select only Youtube, then in the multiple data option, select only playlists and download the data.