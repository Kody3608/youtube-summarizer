from flask import Flask, render_template, request
import subprocess
import os
import whisper

app = Flask(__name__)

# Whisperモデルロード（tinyで高速）
model = whisper.load_model("tiny")

@app.route("/", methods=["GET", "POST"])
def index():
    transcript = ""
    if request.method == "POST":
        url = request.form.get("url")
        if url:
            # 音声ダウンロード
            os.makedirs("output", exist_ok=True)
            audio_path = "output/audio.mp3"
            subprocess.run([
                "yt-dlp", "-x", "--audio-format", "mp3",
                "-o", audio_path, url
            ])

            # 文字起こし
            result = model.transcribe(audio_path)
            transcript = result["text"]

    return render_template("index.html", transcript=transcript)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
