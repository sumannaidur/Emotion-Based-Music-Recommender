import spotipy
import csv
import os
import yt_dlp
import librosa
import numpy as np
import pandas as pd
from spotipy.oauth2 import SpotifyOAuth
from youtubesearchpython import VideosSearch  # ✅ Replacing YouTube API

# === Spotify Credentials ===
SPOTIPY_CLIENT_ID = "15adf67aec934fe792bee0d467742326"
SPOTIPY_CLIENT_SECRET = "d03b2411aad24b8e80f3257660f9f10f"
SPOTIPY_REDIRECT_URI = "http://127.0.0.1:8888/callback"

# === Authenticate with Spotify ===
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                               client_secret=SPOTIPY_CLIENT_SECRET,
                                               redirect_uri=SPOTIPY_REDIRECT_URI,
                                               scope="user-read-recently-played user-library-read"))

# === Folder Setup ===
csv_folder = "csvs"
audio_folder = "audio_files"
os.makedirs(csv_folder, exist_ok=True)
os.makedirs(audio_folder, exist_ok=True)

# === Define Languages and Years ===
languages = ["Telugu"]
years = list(range(2025, 2026))

# === Function to Fetch Songs from Spotify ===
def get_songs_by_year_and_language(year, language):
    songs_list = []
    offset = 0
    limit = 50
    total_tracks = None

    while total_tracks is None or offset < total_tracks:
        search_query = f"year:{year} {language}"
        try:
            results = sp.search(q=search_query, type="track", limit=limit, offset=offset)
        except Exception as e:
            print(f"Error fetching data for {year} - {language}: {e}")
            break

        if total_tracks is None:
            total_tracks = results["tracks"]["total"]

        for track in results["tracks"]["items"]:
            song_data = {
                "Spotify ID": track["id"],
                "Title": track["name"],
                "Artist": ", ".join(artist["name"] for artist in track["artists"]),
                "Album": track["album"]["name"],
                "Release Date": track["album"]["release_date"],
                "Popularity": track["popularity"]
            }
            songs_list.append(song_data)

        offset += limit
        if len(results["tracks"]["items"]) == 0:
            break

    return songs_list

# === Function to Save Songs to CSV ===
def save_songs_to_csv(songs, year, language):
    year_folder = os.path.join(csv_folder, str(year))
    os.makedirs(year_folder, exist_ok=True)

    filename = f"songs_{year}_{language.lower()}.csv"
    filepath = os.path.join(year_folder, filename)

    with open(filepath, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Spotify ID", "Title", "Artist", "Album", "Release Date", "Popularity"])
        for song in songs:
            writer.writerow([song["Spotify ID"], song["Title"], song["Artist"], song["Album"], song["Release Date"], song["Popularity"]])

    print(f"✅ Saved {len(songs)} songs to {filepath}")

# === Function to Search for YouTube Videos (Without API) ===
def get_youtube_url(song_title, artist):
    query = f"{song_title} {artist} official audio OR lyrics OR video"
    search = VideosSearch(query, limit=1)
    
    try:
        results = search.result()
        if "result" in results and results["result"]:
            return results["result"][0]["link"]
    except Exception as e:
        print(f"❌ YouTube search failed for {song_title}: {e}")

    return None

# === Function to Download Audio from YouTube ===
def download_audio(youtube_url, filename):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{audio_folder}/{filename}.%(ext)s",
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav", "preferredquality": "192"}],
        "quiet": True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])
    return f"{audio_folder}/{filename}.wav"

# === Function to Extract Audio Features ===
def extract_audio_features(file_path):
    y, sr = librosa.load(file_path, sr=22050)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

    features = {
        "tempo": tempo,
        "loudness": np.mean(librosa.feature.rms(y=y)),
        "key": librosa.feature.chroma_stft(y=y, sr=sr).mean(),
        "danceability": np.mean(librosa.feature.spectral_contrast(y=y, sr=sr)),
        "energy": np.mean(librosa.feature.mfcc(y=y, sr=sr, n_mfcc=1)),
        "speechiness": np.mean(librosa.feature.mfcc(y=y, sr=sr, n_mfcc=2)),
        "instrumentalness": np.mean(librosa.feature.zero_crossing_rate(y=y))
    }
    return features

# === Function to Process Songs ===
def process_song(song_details):
    song_title = song_details["Title"]
    artist_name = song_details["Artist"]
    spotify_id = song_details["Spotify ID"]

    print(f"🎵 Searching for YouTube link for {song_title} by {artist_name}...")
    youtube_url = get_youtube_url(song_title, artist_name)
    
    if not youtube_url:
        print(f"❌ No YouTube link found for {song_title}")
        return None

    print(f"🎧 Downloading {song_title}...")
    audio_path = download_audio(youtube_url, spotify_id)

    print(f"🔍 Extracting features for {song_title}...")
    audio_features = extract_audio_features(audio_path)

    # Delete audio file after processing
    if os.path.exists(audio_path):
        os.remove(audio_path)
        print(f"🗑️ Deleted {audio_path}")

    # ✅ Ensure the song metadata is merged properly
    song_data = {
        **song_details,  # Merge original song details
        **audio_features  # Merge extracted audio features
    }

    return song_data

# === Save Extracted Features One by One ===
csv_file = "song_features.csv"
csv_columns = ["Spotify ID", "Title", "Artist", "Album", "Release Date", "Popularity", 
               "tempo", "loudness", "key", "danceability", "energy", "speechiness", "instrumentalness"]

# If the CSV file does not exist, create it with headers
if not os.path.exists(csv_file):
    with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(csv_columns)

for year in years:
    for language in languages:
        print(f"🔎 Fetching songs for {year} - {language}...")
        songs = get_songs_by_year_and_language(year, language)

        if songs:
            save_songs_to_csv(songs, year, language)

            for song in songs:
                song_data = process_song(song)
                if song_data:
                    # Append the extracted features to CSV
                    with open(csv_file, mode="a", newline="", encoding="utf-8") as file:
                        writer = csv.writer(file)
                        writer.writerow([song_data.get(col, "N/A") for col in csv_columns])

        else:
            print(f"⚠️ No songs found for {year} - {language}")

print("✅ All song features saved to song_features.csv!")  
