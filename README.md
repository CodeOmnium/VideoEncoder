# Telegram Video Compressor Bot

A simple yet powerful Telegram bot that compresses videos sent by users to a more manageable 360p resolution. It's designed to be easy to deploy and use.

## Features

- **Video Compression:** Automatically compresses uploaded videos to 360p using FFmpeg.
- **Progress Updates:** Provides real-time feedback to the user on the status of their download, compression, and upload.
- **Large File Support:** Built to handle large video files, with progress callbacks for both downloading and uploading.
- **Easy to Deploy:** Can be run locally for testing or deployed to any server with Python and FFmpeg support.
- **Secure:** Keeps your API keys and tokens safe using a `.env` file.

## How It Works

1.  A user sends a video file to the bot.
2.  The bot downloads the video to a local `downloads/` directory.
3.  It then uses **FFmpeg** to compress the video, saving the new file to a `processed/` directory.
4.  Finally, the bot uploads the compressed video back to the user.
5.  Temporary files are cleaned up to save disk space.

## Installation & Running

Follow these steps to run the bot on your local machine.

### 1. Prerequisites

- **Python 3.8+**
- **FFmpeg:** You must have FFmpeg installed and accessible in your system's PATH.
  - **Windows:** Follow the [official guide](https://www.gyan.dev/ffmpeg/builds/) to download and add FFmpeg to your PATH.
  - **Linux (Debian/Ubuntu):** `sudo apt update && sudo apt install ffmpeg`
  - **macOS (using Homebrew):** `brew install ffmpeg`

### 2. Clone & Set Up the Project

```bash
# Clone this repository (or download the source)
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name

# Create and activate a Python virtual environment
python -m venv venv
# On Windows
.\venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate

# Install the required dependencies
pip install -r requirements.txt
```

### 3. Configure Your Credentials

1.  **Get API Credentials:**
    - **API ID & Hash:** Log in to [my.telegram.org](https://my.telegram.org) to get your `api_id` and `api_hash`.
    - **Bot Token:** Create a new bot by talking to [@BotFather](https://t.me/BotFather) on Telegram to get your `TELEGRAM_BOT_TOKEN`.

2.  **Create the `.env` file:**
    - Rename the `.env.example` file (if you have one) or create a new file named `.env`.
    - Add your credentials to it like this:

    ```env
    TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN_HERE"
    API_ID="YOUR_API_ID_HERE"
    API_HASH="YOUR_API_HASH_HERE"
    ```

### 4. Run the Bot

With your virtual environment activated, start the bot:

```bash
python main.py
```

Your bot is now running! Send it a video on Telegram to test it out.
