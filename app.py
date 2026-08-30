from flask import Flask, render_template, request, send_file, jsonify
import os
import uuid
import requests
from urllib.parse import urlparse
from ipaddress import ip_address
import socket

app = Flask(__name__)

DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

ALLOWED_TYPES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "audio/mpeg",
    "audio/mp4",
    "audio/webm",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}

MAX_SIZE = 100 * 1024 * 1024  # 100 MB


def is_safe_url(url):
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False

    host = parsed.hostname

    try:
        addresses = socket.getaddrinfo(host, None)
        for item in addresses:
            ip = ip_address(item[4][0])
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            ):
                return False
    except Exception:
        return False

    return True


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/download")
def download():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()

    if not url:
        return jsonify(error="Masukkan URL media."), 400

    if not is_safe_url(url):
        return jsonify(error="URL tidak valid atau tidak diizinkan."), 400

    try:
        response = requests.get(
            url,
            stream=True,
            timeout=20,
            allow_redirects=True,
            headers={"User-Agent": "MediaDownloader/1.0"},
        )
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").split(";")[0].lower()
        content_length = int(response.headers.get("Content-Length", "0") or 0)

        if content_type not in ALLOWED_TYPES:
            return jsonify(
                error="URL harus mengarah langsung ke file media yang didukung."
            ), 400

        if content_length > MAX_SIZE:
            return jsonify(error="Ukuran file maksimal 100 MB."), 400

        extension = {
            "video/mp4": ".mp4",
            "video/webm": ".webm",
            "video/quicktime": ".mov",
            "audio/mpeg": ".mp3",
            "audio/mp4": ".m4a",
            "audio/webm": ".webm",
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
        }.get(content_type, ".bin")

        filename = uuid.uuid4().hex + extension
        path = os.path.join(DOWNLOAD_DIR, filename)

        total = 0

        with open(path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 64):
                if not chunk:
                    continue

                total += len(chunk)

                if total > MAX_SIZE:
                    f.close()
                    os.remove(path)
                    return jsonify(error="Ukuran file melebihi 100 MB."), 400

                f.write(chunk)

        return send_file(
            path,
            as_attachment=True,
            download_name="media" + extension,
        )

    except requests.RequestException:
        return jsonify(error="Gagal mengambil file dari URL tersebut."), 400
    except Exception:
        return jsonify(error="Terjadi kesalahan saat memproses file."), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
