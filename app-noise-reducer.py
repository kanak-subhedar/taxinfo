import os
import tempfile
import subprocess
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def reduce_noise_ffmpeg(input_path, output_path):
    # ffmpeg built-in noise reduction (adaptive filter)
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-af", "anlmdn=s=12",  # apply noise reduction
        output_path
    ]
    subprocess.run(cmd, check=True)

@app.route("/")
def home():
    return jsonify({"status": "Noise Reduction API running"})

@app.route("/process", methods=["POST"])
def process_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    file_type = request.form.get("fileType", "audio")

    # Save temp input
    input_path = os.path.join(tempfile.gettempdir(), file.filename)
    file.save(input_path)

    # Prepare output base
    base, _ = os.path.splitext(file.filename)
    output_base = os.path.join(tempfile.gettempdir(), base)

    if file_type == "audio":
        try:
            out_file = output_base + "_cleaned.wav"
            reduce_noise_ffmpeg(input_path, out_file)
            return send_file(out_file, as_attachment=True)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif file_type == "video":
        try:
            audio_path = output_base + "_audio.wav"
            # Extract audio
            subprocess.run(
                ["ffmpeg", "-y", "-i", input_path, "-q:a", "0", "-map", "a", audio_path],
                check=True
            )

            # Clean extracted audio
            cleaned_audio = output_base + "_cleaned.wav"
            reduce_noise_ffmpeg(audio_path, cleaned_audio)

            # Merge cleaned audio with original video
            out_file = output_base + "_cleaned.mp4"
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", input_path, "-i", cleaned_audio,
                    "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0",
                    out_file
                ],
                check=True
            )

            return send_file(out_file, as_attachment=True)

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    else:
        return jsonify({"error": "Invalid fileType"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
