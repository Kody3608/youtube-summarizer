from flask import Flask, request, render_template
import openai
import os
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

app = Flask(__name__)

# OpenAI APIキーを環境変数から取得
openai.api_key = os.environ.get("OPENAI_API_KEY")

# -----------------------------
# YouTube URL → video_id 抽出
# -----------------------------
def extract_video_id(url):
    parsed = urlparse(url)
    if parsed.hostname in ["www.youtube.com", "youtube.com"]:
        return parse_qs(parsed.query).get("v", [None])[0]
    if parsed.hostname == "youtu.be":
        return parsed.path[1:]
    return None

# -----------------------------
# 字幕取得（v0系互換）
# -----------------------------
def get_captions(video_url):
    video_id = extract_video_id(video_url)
    if not video_id:
        return None, "URLが正しくありません。"

    try:
        # v0系の get_transcript を使用
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["ja","en"])
        text = " ".join([item["text"] for item in transcript])
        return text, None

    except (TranscriptsDisabled, NoTranscriptFound) as e:
        return None, f"字幕を取得できませんでした: {e}"
    except Exception as e:
        return None, f"予期せぬエラー: {e}"

# -----------------------------
# GPT 要約
# -----------------------------
def summarize_text(text):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "以下の字幕を日本語で簡潔に要約してください。"},
                {"role": "user", "content": text}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"OpenAI APIでエラーが発生しました: {e}"

# -----------------------------
# Flask ルート
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    summary = ""
    error = ""
    if request.method == "POST":
        url = request.form.get("url")
        if url:
            captions, err = get_captions(url)
            if err:
                error = err
            else:
                summary = summarize_text(captions)
    return render_template("index.html", summary=summary, error=error)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
