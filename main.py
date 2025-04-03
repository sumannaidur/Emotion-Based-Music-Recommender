import spotipy
import csv
import os
from spotipy.oauth2 import SpotifyOAuth
from features import process_song  # Import feature extraction function

# Replace with your Spotify credentials
client_id = "15adf67aec934fe792bee0d467742326"
client_secret = "d03b2411aad24b8e80f3257660f9f10f"
redirect_uri = "http://localhost:8888/callback"

# Authenticate with Spotify
scope = "user-read-recently-played user-library-read"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id, client_secret, redirect_uri, scope=scope))

# Define the languages and years we want to fetch
languages = ["Kannada", "Telugu", "Tamil", "English", "Hindi"]
years = list(range(2020, 2025))  # Reduce range for faster testing

# Create folders for CSVs
csv_folder = "csvs"
os.makedirs(csv_folder, exist_ok=True)

def get_songs_by_year_and_language(year, language):
    """
    Fetch songs from Spotify by year and language.
    """
    songs_list = []
    search_query = f"year:{year} {language}"
    results = sp.search(q=search_query, type="track", limit=10)  # Reduce limit for testing

    for track in results["tracks"]["items"]:
        song_data = {
            "spotify_id": track["id"],
            "title": track["name"],
            "artist": ", ".join(artist["name"] for artist in track["artists"]),
            "album": track["album"]["name"],
            "release_date": track["album"]["release_date"]
        }
        songs_list.append(song_data)

    return songs_list

def save_songs_with_features(songs, year, language):
    """
    Saves song details along with extracted features to a CSV.
    """
    year_folder = os.path.join(csv_folder, str(year))
    os.makedirs(year_folder, exist_ok=True)
    
    filename = f"song_features_{year}_{language.lower()}.csv"
    filepath = os.path.join(year_folder, filename)

    with open(filepath, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Spotify ID", "Title", "Artist", "Album", "Release Date", "Tempo", "Loudness", "Key", "Danceability", "Energy", "Speechiness", "Instrumentalness"])

        for song in songs:
            features = process_song(song["title"], song["artist"])
            if features:
                writer.writerow([
                    song["spotify_id"], song["title"], song["artist"], song["album"], song["release_date"],
                    features["tempo"], features["loudness"], features["key"], features["danceability"], 
                    features["energy"], features["speechiness"], features["instrumentalness"]
                ])

    print(f"✅ Songs with features saved to {filepath}")

# Fetch and process songs
for year in years:
    for language in languages:
        print(f"Fetching songs for {year} - {language}...")
        songs = get_songs_by_year_and_language(year, language)

        if songs:
            save_songs_with_features(songs, year, language)
        else:
            print(f"No songs found for {year} - {language}.")
