from flask import Flask, request, render_template
import openai
import os
from yt_dlp import YoutubeDL

openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

# -----------------------------
# 字幕を取得する関数
# -----------------------------
def get_captions(video_url):
    ydl_opts = {
        "skip_download": True,          # 動画・音声はDLしない
        "writesubtitles": True,
        "writeautomaticsub": True,      # 自動生成字幕もOK
        "subtitleslangs": ["ja", "en"],
        "subtitlesformat": "vtt",
        "quiet": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)

        subtitles = info.get("subtitles") or info.get("automatic_captions")
        if not subtitles:
            return None

        # 日本語優先、なければ英語
        for lang in ["ja", "en"]:
            if lang in subtitles:
                subtitle_url = subtitles[lang][0]["url"]
                return subtitle_url

    return None


# -----------------------------
# 字幕URLからテキスト取得
# -----------------------------
def fetch_subtitle_text(subtitle_url):
    import requests
    response = requests.get(subtitle_url)
    text = response.text

    lines = []
    for line in text.splitlines():
        if "-->" in line:
            continue
        if line.strip() == "" or line.strip().isdigit():
            continue
        lines.append(line)

    return " ".join(lines)


# -----------------------------
# GPTで要約
# -----------------------------
def summarize_text(text):
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": f"以下の字幕テキストを日本語で簡潔に要約してください。\n\n{text}"
            }
        ]
    )
    return response.choices[0].message.content


# -----------------------------
# メイン処理
# -----------------------------
def summarize_youtube(video_url):
    subtitle_url = get_captions(video_url)
    if not subtitle_url:
        return "この動画には字幕がありません。要約できません。"

    text = fetch_subtitle_text(subtitle_url)
    if not text:
        return "字幕の取得に失敗しました。"

    return summarize_text(text)


# -----------------------------
# Flask
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    summary = ""
    if request.method == "POST":
        url = request.form.get("url")
        if url:
            try:
                summary = summarize_youtube(url)
            except Exception as e:
                summary = f"エラーが発生しました: {e}"

    return render_template("index.html", summary=summary)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
