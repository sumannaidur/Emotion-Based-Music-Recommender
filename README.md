# 🎧 Emotion-Based Music Recommender

An AI-powered web application that detects user **mood** via **text or voice input** and recommends personalized songs using **Spotify**, **YouTube**, and **lyrics analysis**.

---
## 🎬 Demo

[![Demo Video](media/preview_thumbnail.png)](media/demo.mp4")

Click the image to watch the demo.
---

## 🔍 Overview

This project intelligently recommends music based on a user's emotional state. It leverages:
- **Gemini AI** for emotion detection (text/voice)
- **Spotify and YouTube APIs** for music discovery
- **Genius/Gemini fallback** for lyrics analysis
- **Librosa** for audio feature extraction
- **SQLite** for lightweight local storage

---

## 🚀 Features

- 🎤 **Dual-mode mood input** (Text + Voice)
- 🤖 **Gemini-powered mood analysis**
- 🎶 **Real-time music suggestions**
- 🧠 **Fallback lyrics + mood extraction via Gemini**
- 📊 **Tempo & key analysis with Librosa**
- 💾 **Database storage using SQLite**

---

## 🛠️ Tech Stack

| Category     | Tools/APIs                              |
|--------------|----------------------------------------|
| Language     | Python 3.x                             |
| Backend      | Flask                                  |
| AI/ML        | Google Gemini, Librosa                 |
| APIs         | Spotify, YouTube Data API, Genius      |
| Frontend     | HTML5, CSS3, JavaScript (Basic)        |
| Database     | SQLite                                 |

---

## ⚙️ Setup Instructions

### 🔐 1. Clone the Repository
```bash
git clone https://github.com/sumannaidur/Emotion-Based-Music-Recommender.git
cd Emotion-Based-Music-Recommender
```

### 🧪 2. Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate
```

### 📦 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 🔑 4. Set Up API Keys
Create a `.env` file in the root directory with the following variables:
```env
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
YOUTUBE_API_KEY=your_youtube_api_key
GEMINI_API_KEY_1=your_gemini_key
GEMINI_API_KEY_2=optional_secondary
GEMINI_API_KEY_3=optional_tertiary
```

> **Note:** Use dotenv to securely load environment variables.

### ▶️ 5. Run the App
```bash
python app.py
```
Visit: [http://localhost:5000](http://localhost:5000)

---

## 🎯 How It Works

1. **Mood Detection**: User inputs mood via text or voice
2. **AI Analysis**: Gemini AI processes and categorizes emotions
3. **Music Matching**: System searches Spotify/YouTube for mood-appropriate songs
4. **Lyrics Analysis**: Fallback system analyzes song lyrics for emotional context
5. **Audio Features**: Librosa extracts tempo, key, and other musical characteristics
6. **Recommendation**: Personalized playlist generated based on detected mood

---

## 🔧 API Requirements

To run this project, you'll need API keys from:

- **Spotify for Developers** - Music streaming and metadata
- **YouTube Data API** - Video content and metadata
- **Google Gemini API** - AI-powered emotion detection
- **Genius API** - Lyrics fetching and analysis

---

## 📚 Acknowledgements

- [Google Gemini API](https://ai.google.dev/)
- [Spotify for Developers](https://developer.spotify.com/)
- [YouTube Data API](https://developers.google.com/youtube/v3)
- [Librosa](https://librosa.org/)
- [Genius API](https://docs.genius.com/)
- [Flask Framework](https://flask.palletsprojects.com/)

---

## 👨‍💻 Developed By

**Suman Naidu R**, **Yashaswini N P**, **Divya L**

B.E. (Information Science), APS College of Engineering[2021-2025]

---

## 🙋‍♂️ Contributing

Contributions are welcome! For major changes, please open an issue first to discuss what you'd like to change.

1. Fork the Project
2. Create your Feature Branch 
3. Commit your Changes 
4. Push to the Branch 
5. Open a Pull Request

---

**⭐ If you found this project helpful, please consider giving it a star!**
