from flask import Flask, request, render_template
import openai
import os
import requests
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

# 環境変数からキー取得
openai.api_key = os.environ.get("OPENAI_API_KEY")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

# -----------------------------
# YouTube URL → video_id
# -----------------------------
def extract_video_id(url):
    parsed = urlparse(url)
    if parsed.hostname in ["www.youtube.com", "youtube.com"]:
        return parse_qs(parsed.query).get("v", [None])[0]
    if parsed.hostname == "youtu.be":
        return parsed.path[1:]
    return None

# -----------------------------
# 字幕取得（APIキー専用・エラーハンドリング強化）
# -----------------------------
def get_captions(video_url):
    video_id = extract_video_id(video_url)
    if not video_id:
        return None, "URLが正しくありません。"

    if not YOUTUBE_API_KEY:
        return None, "YouTube APIキーが設定されていません。Render環境変数を確認してください。"

    try:
        # captions.list を直接 REST API 呼び出し
        url = f"https://youtube.googleapis.com/youtube/v3/captions?part=snippet&videoId={video_id}&key={YOUTUBE_API_KEY}"
        r = requests.get(url)
        if r.status_code == 400:
            return None, f"APIキーが無効です。正しいキーを設定してください。"
        if r.status_code != 200:
            return None, f"字幕取得中にエラーが発生しました: HTTP {r.status_code}"

        data = r.json()
        items = data.get("items", [])
        if not items:
            return None, "字幕が見つかりませんでした"

        # 日本語優先 → 英語 fallback
        caption_id = None
        for item in items:
            lang = item["snippet"]["language"]
            if lang.startswith("ja"):
                caption_id = item["id"]
                break
        if not caption_id:
            for item in items:
                lang = item["snippet"]["language"]
                if lang.startswith("en"):
                    caption_id = item["id"]
                    break
        if not caption_id:
            return None, "対応言語の字幕がありません"

        # 字幕ダウンロード
        download_url = f"https://www.googleapis.com/youtube/v3/captions/{caption_id}?tfmt=srt&key={YOUTUBE_API_KEY}"
        r2 = requests.get(download_url)
        if r2.status_code != 200:
            return None, f"字幕ダウンロード中にエラーが発生しました: HTTP {r2.status_code}"

        text = r2.text
        return text, None

    except Exception as e:
        return None, f"字幕取得中に予期せぬエラーが発生しました: {e}"

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
