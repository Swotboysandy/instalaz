from flask import Flask
import subprocess

app = Flask(__name__)

@app.route("/run-bot")
def run_bot():
    result = subprocess.run(["python3", "app.py"], capture_output=True, text=True)
    return result.stdout or result.stderr

@app.route("/")
def index():
    return open("index.html").read()

if __name__ == "__main__":
    app.run(debug=True)
