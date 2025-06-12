import time
import spotipy
import pandas as pd
import logging
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
from datetime import datetime
from yt_dlp import YoutubeDL
import librosa
import numpy as np
from tqdm import tqdm
import os
from pydub import AudioSegment
from filelock import FileLock
from difflib import SequenceMatcher
import re
import webbrowser
from google import genai
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch
import joblib
# Load API credentials
load_dotenv()

if not os.getenv("GEMINI_API_KEY"):
    raise EnvironmentError("GEMINI_API_KEY not set. Please add it to your .env file.")

try:
    logging.basicConfig(
    level=logging.DEBUG,  # <- changed from INFO to DEBUG
    filename="spotify_scraper.log",filemode="a",format="%(asctime)s - %(levelname)s - %(message)s"
    )
except Exception as e:
    print(f"⚠ Logging setup failed: {e}")

DEFAULT_DOWNLOAD_DIR = "downloads"
DEFAULT_LYRICS_DIR = "lyrics"

REQUESTS_MADE = 0
START_TIME = time.time()
RATE_LIMIT = 175
TIME_WINDOW = 60  # seconds

SPOTIFY_CREDENTIALS = [
    {"client_id": os.getenv("SPOTIFY_CLIENT_ID_1"), "client_secret": os.getenv("SPOTIFY_CLIENT_SECRET_1")},
    {"client_id": os.getenv("SPOTIFY_CLIENT_ID_2"), "client_secret": os.getenv("SPOTIFY_CLIENT_SECRET_2")},
    {"client_id": os.getenv("SPOTIFY_CLIENT_ID_3"), "client_secret": os.getenv("SPOTIFY_CLIENT_SECRET_3")}
]
credential_index = 0
sp = None

def cleanup_files(file_list):
    for file in file_list:
        try:
            if file and os.path.exists(file):
                os.remove(file)
                logging.debug(f"🧹 Deleted: {file}")
        except Exception as e:
            logging.warning(f"⚠ Could not delete file {file}: {e}")

def get_spotify_client():
    creds = SPOTIFY_CREDENTIALS[credential_index]
    return spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=creds["client_id"], client_secret=creds["client_secret"]))

sp = get_spotify_client()

def rate_limiter():
    global REQUESTS_MADE, START_TIME

    REQUESTS_MADE += 1
    elapsed_time = time.time() - START_TIME

    if REQUESTS_MADE >= RATE_LIMIT:
        sleep_time = TIME_WINDOW - elapsed_time
        if sleep_time > 0:
            logging.info(f"⏳ API rate limit reached. Sleeping for {round(sleep_time, 2)} seconds...")
            time.sleep(sleep_time)

        REQUESTS_MADE = 0
        START_TIME = time.time()

def switch_spotify_client():
    global credential_index, sp

    try:
        if not SPOTIFY_CREDENTIALS:
            logging.error("❌ No Spotify credentials available to switch.")
            return

        logging.warning("⏳ Rate limit hit. Waiting 10 seconds before switching credentials...")
        time.sleep(10)

        credential_index = (credential_index + 1) % len(SPOTIFY_CREDENTIALS)
        sp = get_spotify_client()

        logging.info(f"🔁 Switched to Spotify credentials set {credential_index + 1}")

    except Exception as e:
        logging.error(f"❌ Failed to switch Spotify credentials: {e}")

def sanitize_filename(name):
    if not name:
        return "untitled"

    # Remove illegal characters
    sanitized = re.sub(r'[\\/*?:"<>|]', "", name)

    # Optional: replace spaces with underscores for file safety
    sanitized = sanitized.strip().replace(" ", "_")

    # Fallback in case name becomes empty
    if not sanitized:
        sanitized = "untitled"

    logging.debug(f"Sanitized filename: {name} -> {sanitized}")
    return sanitized


