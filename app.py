from flask import Flask, render_template, request
import subprocess
import os
import openai
import uuid

app = Flask(__name__)

openai.api_key = os.environ.get("OPENAI_API_KEY")


def get_captions(youtube_url):
    uid = str(uuid.uuid4())
    output_template = f"/tmp/{uid}.%(ext)s"

    command = [
        "yt-dlp",
        "--skip-download",
        "--write-auto-sub",
        "--write-sub",
        "--sub-lang", "ja,en",
        "--sub-format", "vtt",
        "-o", output_template,
        youtube_url
    ]

    subprocess.run(command, capture_output=True, text=True)

    # 字幕ファイル探索
    for file in os.listdir("/tmp"):
        if file.startswith(uid) and file.endswith(".vtt"):
            with open(f"/tmp/{file}", "r", encoding="utf-8") as f:
                return f.read()

    return None


def summarize(text):
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "以下の字幕を日本語で簡潔に要約してください。"},
            {"role": "user", "content": text}
        ],
        max_tokens=500
    )
    return response.choices[0].message.content


@app.route("/", methods=["GET", "POST"])
def index():
    summary = None
    error = None

    if request.method == "POST":
        url = request.form["url"]

        captions = get_captions(url)
        if not captions:
            error = "この動画には字幕がないか、取得できませんでした。"
        else:
            summary = summarize(captions)

    return render_template("index.html", summary=summary, error=error)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
