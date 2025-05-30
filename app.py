from flask import Flask
app = Flask(__name__)

@app.route('/trial')
def trial():
    return 'This is the trial version.'

@app.route('/full')
def full():
    return 'This is the full version. Payment verified.'
