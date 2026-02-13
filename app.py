from flask import Flask, request, render_template
import os
import requests
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
HF_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")

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
# 字幕取得（YouTube Data API）
# -----------------------------
def get_captions(video_url):
    video_id = extract_video_id(video_url)
    if not video_id:
        return None, "URLが正しくありません。"

    if not YOUTUBE_API_KEY:
        return None, "YouTube APIキーが未設定です。Render環境変数を確認してください。"

    # キャプションリストを取得
    url = f"https://youtube.googleapis.com/youtube/v3/captions?part=snippet&videoId={video_id}&key={YOUTUBE_API_KEY}"
    r = requests.get(url)
    if r.status_code == 400:
        return None, "YouTube APIキーが無効です。"
    if r.status_code != 200:
        return None, f"字幕取得中にエラー({r.status_code})"

    data = r.json()
    items = data.get("items", [])
    if not items:
        return None, "字幕が見つかりません。"

    # 日本語優先、次に英語
    caption_id = None
    for item in items:
        if item["snippet"]["language"].startswith("ja"):
            caption_id = item["id"]
            break
    if not caption_id:
        for item in items:
            if item["snippet"]["language"].startswith("en"):
                caption_id = item["id"]
                break
    if not caption_id:
        return None, "対応言語の字幕がありません。"

    download_url = f"https://www.googleapis.com/youtube/v3/captions/{caption_id}?tfmt=srt&key={YOUTUBE_API_KEY}"
    r2 = requests.get(download_url)
    if r2.status_code != 200:
        return None, f"字幕ダウンロード中にエラー({r2.status_code})"

    text = r2.text
    return text, None

# -----------------------------
# Hugging Face 要約
# -----------------------------
def hf_summarize(text):
    if not HF_API_KEY:
        return "Hugging Face APIキーが未設定です。Render環境変数を確認してください。"

    # モデル指定（無料枠で使える）
    API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}

    payload = {
        "inputs": text,
        "parameters": {"max_length": 150, "min_length": 40, "do_sample": False}
    }

    response = requests.post(API_URL, headers=headers, json=payload)

    if response.status_code != 200:
        return f"Hugging Face 要約エラー: HTTP {response.status_code}"

    result = response.json()
    if isinstance(result, dict) and "error" in result:
        return f"Hugging Face エラー: {result['error']}"

    # 要約テキスト抽出
    summary_text = ""
    if isinstance(result, list):
        item = result[0]
        if isinstance(item, dict) and "summary_text" in item:
            summary_text = item["summary_text"]
        else:
            summary_text = str(result)
    else:
        summary_text = str(result)

    return summary_text

# -----------------------------
# Flask ルート
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    summary = ""
    error = ""
    if request.method == "POST":
        url = request.form.get("url")
        captions, err = get_captions(url)
        if err:
            error = err
        else:
            summary = hf_summarize(captions)
    return render_template("index.html", summary=summary, error=error)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
