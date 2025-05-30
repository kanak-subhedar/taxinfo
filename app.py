from flask import Flask, send_from_directory, request, abort

app = Flask(__name__)

# Route for trial version (no check)
@app.route("/trial")
def trial():
    return send_from_directory("trial", "index.html")

# Route for full version (with dummy check for now)
@app.route("/full")
def full():
    # TEMP: Replace with Razorpay/Render payment check logic later
    paid = request.args.get("paid", "false")
    if paid == "true":
        return send_from_directory("full", "index.html")
    else:
        return abort(403, description="Payment required")

@app.route("/")
def root():
    return "Backend is running. Use /trial or /full routes."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
    #app.run(host="0.0.0.0", port=10000)

