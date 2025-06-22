import os
from flask import Flask, request, redirect, render_template_string, send_file

app = Flask(__name__)

UPLOAD_FOLDER = 'private'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return "✅ Client Magnet Server is Running!"

@app.route('/upload-pdf', methods=['GET', 'POST'])
def upload_pdf():
    # Set your secret key here
    secret_key = "ashish123"

    # Check if the key is correct
    if request.args.get("key") != secret_key:
        return "❌ Unauthorized access", 403

    if request.method == 'POST':
        file = request.files['pdf']
        if file:
            save_path = os.path.join(UPLOAD_FOLDER, 'Client_Magnet_Cold_Email_Scripts.pdf')
            file.save(save_path)
            return 'Upload successful ✅'
    return render_template_string('''
        <h2>Upload PDF to /private/</h2>
        <form method="POST" enctype="multipart/form-data">
            <input type="file" name="pdf">
            <input type="submit" value="Upload">
        </form>
    ''')

@app.route('/client-magnet.pdf')
def download_pdf():
    return send_file('private/Client_Magnet_Cold_Email_Scripts.pdf', as_attachment=True)
