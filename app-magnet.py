import os
from flask import Flask, request, jsonify, send_file, redirect, render_template_string
import razorpay
from flask_cors import CORS
import requests
import whois
from flask_cors import CORS  # ✅ 1. Import CORS
from fetch_client_magnet_email_pdf import fetch_pdf_if_missing
import socket

app = Flask(__name__)
CORS(app)


@app.route('/')
def home():
    return jsonify({"message": "Client Magnet backend is running successfully!"})

# Razorpay credentials (from Render environment variables)
RAZORPAY_KEY_ID = os.getenv("RZR_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RZR_KEY_SEC")

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

@app.route("/get-key", methods=["GET"])
def get_key():
    return jsonify({"key": RAZORPAY_KEY_ID})

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

@app.route("/verify-and-download", methods=["POST"])
def verify_payment():
    try:
        data = request.json
        payment_id = data.get("payment_id")

        # Fetch payment details from Razorpay
        payment = client.payment.fetch(payment_id)

        if payment["status"] == "captured":
            # ✅ Payment successful → Send PDF
            return send_file(
                "Client_Magnet_Cold_Email_Scripts.pdf",
                as_attachment=True
            )
        else:
            return jsonify({"error": "Payment not captured"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 400

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

@app.route("/verify-license", methods=["POST"])
def verify_license():
    data = request.get_json()
    key = data.get("license", "").strip()

    VALID_KEYS = os.getenv("LICENSE_KEYS", "").split(",")
    if key in VALID_KEYS:
        return jsonify({"valid": True})

    return jsonify({"valid": False}), 401

# ✅ This must ALWAYS be LAST
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
