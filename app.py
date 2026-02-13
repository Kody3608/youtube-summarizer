from flask import Flask, request, render_template
import openai
import os
import subprocess
import math
from yt_dlp import YoutubeDL
from tempfile import NamedTemporaryFile

openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

# 音声を一定時間ごとに分割
def split_audio(input_file, segment_length=300):
    """
    segment_length: 1ファイルの長さ（秒） 300秒=5分
    """
    import ffmpeg
    import os

    # 音声情報を取得
    probe = ffmpeg.probe(input_file)
    duration = float(probe['format']['duration'])
    segments = []

    for i in range(0, math.ceil(duration), segment_length):
        output_file = f"segment_{i//segment_length}.mp3"
        (
            ffmpeg
            .input(input_file, ss=i, t=segment_length)
            .output(output_file, acodec='mp3', vn=True)
            .overwrite_output()
            .run(quiet=True)
        )
        segments.append(output_file)
    return segments

# Whisperで文字起こし
def transcribe_audio(file_path):
    with open(file_path, "rb") as f:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=f
        )
    return transcript['text']

# GPTで要約
def summarize_text(text):
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"以下の文章を日本語で簡潔に要約してください:\n{text}"}
        ]
    )
    return response.choices[0].message.content

# YouTube音声をダウンロードして分割・要約
def transcribe_and_summarize(video_url):
    # yt-dlp 設定
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'audio.%(ext)s',
        'quiet': True,
        'no_warnings': True
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        audio_file = ydl.prepare_filename(info)

    # 音声分割（5分ごと）
    segments = split_audio(audio_file, segment_length=300)

    # 分割ごとに文字起こし
    full_text = ""
    for seg in segments:
        text = transcribe_audio(seg)
        full_text += text + "\n"

    # GPTで要約
    summary = summarize_text(full_text)
    return summary

@app.route("/", methods=["GET", "POST"])
def index():
    summary = ""
    if request.method == "POST":
        url = request.form.get("url")
        if url:
            try:
                summary = transcribe_and_summarize(url)
            except Exception as e:
                summary = f"エラーが発生しました: {e}"
    return render_template("index.html", summary=summary)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