def download_song_youtube(song_name, artist_name, save_path="downloads", cookie_path="youtube_cookies.txt"):
    global REQUESTS_MADE  # Required for external rate limiter
    os.makedirs(save_path, exist_ok=True)

    query = f"{song_name} {artist_name} audio"
    sanitized_song = sanitize_filename(song_name)
    sanitized_artist = sanitize_filename(artist_name)
    output_filename = f"{sanitized_song} - {sanitized_artist}.%(ext)s"
    full_output_path = os.path.join(save_path, output_filename.replace("%(ext)s", "mp3"))

    print(f"🔍 Attempting to download: {song_name} by {artist_name}")
    logging.info(f"Downloading YouTube audio: '{query}' -> '{full_output_path}'")

    rate_limiter()

    if not os.path.exists(cookie_path):
        logging.warning(f"⚠️ Cookie file not found: {cookie_path}")
    else:
        logging.info(f"🍪 Using cookie file: {cookie_path}")

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'socket_timeout': 15,
        'cookies': cookie_path if os.path.exists(cookie_path) else None,
        'outtmpl': os.path.join(save_path, output_filename),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"ytsearch1:{query}"])

        if os.path.exists(full_output_path):
            logging.info(f"✅ Downloaded: {full_output_path}")
            return full_output_path
        else:
            logging.warning(f"❌ File not found: {full_output_path}")
            return None

    except Exception as e:
        err_msg = str(e)
        logging.error(f"❌ YouTube download failed for '{query}': {err_msg}")

        if "Sign in to confirm" in err_msg or "Login Required" in err_msg:
            print("🔐 Login required. Opening browser...")
            webbrowser.open(f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}")
            input("🕐 Press Enter after login to retry download...")
            return download_song_youtube(song_name, artist_name, save_path, cookie_path)

        return None

def convert_mp3_to_wav(mp3_path):
    try:
        if not os.path.exists(mp3_path):
            print(f"❌ MP3 file does not exist: {mp3_path}")
            logging.error(f"MP3 file missing: {mp3_path}")
            return None

        wav_path = mp3_path.replace(".mp3", ".wav")
        print(f"🔄 Converting MP3 to WAV: {mp3_path} ➡ {wav_path}")
        logging.info(f"Converting MP3 to WAV: {mp3_path} -> {wav_path}")

        # Load and export
        sound = AudioSegment.from_file(mp3_path, format="mp3")
        sound.export(wav_path, format="wav")

        if os.path.exists(wav_path):
            print(f"✅ Successfully converted to WAV: {wav_path}")
            logging.info(f"MP3 to WAV conversion successful: {wav_path}")
            return wav_path
        else:
            print(f"❌ Conversion failed: WAV file not found.")
            logging.warning(f"WAV file not created: {wav_path}")
            return None

    except Exception as e:
        print(f"❌ Error converting {mp3_path} to WAV: {e}")
        logging.error(f"Exception during MP3 to WAV conversion: {e}")
        return None

def predict_mood_from_audio_features(features_dict):
    try:
        # Validate file presence
        if not (os.path.exists("mood_classifier.pkl") and os.path.exists("label_encoder.pkl")):
            logging.error("❌ Mood prediction model files not found.")
            return "unknown"

        # Load model and encoder
        clf = joblib.load("mood_classifier.pkl")
        le = joblib.load("label_encoder.pkl")

        expected_features = [
            "danceability", "acousticness", "energy", "instrumentalness",
            "liveness", "valence", "loudness", "speechiness", "tempo",
            "key", "time_signature"
        ]

        # Check for missing features
        if not all(f in features_dict for f in expected_features):
            logging.warning("⚠ Feature set incomplete for mood prediction.")
            return "unknown"

        # Prepare DataFrame
        df = pd.DataFrame([features_dict])[expected_features]

        # Predict mood
        prediction = clf.predict(df)[0]
        mood_label = le.inverse_transform([prediction])[0]
        logging.info(f"🎵 Predicted mood: {mood_label}")
        return mood_label

    except Exception as e:
        logging.warning(f"⚠ Error during mood prediction: {e}")
        return "unknown"
       
