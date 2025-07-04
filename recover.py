import os
import asyncio
from dotenv import load_dotenv
from telegram.ext import Application
from telethon import TelegramClient

# Import the functions and variables we need from the main script
from main import (
    compress_video,
    upload_video,
    sanitize_filename,  # <-- Import the sanitizer
    TELEGRAM_BOT_TOKEN,
    API_ID,
    API_HASH,
    DOWNLOAD_PATH,
    PROCESSED_PATH
)

# --- ⚠️ USER CONFIGURATION - YOU MUST FILL THESE OUT ⚠️ ---

# 1. The ID of the chat where the bot should send the file and messages.
#    To get this, you can use a bot like @userinfobot.
CHAT_ID = 0  # <--- ❗️❗️❗️ REPLACE 0 WITH YOUR CHAT ID ❗️❗️❗️

# 2. The exact, full name of the video file that is in the 'downloads' folder.
#    This should be the ORIGINAL filename, before sanitization.
FILE_NAME = ""  # <--- ❗️❗️❗️ REPLACE "" WITH THE FILENAME (e.g., "my_large_video.mp4") ❗️❗️❗️

# --------------------------------------------------------------------

class MockContext:
    """A simple class to mock the parts of the context object our functions need."""
    def __init__(self, application):
        self.bot = application.bot
        self.bot_data = application.bot_data

async def main():
    """The main recovery function."""
    if not all([CHAT_ID, FILE_NAME]):
        print("❌ Error: Please fill out all the required variables (CHAT_ID, FILE_NAME) in the recover.py script before running.")
        return

    # --- Setup ---
    # Apply the same robust timeout settings as the main bot
    telethon_client = TelegramClient(
        'bot_session', 
        API_ID, 
        API_HASH,
        connection_retries=5,
        timeout=86400  # 24 hours
    )
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .connect_timeout(86400.0)
        .read_timeout(86400.0)
        .build()
    )
    application.bot_data['telethon_client'] = telethon_client
    context = MockContext(application)

    # Sanitize the filename to match the name on disk
    # This ensures the recovery script finds the file saved by the main bot
    safe_filename = sanitize_filename(FILE_NAME)
    input_path = os.path.join(DOWNLOAD_PATH, safe_filename)
    output_path = os.path.join(PROCESSED_PATH, f"processed_{safe_filename}")
    status_message = None

    # --- Run Recovery ---
    async with telethon_client:
        print(f"🚀 Starting recovery process for: {safe_filename}")
        if not os.path.exists(input_path):
            print(f"❌ Error: File not found at {input_path}. Make sure the original FILE_NAME in the script is correct.")
            return
        
        try:
            # Send a new message to use for status updates
            status_message = await context.bot.send_message(
                chat_id=CHAT_ID,
                text=f"Recovering interrupted file: {FILE_NAME}"
            )
            message_id = status_message.message_id

            # 1. Compress the existing video
            await compress_video(context, CHAT_ID, message_id, input_path, output_path)

            # 2. Upload the compressed video
            await upload_video(context, CHAT_ID, message_id, output_path)

            print("✅ Recovery complete!")

        except Exception as e:
            print(f"An error occurred during recovery: {e}")
            # Try to update the status message with the error
            if status_message:
                try:
                    await context.bot.edit_message_text(
                        chat_id=CHAT_ID,
                        message_id=status_message.message_id,
                        text=f"An error occurred during recovery: {e}"
                    )
                except Exception:
                    pass
        finally:
            # 3. Cleanup
            print("🧹 Cleaning up files...")
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)
            # Delete the status message we created
            if status_message:
                try:
                    await context.bot.delete_message(chat_id=CHAT_ID, message_id=status_message.message_id)
                except Exception:
                    pass

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())