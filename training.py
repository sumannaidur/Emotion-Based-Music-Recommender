import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report
import joblib

# Load your dataset
df = pd.read_csv("data_moods.csv")

# Drop rows with missing or unknown mood
df = df[df["mood"].notna() & (df["mood"] != "unknown")]

# Select feature columns (excluding non-numeric metadata)
feature_cols = [
    "danceability", "acousticness", "energy", "instrumentalness",
    "liveness", "valence", "loudness", "speechiness", "tempo",
    "key", "time_signature"
]
X = df[feature_cols]

# Encode the mood labels
le = LabelEncoder()
y = le.fit_transform(df["mood"])

# Split into training and test sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, stratify=y, test_size=0.2, random_state=42
)

# Train a random forest classifier
clf = RandomForestClassifier(n_estimators=150, random_state=42)
clf.fit(X_train, y_train)

# Evaluate
y_pred = clf.predict(X_test)
print("🎯 Classification Report:\n")
print(classification_report(y_test, y_pred, target_names=le.classes_))

# Save model and label encoder
joblib.dump(clf, "mood_classifier.pkl")
joblib.dump(le, "label_encoder.pkl")
print("✅ Saved mood_classifier.pkl and label_encoder.pkl")
