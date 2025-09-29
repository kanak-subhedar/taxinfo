import os
import tempfile
import subprocess
from flask import Flask, request, send_file, jsonify
import librosa
import noisereduce as nr
import soundfile as sf
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

    # save temp input
    input_path = os.path.join(tempfile.gettempdir(), file.filename)
    file.save(input_path)

    # Output file path
    output_path = os.path.join(tempfile.gettempdir(), "output")
    
    if file_type == "audio":
    try:
        out_file = output_path + "_cleaned.wav"
        reduce_noise_ffmpeg(input_path, out_file)
        return send_file(out_file, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    elif file_type == "video":
        try:
            # Extract audio
            audio_path = output_path + "_audio.wav"
            subprocess.run(
                ["ffmpeg", "-i", input_path, "-q:a", "0", "-map", "a", audio_path, "-y"],
                check=True
            )

            # Reduce noise
            y, sr = librosa.load(audio_path, sr=None)
            reduced = nr.reduce_noise(y=y, sr=sr)
            cleaned_audio = output_path + "_cleaned.wav"
            sf.write(cleaned_audio, reduced, sr)

            # Merge back into video
            out_file = output_path + ".mp4"
            subprocess.run(
                ["ffmpeg", "-i", input_path, "-i", cleaned_audio, "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0", out_file, "-y"],
                check=True
            )

            return send_file(out_file, as_attachment=True)

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    else:
        return jsonify({"error": "Invalid fileType"}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
