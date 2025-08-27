import os
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from io import BytesIO

app = Flask(__name__)
CORS(app)

# --- Environment Variables ---
RZR_KEY_ID = os.getenv("RZR_KEY_ID")               # Live Razorpay Key
RZR_KEY_SEC = os.getenv("RZR_KEY_SEC")             # Live Razorpay Secret
RZR_TST_KEY_ID = os.getenv("RZR_TST_KEY_ID")       # Test Razorpay Key
RZR_TST_KEY_SEC = os.getenv("RZR_TST_KEY_SEC")     # Test Razorpay Secret

GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_FILE_PATH = os.getenv("GITHUB_FILE_PATH")   # path in repo like: files/my.pdf
GITHUB_PAT_FILE_DOWNLOAD = os.getenv("GITHUB_PAT_FILE_DOWNLOAD")  # GitHub Personal Access Token

DOWNLOAD_KEY = os.getenv("DOWNLOAD_KEY", "secret-download-key")  # extra protection


# --- Route 1: Give Razorpay Key to Frontend ---
@app.route("/get-razorpay-key", methods=["GET"])
def get_razorpay_key():
    mode = request.args.get("mode", "test")
    if mode == "live":
        return jsonify({"key": RZR_KEY_ID})
    return jsonify({"key": RZR_TST_KEY_ID})


# --- Helper: Verify Razorpay Signature ---
def verify_razorpay_signature(order_id, payment_id, signature, secret):
    payload = f"{order_id}|{payment_id}"
    expected_signature = hmac.new(
        secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)


# --- Route 2: Verify Payment and Allow Download ---
@app.route("/verify-payment", methods=["POST"])
def verify_payment():
    data = request.json
    order_id = data.get("order_id")
    payment_id = data.get("razorpay_payment_id")
    signature = data.get("razorpay_signature")
    mode = data.get("mode", "test")  # "test" or "live"

    if not order_id or not payment_id or not signature:
        return jsonify({"error": "Missing parameters"}), 400

    secret = RZR_KEY_SEC if mode == "live" else RZR_TST_KEY_SEC
    is_valid = verify_razorpay_signature(order_id, payment_id, signature, secret)

    if not is_valid:
        return jsonify({"error": "Invalid payment signature"}), 400

    # ✅ Fetch file securely from GitHub private repo
    file_url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/{GITHUB_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_PAT_FILE_DOWNLOAD}"}
    r = requests.get(file_url, headers=headers)

    if r.status_code != 200:
        return jsonify({"error": "File not found"}), 404

    file_data = BytesIO(r.content)
    filename = os.path.basename(GITHUB_FILE_PATH)

    return send_file(file_data, as_attachment=True, download_name=filename)


# --- Route 3: Secure Direct Download (Optional) ---
@app.route("/download", methods=["GET"])
def secure_download():
    key = request.args.get("key")
    if key != DOWNLOAD_KEY:
        return jsonify({"error": "Unauthorized"}), 403

    file_url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/{GITHUB_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_PAT_FILE_DOWNLOAD}"}
    r = requests.get(file_url, headers=headers)

    if r.status_code != 200:
        return jsonify({"error": "File not found"}), 404

    file_data = BytesIO(r.content)
    filename = os.path.basename(GITHUB_FILE_PATH)

    return send_file(file_data, as_attachment=True, download_name=filename)


# --- Run (for local debugging) ---
if __name__ == "__main__":
    app.run(port=5000, debug=True)
