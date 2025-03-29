# Emotion-Based Music Recommendation System

## Overview
This project is an **Emotion-Based Music Recommendation System** that detects user emotions from text and facial expressions and recommends songs accordingly. The system utilizes **Flask** for the web application, **DeepFace** for facial emotion recognition, **TextBlob** for sentiment analysis, and **Spotify API** for fetching song details.

## Features
- **Emotion Detection from Text**: Uses **TextBlob** to analyze sentiment polarity and determine emotions.
- **Facial Emotion Recognition**: Uses **DeepFace** to detect emotions from uploaded face images.
- **Music Recommendation**: Fetches songs from pre-saved CSV datasets based on detected emotions.
- **Spotify Integration**: Retrieves song IDs and URLs from Spotify API for enhanced recommendations.
- **Machine Learning Model for Mood Prediction**: Trains an XGBoost and Random Forest model to classify moods based on song features.

## Technologies Used
- **Backend**: Python, Flask
- **Machine Learning**: Scikit-Learn, XGBoost, RandomForestClassifier
- **Face Emotion Detection**: OpenCV, DeepFace
- **Text Analysis**: TextBlob
- **Data Handling**: Pandas, NumPy
- **Spotify API**: Spotipy (for retrieving song IDs and URLs)

## Project Structure
```
📂 project_root
 ├── app.py                 # Flask web application for emotion detection
 ├── training.py            # ML training script for predicting song moods
 ├── id&url.py              # Spotify API script to fetch song IDs & URLs
 ├── templates/             # HTML templates for the web app
 ├── csvs/                  # Folder containing song datasets
 │   ├── Labeled data/      # Data with labeled moods
 │   ├── Unlabeled data/    # New data to be processed
 │   ├── predicated/        # Output predictions
 │   ├── url_id/            # Song dataset with Spotify URLs
 ├── uploaded_face.jpg      # Temporary storage for uploaded face images
 └── requirements.txt       # Dependencies list
```

## Setup & Installation
### 1️⃣ Clone the Repository
```sh
git clone https://github.com/sumannaidur/Emotion-Based-Music-Recommender.git
cd project_root
```

### 2️⃣ Install Dependencies
```sh
pip install -r requirements.txt
```

### 3️⃣ Run the Flask Application
```sh
python app.py
```
Access the web application at **http://127.0.0.1:5000/**

## Usage Guide
### **🎭 Emotion Detection via Text**
1. Enter text describing your mood.
2. Select the preferred language (Kannada, Telugu, Tamil).
3. Click submit to get a list of recommended songs.

### **📷 Emotion Detection via Face Image**
1. Upload a selfie or face image.
2. Select the preferred language.
3. Click submit to receive song recommendations.

### **🎵 Fetching Spotify IDs & URLs**
1. The script `id&url.py` queries the Spotify API for track IDs and URLs.
2. It uses multiple API credentials to avoid rate limits.
3. Updated results are stored in `updated_Telugu_songs.csv`.

### **📊 Training the Mood Prediction Model**
1. `training.py` loads labeled song data from `csvs/Labeled data/`.
2. Trains an **XGBoost** and **RandomForest** classifier.
3. Predicts moods for new songs and saves results to `csvs/predicated/`.

## API Routes
| Route | Method | Description |
|--------|--------|----------------|
| `/` | GET | Home page with input form |
| `/detect_text` | POST | Detect emotion from user text input |
| `/detect_face` | POST | Detect emotion from uploaded face image |

## Future Enhancements
- **Improve Emotion Detection Accuracy**: Fine-tune models for better precision.
- **Expand Language Support**: Add more regional languages.
- **Enhanced UI/UX**: Make the web app more interactive.
- **Mobile App Integration**: Develop an Android/iOS version.
