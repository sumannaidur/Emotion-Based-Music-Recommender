import spotipy
from spotipy.oauth2 import SpotifyOAuth
import yt_dlp
import librosa
import numpy as np
import os
from googleapiclient.discovery import build
import re
from pydub import AudioSegment

# Spotify and YouTube credentials
SPOTIPY_CLIENT_ID = "15adf67aec934fe792bee0d467742326"
SPOTIPY_CLIENT_SECRET = "d03b2411aad24b8e80f3257660f9f10f"
SPOTIPY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
YOUTUBE_API_KEY = "AIzaSyDVUD2sWD33a93ScWcOdKn6nnJtk06yiQY"

# Authenticate with Spotify
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                               client_secret=SPOTIPY_CLIENT_SECRET,
                                               redirect_uri=SPOTIPY_REDIRECT_URI,
                                               scope="user-read-recently-played user-library-read"))

os.makedirs("audio_files", exist_ok=True)

def clean_filename(filename):
    return re.sub(r'[^\w\-_\.]', '_', filename)  # Replace special characters with "_"

def convert_wav(file_path):
    sound = AudioSegment.from_file(file_path)
    sound.export(file_path, format="wav", parameters=["-ac", "1"])  # Convert to mono


def get_youtube_url(song_title, artist):
    """
    Fetch YouTube video URL for the song.
    """
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    query = f"{song_title} {artist} official audio OR official video OR lyrics"
    
    request = youtube.search().list(q=query, part="snippet", maxResults=1, type="video")
    response = request.execute()
    
    if "items" in response and response["items"]:
        video_id = response["items"][0]["id"]["videoId"]
        return f"https://www.youtube.com/watch?v={video_id}"
    
    return None

def download_audio(youtube_url, filename):
    """
    Download YouTube audio.
    """
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"audio_files/{filename}.%(ext)s",
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav", "preferredquality": "192"}],
        "quiet": True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])
    return f"audio_files/{filename}.wav"

def extract_audio_features(file_path):
    """
    Extract audio features using librosa.
    """
    convert_wav(file_path)
    y, sr = librosa.load(file_path, sr=22050)  # Remove backend='audioread'
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

    return {
        "tempo": tempo,
        "loudness": np.mean(librosa.feature.rms(y=y)),
        "key": librosa.feature.chroma_stft(y=y, sr=sr).mean(),
        "danceability": np.mean(librosa.feature.spectral_contrast(y=y, sr=sr)),
        "energy": np.mean(librosa.feature.mfcc(y=y, sr=sr, n_mfcc=1)),
        "speechiness": np.mean(librosa.feature.mfcc(y=y, sr=sr, n_mfcc=2)),
        "instrumentalness": np.mean(librosa.feature.zero_crossing_rate(y=y))
    }

def process_song(song_name, artist_name):
    """
    Fetch song features and extract audio features.
    """
    youtube_url = get_youtube_url(song_name, artist_name)
    if not youtube_url:
        print(f"❌ No YouTube link found for {song_name} - {artist_name}")
        return None

    print(f"🎵 Downloading {song_name} by {artist_name}...")
    audio_path = download_audio(youtube_url, f"{song_name}_{artist_name}".replace(" ", "_"))
    
    print(f"🎧 Extracting features for {song_name}...")
    return extract_audio_features(audio_path)
