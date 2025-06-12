import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import LabelEncoder

# ✅ Paths
TRAINING_FILE = "csvs/Labeled data/data_moods.csv"
PREDICTION_FOLDER = "csvs/Unlabeled data/"
OUTPUT_FOLDER = "csvs/predicated/"

# ✅ Load training data
print("Loading training data...")
df_labeled = pd.read_csv(TRAINING_FILE)

# ✅ Features
features = ['popularity', 'danceability', 'duration', 'energy', 'instrumentalness', 
            'key', 'liveliness', 'loudness', 'mode', 'speechiness', 'tempo', 
            'time_signature', 'valence']

metadata_cols = ['song_name', 'singer', 'singer_id', 'language', 'released_date']

# ✅ Fix missing features
missing_features = [f for f in features if f not in df_labeled.columns]
if missing_features:
    print(f"Warning: Missing features in dataset: {missing_features}")
    for col in missing_features:
        df_labeled[col] = 0

# ✅ Convert all features to numeric
for col in features:
    df_labeled[col] = pd.to_numeric(df_labeled[col], errors='coerce').fillna(0)

# ✅ Extract features and labels
X = df_labeled[features]
y = df_labeled['mood']

# ✅ Encode mood labels
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

# ✅ Train-Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)

# ✅ Models
rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
xgb_model = xgb.XGBClassifier(use_label_encoder=False, eval_metric='mlogloss')

# ✅ Train Models
print("Training Random Forest model...")
rf_model.fit(X_train, y_train)

print("Training XGBoost model...")
xgb_model.fit(X_train, y_train)

# ✅ Evaluate
rf_pred = rf_model.predict(X_test)
xgb_pred = xgb_model.predict(X_test)

print("\nRandom Forest Accuracy:", accuracy_score(y_test, rf_pred))
print("XGBoost Accuracy:", accuracy_score(y_test, xgb_pred))
print("\nClassification Report (Random Forest):\n", classification_report(y_test, rf_pred))
print("\nClassification Report (XGBoost):\n", classification_report(y_test, xgb_pred))

# ✅ Process multiple files
print("\nProcessing files in:", PREDICTION_FOLDER)
for file_name in os.listdir(PREDICTION_FOLDER):
    if file_name.endswith(".csv"):
        file_path = os.path.join(PREDICTION_FOLDER, file_name)
        print(f"\nLoading file: {file_path}")

        df_unlabeled = pd.read_csv(file_path)

        # ✅ Fix missing features
        available_features = [col for col in features if col in df_unlabeled.columns]
        missing_features = [f for f in features if f not in df_unlabeled.columns]
        if missing_features:
            print(f"Warning: {missing_features} missing in {file_name}, filling with 0")
            for col in missing_features:
                df_unlabeled[col] = 0

        # ✅ Convert all features to numeric
        for col in features:
            df_unlabeled[col] = pd.to_numeric(df_unlabeled[col], errors='coerce').fillna(0)

        # ✅ Debugging: Print column types
        print("\nFeature types before prediction:")
        print(df_unlabeled[features].dtypes)

        # ✅ Predict moods
        df_unlabeled['predicted_mood'] = label_encoder.inverse_transform(
            xgb_model.predict(df_unlabeled[features])
        )

        # ✅ Ensure metadata columns exist
        for col in metadata_cols:
            if col not in df_unlabeled.columns:
                df_unlabeled[col] = "Unknown"

        # ✅ Sort by release date if available
        if 'released_date' in df_unlabeled.columns:
            df_unlabeled['released_date'] = pd.to_datetime(df_unlabeled['released_date'], errors='coerce')
            df_unlabeled = df_unlabeled.sort_values(by='released_date', ascending=True)
        else:
            print("Warning: 'released_date' column not found. Skipping sorting.")

        # ✅ Save the results
        output_file = os.path.join(OUTPUT_FOLDER, f"predicted_{file_name}")
        df_unlabeled.to_csv(output_file, index=False)
        print(f"Predictions saved to: {output_file}")

print("\n✅ All files processed successfully!")
