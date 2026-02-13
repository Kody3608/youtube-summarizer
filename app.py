from flask import Flask, request, render_template
import openai
import os
import subprocess
import uuid

app = Flask(__name__)

# OpenAI APIキーを環境変数から取得
openai.api_key = os.environ.get("OPENAI_API_KEY")

# -----------------------------
# 字幕を取得する関数
# -----------------------------
def get_captions(youtube_url):
    uid = str(uuid.uuid4())
    output_template = f"/tmp/{uid}.%(ext)s"

    # Python モジュール経由で yt-dlp を呼ぶ
    command = [
        "python", "-m", "yt_dlp",
        "--skip-download",             # 音声・動画はDLしない
        "--write-auto-sub",            # 自動生成字幕
        "--write-sub",                 # 公式字幕
        "--sub-lang", "ja,en",
        "--sub-format", "vtt",
        "-o", output_template,
        youtube_url
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    # デバッグ用ログ出力（Render Logs に表示される）
    print("yt-dlp stdout:\n", result.stdout)
    print("yt-dlp stderr:\n", result.stderr)
    print("return code:", result.returncode)

    if result.returncode != 0:
        return None, f"yt-dlp 実行でエラーが発生しました:\n{result.stderr}"

    # 出力ファイルを探す
    for file in os.listdir("/tmp"):
        if file.startswith(uid) and file.endswith(".vtt"):
            with open(f"/tmp/{file}", "r", encoding="utf-8") as f:
                return f.read(), None

    return None, "字幕ファイルが見つかりませんでした。"

# -----------------------------
# GPTで要約
# -----------------------------
def summarize_text(text):
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"以下の字幕を日本語で簡潔に要約してください。\n\n{text}"}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"OpenAI APIでエラーが発生しました: {e}"

# -----------------------------
# メイン処理
# -----------------------------
def summarize_youtube(video_url):
    captions, error = get_captions(video_url)
    if error:
        return error
    if not captions:
        return "字幕が取得できませんでした。"
    return summarize_text(captions)

# -----------------------------
# Flask
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    summary = ""
    if request.method == "POST":
        url = request.form.get("url")
        if url:
            summary = summarize_youtube(url)
    return render_template("index.html", summary=summary)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
