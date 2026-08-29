from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os, uuid, glob

app = Flask(__name__)
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.post("/download")
def download():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    kind = data.get("kind", "video")

    if not url or ("tiktok.com" not in url and "vm.tiktok.com" not in url):
        return jsonify(error="Masukkan URL TikTok yang valid."), 400

    job = uuid.uuid4().hex
    outtmpl = os.path.join(DOWNLOAD_DIR, job + ".%(ext)s")

    opts = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    if kind == "audio":
        opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })
    else:
        opts.update({
            "format": "best[ext=mp4]/best",
            "merge_output_format": "mp4",
        })

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        matches = glob.glob(os.path.join(DOWNLOAD_DIR, job + ".*"))
        if not matches:
            return jsonify(error="File hasil download tidak ditemukan."), 500

        path = matches[0]
        return send_file(path, as_attachment=True, download_name=os.path.basename(path))
    except Exception as e:
        return jsonify(error="Gagal memproses URL. Pastikan videonya dapat diakses dan coba lagi."), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
