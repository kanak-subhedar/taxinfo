import os
from flask import Flask, request, redirect, render_template_string, send_file, jsonify
import whois
import razorpay
from flask_cors import CORS  # ✅ 1. Import CORS
from fetch_client_magnet_email_pdf import fetch_pdf_if_missing

app = Flask(__name__)        # ✅ 2. Create Flask app

fetch_pdf_if_missing()

CORS(app, origins=["https://t24k.com"])  # ✅ 3. Apply CORS immediately after app is created
UPLOAD_FOLDER = 'private'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

RAZORPAY_KEY = os.getenv("RZR_KEY_ID")
RAZORPAY_SECRET = os.getenv("RZR_KEY_SEC")

client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))

@app.route('/verify-and-download', methods=['POST'])
def verify_and_download():
    data = request.json
    payment_id = data.get('payment_id')
    # print(f"🧾 Received payment_id: {payment_id}")

    try:
        payment = client.payment.fetch(payment_id)
        # Capture manually in test mode (only needed if auto-capture is OFF)
        if payment['status'] == 'authorized':
            client.payment.capture(payment_id, payment['amount'])
            payment = client.payment.fetch(payment_id)
            
        if payment['status'] == 'captured':
            increment_sales_count()  # ✅ Call the function here
            filepath = os.path.join(UPLOAD_FOLDER, 'Client_Magnet_Cold_Email_Scripts.pdf')
            return send_file('private/Client_Magnet_Cold_Email_Scripts.pdf', as_attachment=True) #return send_file(filepath, as_attachment=True)  
        else:
            return "❌ Payment not captured", 403
    except Exception as e:
        return f"❌ Verification failed: {str(e)}", 400

#separate

#app = Flask(__name__) // this code is present above

@app.route('/')
def home():
    return "✅ Client Magnet Server is Running!"

@app.route('/list-uploads')
def list_uploads():
    secret_key = "ashish123"
    if request.args.get("key") != secret_key:
        return "❌ Unauthorized access", 403

    files = os.listdir(UPLOAD_FOLDER)
    if not files:
        return "<p>No files uploaded yet.</p>"

    links = [f"<li><a href='/{UPLOAD_FOLDER}/{fname}'>{fname}</a></li>" for fname in files]
    return f"<h3>Uploaded Files:</h3><ul>{''.join(links)}</ul>"

@app.route('/get-key')
def get_key():
    return jsonify({"key": os.getenv("RZR_KEY_ID")})

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

# @app.route('/client-magnet.pdf')
# def download_pdf():
    # return send_file('private/Client_Magnet_Cold_Email_Scripts.pdf', as_attachment=True)

def increment_sales_count():
    counter_file = "our_count.txt"
    if not os.path.exists(counter_file):
        with open(counter_file, "w") as f:
            f.write("0")

    with open(counter_file, "r+") as f:
        count = int(f.read().strip())
        f.seek(0)
        f.write(str(count + 1))
        f.truncate()

@app.route("/read-file")
def read_file():
    # 🔐 Read secret key from environment variable
    expected_key = os.getenv("READ_KEY")  # Make sure this is set on your hosting environment
    received_key = request.args.get("key")
    filename = request.args.get("file")

    if received_key != expected_key:
        return "❌ Unauthorized", 403

    # ✅ Allow only specific safe files
    allowed_files = {"our_count.txt"}
    if filename not in allowed_files:
        return "❌ Access denied", 403

    try:
        with open(filename, "r") as f:
            content = f.read()
        return f"<pre>{content}</pre>"
    except Exception as e:
        return f"❌ Error reading file: {str(e)}", 500

# service for whois

@app.route('/whois')
def whois_lookup():
    domain = request.args.get('domain', '').strip()
    if not domain:
        return "❌ No domain provided.", 400

    try:
        data = whois.whois(domain)
        if not data:
            return "⚠️ WHOIS data not found.", 404

        response_lines = [f"{key}: {value}" for key, value in data.items()]
        return "\n".join(response_lines)

    except Exception as e:
        return f"❌ Error: {str(e)}", 500

#Additional 4 features - Domain Age Calculation, Expiry Reminder Email, Domain Availability Checker, IP & DNS Records Fetcher

from datetime import datetime
import socket
import dns.resolver

@app.route("/domain-age")
def domain_age():
    domain = request.args.get('domain', '').strip()
    if not domain:
        return "❌ No domain provided", 400
    try:
        data = whois.whois(domain)
        creation = data.creation_date
        if isinstance(creation, list):
            creation = creation[0]
        if not creation:
            return "⚠️ Creation date not found.", 404
        today = datetime.utcnow()
        age_days = (today - creation).days
        return f"🕓 Domain {domain} is {age_days} days old (Created: {creation.date()})"
    except Exception as e:
        return f"❌ Error: {str(e)}", 500

@app.route("/expiry-reminder", methods=["POST"])
def expiry_reminder():
    data = request.json
    domain = data.get("domain", "").strip()
    email = data.get("email", "").strip()

    if not domain or not email:
        return "❌ Domain and email are required.", 400
    # You can log these or store in DB/Google Sheets for now
    try:
        with open("reminder_requests.txt", "a") as f:
            f.write(f"{datetime.now()} | {domain} | {email}\n")
        return "✅ Reminder request received. You'll be notified via email before expiry (manual process)."
    except Exception as e:
        return f"❌ Failed to save request: {str(e)}", 500

@app.route("/check-availability")
def check_availability():
    domain = request.args.get("domain", "").strip()
    if not domain:
        return jsonify({"error": "No domain provided"}), 400

    try:
        socket.gethostbyname(domain)
        return jsonify({"available": False})  # Registered
    except socket.gaierror:
        return jsonify({"available": True})   # Available

@app.route("/dns-info")
def dns_info():
    domain = request.args.get("domain", "").strip()
    if not domain:
        return "❌ No domain provided", 400
    try:
        ip = socket.gethostbyname(domain)
        records = {}
        for qtype in ['A', 'MX', 'NS', 'TXT']:
            try:
                answers = dns.resolver.resolve(domain, qtype)
                records[qtype] = [r.to_text() for r in answers]
            except Exception:
                records[qtype] = []
        return jsonify({
            "IP": ip,
            "DNS": records
        })
    except Exception as e:
        return f"❌ DNS fetch error: {str(e)}", 500
