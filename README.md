# VDROP — Video Downloader

Download videos from YouTube, Twitter, Instagram, TikTok, and 1000+ sites at source quality.

## Deploy to Railway (free)

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app)

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Select this repo — Railway auto-detects everything via `nixpacks.toml`
4. Done! Your public URL appears in the Railway dashboard

No environment variables needed.

## Run locally

```bash
# Prerequisites: Python 3.8+, FFmpeg in PATH
pip install -r requirements.txt
python app.py
# → http://localhost:5000
```

## Project structure

```
app.py          # Flask backend — serves frontend + /api/info + /api/download
index.html      # Frontend (served by Flask at /)
requirements.txt
Procfile        # gunicorn start command for Railway
nixpacks.toml   # Tells Railway to install FFmpeg + Python
.gitignore
```

## How it works

```
Browser → Flask (Railway) → yt-dlp + FFmpeg → send_file() → Browser saves file
```

Direct stream URL grabs from DevTools don't work because CDNs block non-browser
requests and URLs expire. This project downloads server-side and streams the
finished file back with Content-Disposition: attachment.
