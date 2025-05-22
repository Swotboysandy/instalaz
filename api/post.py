import os
import json
import requests
from time import sleep
from flask import Flask, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")

BASE_URL = "https://instimage.vercel.app/images"
CAPTION_URL = "https://instimage.vercel.app/captions.txt"
CAPTION_STATE_FILE = "/tmp/caption_index.txt"
IMAGE_STATE_FILE = "/tmp/image_index.json"

def get_next_caption():
    try:
        res = requests.get(CAPTION_URL)
        if res.status_code != 200:
            return "Stay inspired. @sandy_dumps_here"

        captions = res.text.strip().splitlines()
        if not captions:
            return "Stay inspired. @sandy_dumps_here"

        index = 0
        if os.path.exists(CAPTION_STATE_FILE):
            with open(CAPTION_STATE_FILE, "r") as f:
                index = int(f.read().strip())

        caption = captions[index] if index < len(captions) else captions[-1]

        with open(CAPTION_STATE_FILE, "w") as f:
            f.write(str(index + 1))

        return caption
    except Exception as e:
        return f"🧠 Daily drop failed. @sandy_dumps_here ({e})"

def get_next_image_pair():
    index = 0
    if os.path.exists(IMAGE_STATE_FILE):
        with open(IMAGE_STATE_FILE, "r") as f:
            index = json.load(f).get("last_index", 0)

    url1 = f"{BASE_URL}/{index}.jpg?v={index}"
    url2 = f"{BASE_URL}/{index + 1}.jpg?v={index + 1}"

    with open(IMAGE_STATE_FILE, "w") as f:
        json.dump({"last_index": index + 2}, f)

    return [url1, url2]

def upload_and_wait(image_url):
    res = requests.post(
        f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media",
        data={
            "image_url": image_url,
            "is_carousel_item": "true",
            "access_token": ACCESS_TOKEN
        }
    )
    data = res.json()
    if res.status_code != 200 or "id" not in data:
        print("❌ Upload failed:", data)
        return None

    container_id = data["id"]
    for _ in range(10):
        status = requests.get(
            f"https://graph.facebook.com/v19.0/{container_id}",
            params={"fields": "status_code", "access_token": ACCESS_TOKEN}
        ).json().get("status_code")
        if status == "FINISHED":
            return container_id
        elif status == "ERROR":
            return None
        sleep(2)

    return None

def publish_carousel(media_ids):
    caption = get_next_caption()
    sleep(5)
    res = requests.post(
        f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media",
        data={
            "media_type": "CAROUSEL",
            "children": ",".join(media_ids),
            "caption": caption,
            "access_token": ACCESS_TOKEN
        }
    )
    creation = res.json()
    cid = creation.get("id")
    if not cid:
        print("❌ Carousel creation failed:", creation)
        return False

    publish = requests.post(
        f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish",
        data={
            "creation_id": cid,
            "access_token": ACCESS_TOKEN
        }
    ).json()

    print("🚀 Carousel published:", publish)
    return True

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/post", methods=["GET"])
def post_carousel():
    try:
        media_ids = []
        image_urls = get_next_image_pair()

        for url in image_urls:
            cid = upload_and_wait(url)
            if cid:
                media_ids.append(cid)

        if len(media_ids) != 2:
            return jsonify({"error": "Only found 1 image, need 2 for carousel."}), 400

        success = publish_carousel(media_ids)
        if success:
            return jsonify({"success": True, "message": "Carousel posted!"})
        else:
            return jsonify({"error": "Failed to publish carousel."}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
