from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from deepface import DeepFace
from textblob import TextBlob
import os
import pandas as pd
import random
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
app = Flask(__name__)
app.secret_key = "secret123"

# ---------- SQLite DB Connection ----------
def get_db_connection():
    conn = sqlite3.connect('music_project.db')
    conn.row_factory = sqlite3.Row
    return conn

# ---------- Spotify Credentials ----------
SPOTIFY_CLIENT_ID = "15adf67aec934fe792bee0d467742326"
SPOTIFY_CLIENT_SECRET = "d03b2411aad24b8e80f3257660f9f10f"

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

# ---------- Gemini Configuration ----------
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

# ---------- Emotion Detection ----------
def detect_emotion_from_face(image_path):
    try:
        result = DeepFace.analyze(image_path, actions=['emotion'], enforce_detection=False)
        return result[0]['dominant_emotion'].lower()
    except:
        return "neutral"

# ---------- Fetch Songs ----------
def fetch_songs(emotion=None, language=None, base_folder="output"):
    songs = []

    mood_map = {
        "happy": ["happy"],
        "sad": ["sad", "happy"],
        "angry": ["calm"],
        "relaxed": ["calm"],
        "fear": ["calm"],
        "excited": ["energetic"],
        "neutral": ["happy", "sad", "calm", "energetic"]
    }

    languages = [d for d in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, d))]
    if not languages:
        return []

    chosen_language = language if language in languages else random.choice(languages)
    language_path = os.path.join(base_folder, chosen_language)
    years = [y for y in os.listdir(language_path) if os.path.isdir(os.path.join(language_path, y))]
    if not years:
        return []

    chosen_year = random.choice(years)
    csv_path = os.path.join(language_path, chosen_year, "songs.csv")

    if not os.path.exists(csv_path):
        return []

    try:
        df = pd.read_csv(csv_path).dropna(subset=['name', 'id', 'artist'])
        if emotion and 'mood' in df.columns:
            target_moods = mood_map.get(emotion.lower(), [])
            df = df[df['mood'].str.lower().isin([m.lower() for m in target_moods])]
            if df.empty:
                df = pd.read_csv(csv_path).dropna(subset=['name', 'id', 'artist'])

        selected = df.sample(n=min(5, len(df)))
        for _, row in selected.iterrows():
            songs.append({
                "song_name": row['name'],
                "track_id": row['id'],
                "language": chosen_language,
                "year": chosen_year,
                "artist": row['artist']
            })
        return songs

    except Exception as e:
        print(f"Error reading CSV: {e}")
        return []

# ---------- Routes ----------
@app.route('/')
def home():
    session['chat_history'] = []
    session['user_messages'] = []
    session['final_mood_given'] = False
    return render_template("index.html")

@app.route('/chat', methods=['POST'])
def chat():
    user_msg = request.json['message']
    session['chat_history'] = session.get('chat_history', [])
    session['user_messages'] = session.get('user_messages', [])

    session['chat_history'].append(f"User: {user_msg}")
    session['user_messages'].append(user_msg)

    if session.get("final_mood_given", False):
        return jsonify({
            "reply": "Thanks for chatting with me! Refresh the page to start a new session.",
            "mood": session.get("last_mood", "unknown"),
            "final": True
        })

    prompt = (
        "You are a kind and empathetic chatbot having a natural conversation with a human. "
        "Ask thoughtful follow-up questions based on their answers to learn how they feel. "
        "Keep your responses short and conversational.\n"
        "Do not give any mood prediction yet.\n\n"
        + "\n".join(session['chat_history']) +
        "\n\nBot:"
    )

    try:
        response = model.generate_content(prompt)
        bot_reply = response.text.strip()
    except Exception as e:
        return jsonify({"reply": "Oops! Something went wrong.", "mood": None, "final": False})

    session['chat_history'].append(f"Bot: {bot_reply}")

    if len(session['user_messages']) >= 6:
        mood_prompt = (
            "You have been having a conversation with a user. Based on their responses, "
            "what is their current emotional state? Choose ONLY from: happy, sad, angry, relaxed, excited.\n"
            "Respond with ONLY the mood word, nothing else.\n\n"
            + "\n".join(session['chat_history'])
        )

        try:
            mood_response = model.generate_content(mood_prompt)
            mood = mood_response.text.strip().lower()
            if mood not in ["happy", "sad", "angry", "relaxed", "excited"]:
                mood = "happy"

            session['last_mood'] = mood
            session['final_mood_given'] = True

            return jsonify({"reply": bot_reply, "mood": mood, "final": True})
        except:
            return jsonify({"reply": bot_reply, "mood": "happy", "final": True})

    return jsonify({"reply": bot_reply, "mood": None, "final": False})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_input = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user and check_password_hash(user['password'], password_input):
            session['username'] = username
            session['user_id'] = user['id']
            return redirect(url_for('buttons', username=username))
        else:
            return "Invalid username or password."
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            return "Passwords do not match."
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, phone, password) VALUES (?, ?, ?)",
                           (username, phone, hashed_password))
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Username already exists."
        finally:
            cursor.close()
            conn.close()
    return render_template('register.html')

@app.route('/buttons')
def buttons():
    username = request.args.get('username', 'User')
    return render_template('buttons.html', username=username)

@app.route('/text_input')
def text_input():
    return render_template('text.html')

@app.route('/face_input')
def face_input():
    return render_template('face.html')

@app.route('/voice_input')
def voice_input():
    return render_template('voice.html')

@app.route('/set_language', methods=['POST'])
def set_language():
    selected_language = request.form.get('language')
    if selected_language:
        session['language'] = selected_language
    return redirect(url_for('buttons'))

@app.route("/reset_chat", methods=["POST"])
def reset_chat():
    session.pop("conversation", None)
    return jsonify({"status": "reset"})

@app.route('/final_mood/<mood>')
def final_mood(mood):
    language = session.get('language')
    songs = fetch_songs(mood, language=language)
    for key in ['chat_history', 'user_messages', 'final_mood_given', 'last_mood']:
        session.pop(key, None)
    return render_template('resulting.html', emotion=mood, songs=songs)

@app.route("/reset_session", methods=["POST"])
def reset_session():
    username = session.get('username')
    user_id = session.get('user_id')
    language = session.get('language')
    session.clear()
    if username: session['username'] = username
    if user_id: session['user_id'] = user_id
    if language: session['language'] = language
    return jsonify({"status": "ok"})

@app.route('/detect_face', methods=['POST'])
def detect_face():
    file = request.files['file']
    image_path = "uploaded_face.jpg"
    file.save(image_path)
    emotion = detect_emotion_from_face(image_path)
    language = session.get('language')
    songs = fetch_songs(emotion, language=language)
    return render_template('resulting.html', emotion=emotion, songs=songs)

@app.route('/save_feedback', methods=['POST'])
def save_feedback():
    song_name = request.form['song_name']
    user_feedback = request.form['feedback']
    emotion = request.form['emotion']

    if 'username' not in session:
        return "User not logged in."

    username = session['username']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()

    if user:
        user_id = user['id']
        cursor.execute("INSERT INTO feedback (song_name, user_id, emotion, feedback) VALUES (?, ?, ?, ?)",
                       (song_name, user_id, emotion, user_feedback))
        conn.commit()
        cursor.close()
        conn.close()
        return "Feedback submitted successfully."
    else:
        cursor.close()
        conn.close()
        return "User not found."

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
