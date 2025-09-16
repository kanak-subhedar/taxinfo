import os
import zipfile
from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
from pydub import AudioSegment
from PIL import Image

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Use stored key from environment, or generate if missing
SECRET_KEY = os.environ.get("ENCRYPTION_KEY")
if SECRET_KEY is None:
    SECRET_KEY = Fernet.generate_key()
    print("Generated new encryption key:", SECRET_KEY.decode())
cipher = Fernet(SECRET_KEY)

@app.route("/")
def index():
    return "Backend is running for File Management Tool"

# 1️⃣ File Compression
@app.route("/compress", methods=["POST"])
def compress_file():
    if "file" not in request.files:
        return "❌ No file uploaded", 400
    file = request.files["file"]
    filepath = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
    file.save(filepath)

    zip_path = filepath + ".zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(filepath, os.path.basename(filepath))

    return send_file(zip_path, as_attachment=True)

# 2️⃣ File Encryption
@app.route("/encrypt", methods=["POST"])
def encrypt_file():
    if "file" not in request.files:
        return "❌ No file uploaded", 400
    file = request.files["file"]
    filepath = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
    file.save(filepath)

    with open(filepath, "rb") as f:
        encrypted_data = cipher.encrypt(f.read())

    encrypted_path = filepath + ".enc"
    with open(encrypted_path, "wb") as ef:
        ef.write(encrypted_data)

    return send_file(encrypted_path, as_attachment=True)

# 2️⃣b File Decryption
@app.route("/decrypt", methods=["POST"])
def decrypt_file():
    if "file" not in request.files:
        return "❌ No file uploaded", 400
    file = request.files["file"]
    filepath = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
    file.save(filepath)

    with open(filepath, "rb") as f:
        decrypted_data = cipher.decrypt(f.read())

    original_path = filepath.replace(".enc", "_decrypted.txt")
    with open(original_path, "wb") as df:
        df.write(decrypted_data)

    return send_file(original_path, as_attachment=True)

# 3️⃣ File Format Conversion (Example: PNG → JPG, WAV → MP3)
@app.route("/convert", methods=["POST"])
def convert_file():
    if "file" not in request.files or "target" not in request.form:
        return "❌ File and target format required", 400

    file = request.files["file"]
    target_format = request.form["target"].lower()
    filepath = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
    file.save(filepath)

    output_path = None

    # Image conversion
    if file.filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
        img = Image.open(filepath)
        output_path = filepath.rsplit(".", 1)[0] + f".{target_format}"
        img.save(output_path)

    # Audio conversion
    elif file.filename.lower().endswith((".mp3", ".wav", ".ogg")):
        audio = AudioSegment.from_file(filepath)
        output_path = filepath.rsplit(".", 1)[0] + f".{target_format}"
        audio.export(output_path, format=target_format)

    else:
        return "❌ Unsupported file type for conversion", 400

    return send_file(output_path, as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
