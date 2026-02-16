import os
from flask import Flask, request, render_template
from youtube_transcript_api import YouTubeTranscriptApi

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    transcript_text = ""
    if request.method == "POST":
        youtube_url = request.form.get("youtube_url")
        if youtube_url:
            try:
                # URLから動画IDを抽出
                video_id = youtube_url.split("v=")[-1].split("&")[0]
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                
                # 文字起こしをまとめる
                transcript_text = "\n".join([t['text'] for t in transcript_list])
            except Exception as e:
                transcript_text = f"Error: {str(e)}"

    return render_template("index.html", transcript=transcript_text)

if __name__ == "__main__":
    # Render が指定するポートにバインド
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
