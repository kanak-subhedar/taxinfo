import os
from flask import Flask, send_from_directory, request, abort

app = Flask(__name__)

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

@app.route("/")
def hello():
    return "Backend is running"

@app.route("/verify", methods=["POST"])
def verify_payment():
    try:
        data = request.json
        razorpay_order_id = data.get("razorpay_order_id")
        razorpay_payment_id = data.get("razorpay_payment_id")
        razorpay_signature = data.get("razorpay_signature")

        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }

        client.utility.verify_payment_signature(params_dict)

        # If verification succeeds, send the file
        pdf_path = "private/client-magnet.pdf"
        return send_file(pdf_path, as_attachment=True)
  
    except razorpay.errors.SignatureVerificationError:
        return jsonify({"status": "error", "message": "Payment verification failed"}), 403

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
