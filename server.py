import os
import subprocess
from threading import Thread
from flask import Flask, render_template, jsonify

# point Flask at your templates folder under api/
app = Flask(__name__, template_folder="api/templates")

def run_instagram_post():
    # Adjust path if needed
    subprocess.call(["python", os.path.join("api", "post.py")])

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/post", methods=["POST"])
def post_carousel():
    # Run in background so HTTP doesn’t block
    Thread(target=run_instagram_post).start()
    return jsonify({"status": "started"}), 202

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
