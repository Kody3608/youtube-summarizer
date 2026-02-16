from flask import Flask, request, render_template
import os
import requests
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    VideoUnavailable,
    TranscriptsDisabled
)

app = Flask(__name__)

# ===== Hugging Face 設定 =====
HF_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")
HF_MODEL = "sonoisa/t5-small-japanese"  # Render向き・要約対応

# ===== YouTube URL → video_id =====
def extract_video_id(url):
    parsed = urlparse(url)
    if parsed.hostname in ["www.youtube.com", "youtube.com"]:
        return parse_qs(parsed.query).get("v", [None])[0]
    if parsed.hostname == "youtu.be":
        return parsed.path[1:]
    return None

# ===== 字幕取得 =====
def get_captions(video_url):
    video_id = extract_video_id(video_url)
    if not video_id:
        return None, "URLが正しくありません。", None

    try:
        try:
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id, languages=["ja"]
            )
            language = "日本語"
        except NoTranscriptFound:
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id, languages=["en"]
            )
            language = "英語"

        text = "\n".join([x["text"] for x in transcript])
        return text, None, language

    except VideoUnavailable:
        return None, "動画が存在しません。", None
    except TranscriptsDisabled:
        return None, "字幕が無効になっています。", None
    except NoTranscriptFound:
        return None, "字幕が見つかりません。", None
    except Exception as e:
        return None, f"字幕取得エラー: {e}", None

# ===== Hugging Face 要約 =====
def hf_summarize(text):
    if not HF_API_KEY:
        return "Hugging Face APIキーが未設定です。"

    API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": "要約: " + text[:3000],  # ★長さ制限（超重要）
        "parameters": {
            "max_length": 150,
            "min_length": 40,
            "do_sample": False
        }
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        if response.status_code != 200:
            return f"Hugging Face エラー: HTTP {response.status_code}"

        result = response.json()

        if isinstance(result, dict) and "error" in result:
            return f"Hugging Face エラー: {result['error']}"

        if isinstance(result, list) and "summary_text" in result[0]:
            return result[0]["summary_text"]

        return str(result)

    except Exception as e:
        return f"要約処理エラー: {e}"

# ===== Flask ルート =====
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
            summary = hf_summarize(captions)

    return render_template(
        "index.html",
        summary=summary,
        error=error,
        language=language
    )

# ===== ローカル用（Renderではgunicornが起動）=====
if __name__ == "__main__":
    app.run(debug=True)
