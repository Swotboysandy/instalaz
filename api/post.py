import os
import json
import requests
from time import sleep
from dotenv import load_dotenv
from urllib.parse import quote

# ──────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────

load_dotenv()
ACCESS_TOKEN       = os.getenv("ACCESS_TOKEN")
IG_USER_ID         = os.getenv("IG_USER_ID")

BASE_URL           = "https://instimage.vercel.app/images"
CAPTION_URL        = "https://instimage.vercel.app/captions.txt"

IMAGE_STATE_FILE   = "image_state.json"
CAPTION_STATE_FILE = "caption_state.json"

DEFAULT_CAPTION    = "🧠 Daily carousel drop! #Pracandy #InstaBot"
# ──────────────────────────────────────────────────────────

def get_next_image_pair():
    """Return next two image URLs (img (N).jpg), track in IMAGE_STATE_FILE."""
    # load last index (0 if missing)
    last = 0
    if os.path.exists(IMAGE_STATE_FILE):
        with open(IMAGE_STATE_FILE, "r") as f:
            last = json.load(f).get("last_index", 0)

    # next two indices
    i1, i2 = last + 1, last + 2

    # build and quote filenames
    fn1 = quote(f"img ({i1}).jpg")
    fn2 = quote(f"img ({i2}).jpg")

    url1 = f"{BASE_URL}/{fn1}"
    url2 = f"{BASE_URL}/{fn2}"

    # save updated index
    with open(IMAGE_STATE_FILE, "w") as f:
        json.dump({"last_index": last + 2}, f)

    print("🗂️ Next images:", fn1, fn2)
    return [url1, url2]

def get_next_caption():
    """Fetch the next caption line, track in CAPTION_STATE_FILE."""
    try:
        res = requests.get(CAPTION_URL)
        if res.status_code != 200:
            raise ValueError("Failed to fetch captions.txt")

        lines = [line for line in res.text.splitlines() if line.strip()]
        if not lines:
            return DEFAULT_CAPTION

        # load last caption index
        idx = 0
        if os.path.exists(CAPTION_STATE_FILE):
            with open(CAPTION_STATE_FILE, "r") as f:
                idx = json.load(f).get("last_index", 0)

        # pick caption (or last if idx out of range)
        caption = lines[idx] if idx < len(lines) else lines[-1]

        # save next index
        with open(CAPTION_STATE_FILE, "w") as f:
            json.dump({"last_index": idx + 1}, f)

        return caption

    except Exception as e:
        print("❌ Caption error:", e)
        return DEFAULT_CAPTION

def upload_and_wait(image_url):
    """Upload an image URL to IG and wait until it's processed."""
    res = requests.post(
        f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media",
        data={
            "image_url":       image_url,
            "is_carousel_item":"true",
            "access_token":    ACCESS_TOKEN
        }
    )
    data = res.json()
    if res.status_code != 200 or "id" not in data:
        print("❌ Upload failed:", image_url, data)
        return None

    cid = data["id"]
    print(f"✅ Uploaded: {cid}")

    # poll until FINISHED
    for _ in range(10):
        status = requests.get(
            f"https://graph.facebook.com/v19.0/{cid}",
            params={"fields":"status_code","access_token":ACCESS_TOKEN}
        ).json().get("status_code")
        if status == "FINISHED":
            return cid
        if status == "ERROR":
            print("❌ Processing error for:", cid)
            return None
        sleep(2)

    print("❌ Timeout on processing:", cid)
    return None

def publish_carousel(media_ids, caption):
    """Create & publish a 2-item carousel with the given caption."""
    sleep(5)  # safety delay
    creation = requests.post(
        f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media",
        data={
            "media_type": "CAROUSEL",
            "children":   ",".join(media_ids),
            "caption":    caption,
            "access_token":ACCESS_TOKEN
        }
    ).json()

    cid = creation.get("id")
    if not cid:
        print("❌ Carousel creation failed:", creation)
        return False

    published = requests.post(
        f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish",
        data={"creation_id": cid, "access_token": ACCESS_TOKEN}
    ).json()
    print("🚀 Published carousel:", published)
    return True

def run_today():
    # 1) get next images
    urls = get_next_image_pair()
    if len(urls) < 2:
        return

    # 2) upload both
    media_ids = []
    for url in urls:
        cid = upload_and_wait(url)
        if cid:
            media_ids.append(cid)

    # 3) fetch next caption
    caption = get_next_caption()

    # 4) publish if ready
    if len(media_ids) == 2:
        publish_carousel(media_ids, caption)
    else:
        print("⚠️ Skipping: need exactly 2 media IDs, got", len(media_ids))

if __name__ == "__main__":
    run_today()
