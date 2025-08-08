from flask import Flask, request
import subprocess
import os

app = Flask(__name__)
ALERTS_LOG = "/home/braydenchaffee/Projects/encodarr/alerts_log.log"


@app.route("/notify", methods=["POST"])
def notify():
    data = request.get_json()
    filepath = data.get("file")
    video = data.get("video")
    audio = data.get("audio")

    # Log the incoming request
    with open(ALERTS_LOG, "a") as f:
        f.write(f"[NEEDS TRANSCODE] {filepath}\nVideo: {video} | Audio: {audio}\n\n")

    # Execute transcode script
    try:
        result = subprocess.run(
            ["/app/transcode.sh", filepath], capture_output=True, text=True, timeout=600
        )
        log_entry = f"[TRANSCODE OUTPUT]\n{result.stdout}\n{result.stderr}\n\n"
    except Exception as e:
        log_entry = f"[TRANSCODE ERROR] {str(e)}\n\n"

    with open(ALERTS_LOG, "a") as f:
        f.write(log_entry)

    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8099)
