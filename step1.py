import requests
import pandas as pd
import time
import os
import logging
import wikipedia
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("TMDB_API_KEY")

# Constants
BASE_URL = 'https://api.themoviedb.org/3/discover/movie'
CREDITS_URL = 'https://api.themoviedb.org/3/movie/{movie_id}/credits'
YEARS = list(range(2000, 2027))
LANGUAGES = {'hi': 'Hindi', 'kn': 'Kannada', 'ta': 'Tamil', 'te': 'Telugu'}
OUTPUT_FOLDER = 'movies_by_language'
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# === Cleaning Function ===
def clean_title(title):
    if not title:
        return ""
    title = title.strip()
    title = title.replace(":", "")
    title = title.replace("–", "-")
    title = title.replace("’", "'")
    title = ''.join(c for c in title if c.isalnum() or c.isspace())  # Remove special characters
    return title.title()

# === Wikipedia Validation ===
def is_valid_movie_on_wikipedia(title, year=None):
    try:
        results = wikipedia.search(title + " film")
        if not results:
            return False
        summary = wikipedia.summary(results[0], sentences=2).lower()
        if "film" in summary or "movie" in summary:
            if year and str(year) in summary:
                return True
            return True
        return False
    except wikipedia.exceptions.DisambiguationError as e:
        logging.warning(f"⚠ Disambiguation for '{title}': {e.options[:2]}")
        return True
    except wikipedia.exceptions.PageError:
        return False
    except Exception as e:
        logging.warning(f"⚠ Wikipedia check failed for '{title}': {e}")
        return False

# === Extract Song List from Wikipedia ===
def get_wikipedia_song_list(title):
    try:
        page = wikipedia.page(title + " soundtrack")
        html = page.html()
        soup = BeautifulSoup(html, "html.parser")

        song_list = []
        tables = soup.find_all("table", class_="tracklist") or soup.find_all("table", class_="wikitable")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows[1:]:  # skip header
                cols = row.find_all("td")
                if len(cols) >= 2:
                    song = cols[0].get_text(strip=True)
                    if song:
                        song_list.append(song)
        return "; ".join(song_list) if song_list else None
    except Exception as e:
        logging.warning(f"🎵 Could not get tracks for '{title}': {e}")
        return None

# === Fetch Hero and Heroine from TMDb ===
def get_cast(movie_id):
    try:
        response = requests.get(CREDITS_URL.format(movie_id=movie_id), params={'api_key': API_KEY})
        response.raise_for_status()
        data = response.json()
        hero, heroine = None, None
        for actor in data.get('cast', []):
            if actor.get('gender') == 2 and not hero:
                hero = actor.get('name')
            elif actor.get('gender') == 1 and not heroine:
                heroine = actor.get('name')
            if hero and heroine:
                break
        return hero, heroine
    except Exception as e:
        logging.warning(f"❌ Error getting cast for movie ID {movie_id}: {e}")
        return None, None

# === Fetch Movies by Language and Save ===
def fetch_movies(lang_code, lang_name):
    movie_data = []
    logging.info(f"📥 Fetching movies for: {lang_name}")

    for year in YEARS:
        page = 1
        logging.info(f"  Year {year}...")

        while True:
            params = {
                'api_key': API_KEY,
                'language': 'en-US',
                'sort_by': 'popularity.desc',
                'include_adult': False,
                'include_video': False,
                'page': page,
                'primary_release_year': year,
                'with_original_language': lang_code
            }

            try:
                response = requests.get(BASE_URL, params=params)
                if response.status_code == 429:
                    logging.warning("⏳ Rate limit exceeded! Waiting 10 seconds...")
                    time.sleep(10)
                    continue
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                logging.error(f"❌ Error fetching movies: {e}")
                break

            if 'results' not in data or not data['results']:
                break

            for movie in data['results']:
                raw_title = movie.get('title')
                cleaned_title = clean_title(raw_title)

                if not is_valid_movie_on_wikipedia(cleaned_title, year):
                    logging.info(f"⛔ Skipping '{cleaned_title}' (not verified on Wikipedia)")
                    continue

                hero, heroine = get_cast(movie.get('id'))
                song_list = get_wikipedia_song_list(cleaned_title)

                movie_data.append({
                    'Title': cleaned_title,
                    'Original Title': raw_title,
                    'Release Date': movie.get('release_date'),
                    'Language': lang_name,
                    'Hero': hero,
                    'Heroine': heroine,
                    'Overview': movie.get('overview'),
                    'Vote Average': movie.get('vote_average'),
                    'Popularity': movie.get('popularity'),
                    'Wikipedia Songs': song_list
                })

            page += 1
            if page > data.get('total_pages', 1):
                break
            time.sleep(0.5)

    # Save CSV
    df = pd.DataFrame(movie_data)
    filepath = os.path.join(OUTPUT_FOLDER, f"{lang_name.lower()}_movies.csv")
    try:
        df.to_csv(filepath, index=False)
        logging.info(f"✅ Saved {len(movie_data)} movies to '{filepath}'")
    except Exception as e:
        logging.error(f"❌ Error saving CSV for {lang_name}: {e}")

# === Entry Point ===
if __name__ == "__main__":
    if not API_KEY:
        logging.error("TMDB_API_KEY not found in .env")
    else:
        for code, name in LANGUAGES.items():
            fetch_movies(code, name)
        logging.info("🎉 All movie data saved successfully!")
