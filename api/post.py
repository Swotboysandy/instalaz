import os
import json
import requests
from time import sleep

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")

BASE_URL = "https://instimage.vercel.app/images"
CAPTION_URL = "https://instimage.vercel.app/captions.txt"
CAPTION_STATE_FILE = "/tmp/caption_index.txt"
IMAGE_STATE_FILE = "/tmp/image_index.json"

def get_next_caption():
    """Fetch the next caption from hosted file and track index locally."""
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
    """Return next 2 image URLs based on image_index.json tracking."""
    index = 0
    if os.path.exists(IMAGE_STATE_FILE):
        with open(IMAGE_STATE_FILE, "r") as f:
            index = json.load(f).get("last_index", 0)

    file1 = f"{index}.jpg"
    file2 = f"{index + 1}.jpg"
    url1 = f"{BASE_URL}/{file1}?v={index}"
    url2 = f"{BASE_URL}/{file2}?v={index + 1}"

    with open(IMAGE_STATE_FILE, "w") as f:
        json.dump({"last_index": index + 2}, f)

    return [url1, url2]

def upload_and_wait(image_url):
    """Upload an image container and wait until processing finishes."""
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
    """Publish the final carousel to Instagram."""
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

def handler(request, response):
    try:
        media_ids = []
        image_urls = get_next_image_pair()

        for url in image_urls:
            cid = upload_and_wait(url)
            if cid:
                media_ids.append(cid)

        if len(media_ids) != 2:
            return response.status(400).json({"error": "Only found 1 image, need 2 for carousel."})

        success = publish_carousel(media_ids)
        if success:
            return response.status(200).json({"success": True, "message": "Carousel posted!"})
        else:
            return response.status(500).json({"error": "Failed to publish carousel."})

    except Exception as e:
        return response.status(500).json({"error": str(e)})
