from flask import Flask, request, render_template
from pytube import YouTube
import openai
import os

# OpenAI APIキーを環境変数から取得
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

def transcribe_and_summarize(video_url):
    # 1. YouTube動画をダウンロード（音声のみ）
    yt = YouTube(video_url)
    stream = yt.streams.filter(only_audio=True).first()
    audio_file = "audio.mp4"
    stream.download(filename=audio_file)

    # 2. Whisperで文字起こし
    with open(audio_file, "rb") as f:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=f
        )

    text = transcript["text"]

    # 3. GPTで要約
    summary_response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"以下の文章を日本語で簡潔に要約してください:\n{text}"}
        ]
    )
    summary = summary_response.choices[0].message.content
    return summary

@app.route("/", methods=["GET", "POST"])
def index():
    summary = ""
    if request.method == "POST":
        url = request.form["url"]
        if url:
            summary = transcribe_and_summarize(url)
    return render_template("index.html", summary=summary)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
