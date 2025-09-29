import os
import tempfile
import subprocess
import threading
import uuid
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# In-memory job tracker
JOBS = {}

def run_ffmpeg_job(job_id, input_path, output_path, file_type):
    try:
        if file_type == "audio":
            # Clean audio directly
            subprocess.run(
                ["ffmpeg", "-y", "-i", input_path, "-af", "anlmdn=s=12", output_path],
                check=True
            )
        elif file_type == "video":
            audio_path = output_path + "_audio.wav"
            cleaned_audio = output_path + "_cleaned.wav"

            # Extract audio
            subprocess.run(
                ["ffmpeg", "-y", "-i", input_path, "-q:a", "0", "-map", "a", audio_path],
                check=True
            )

            # Clean audio
            subprocess.run(
                ["ffmpeg", "-y", "-i", audio_path, "-af", "anlmdn=s=12", cleaned_audio],
                check=True
            )

            # Merge cleaned audio with video
            final_output = output_path + "_final.mp4"
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", input_path, "-i", cleaned_audio,
                    "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0",
                    final_output
                ],
                check=True
            )

            output_path = final_output

        JOBS[job_id]["status"] = "done"
        JOBS[job_id]["output"] = output_path

    except Exception as e:
        JOBS[job_id]["status"] = "error"
        JOBS[job_id]["error"] = str(e)


@app.route("/")
def home():
    return jsonify({"status": "Noise Reduction API running"})


@app.route("/process", methods=["POST"])
def process_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    file_type = request.form.get("fileType", "audio")

    # Save input file
    input_path = os.path.join(tempfile.gettempdir(), file.filename)
    file.save(input_path)

    # Output file path (base name only, extension added later)
    output_path = os.path.join(tempfile.gettempdir(), "output_" + str(uuid.uuid4()))

    # Create job ID
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "processing", "output": None}

    # Start background thread
    thread = threading.Thread(
        target=run_ffmpeg_job, args=(job_id, input_path, output_path, file_type)
    )
    thread.start()

    return jsonify({"job_id": job_id, "status": "processing"})


@app.route("/status/<job_id>", methods=["GET"])
def check_status(job_id):
    if job_id not in JOBS:
        return jsonify({"error": "Invalid job_id"}), 404
    return jsonify(JOBS[job_id])


@app.route("/download/<job_id>", methods=["GET"])
def download_file(job_id):
    if job_id not in JOBS:
        return jsonify({"error": "Invalid job_id"}), 404
    job = JOBS[job_id]
    if job["status"] != "done":
        return jsonify({"error": "Job not finished yet"}), 400
    return send_file(job["output"], as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