def extract_audio_features(file_path):
    try:
        if not os.path.exists(file_path) or os.path.getsize(file_path) < 10_000:
            raise ValueError("File is invalid or too small")

        print(f"🎧 Extracting features from: {file_path}")
        y, sr = librosa.load(file_path, sr=None, mono=True, duration=60)

        # Constants
        hop_length = 512
        n_fft = 2048

        # Base Features
        duration = librosa.get_duration(y=y, sr=sr)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=hop_length, n_fft=n_fft)
        rms = librosa.feature.rms(y=y, hop_length=hop_length)
        zcr = librosa.feature.zero_crossing_rate(y=y, hop_length=hop_length)
        spec_contrast = librosa.feature.spectral_contrast(y=y, sr=sr, hop_length=hop_length, n_fft=n_fft)
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length, n_fft=n_fft)
        tempogram = librosa.feature.tempogram(y=y, sr=sr, hop_length=hop_length)
        harmonic = librosa.effects.harmonic(y)
        percussive = librosa.effects.percussive(y)

        # Derived Stats
        loudness = np.mean(librosa.amplitude_to_db(rms))
        loudness = max(-60, min(0, loudness))  # Clamp loudness to Spotify-like range

        def normalize(val, min_val, max_val):
            return max(0.0, min(1.0, (val - min_val) / (max_val - min_val))) if max_val > min_val else 0.0

        # Feature Aggregation
        mean_chroma = np.mean(chroma, axis=1)
        max_spec_centroid = np.max(spectral_centroid) + 1e-6

        features = {
            "duration_ms": int(duration * 1000),
            "tempo": float(tempo),
            "danceability": normalize(np.std(np.diff(tempogram)), 0, 0.5),
            "acousticness": normalize(np.mean(zcr), 0, 0.2),
            "energy": normalize(np.mean(rms), 0, 0.1),
            "instrumentalness": normalize(np.mean(harmonic) / (np.mean(percussive) + 1e-6), 0, 10),
            "liveness": normalize(np.mean(spec_contrast), 0, 2),
            "loudness": loudness,
            "speechiness": normalize(np.var(chroma), 0, 1.0),
            "valence": normalize(np.mean(spectral_centroid) / max_spec_centroid, 0, 1),
            "key": int(np.argmax(mean_chroma)),
            "mode": int(np.argmax(mean_chroma) in [0, 2, 4, 5, 7, 9, 11]),
            "time_signature": min(max(3, len(librosa.onset.onset_detect(y=y, sr=sr))), 7)
        }

        print(f"✅ Features extracted successfully for {os.path.basename(file_path)}")
        return features

    except Exception as e:
        print(f"❌ Error extracting audio features from {file_path}: {e}")
        return None

def clean(text):
    """
    Normalize input text by lowering case, removing special characters,
    and standardizing whitespace.
    """
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"[-_]", " ", text)              # Replace hyphens/underscores with space
    text = re.sub(r"[^\w\s]", "", text)            # Remove punctuation
    text = re.sub(r"\s+", " ", text)               # Collapse multiple spaces
    return text.strip()

def similarity(a, b):
    """
    Compute similarity score (0 to 1) between two strings using SequenceMatcher.
    """
    return SequenceMatcher(None, clean(a), clean(b)).ratio()

def match_album_heuristic(album, movie_name, year, language, music_director=None, hero=None):
    def safe_clean(text):
        return clean(text) if isinstance(text, str) else ""

    album_name = safe_clean(album.get("name", ""))
    movie_name = safe_clean(movie_name)
    name_score = similarity(album_name, movie_name)

    artist_names = " ".join([safe_clean(a.get("name", "")) for a in album.get("artists", [])])
    artist_match = music_director and safe_clean(music_director) in artist_names
    hero_match = hero and safe_clean(hero) in artist_names

    release_date = str(album.get("release_date", ""))
    year_match = str(year) in release_date

    lang_match = safe_clean(language) in album_name or safe_clean(language) in artist_names

    # Score calculation
    score = 0
    if name_score >= 0.85:
        score += 2  # strong title match
    elif name_score >= 0.75:
        score += 1  # weak title match

    if artist_match or hero_match:
        score += 1
    if year_match:
        score += 1
    if lang_match:
        score += 1

    return score, name_score

