from flask import Flask, render_template, jsonify
import subprocess

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/run-bot", methods=["POST"])
def run_bot():
    try:
        # Run your main bot script
        subprocess.run(["python", "app.py"])
        return jsonify({"message": "Instagram bot executed successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
