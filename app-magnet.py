import os
from flask import Flask, request, jsonify, send_file
import razorpay
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
# Razorpay credentials (from Render environment variables)
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

@app.route("/get-key", methods=["GET"])
def get_key():
    return jsonify({"key": RAZORPAY_KEY_ID})

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
