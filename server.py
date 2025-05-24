# ─────────────────────────────────────────────
# server.py
# ─────────────────────────────────────────────
import os
import subprocess
import threading
from flask import Flask, render_template, jsonify

app = Flask(__name__, template_folder="api/templates")

# A simple flag + lock to prevent overlapping runs
_run_lock = threading.Lock()
_is_running = False

def run_instagram_post():
    global _is_running
    try:
        print("🔥 Starting Instagram post subprocess…")
        result = subprocess.run(["python", "api/post.py"], capture_output=True, text=True)
        print("📤 STDOUT:", result.stdout)
        print("📥 STDERR:", result.stderr)
    except Exception as e:
        print("❌ Error in subprocess:", e)
    finally:
        with _run_lock:
            _is_running = False

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/post", methods=["POST"])
def post_carousel():
    global _is_running
    with _run_lock:
        if _is_running:
            return jsonify({"error": "A post is already in progress. Please wait."}), 429
        _is_running = True

    threading.Thread(target=run_instagram_post, daemon=True).start()
    return jsonify({"status": "started"}), 202

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
