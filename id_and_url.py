import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import pandas as pd

# ✅ Step 1: Set Up Spotify API Credentials
SPOTIPY_CLIENT_ID = "15adf67aec934fe792bee0d467742326"  # 🔴 Replace with your Client ID
SPOTIPY_CLIENT_SECRET = "d03b2411aad24b8e80f3257660f9f10f"  # 🔴 Replace with your Client Secret

# ✅ Step 2: Authenticate with Spotify
print("[INFO] Authenticating with Spotify API...")
client_credentials_manager = SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
print("[SUCCESS] Authentication successful!\n")

# ✅ Step 3: Load Your Songs List (Example CSV)
input_csv = "csvs/predicated/predicted_Telugu_songs.csv"  # 🔴 Change to your file
print(f"[INFO] Loading dataset: {input_csv}")

try:
    df = pd.read_csv(input_csv)
    print(f"[SUCCESS] Loaded dataset with {len(df)} records.\n")
except FileNotFoundError:
    print(f"[ERROR] File '{input_csv}' not found. Please check the path and try again.")
    exit()

# ✅ Ensure necessary columns exist
required_columns = ['song_name', 'singer']
missing_columns = [col for col in required_columns if col not in df.columns]

if missing_columns:
    print(f"[ERROR] Missing columns in dataset: {missing_columns}. Please check the CSV format.")
    exit()

# ✅ Step 4: Function to Find Song ID & URL
def get_spotify_info(song, artist):
    """Searches for a song on Spotify and returns its ID and URL."""
    query = f"track:{song} artist:{artist}"
    print(f"[INFO] Searching for: {song} by {artist}...")

    try:
        results = sp.search(q=query, limit=1, type="track")

        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            song_id = track['id']
            song_url = track['external_urls']['spotify']
            print(f"[SUCCESS] Found: {song} (ID: {song_id})\n")
            return song_id, song_url
        else:
            print(f"[WARNING] No results found for: {song} by {artist}\n")
            return None, None
    except Exception as e:
        print(f"[ERROR] API Error while searching for {song}: {e}")
        return None, None

# ✅ Step 5: Get Spotify Info for Each Song
df['spotify_id'] = None
df['spotify_url'] = None
found_count = 0  # Counter for successfully found songs

print("[INFO] Fetching Spotify details for each song...\n")
for index, row in df.iterrows():
    song_name = row['song_name']
    singer = row['singer']

    song_id, song_url = get_spotify_info(song_name, singer)

    df.at[index, 'spotify_id'] = song_id
    df.at[index, 'spotify_url'] = song_url

    if song_id is not None:
        found_count += 1  # Increment count for found songs

print(f"\n[SUCCESS] Spotify data retrieval completed!")
print(f"[INFO] Successfully found Spotify IDs & URLs for {found_count} out of {len(df)} songs.\n")

# ✅ Step 6: Save Updated CSV
output_csv = "csvs/predicated/Telugu_songs_with_spotify_links.csv"
df.to_csv(output_csv, index=False)
print(f"[INFO] Updated CSV saved at: {output_csv}")
