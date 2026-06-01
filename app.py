import os
import uuid
import threading
import time
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
import yt_dlp

app = Flask(__name__, static_folder="static")
CORS(app)  # Railway serves frontend from same domain, CORS still needed for dev

DOWNLOAD_DIR = Path("/tmp/downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


def cleanup_file(filepath, delay=120):
    def _delete():
        time.sleep(delay)
        try:
            os.remove(filepath)
        except Exception:
            pass
    threading.Thread(target=_delete, daemon=True).start()


# ── Serve frontend ──────────────────────────────────────────────────────────
@app.route("/")
def index():
    with open(Path(__file__).parent / "index.html", "r") as f:
        return f.read(), 200, {"Content-Type": "text/html"}


# ── API: video info (preview) ───────────────────────────────────────────────
@app.route("/api/info", methods=["POST"])
def get_info():
    data = request.json or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                "title": info.get("title", "Unknown"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader", "Unknown"),
                "view_count": info.get("view_count"),
                "like_count": info.get("like_count"),
                "description": (info.get("description") or "")[:300],
            })
    except yt_dlp.utils.DownloadError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


# ── API: download ───────────────────────────────────────────────────────────
@app.route("/api/download", methods=["POST"])
def download_video():
    data = request.json or {}
    url = data.get("url", "").strip()
    quality = data.get("quality", "best")

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    job_id = str(uuid.uuid4())
    output_template = str(DOWNLOAD_DIR / f"{job_id}.%(ext)s")

    if quality == "audio":
        fmt = "bestaudio/best"
        postprocessors = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    elif quality in ("1080", "720", "480", "360"):
        fmt = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"
        postprocessors = [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}]
    else:
        fmt = "bestvideo+bestaudio/best"
        postprocessors = [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}]

    ydl_opts = {
        "format": fmt,
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": postprocessors,
        "merge_output_format": "mp4",
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "video")

        downloaded = list(DOWNLOAD_DIR.glob(f"{job_id}.*"))
        if not downloaded:
            return jsonify({"error": "Download failed — file not found"}), 500

        filepath = downloaded[0]
        ext = filepath.suffix.lstrip(".")
        safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
        download_name = f"{safe_title[:80]}.{ext}"

        cleanup_file(str(filepath), delay=120)

        return send_file(
            str(filepath),
            as_attachment=True,
            download_name=download_name,
            mimetype="video/mp4" if ext == "mp4" else "audio/mpeg",
        )

    except yt_dlp.utils.DownloadError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/ffmpeg-test")
def ffmpeg_test():
    import subprocess

    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True
        )
        return f"<pre>{result.stdout}\n{result.stderr}</pre>"
    except Exception as e:
        return f"ERROR: {e}"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
