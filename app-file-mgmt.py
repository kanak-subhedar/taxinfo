import os
import io
import zipfile
from flask import Flask, request, render_template_string, send_file
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
from pydub import AudioSegment
from docx import Document
from PyPDF2 import PdfReader
from PIL import Image
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# === Encryption Key ===
KEY_FILE = "secret.key"
if os.path.exists(KEY_FILE):
    with open(KEY_FILE, "rb") as f:
        key = f.read()
else:
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
cipher = Fernet(key)

# === HTML Form ===
HTML = """
<!DOCTYPE html>
<html>
<head><title>Universal File Manager</title></head>
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

  <form method="post" action="/convert-audio" enctype="multipart/form-data">
    <input type="file" name="file">
    <select name="format">
        <option value="mp3">MP3</option>
        <option value="wav">WAV</option>
        <option value="ogg">OGG</option>
    </select>
    <button type="submit">Convert Audio</button>
  </form>

  <form method="post" action="/extract-pdf" enctype="multipart/form-data">
    <input type="file" name="file">
    <button type="submit">Extract PDF Text</button>
  </form>

  <form method="post" action="/extract-docx" enctype="multipart/form-data">
    <input type="file" name="file">
    <button type="submit">Extract DOCX Text</button>
  </form>

  <form method="post" action="/convert-image" enctype="multipart/form-data">
    <input type="file" name="file">
    <select name="format">
        <option value="png">PNG</option>
        <option value="jpg">JPG</option>
        <option value="webp">WEBP</option>
    </select>
    <button type="submit">Convert Image</button>
  </form>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

# === Compression ===
@app.route("/compress", methods=["POST"])
def compress():
    file = request.files["file"]
    filename = secure_filename(file.filename)
    data = file.read()

    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr(filename, data)
    mem_zip.seek(0)

    return send_file(mem_zip, as_attachment=True, download_name=filename + ".zip")

# === Decompression ===
@app.route("/decompress", methods=["POST"])
def decompress():
    file = request.files["file"]
    mem_zip = io.BytesIO(file.read())

    with zipfile.ZipFile(mem_zip, "r") as zipf:
        extracted = zipf.namelist()
        if not extracted:
            return "Empty archive"
        fname = extracted[0]
        data = zipf.read(fname)

    return send_file(io.BytesIO(data), as_attachment=True, download_name=fname)

# === Encryption ===
@app.route("/encrypt", methods=["POST"])
def encrypt():
    file = request.files["file"]
    filename = secure_filename(file.filename)
    encrypted = cipher.encrypt(file.read())
    return send_file(io.BytesIO(encrypted), as_attachment=True, download_name=filename + ".enc")

# === Decryption ===
@app.route("/decrypt", methods=["POST"])
def decrypt():
    file = request.files["file"]
    filename = secure_filename(file.filename)
    decrypted = cipher.decrypt(file.read())
    out_name = filename.replace(".enc", "_decrypted")
    return send_file(io.BytesIO(decrypted), as_attachment=True, download_name=out_name)

# === Audio Conversion ===
@app.route("/convert-audio", methods=["POST"])
def convert_audio():
    file = request.files["file"]
    fmt = request.form.get("format", "mp3")
    audio = AudioSegment.from_file(file)
    buf = io.BytesIO()
    audio.export(buf, format=fmt)
    buf.seek(0)
    out_name = os.path.splitext(secure_filename(file.filename))[0] + "." + fmt
    return send_file(buf, as_attachment=True, download_name=out_name)

# === PDF Extraction ===
@app.route("/extract-pdf", methods=["POST"])
def extract_pdf():
    file = request.files["file"]
    reader = PdfReader(file)
    text = "\n".join([page.extract_text() or "" for page in reader.pages])
    buf = io.BytesIO(text.encode("utf-8"))
    return send_file(buf, as_attachment=True, download_name="extracted.txt")

# === DOCX Extraction ===
@app.route("/extract-docx", methods=["POST"])
def extract_docx():
    file = request.files["file"]
    doc = Document(file)
    text = "\n".join([p.text for p in doc.paragraphs])
    buf = io.BytesIO(text.encode("utf-8"))
    return send_file(buf, as_attachment=True, download_name="extracted.txt")

# === Image Conversion ===
@app.route("/convert-image", methods=["POST"])
def convert_image():
    file = request.files["file"]
    fmt = request.form.get("format", "png")
    img = Image.open(file)
    buf = io.BytesIO()
    img.save(buf, format=fmt.upper())
    buf.seek(0)
    out_name = os.path.splitext(secure_filename(file.filename))[0] + "." + fmt
    return send_file(buf, as_attachment=True, download_name=out_name)

# === Start Server ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
