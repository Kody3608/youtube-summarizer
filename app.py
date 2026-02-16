from flask import Flask, request, render_template
import os
import requests
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, VideoUnavailable, TranscriptsDisabled

app = Flask(__name__)

HF_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")
HF_MODEL = "rinna/japanese-gpt2-medium-summary"
HF_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

HEADERS = {
    "Authorization": f"Bearer {HF_API_KEY}"
}

# ------------------------
# YouTube URL → video_id
# ------------------------
def extract_video_id(url):
    parsed = urlparse(url)
    if parsed.hostname in ("www.youtube.com", "youtube.com"):
        return parse_qs(parsed.query).get("v", [None])[0]
    if parsed.hostname == "youtu.be":
        return parsed.path[1:]
    return None

# ------------------------
# 字幕取得
# ------------------------
def get_captions(url):
    video_id = extract_video_id(url)
    if not video_id:
        return None, "URLが正しくありません", None

    try:
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["ja"])
            lang = "日本語"
        except NoTranscriptFound:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
            lang = "英語"

        text = " ".join([t["text"] for t in transcript])
        return text, None, lang

    except VideoUnavailable:
        return None, "動画が存在しません", None
    except TranscriptsDisabled:
        return None, "この動画は字幕取得が無効です", None
    except Exception as e:
        return None, f"字幕取得エラー: {e}", None

# ------------------------
# 長文を分割
# ------------------------
def split_text(text, max_chars=800):
    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

# ------------------------
# Hugging Face 要約
# ------------------------
def summarize(text):
    if not HF_API_KEY:
        return "Hugging Face APIキーが設定されていません"

    summaries = []
    chunks = split_text(text)

    for chunk in chunks[:5]:  # ← 無料枠安定用（最大5分割）
        payload = {
            "inputs": chunk,
            "parameters": {
                "max_length": 120,
                "min_length": 40,
                "do_sample": False
            }
        }
        res = requests.post(HF_URL, headers=HEADERS, json=payload, timeout=30)
        if res.status_code != 200:
            return f"要約エラー HTTP {res.status_code}"
        summaries.append(res.json()[0]["summary_text"])

    return "\n".join(summaries)

# ------------------------
# Flask
# ------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    summary = ""
    error = ""
    language = ""

    if request.method == "POST":
        url = request.form.get("url")
        captions, err, language = get_captions(url)
        if err:
            error = err
        else:
            summary = summarize(captions)

    return render_template(
        "index.html",
        summary=summary,
        error=error,
        language=language
    )

if __name__ == "__main__":
    print("App starting...")
    app.run()
