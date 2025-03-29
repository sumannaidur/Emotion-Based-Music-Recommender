import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import itertools
import time
from concurrent.futures import ThreadPoolExecutor

# 🔹 Load CSV
csv_file = "csvs/predicated/predicted_Telugu_songs.csv"
df = pd.read_csv(csv_file)

# 🔹 List of multiple Spotify API credentials
SPOTIFY_CREDENTIALS = [
    {"client_id": "15adf67aec934fe792bee0d467742326", "client_secret": "d03b2411aad24b8e80f3257660f9f10f"},
    {"client_id": "241765db513d43218e1e996b7d13d73f", "client_secret": "0fb1d0f0eed44f2e98d0e022335dd9e1"},
    {"client_id": "56bfb61f27234852826fd13e813174e6", "client_secret": "401f40941cba4f5bb2a0274f9fb34df2"}
]

# 🔹 Initialize Spotify Clients
def get_spotify_client(credentials):
    return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=credentials["client_id"],
        client_secret=credentials["client_secret"]
    ))

# 🔹 Divide DataFrame Based on Credentials
num_credentials = len(SPOTIFY_CREDENTIALS)
split_dfs = [df.iloc[i::num_credentials].copy() for i in range(num_credentials)]  # Split into N parts

# 🔹 Fetch Spotify IDs
def get_spotify_id(index, row, sp):
    query = f"{row['song_name']} {row['singer']}"
    try:
        results = sp.search(q=query, type="track", limit=1)
        if results["tracks"]["items"]:
            track = results["tracks"]["items"][0]
            print(f"✅ Found: {query} → {track['id']}")  # Debugging statement
            return index, track["id"], track["external_urls"]["spotify"]
    except Exception as e:
        print(f"⚠️ Error fetching {query}: {e}")
    return index, None, None

# 🔹 Process in Parallel
def process_batch(df_batch, spotify_cred, batch_id):
    sp = get_spotify_client(spotify_cred)
    updated_data = []

    for index, row in df_batch.iterrows():
        song_id, song_url = None, None
        if pd.isna(row.get("spotify_id")):
            index, song_id, song_url = get_spotify_id(index, row, sp)
            df_batch.at[index, "spotify_id"] = song_id
            df_batch.at[index, "spotify_url"] = song_url
        updated_data.append((index, song_id, song_url))
        time.sleep(0.5)  # Avoid rate limits

    # 🔹 Save intermediate results
    batch_filename = f"updated_Telugu_songs_batch_{batch_id}.csv"
    df_batch.to_csv(batch_filename, index=False)
    print(f"📁 Saved batch {batch_id} to {batch_filename}")

    return updated_data

# 🔹 Run Parallel Processing
with ThreadPoolExecutor(max_workers=num_credentials) as executor:
    futures = [executor.submit(process_batch, split_dfs[i], SPOTIFY_CREDENTIALS[i], i) for i in range(num_credentials)]
    results = [future.result() for future in futures]

# 🔹 Combine Updated Data
df_updated = pd.concat(split_dfs)
df_updated.to_csv("updated_Telugu_songs.csv", index=False)
print("✅ All Spotify IDs added and saved to updated_Telugu_songs.csv!")
