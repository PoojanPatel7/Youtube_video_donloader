# ☠ YT-BREACH — YouTube Video Downloader

A powerful YouTube video downloader with a hacker-themed UI built with Python and CustomTkinter.

![Python](https://img.shields.io/badge/Python-3.8+-green?style=flat-square&logo=python)
![License](https://img.shields.io/badge/License-MIT-brightgreen?style=flat-square)

## Features

- 🎬 Download YouTube videos in all available qualities (144p to 4K)
- 🎵 Download audio-only (M4A, MP3, WebM)
- 💾 Real-time drive storage display for selected download location
- 📊 Accurate download progress with speed, ETA, and elapsed time
- 🖥️ Hacker/cyber-breach themed terminal UI
- ⚡ Boot sequence animation on startup
- 🔄 Multiple YouTube API client fallbacks for reliability
- 🛡️ SSL bypass and User-Agent spoofing for maximum compatibility

## Installation

```bash
# Install dependencies
pip install customtkinter yt-dlp Pillow requests

# Optional: Install FFmpeg for 1080p/4K support
# Windows
winget install ffmpeg

# Mac
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

## Usage

```bash
python youtube_downloader.py
```

1. Paste a YouTube URL
2. Click **⚡ BREACH** to scan the video
3. Select your desired quality/format
4. Choose download location
5. Click **⚡ EXTRACT** to download

## Version History

| Version | Description |
|---------|-------------|
| v4 | Original YTDROP — basic dark UI with full download functionality |
| v5 | Bug fixes — fixed progress hooks, download retry logic, SSL warnings, proper UI state management |
| v6 | Hacker UI — complete redesign with matrix-green terminal aesthetic, boot animation, glitch effects |
| v7 | Final — fixed video playback (combined streams only without FFmpeg), greatly improved text readability, drive storage display |

## Requirements

- Python 3.8+
- customtkinter
- yt-dlp
- Pillow
- requests
- FFmpeg (optional, for 1080p+ and MP3)

## Author

**Poojan Patel** — [@PoojanPatel7](https://github.com/PoojanPatel7)
