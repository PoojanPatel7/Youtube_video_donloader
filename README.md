# YTDROP PRO — Premium YouTube Downloader

YTDROP PRO is a sleek, high-fidelity YouTube video and audio downloader tool built entirely in Python using a premium Material-based UI. It natively avoids common black-screen 1080p issues by integrating seamlessly with FFmpeg while offering clean, exact downloading logic mirroring your favorite modern browsers. 

![Build Status](https://img.shields.io/badge/Build-Stable-success)
![Version](https://img.shields.io/badge/Version-8.3-blue)
![Theme](https://img.shields.io/badge/Theme-Dark_Material-black)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Mac%20%7C%20Linux-lightgrey)

## ✨ Features
* **Modern Box-Grid Interface**: Clean, boxed formatting selections built gracefully with `customtkinter`.
* **Reliable Resolutions**: Direct 1080p, 2K, and 4K downloading! *Automatically utilizes FFmpeg inside containers.*
* **Surgically Accurate Progress**: Chrome-style precise percentage monitoring down to the fractional decimal.
* **Instant Pause & Cancel**: Natively pause or resume download streams midway through network fetching.
* **Intelligent FFmpeg Handling**: Instantly locates pre-installed global or local `ffmpeg` paths.
* **Drive Health Checks**: Displays current available data-storage capabilities directly in the app.
* **Auto Error-Resilience**: Bypasses network blocks using advanced `yt-dlp` multi-platform client fallbacks.

## ⚙️ Prerequisites
To correctly run this application, it is recommended to run this on Python `3.9+`. You additionally must have FFmpeg installed for HD (1080p, 1440p, 2160p) videos without audio issues.

**1. Install Python Libraries:**
```bash
pip install customtkinter yt-dlp Pillow requests
```

**2. Install FFmpeg (Windows):**
Run the following inside an Administrator PowerShell, or just install manually via Scoop.
```bash
winget install ffmpeg
```
*(Remember to restart your application or terminal after a fresh install!)*

## 🚀 Running the App
After installing prerequisites, run the launcher script using:
```bash
python youtube_downloader.py
```

## 🛠️ Technical Details & Acknowledgements
- **UI Framework**: `customtkinter`
- **Fetching Engine**: `yt-dlp`
- **Processing**: `FFmpeg` 

The application utilizes an advanced network hooking state to manually prevent hanging chunks, parsing bytes down perfectly without reading terminal formatting ANSI escapes. 

---
*Created carefully as a fully featured local system script.*