def search_album_on_spotify(movie_name, year, language, music_director=None, hero=None, market="IN"):
    try:
        rate_limiter()
        search_phrases = [
            f"{movie_name} {year} {language} {music_director or ''}",
            f"{movie_name} {year} {language} {hero or ''}",
            f"{movie_name} {language}",
            f"{movie_name} {year}",
            movie_name
        ]

        for query in search_phrases:
            print(f"🔍 Spotify Search Query: {query}")
            logging.info(f"Spotify Search: {query}")
            results = sp.search(q=query.strip(), type="album", limit=20, market=market)
            albums = results.get("albums", {}).get("items", [])

            if not albums:
                continue

            best_album = None
            best_score = -1
            best_similarity = 0.0

            for album in albums:
                score, sim = match_album_heuristic(album, movie_name, year, language, music_director, hero)
                if score > best_score or (score == best_score and sim > best_similarity):
                    best_album = album
                    best_score = score
                    best_similarity = sim

            if best_album:
                if best_score >= 2:
                    print(f"✅ Matched: {best_album['name']} by {[a['name'] for a in best_album['artists']]} (score={best_score}, sim={best_similarity:.2f})")
                    logging.info(f"Selected album: {best_album['name']} (score={best_score})")
                    return best_album["id"]
                else:
                    print(f"⚠️ Weak fallback: {best_album['name']} (score={best_score}, sim={best_similarity:.2f}) — skipping.")
                    logging.warning(f"Weak fallback album rejected: {best_album['name']}")

        logging.error(f"❌ No suitable album found for '{movie_name}' ({year}, {language})")
        return None

    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 429:
            logging.warning("⏳ Rate limit hit. Switching Spotify client...")
            switch_spotify_client()
            return search_album_on_spotify(movie_name, year, language, music_director, hero, market)
        else:
            logging.error(f"Spotify API error: {e}")
            return None

    except Exception as e:
        logging.error(f"Unexpected error during album search: {e}")
        return None
    
def fetch_mood_from_gemini_only(song_name, artist_name):
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    model_id = "gemini-2.0-flash"
    tool = Tool(google_search=GoogleSearch())

    prompts = [
        f"What is the mood (choose from [happy, sad, energetic, calm]) of the song '{song_name}' by '{artist_name}'? Just return one mood word.",
        f"Classify the mood of the song '{song_name}' by '{artist_name}'. Only respond with one word from [happy, sad, energetic, calm].",
        f"Which one best describes the mood of the song '{song_name}' by '{artist_name}': happy, sad, energetic, or calm? Just the word."
    ]

    allowed_moods = {"happy", "sad", "energetic", "calm"}

    print("🧠 Attempting Gemini mood classification...")

    for attempt, prompt in enumerate(prompts, start=1):
        print(f"🔁 Attempt {attempt}: {prompt}")
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=GenerateContentConfig(
                    tools=[tool],
                    response_modalities=["TEXT"]
                )
            )

            if response.candidates and response.candidates[0].content.parts:
                text = "\n".join(
                    part.text for part in response.candidates[0].content.parts if hasattr(part, "text")
                ).strip().lower()

                for mood in allowed_moods:
                    if mood in text:
                        print(f"🎯 Identified mood: {mood}")
                        return mood
                print(f"⚠ Gemini response didn't match expected moods: {text}")
        except Exception as e:
            logging.warning(f"⚠ Gemini mood fetch attempt {attempt} failed: {e}")

    logging.warning("❌ All Gemini mood prompt attempts failed.")
    return "unknown"


def log_missing_lyrics(song_name, artist_name, album_name):
    try:
        folder = os.path.join("lyrics", "missing")
        os.makedirs(folder, exist_ok=True)
        file_path = os.path.join(folder, "missing_lyrics.txt")

        entry = f"{song_name} | {artist_name} | {album_name}\n"

        # Avoid logging duplicate entries
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                if entry in f.readlines():
                    return  # Already logged

        with open(file_path, "a", encoding="utf-8") as f:
            f.write(entry)

        logging.info(f"📝 Logged missing lyrics: {entry.strip()}")
        
    except Exception as e:
        logging.error(f"❌ Failed to log missing lyrics for {song_name}: {e}")

