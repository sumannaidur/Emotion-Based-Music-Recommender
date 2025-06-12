import spotipy
import csv
import os
from spotipy.oauth2 import SpotifyOAuth

# Replace with your Spotify credentials
client_id = "15adf67aec934fe792bee0d467742326"
client_secret = "d03b2411aad24b8e80f3257660f9f10f"
redirect_uri = "http://localhost:8888/callback"

# Authenticate with Spotify
scope = "user-read-recently-played user-library-read"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id, client_secret, redirect_uri, scope=scope))

# Define the languages and the years we want to fetch
languages = ["Kannada", "Telugu", "Tamil", "English", "Hindi"]
years = list(range(2000, 2026))  # From 2000 to 2025

# Create a main folder for CSVs
csv_folder = "csvs"
os.makedirs(csv_folder, exist_ok=True)

def get_songs_by_year_and_language(year, language):
    """
    Fetches songs released in a given year and language from the Spotify API.

    Args:
        year (int): The year to search for.
        language (str): The language name (e.g., "Kannada", "English").
    
    Returns:
        list: A list of song dictionaries with details like title, artist, album, release date, and Spotify ID.
    """
    
    songs_list = []
    offset = 0
    limit = 50  # Max limit per request
    total_tracks = None

    while total_tracks is None or offset < total_tracks:
        # Search query with year (Spotify does not support direct language filter)
        search_query = f"year:{year} {language}"

        try:
            results = sp.search(q=search_query, type="track", limit=limit, offset=offset)
        except Exception as e:
            print(f"Error fetching data for {year} - {language}: {e}")
            break

        if total_tracks is None:
            total_tracks = results["tracks"]["total"]  # Get total track count from first request

        for track in results["tracks"]["items"]:
            song_data = {
                "spotify_id": track["id"],  # Fetching Spotify Track ID
                "title": track["name"],
                "artist": ", ".join(artist["name"] for artist in track["artists"]),
                "album": track["album"]["name"],
                "release_date": track["album"]["release_date"]
            }
            songs_list.append(song_data)

        offset += limit  # Move to the next batch of tracks

        # Break if no more results
        if len(results["tracks"]["items"]) == 0:
            break

    return songs_list

def save_songs_to_csv(songs, year, language):
    """
    Saves the song details to a CSV file in a structured folder format.

    Args:
        songs (list): List of song dictionaries.
        year (int): The year of the songs.
        language (str): The language of the songs.
    """
    
    # Create a subfolder for the year
    year_folder = os.path.join(csv_folder, str(year))
    os.makedirs(year_folder, exist_ok=True)
    
    # Define the CSV file path
    filename = f"songs_{year}_{language.lower()}.csv"
    filepath = os.path.join(year_folder, filename)

    with open(filepath, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Spotify ID", "Title", "Artist", "Album", "Release Date"])  # CSV Header
        
        for song in songs:
            writer.writerow([song["spotify_id"], song["title"], song["artist"], song["album"], song["release_date"]])

    print(f"Saved {len(songs)} songs to {filepath}")

# Loop through each year and language and fetch songs
for year in years:
    for language in languages:
        print(f"Fetching songs for {year} - {language}...")
        songs = get_songs_by_year_and_language(year, language)
        
        if songs:
            save_songs_to_csv(songs, year, language)
        else:
            print(f"No songs found for {year} - {language}. Skipping CSV creation.")
