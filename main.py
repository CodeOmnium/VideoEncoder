
import os
import time
import asyncio
import ffmpeg
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telethon import TelegramClient
from telethon.tl.types import DocumentAttributeVideo
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
if API_ID == 0:
    raise ValueError("API_ID environment variable is required")
if not API_HASH:
    raise ValueError("API_HASH environment variable is required")

DOWNLOAD_PATH = "downloads/"
PROCESSED_PATH = "processed/"
DOWNLOAD_CHUNK_SIZE = 16 * 1024  # 16 KB
PROGRESS_UPDATE_INTERVAL = 15  # seconds
HTTPX_TIMEOUT = 300  # seconds (5 minutes) - increased for large files

# --- Helper Functions ---
def format_bytes(size):
    """Converts bytes to a human-readable format."""
    if size == 0:
        return "0B"
    power = 1024
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size >= power and n < len(power_labels) -1:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"

async def send_progress_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, start_time: float, current_size: int, total_size: int, action: str):
    """Sends or edits a progress message."""
    elapsed_time = time.time() - start_time
    speed = current_size / elapsed_time if elapsed_time > 0 else 0
    progress = (current_size / total_size) * 100 if total_size > 0 else 0
    
    message = (
        f"**{action}**\n"
        f"Progress: {progress:.1f}%\n"
        f"[{'█' * int(progress // 5)}{' ' * (20 - int(progress // 5))}]\n"
        f"{format_bytes(current_size)} / {format_bytes(total_size)}\n"
        f"Speed: {format_bytes(speed)}/s\n"
        f"Elapsed: {elapsed_time:.2f}s"
    )
    
    try:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=message)
    except Exception:
        pass # Ignore if message not found or not modified

async def update_progress_periodically(context, chat_id, message_id, start_time, get_current_size, total_size, action):
    """Periodically updates the progress message."""
    while True:
        current_size = get_current_size()
        await send_progress_message(context, chat_id, message_id, start_time, current_size, total_size, action)
        await asyncio.sleep(PROGRESS_UPDATE_INTERVAL)

# --- Core Logic ---

async def download_video(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, telethon_message, file_path: str):
    """Downloads a video using Telethon with progress updates."""
    await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Starting download...")
    start_time = time.time()
    
    telethon_client = context.bot_data['telethon_client']
    total_size = telethon_message.file.size

    async def progress_callback(current_bytes, total_bytes):
        await send_progress_message(context, chat_id, message_id, start_time, current_bytes, total_bytes, "Downloading")

    await telethon_client.download_media(telethon_message.media, file=file_path, progress_callback=progress_callback)
    
    await send_progress_message(context, chat_id, message_id, start_time, total_size, total_size, "Download Complete")

async def compress_video(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, input_path: str, output_path: str):
    """Compresses a video using FFmpeg."""
    await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Compressing video... This is CPU-intensive and may take a while on a free server.")
    
    try:
        (
            ffmpeg
            .input(input_path)
            .output(output_path, vf='scale=-2:360', vcodec='libx264', preset='ultrafast', crf=30, acodec='aac', strict='experimental', pix_fmt='yuv420p')
            .run(overwrite_output=True)
        )
    except ffmpeg.Error as e:
        # Log the full error to the console for debugging
        stderr = e.stderr.decode() if e.stderr else "No stderr output from FFmpeg."
        print(f"FFmpeg error:\n{stderr}")
        error_message = f"Error processing video. The server might be out of resources for a file this large."
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=error_message)
        raise

    await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Processing complete.")

async def upload_video(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, file_path: str):
    """Uploads a video to the chat using Telethon."""
    await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Starting upload...")

    telethon_client = context.bot_data['telethon_client']
    
    # Get file size for progress updates
    file_size = os.path.getsize(file_path)
    start_time = time.time()

    async def progress_callback(current_bytes, total_bytes):
        await send_progress_message(context, chat_id, message_id, start_time, current_bytes, total_bytes, "Uploading")

    await telethon_client.send_file(chat_id, file_path, progress_callback=progress_callback, attributes=[DocumentAttributeVideo(duration=0, w=0, h=0, supports_streaming=True)])
        
    await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Upload Complete!")


