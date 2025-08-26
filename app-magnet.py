import os
import time
import base64
import hmac
import hashlib
from flask import Flask, request, render_template_string, send_file, jsonify, abort
import requests
import whois
import razorpay
from flask_cors import CORS
from fetch_client_magnet_email_pdf import fetch_pdf_if_missing
import socket
from datetime import datetime
import dns.resolver

# ------------------- CONFIG -------------------
SECRET_DOWNLOAD_KEY = os.getenv("SECRET_DOWNLOAD_KEY", "supersecret")  # 🔐 set this in Render
UPLOAD_FOLDER = "private"
PDF_FILENAME = "Client_Magnet_Cold_Email_Scripts.pdf"
LOCAL_PDF_PATH = os.path.join(UPLOAD_FOLDER, PDF_FILENAME)

# Flask setup
app = Flask(__name__)
CORS(app, origins=["https://t24k.com"])

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
fetch_pdf_if_missing()

# Razorpay
RAZORPAY_KEY = os.getenv("RZR_KEY_ID")
RAZORPAY_SECRET = os.getenv("RZR_KEY_SEC")
client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))

# ------------------- PAYMENT FLOW -------------------

@app.route('/verify-and-download', methods=['POST'])
def verify_and_download():
    data = request.json
    payment_id = data.get('payment_id')

    try:
        payment = client.payment.fetch(payment_id)

        if payment['status'] == 'authorized':
            client.payment.capture(payment_id, payment['amount'])
            payment = client.payment.fetch(payment_id)

        if payment['status'] == 'captured':
            increment_sales_count()

            # ✅ Generate secure signed download link
            expiry = int(time.time()) + 300  # 5 min validity
            token = generate_download_token(expiry)

            link = f"{request.host_url}download-pdf?token={token}&exp={expiry}"
            return jsonify({"download_url": link})

        else:
            return "❌ Payment not captured", 403

    except Exception as e:
        return f"❌ Verification failed: {str(e)}", 400

# ------------------- SECURE DOWNLOAD -------------------

def generate_download_token(expiry: int) -> str:
    """Generate a signed token with expiry timestamp"""
    msg = f"{PDF_FILENAME}:{expiry}".encode()
    sig = hmac.new(SECRET_DOWNLOAD_KEY.encode(), msg, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode()

def verify_download_token(token: str, expiry: int) -> bool:
    if int(expiry) < int(time.time()):
        return False
    expected = generate_download_token(int(expiry))
    return hmac.compare_digest(token, expected)

@app.route("/download-pdf")
def download_pdf():
    token = request.args.get("token")
    expiry = request.args.get("exp")

    if not token or not expiry:
        abort(403)

    if not verify_download_token(token, expiry):
        abort(403)

    return send_file(LOCAL_PDF_PATH, as_attachment=True)

# ------------------- UTILITIES -------------------

@app.route('/')
def home():
    return "✅ Client Magnet Server is Running!"

@app.route('/get-key')
def get_key():
    return jsonify({"key": os.getenv("RZR_KEY_ID")})

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

# ------------------- WHOIS & DOMAIN TOOLS -------------------

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

@app.route("/check-availability")
def check_availability():
    domain = request.args.get("domain", "").strip()
    if not domain:
        return jsonify({"error": "No domain provided"}), 400
    try:
        socket.gethostbyname(domain)
        return jsonify({"available": False})
    except socket.gaierror:
        return jsonify({"available": True})

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
        return jsonify({"IP": ip, "DNS": records})
    except Exception as e:
        return f"❌ DNS fetch error: {str(e)}", 500
