import spotipy
from spotipy.oauth2 import SpotifyOAuth
import yt_dlp
import librosa
import librosa.display
import numpy as np
import pandas as pd
import os
from pydub import AudioSegment
from googleapiclient.discovery import build
from pyAudioAnalysis import ShortTermFeatures

# Spotify Credentials (Replace with your credentials)
SPOTIPY_CLIENT_ID = "15adf67aec934fe792bee0d467742326"
SPOTIPY_CLIENT_SECRET = "d03b2411aad24b8e80f3257660f9f10f"
SPOTIPY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
YOUTUBE_API_KEY = "AIzaSyDVUD2sWD33a93ScWcOdKn6nnJtk06yiQY"

# Authenticate with Spotify
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                               client_secret=SPOTIPY_CLIENT_SECRET,
                                               redirect_uri=SPOTIPY_REDIRECT_URI,
                                               scope="user-read-recently-played user-library-read"))

# Folder for saving downloaded audio files
os.makedirs("audio_files", exist_ok=True)

# Function to search for a song on Spotify
def get_spotify_song_details(query):
    results = sp.search(q=query, type="track", limit=1)
    if results['tracks']['items']:
        track = results['tracks']['items'][0]
        return {
            "spotify_id": track["id"],
            "title": track["name"],
            "artist": ", ".join(artist["name"] for artist in track["artists"]),
            "album": track["album"]["name"],
            "release_date": track["album"]["release_date"],
            "popularity": track["popularity"]
        }
    return None

# Function to search for a song on YouTube
def get_youtube_url(song_title, artist):
    """
    Searches YouTube for the most relevant video based on song title and artist.
    Returns the URL of the first matching video.
    """
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    
    query = f"{song_title} {artist} official audio OR official video OR lyrics"
    
    request = youtube.search().list(
        q=query,
        part="snippet",
        maxResults=1,
        type="video"
    )
    response = request.execute()
    
    if "items" in response and response["items"]:
        video_id = response["items"][0]["id"]["videoId"]
        return f"https://www.youtube.com/watch?v={video_id}"
    
    return None  # No match found

# Function to download audio from YouTube
def download_audio(youtube_url, filename):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"audio_files/{filename}.%(ext)s",
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav", "preferredquality": "192"}],
        "quiet": True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])
    return f"audio_files/{filename}.wav"

# Function to extract features using librosa
def extract_audio_features(file_path):
    y, sr = librosa.load(file_path, sr=22050)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    
    features = {
        "tempo": tempo,
        "loudness": np.mean(librosa.feature.rms(y=y)),
        "key": librosa.feature.chroma_stft(y=y, sr=sr).mean(),
        "danceability": np.mean(librosa.feature.spectral_contrast(y=y, sr=sr)),  # Approximate danceability
        "energy": np.mean(librosa.feature.mfcc(y=y, sr=sr, n_mfcc=1)),  # Approximate energy
        "speechiness": np.mean(librosa.feature.mfcc(y=y, sr=sr, n_mfcc=2)),  # Approximate speechiness
        "instrumentalness": np.mean(librosa.feature.zero_crossing_rate(y=y)),  # Approximate instrumentalness
    }
    return features

# Function to process a song
def process_song(song_name, artist_name):
    query = f"{song_name} {artist_name}"
    song_details = get_spotify_song_details(query)
    
    if not song_details:
        print(f"❌ No song details found for {query}")
        return None

    youtube_url = get_youtube_url(song, artist)
    if not youtube_url:
        print(f"❌ No YouTube link found for {query}")
        return None

    print(f"🎵 Downloading {song_details['title']} by {song_details['artist']}...")
    audio_path = download_audio(youtube_url, f"{song_details['spotify_id']}")
    
    print(f"🎧 Extracting audio features for {song_details['title']}...")
    audio_features = extract_audio_features(audio_path)

    return {**song_details, **audio_features}

# List of sample songs (you can replace this with your list)
songs_to_process = [
    ("Believer", "Imagine Dragons"),
    ("Shape of You", "Ed Sheeran"),
    ("Bad Guy", "Billie Eilish"),
    ("Jai Ho", "A.R. Rahman"),
    ("Naatu Naatu", "Ram Miriyala, Kaala Bhairava")
]

# Process each song
all_song_data = []
for song, artist in songs_to_process:
    song_data = process_song(song, artist)
    if song_data:
        all_song_data.append(song_data)

# Convert to DataFrame and Save CSV
df = pd.DataFrame(all_song_data)
df.to_csv("song_features.csv", index=False)
print("✅ Song features saved to song_features.csv!")
