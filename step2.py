import pandas as pd
import os
import csv

INPUT_FOLDER = 'movies_by_language'  # Folder containing original full CSVs
OUTPUT_FOLDER = 'movie_csvs'           # Folder to save filtered output
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def filter_and_split_by_year(language_csv):
    print(f"\n📂 Processing: {language_csv}")
    lang_name = language_csv.replace('_movies.csv', '')
    lang_folder = os.path.join(OUTPUT_FOLDER, lang_name)
    os.makedirs(lang_folder, exist_ok=True)

    input_path = os.path.join(INPUT_FOLDER, language_csv)
    
    try:
        # Tolerant read: skips malformed rows
        df = pd.read_csv(input_path, engine='python', on_bad_lines='skip', quoting=csv.QUOTE_MINIMAL)
        print(f"📊 Loaded {len(df)} rows from {language_csv}")
    except Exception as e:
        print(f"❌ Could not read {language_csv}: {e}")
        return

    # Clean up missing values in important columns
    df['Hero'] = df['Hero'].fillna("").astype(str).str.strip()
    df['Heroine'] = df['Heroine'].fillna("").astype(str).str.strip()
    df['Music Director'] = df['Music Director'].fillna("").astype(str).str.strip()
    df['Release Date'] = pd.to_datetime(df['Release Date'], errors='coerce')

    # Filter for rows where all 3 are available
    filtered_df = df[(df['Hero'] != "") & (df['Heroine'] != "") & (df['Music Director'] != "")]
    print(f"✅ Found {len(filtered_df)} movies with complete Hero, Heroine, and Music Director")

    # Drop rows without a valid release date
    filtered_df = filtered_df.dropna(subset=["Release Date"])
    filtered_df['Year'] = filtered_df['Release Date'].dt.year

    # Split and save by year
    for year, group in filtered_df.groupby('Year'):
        output_path = os.path.join(lang_folder, f"{year}_filtered.csv")
        group.drop(columns=["Year"]).to_csv(output_path, index=False)
        print(f"📁 Saved {len(group)} movies for year {year} → {output_path}")

# Run filtering for all CSVs in the input folder
for file in os.listdir(INPUT_FOLDER):
    if file.endswith('_movies.csv'):
        filter_and_split_by_year(file)

print("\n🎉 All filtered and year-wise CSVs saved successfully.")
