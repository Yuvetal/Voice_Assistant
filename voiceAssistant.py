import speech_recognition as sr
import pyttsx3
import datetime
import requests
import os
import time
import threading
import random
import webbrowser
import json

# Initialize recognizer and TTS engine
recognizer = sr.Recognizer()
tts_engine = pyttsx3.init()

waiting_for_city = False
waiting_for_reminder_message = False
waiting_for_reminder_time = False
temp_reminder_message = ""
reminders = []

REMINDER_FILE = "reminders.json"

# Available commands
COMMANDS = {
    "weather": "Get current weather for a city",
    "news": "Read top news headlines",
    "time": "Tell the current time",
    "date": "Tell today's date",
    "reminder": "Set a reminder",
    "play music": "Play a random music file",
    "tell a joke": "Tell a random joke",
    "help": "List all available commands",
    "exit": "Stop the assistant"
}

JOKES = [
    "Why don't scientists trust atoms? Because they make up everything!",
    "Why did the computer go to therapy? It had too many bytes of emotional baggage.",
    "Why do programmers prefer dark mode? Because light attracts bugs!"
]

def speak(text):
    print(f"🗣️ Assistant: {text}")
    tts_engine.say(text)
    tts_engine.runAndWait()
    time.sleep(0.3)

def listen():
    with sr.Microphone() as source:
        print("🎤 Listening for wake word...")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=7)
            command = recognizer.recognize_google(audio).lower()
            print(f"You said: {command}")
            if "hey assistant" in command:
                speak("Yes, I'm listening.")
                print("🎤 Listening for command...")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=7)
                command = recognizer.recognize_google(audio).lower()
                print(f"Command: {command}")
                return command
        except sr.UnknownValueError:
            pass
        except sr.RequestError:
            speak("There was a problem with the speech service.")
        except Exception as e:
            print("Error:", e)
        return ""

def handle_command(command):
    global waiting_for_city, waiting_for_reminder_message, waiting_for_reminder_time, temp_reminder_message

    if waiting_for_city:
        get_weather(command)
        waiting_for_city = False
        return

    if waiting_for_reminder_message:
        temp_reminder_message = command
        speak("When should I remind you?")
        waiting_for_reminder_message = False
        waiting_for_reminder_time = True
        return

    if waiting_for_reminder_time:
        set_reminder(temp_reminder_message, command)
        waiting_for_reminder_time = False
        return

    if any(word in command for word in ["help", "commands", "options"]):
        speak("Here are the available commands:")
        for cmd, desc in COMMANDS.items():
            speak(f"{cmd}: {desc}")

    elif any(word in command for word in ["time", "clock"]):
        now = datetime.datetime.now().strftime("%I:%M %p")
        speak(f"The current time is {now}")

    elif any(word in command for word in ["date", "day", "today"]):
        today = datetime.date.today().strftime("%B %d, %Y")
        speak(f"Today's date is {today}")

    elif any(word in command for word in ["weather", "temperature", "humidity"]):
        speak("Which city do you want the weather for?")
        waiting_for_city = True

    elif "news" in command:
        get_news()

    elif "reminder" in command:
        speak("What should I remind you about?")
        waiting_for_reminder_message = True

    elif "play music" in command:
        play_music()

    elif "tell a joke" in command:
        tell_joke()

    elif any(word in command for word in ["exit", "stop", "quit"]):
        speak("Goodbye!")
        return "exit"

    else:
        speak("I didn't recognize that command. Let me search it on Google.")
        webbrowser.open(f"https://www.google.com/search?q={command}")

def parse_time_input(time_input):
    words = time_input.split()
    if "in" in words:
        try:
            value = int(words[1])
            unit = words[2]
            if "second" in unit:
                return value
            elif "minute" in unit:
                return value * 60
            elif "hour" in unit:
                return value * 3600
        except:
            return None
    if "at" in words:
        try:
            target_time = datetime.datetime.strptime(words[1] + " " + words[2], "%I %p").time()
            now = datetime.datetime.now()
            target_datetime = datetime.datetime.combine(now.date(), target_time)
            if target_datetime < now:
                target_datetime += datetime.timedelta(days=1)
            return (target_datetime - now).seconds
        except:
            return None
    return None

def save_reminders():
    with open(REMINDER_FILE, "w") as f:
        json.dump(reminders, f)

def load_reminders():
    global reminders
    if os.path.exists(REMINDER_FILE):
        with open(REMINDER_FILE, "r") as f:
            try:
                reminders = json.load(f)
                now = datetime.datetime.now()
                for message, time_input in reminders:
                    delay = parse_time_input(time_input)
                    if delay is not None:
                        threading.Timer(delay, lambda m=message: speak(f"⏰ Reminder: {m}")).start()
            except:
                reminders = []

def set_reminder(message, time_input):
    delay = parse_time_input(time_input)
    if delay is None:
        speak("Sorry, I couldn't understand the time. Try saying 'in 2 minutes' or 'at 5 pm'.")
        return

    reminders.append((message, time_input))
    save_reminders()
    speak(f"Reminder set: {message}, {time_input}")
    threading.Timer(delay, lambda: speak(f"⏰ Reminder: {message}")).start()

def get_weather(city):
    api_key = "e3a8c3385793201fad0619b5c688c03b"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"

    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if data.get("cod") != 200:
            speak(f"Sorry, I couldn't find weather info for {city}.")
            return
        weather = data["weather"][0]["description"]
        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        speak(f"The weather in {city} is {weather} with a temperature of {temp}°C and humidity of {humidity}%.")
    except Exception as e:
        speak("Sorry, I couldn't fetch the weather right now.")
        print("Error:", e)

def get_news():
    api_key = "79ff012b792c411994c02071985b741a"
    url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={api_key}"

    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if data.get("status") != "ok":
            speak("Sorry, I couldn't fetch the news.")
            return
        articles = data["articles"][:5]
        speak("Here are the top news headlines:")
        for article in articles:
            speak(article["title"])
    except Exception as e:
        speak("Sorry, I couldn't fetch the news right now.")
        print("Error:", e)

def play_music():
    music_folder = "music"
    if not os.path.exists(music_folder):
        speak("Music folder not found.")
        return
    files = [f for f in os.listdir(music_folder) if f.endswith((".mp3", ".wav"))]
    if not files:
        speak("No music files found.")
        return
    song = random.choice(files)
    speak(f"Playing {song}")
    os.startfile(os.path.join(music_folder, song))

def tell_joke():
    joke = random.choice(JOKES)
    speak(joke)

# Main loop
load_reminders()
while True:
    user_command = listen()
    if user_command:
        result = handle_command(user_command)
        if result == "exit":
            break
