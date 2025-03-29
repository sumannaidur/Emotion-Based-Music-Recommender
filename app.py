from flask import Flask, render_template, request
import pandas as pd
from textblob import TextBlob
import cv2
from deepface import DeepFace

app = Flask(__name__)

# 🔹 Load pre-saved song datasets
kannada_songs = pd.read_csv("csvs/url_id/updated_Kannada_songs.csv")
telugu_songs = pd.read_csv("csvs/url_id/updated_Telugu_songs.csv")
tamil_songs = pd.read_csv("csvs/url_id/updated_Tamil_songs.csv")

# 🔹 Emotion Mapping
emotion_map = {
    "happy": ["Happy", "Energetic"],
    "sad": ["Sad"],
    "angry": ["Angry"],
    "relaxed": ["Relaxed"],
    "excited": ["Energetic"]
}

# 🔹 Fetch Songs from CSV based on Emotion & Language
def fetch_songs(emotion, language):
    if language == "Kannada":
        df = kannada_songs
    elif language == "Telugu":
        df = telugu_songs
    else:
        df = tamil_songs
    
    matched_moods = emotion_map.get(emotion, ["Happy"])  # Default to "Happy"
    songs_data = df[df["predicted_mood"].isin(matched_moods)].sample(n=min(10, len(df)))  # Pick 10 random songs

    return songs_data.to_dict(orient="records")

# 🔹 Detect emotion from text input
def detect_emotion_from_text(text):
    analysis = TextBlob(text).sentiment.polarity
    if analysis > 0.5:
        return "happy"
    elif 0 < analysis <= 0.5:
        return "excited"
    elif -0.5 <= analysis < 0:
        return "sad"
    elif analysis < -0.5:
        return "angry"
    else:
        return "relaxed"

# 🔹 Detect emotion from face image
def detect_emotion_from_face(image_path):
    try:
        result = DeepFace.analyze(image_path, actions=['emotion'])
        return result[0]['dominant_emotion'].lower()
    except:
        return "neutral"

# 🔹 Flask Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/detect_text', methods=['POST'])
def detect_text():
    text = request.form['text']
    language = request.form['language']  # Get selected language
    emotion = detect_emotion_from_text(text)
    songs = fetch_songs(emotion, language)
    return render_template('index.html', emotion=emotion, songs=songs, selected_language=language)

@app.route('/detect_face', methods=['POST'])
def detect_face():
    file = request.files['file']
    language = request.form['language']  # Get selected language
    file_path = "uploaded_face.jpg"
    file.save(file_path)
    
    emotion = detect_emotion_from_face(file_path)
    songs = fetch_songs(emotion, language)
    return render_template('index.html', emotion=emotion, songs=songs, selected_language=language)

if __name__ == '__main__':
    app.run(debug=True)
