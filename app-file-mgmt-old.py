import os
import zipfile
from flask import Flask, request, render_template_string, send_file
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
from pydub import AudioSegment
from docx import Document

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Generate or load encryption key
KEY_FILE = "secret.key"
if os.path.exists(KEY_FILE):
    with open(KEY_FILE, "rb") as f:
        key = f.read()
else:
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)

cipher = Fernet(key)

# Simple HTML UI
HTML = """
<!DOCTYPE html>
<html>
<head><title>File Management Tool</title></head>
<body>
  <h2>Upload File</h2>
  <form method="post" action="/compress" enctype="multipart/form-data">
    <input type="file" name="file">
    <button type="submit">Compress</button>
  </form>
  <form method="post" action="/decompress" enctype="multipart/form-data">
    <input type="file" name="file">
    <button type="submit">Decompress</button>
  </form>
  <form method="post" action="/encrypt" enctype="multipart/form-data">
    <input type="file" name="file">
    <button type="submit">Encrypt</button>
  </form>
  <form method="post" action="/decrypt" enctype="multipart/form-data">
    <input type="file" name="file">
    <button type="submit">Decrypt</button>
  </form>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/compress", methods=["POST"])
def compress():
    file = request.files["file"]
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    zip_path = filepath + ".zip"
    with zipfile.ZipFile(zip_path, "w") as zipf:
        zipf.write(filepath, arcname=filename)

    return send_file(zip_path, as_attachment=True)

@app.route("/decompress", methods=["POST"])
def decompress():
    file = request.files["file"]
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    extract_dir = os.path.join(UPLOAD_FOLDER, "extracted")
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(filepath, "r") as zipf:
        zipf.extractall(extract_dir)

    # Return first extracted file for simplicity
    extracted_files = os.listdir(extract_dir)
    if not extracted_files:
        return "No files found in archive"
    extracted_path = os.path.join(extract_dir, extracted_files[0])
    return send_file(extracted_path, as_attachment=True)

@app.route("/encrypt", methods=["POST"])
def encrypt():
    file = request.files["file"]
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    with open(filepath, "rb") as f:
        encrypted_data = cipher.encrypt(f.read())

    encrypted_path = filepath + ".enc"
    with open(encrypted_path, "wb") as f:
        f.write(encrypted_data)

    return send_file(encrypted_path, as_attachment=True)

@app.route("/decrypt", methods=["POST"])
def decrypt():
    file = request.files["file"]
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    with open(filepath, "rb") as f:
        decrypted_data = cipher.decrypt(f.read())

    decrypted_path = filepath.replace(".enc", "_decrypted")
    with open(decrypted_path, "wb") as f:
        f.write(decrypted_data)

    return send_file(decrypted_path, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
