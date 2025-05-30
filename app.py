import os
from flask import Flask, send_from_directory, request, abort

app = Flask(__name__)

# Route for trial version (no check)
@app.route("/trial")
def trial():
    return send_from_directory("full", "offline-messaging-tool.html")

# Route for full version (with dummy payment check)
@app.route("/full")
def full():
    paid = request.args.get("paid", "false")
    if paid == "true":
        return send_from_directory("full", "offline-messaging-tool.html")
    else:
        return abort(403, description="Payment required. Please complete payment to access the full version.")

# Root route
@app.route("/")
def root():
    return "Backend is running. Use /trial or /full?paid=true"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
