import os
import hmac
import hashlib
import base64
import requests
from flask import Flask, request, jsonify, send_file, abort
from io import BytesIO

app = Flask(__name__)

# --- Environment Variables ---
RZR_KEY_ID = os.getenv("RZR_KEY_ID")
RZR_KEY_SEC = os.getenv("RZR_KEY_SEC")
RZR_TST_KEY_ID = os.getenv("RZR_TST_KEY_ID")
RZR_TST_KEY_SEC = os.getenv("RZR_TST_KEY_SEC")

GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_FILE_PATH = os.getenv("GITHUB_FILE_PATH")
GITHUB_PAT_FILE_DOWNLOAD = os.getenv("GITHUB_PAT_FILE_DOWNLOAD")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

DOWNLOAD_KEY = os.getenv("DOWNLOAD_KEY")
READ_KEY = os.getenv("READ_KEY")

# --- Utilities ---
def verify_razorpay_signature(order_id, payment_id, signature, secret):
    payload = f"{order_id}|{payment_id}"
    expected_signature = hmac.new(
        secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)

def fetch_pdf_from_github():
    url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/{GITHUB_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_PAT_FILE_DOWNLOAD}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return BytesIO(r.content)
    else:
        print(f"GitHub fetch failed: {r.status_code} {r.text}")
        return None

# --- Routes ---

@app.route("/verify-payment", methods=["POST"])
def verify_payment():
    """
    Expects JSON:
    {
      "razorpay_order_id": "...",
      "razorpay_payment_id": "...",
      "razorpay_signature": "...",
      "mode": "test" | "live"
    }
    """
    data = request.json
    order_id = data.get("razorpay_order_id")
    payment_id = data.get("razorpay_payment_id")
    signature = data.get("razorpay_signature")
    mode = data.get("mode", "live")

    secret = RZR_TST_KEY_SEC if mode == "test" else RZR_KEY_SEC

    if not order_id or not payment_id or not signature:
        return jsonify({"success": False, "error": "Missing params"}), 400

    if verify_razorpay_signature(order_id, payment_id, signature, secret):
        # generate one-time download token
        token = base64.urlsafe_b64encode(os.urandom(24)).decode()
        app.config[token] = True  # temporary storage
        return jsonify({"success": True, "download_token": token})
    else:
        return jsonify({"success": False, "error": "Signature mismatch"}), 400

@app.route("/download", methods=["GET"])
def download_file():
    token = request.args.get("token")
    key = request.args.get("key")

    if not token or not key:
        abort(403)

    if key != DOWNLOAD_KEY:
        abort(403)

    if not app.config.get(token):
        abort(403)

    pdf_data = fetch_pdf_from_github()
    if pdf_data:
        return send_file(pdf_data, as_attachment=True, download_name="product.pdf")
    else:
        return jsonify({"success": False, "error": "File fetch failed"}), 500

@app.route("/")
def home():
    return "✅ Razorpay + Secure Download Server Running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