def fetch_lyrics_from_gemini_only(song_name, artist_name):
    from google import genai
    from google.genai.types import Tool, GenerateContentConfig, GoogleSearch

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    model_id = "gemini-2.0-flash"
    tool = Tool(google_search=GoogleSearch())

    prompts = [
        f"Get the full lyrics of the song '{song_name}' by '{artist_name}'. Only return the lyrics.",
        f"Provide complete lyrics for '{song_name}' performed by '{artist_name}' without any explanation or extra details.",
        f"Give me only the song lyrics of '{song_name}' by '{artist_name}' as plain text, no intro or summary."
    ]

    rejection_phrases = [
        "i'm sorry", "i am sorry", "i cannot provide", "i couldn’t find",
        "no lyrics available", "unable to provide", "due to copyright",
        "limitations in the search", "here is a snippet", "partial lyrics", "not the full lyrics"
    ]

    print(f"🎤 Attempting Gemini lyrics search for: {song_name} by {artist_name}")
    
    for attempt, prompt in enumerate(prompts, start=1):
        print(f"🔁 Attempt {attempt}: {prompt}")
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=GenerateContentConfig(tools=[tool], response_modalities=["TEXT"])
            )

            if not response.candidates:
                logging.warning("⚠ No response candidates from Gemini.")
                continue

            # Extract lyrics text
            lyrics = "\n".join(
                part.text for part in response.candidates[0].content.parts if hasattr(part, "text")
            ).strip()

            # Reject non-lyrical content
            if any(phrase in lyrics.lower() for phrase in rejection_phrases):
                print(f"⚠ Gemini returned a disqualified response:\n{lyrics}\n")
                continue

            print("✅ Lyrics successfully retrieved.")
            return lyrics

        except Exception as e:
            logging.warning(f"⚠ Gemini lyrics fetch attempt {attempt} failed: {e}")

    logging.warning("❌ All Gemini lyrics prompt attempts failed.")
    return ""

