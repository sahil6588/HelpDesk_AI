import streamlit as st
import requests
import socket
import os
import platform
import subprocess
import tempfile
from gtts import gTTS
import time
from langdetect import detect
from googletrans import Translator
import cohere
import speech_recognition as sr
import threading
import pygame
import psutil  # To handle app status

# === CONFIGURATION ===
COHERE_API_KEY = "q7OFgUlx90M1UE9JLUb6PNYQVJNxKVNZc2Rz8qiW"
WEATHER_API_KEY = "dcc1fc9f6abb95321eaf45af33685ce0"
co = cohere.Client(COHERE_API_KEY)
translator = Translator()

# === VOICE OUTPUT ===
def speak_text(text):
    try:
        tts = gTTS(text)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_path = fp.name
            tts.save(temp_path)
        pygame.mixer.init()
        pygame.mixer.music.load(temp_path)
        pygame.mixer.music.play()
    except Exception as e:
        st.error(f"Voice playback error: {e}")

# === CONNECTIVITY CHECK ===
def is_connected():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except OSError:
        return False

# === TRANSLATION ===
def translate_text(text, target_lang='en'):
    detected = detect(text)
    if detected != target_lang:
        return translator.translate(text, dest=target_lang).text
    return text

# === WEATHER ===
def fetch_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    res = requests.get(url)
    data = res.json()
    if data.get("cod") != 200:
        return "City not found."
    weather = data['weather'][0]['description']
    temp = data['main']['temp']
    return f"Current weather in {city}: {weather}, {temp}°C"

# === AI Q&A ===
def ask_cohere(prompt):
    try:
        response = co.chat(message=prompt)
        return response.text.strip()
    except Exception as e:
        print("Cohere error:", e)
        return "Sorry, I couldn't get a response."

# === APP CONTROL ===
APPS = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "whatsapp": os.path.expandvars(r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe"),
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "vscode": os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
    "pycharm": r"C:\Program Files\JetBrains\PyCharm Community Edition 2023.3.3\bin\pycharm64.exe"
}

def is_app_running(exe_name):
    for proc in psutil.process_iter(['name']):
        try:
            if exe_name.lower() in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False

def open_app(name):
    name = name.lower()
    if name in ["youtube", "google"]:
        os.system(f"start {APPS[name]}")
        return f"Opening {name} in browser."

    if name in APPS:
        exe_path = APPS[name]
        exe_name = os.path.basename(exe_path)

        if is_app_running(exe_name):
            return f"{name.capitalize()} is already running."

        try:
            subprocess.Popen(exe_path)
            return f"Opening {name}."
        except Exception as e:
            return f"Failed to open {name}: {e}"

    return "App not recognized."

def close_app(name):
    name = name.lower()
    exe_name = f"{name}.exe"

    if not is_app_running(exe_name):
        return f"{name.capitalize()} is not running."

    try:
        os.system(f"taskkill /f /im {exe_name}")
        return f"{name.capitalize()} closed."
    except Exception as e:
        return f"Could not close {name}: {e}"

# === SPEECH RECOGNITION ===
def recognize_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=7)
    try:
        return recognizer.recognize_google(audio)
    except Exception:
        return "Sorry, I couldn't understand that."

# === STREAMLIT UI SETUP ===
st.set_page_config(page_title="Helpdesk AI", layout="centered")

# Custom input & bubble styling
st.markdown("""
<style>
  .stTextInput > div > div > input { font-size:1.2rem; padding:10px; }
  .message-bubble { border-radius:10px; padding:10px 15px; margin:8px 0; }
  .user { background-color:#e1f5fe; text-align:right; }
  .bot  { background-color:#e8f5e9; text-align:left; }
</style>
""", unsafe_allow_html=True)

st.title("🎙️ Helpdesk AI - Voice Assistant")

# === SESSION STATE INITIALIZATION ===
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_command" not in st.session_state:
    st.session_state.last_command = ""

# === SIDEBAR CONTROLS ===
st.sidebar.header("🛠️ Assistant Controls")
if st.sidebar.button("🎤 Speak Now"):
    with st.spinner("Listening..."):
        spoken = recognize_speech()
        st.session_state.user_input = spoken
        st.rerun()

if st.sidebar.button("🗑️ Clear Chat"):
    st.session_state.chat_history = []
    st.session_state.last_command = ""

voice_enabled = st.sidebar.checkbox("🔈 Speak Responses", value=True)
st.sidebar.markdown("---")
st.sidebar.subheader("💡 Tips:")
st.sidebar.markdown("- Try: **weather in Delhi**")
st.sidebar.markdown("- Try: **open YouTube** or **close Notepad**")
st.sidebar.markdown("- Ask any general question!")

# === USER INPUT & PROCESSING ===
user_input = st.text_input("Type your message here:", key="user_input")
if user_input and user_input != st.session_state.last_command:
    st.session_state.last_command = user_input  # prevent duplicates
    user_input = user_input.strip()
    prompt = translate_text(user_input)

    if not is_connected():
        response = "You are offline. Please check your internet connection."
    elif "weather in" in prompt.lower():
        city = prompt.lower().split("weather in")[-1].strip()
        response = fetch_weather(city)
    elif prompt.lower().startswith("open"):
        app = prompt.lower().replace("open", "").strip()
        response = open_app(app)
    elif prompt.lower().startswith("close"):
        app = prompt.lower().replace("close", "").strip()
        response = close_app(app)
    else:
        response = ask_cohere(prompt)

    st.session_state.chat_history.append((user_input, response))
    if voice_enabled:
        threading.Thread(target=speak_text, args=(response,), daemon=True).start()
    st.rerun()

# === CHAT HISTORY DISPLAY ===
st.markdown("---")
st.subheader("💬 Chat History")
for u, b in reversed(st.session_state.chat_history):
    st.markdown(f"<div class='message-bubble user'><strong>You:</strong> {u}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='message-bubble bot'><strong>Assistant:</strong> {b}</div>", unsafe_allow_html=True)

st.markdown("---")
st.caption("🧠 Powered by Cohere + OpenWeather | UI by Streamlit")