# --- Command & Message Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message."""
    await update.message.reply_text(
        "Hi! I'm a video compressor bot.\n\n"
        "Send me a video, and I'll compress it to 360p for you."
    )

import re

# ... (rest of the imports)

def sanitize_filename(filename):
    """Removes special characters from a filename to make it safe for shell commands."""
    # Remove invalid characters
    sanitized = re.sub(r'[\/*?:"<>|&]', "", filename)
    # Replace spaces with underscores
    sanitized = re.sub(r'\s+', '_', sanitized)
    return sanitized

# ... (rest of the code)

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """The main handler for receiving and processing videos."""
    chat_id = update.message.chat_id
    status_message = await update.message.reply_text("Initializing...")
    message_id = status_message.message_id

    telethon_client = context.bot_data['telethon_client']
    telethon_message = await telethon_client.get_messages(chat_id, ids=update.message.message_id)

    if not telethon_message or not telethon_message.file:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Sorry, I couldn't retrieve the file from this message.")
        return

    # Sanitize the filename to prevent errors
    original_filename = telethon_message.file.name
    safe_filename = sanitize_filename(original_filename)
    
    input_path = os.path.join(DOWNLOAD_PATH, safe_filename)
    output_path = os.path.join(PROCESSED_PATH, f"processed_{safe_filename}")

    try:
        os.makedirs(DOWNLOAD_PATH, exist_ok=True)
        os.makedirs(PROCESSED_PATH, exist_ok=True)

        await download_video(context, chat_id, message_id, telethon_message, input_path)
        await compress_video(context, chat_id, message_id, input_path, output_path)
        await upload_video(context, chat_id, message_id, output_path)


    except Exception as e:
        print(f"An error occurred: {e}")
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"An unexpected error occurred. Please try again later.")
    finally:
        # --- Cleanup ---
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass

async def handle_other_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles non-video messages."""
    await update.message.reply_text("Please send me a video file to compress.")

def main() -> None:
    """Start the bot."""
    print("Starting bot...")

    # Initialize Telethon client
    telethon_client = TelegramClient('bot_session', API_ID, API_HASH)

    # Build the application
    application_builder = Application.builder().token(TELEGRAM_BOT_TOKEN)
    application_builder.http_version("1.1").get_updates_http_version("1.1")
    application = application_builder.build()

    # Pass telethon_client to context
    application.bot_data['telethon_client'] = telethon_client

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_other_messages))

    # Start the bot
    # The 'with' block will automatically log in the bot using the bot token
    # This is crucial for non-interactive environments like Render
    with telethon_client:
        print("Telethon client started.")
        application.run_polling()

from flask import Flask
from threading import Thread

# ... (imports)

# --- Keep-Alive Web Server ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is alive!"

def run_web_server():
    # Render provides the PORT environment variable
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ... (rest of the code)

if __name__ == "__main__":
    
    # Start the keep-alive web server in a separate thread
    keep_alive_thread = Thread(target=run_web_server)
    keep_alive_thread.daemon = True
    keep_alive_thread.start()
    print("Keep-alive server started.")

    async def main():
        # ... (rest of the main async function remains the same)
        
        # Initialize Telethon client and start it
        telethon_client = TelegramClient('bot_session', API_ID, API_HASH)
        await telethon_client.start(bot_token=TELEGRAM_BOT_TOKEN)
        print("Telethon client started.")

        # Build the python-telegram-bot application
        # Set high timeouts to prevent issues on slow networks or with large files
        application = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .http_version("1.1")
            .get_updates_http_version("1.1")
            .connect_timeout(3600.0)
            .read_timeout(3600.0)
            .write_timeout(3600.0)
            .pool_timeout(3600.0)
            .get_updates_read_timeout(3600.0)
            .get_updates_connect_timeout(3600.0)
            .build()
        )

        # Add the Telethon client to the bot's context data
        application.bot_data['telethon_client'] = telethon_client

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.VIDEO, handle_video))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_other_messages))
        
        # Run the bot until the user presses Ctrl-C
        print("Starting bot polling...")
        async with application:
            await application.initialize()
            await application.start()
            await application.updater.start_polling()
            
            # Keep the script running until it's stopped
            while True:
                await asyncio.sleep(3600)

    # Run the main async function
    asyncio.run(main())