def save_lyrics(lyrics, album_name, song_name):
    try:
        # Skip saving generic responses
        if any(phrase in lyrics.lower() for phrase in [
            "i'm sorry", "could not find", "snippet", "not available", "restrictions"
        ]):
            logging.warning(f"🚫 Skipping save: Lyrics for '{song_name}' appear incomplete or generic.")
            return

        folder = os.path.join("lyrics", sanitize_filename(album_name))
        os.makedirs(folder, exist_ok=True)
        file_path = os.path.join(folder, f"{sanitize_filename(song_name)}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(lyrics.strip())
        logging.info(f"💾 Saved lyrics to {file_path}")
    except Exception as e:
        logging.error(f"❌ Error saving lyrics for {song_name}: {e}")

def process_track(song_meta, movie_name, use_separate_lyrics_and_mood=False):
    song_name = song_meta["name"]
    artist_name = song_meta["artists"][0]["name"]
    album_name = song_meta["album"]["name"]
    logging.info(f"🎧 Processing: {song_name} by {artist_name}")

    audio_file = download_song_youtube(song_name, artist_name)
    if not audio_file:
        logging.warning(f"❌ Skipping download failure: {song_name}")
        return None

    wav_file = convert_mp3_to_wav(audio_file)
    if not wav_file:
        logging.warning(f"❌ Skipping conversion failure: {song_name}")
        cleanup_files([audio_file])
        return None

    try:
        audio_features = extract_audio_features(wav_file)
        if not audio_features:
            raise Exception("Feature extraction failed")

        # Lyrics & mood logic
        lyrics = fetch_lyrics_from_gemini_only(song_name, artist_name)
        if not lyrics:
            log_missing_lyrics(song_name, artist_name, album_name)
        mood = fetch_mood_from_gemini_only(song_name, artist_name)
        if mood == "unknown":
            logging.info(f"🤖 Falling back to audio-based mood prediction for '{song_name}'")
            mood = predict_mood_from_audio_features(audio_features)

        lyrics_available = bool(lyrics)
        if lyrics_available:
            save_lyrics(lyrics, album_name, song_name)

        return {
            "name": song_name,
            "album": album_name,
            "artist": ", ".join([artist["name"] for artist in song_meta["artists"]]),
            "id": song_meta["id"],
            "release_date": song_meta["album"]["release_date"],
            "popularity": song_meta["popularity"],
            "mood": mood,
            "lyrics_available": lyrics_available,
            **audio_features
        }

    except Exception as e:
        logging.warning(f"❌ Failed processing song {song_name}: {e}")
        return None
    finally:
        cleanup_files([audio_file, wav_file])


def get_songs_from_album(album_id, movie_name, use_separate_lyrics_and_mood=False):
    songs_data = []
    if not album_id:
        logging.warning(f"⚠ Skipping: No album ID for '{movie_name}'")
        return songs_data

    try:
        rate_limiter()
        tracks = sp.album_tracks(album_id)
        track_ids = [track["id"] for track in tracks["items"]]

        for i in tqdm(range(0, len(track_ids), 50), desc=f"🎵 {movie_name}", unit="batch"):
            rate_limiter()
            track_details = sp.tracks(track_ids[i:i+50])["tracks"]

            for song_meta in track_details:
                record = process_track(song_meta, movie_name, use_separate_lyrics_and_mood)
                if record:
                    songs_data.append(record)

    except Exception as e:
        logging.error(f"🔥 Error processing album {album_id} ({movie_name}): {e}")

    return songs_data


def save_progress(processed_movies, filename="processed_movies.txt"):
    lock_file = filename + ".lock"
    try:
        with FileLock(lock_file):
            with open(filename, "w", encoding="utf-8") as file:
                for movie in sorted(set(processed_movies)):
                    file.write(movie + "\n")
        print(f"💾 Progress saved to '{filename}'. Total processed movies: {len(processed_movies)}")
    except Exception as e:
        print(f"❌ Failed to save progress to '{filename}' with lock '{lock_file}': {e}")

def load_processed_movies(filename="processed_movies.txt"):
    try:
        if not os.path.isfile(filename):
            print(f"📄 No processed movie log found at '{filename}'. Starting fresh.")
            return set()
        
        with open(filename, "r", encoding="utf-8") as file:
            processed = {line.strip() for line in file if line.strip()}
        
        print(f"📂 Loaded {len(processed)} processed movies from {filename}")
        return processed

    except Exception as e:
        print(f"❌ Failed to load processed movies from '{filename}': {e}")
        return set()

def process_movie_csv(file_path, processed_movies):
    print(f"📂 Processing file: {file_path}")
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()
    for _, row in tqdm(df.iterrows(), total=len(df), desc=f"🎬 {os.path.basename(file_path)}", unit="movie"):
        movie_name = row.get("Title", "").strip()
        if not movie_name or movie_name in processed_movies:
            continue
        try:
            release_date = row.get("Release Date", "")
            year = datetime.strptime(str(release_date), "%d-%m-%Y").year
            language = row.get("Language", "").strip()
            hero = row.get("Hero", "").strip()
            music_director = row.get("Music Director", "").strip()
            album_id = search_album_on_spotify(movie_name, year, language, music_director, hero)
            songs = get_songs_from_album(album_id, movie_name)
            if songs:
                output_df = pd.DataFrame(songs)
                folder_path = os.path.join("output", sanitize_filename(language), str(year))
                os.makedirs(folder_path, exist_ok=True)
                output_file = os.path.join(folder_path, "songs.csv")
                if os.path.exists(output_file):
                    existing_df = pd.read_csv(output_file)
                    output_df = pd.concat([existing_df, output_df], ignore_index=True)
                output_df.to_csv(output_file, index=False)
                print(f"✅ Saved {len(songs)} songs for '{movie_name}' → {output_file}")
            else:
                print(f"⚠ No songs found for: {movie_name}")
        except Exception as e:
            print(f"❌ Error processing movie '{movie_name}': {e}")
        processed_movies.add(movie_name)
        save_progress(processed_movies)
        
def process_all_csv_files():
    MOVIE_CSV_FOLDER = "movie_csvs"
    
    if not os.path.exists(MOVIE_CSV_FOLDER):
        logging.error(f"❌ Folder '{MOVIE_CSV_FOLDER}' does not exist!")
        return

    # Recursively collect all CSV files
    csv_files = [
        os.path.join(root, file)
        for root, _, files in os.walk(MOVIE_CSV_FOLDER)
        for file in files if file.lower().endswith(".csv")
    ]

    if not csv_files:
        logging.warning("❌ No CSV files found in 'movie_csvs' or subfolders!")
        return

    logging.info(f"✅ Found {len(csv_files)} CSV files. Beginning processing...")
    processed_movies = load_processed_movies()

    for file in tqdm(csv_files, desc="📁 CSV Files", unit="file"):
        try:
            process_movie_csv(file, processed_movies)
        except Exception as e:
            logging.exception(f"⚠ Error processing file '{file}': {e}")

    logging.info("🎉 All CSV files processed successfully.")

if __name__ == "__main__":
    try:
        print("🚀 Starting Spotify + YouTube Audio Feature Extraction...")
        process_all_csv_files()
        print("🎉 Done!")
    except KeyboardInterrupt:
        print("❌ Interrupted by user. Exiting...")
    except Exception as e:
        logging.exception(f"🔥 Unhandled error occurred during execution: {e}")
