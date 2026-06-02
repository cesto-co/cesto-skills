#!/usr/bin/env python3
"""
Upscale a quadrant for download and save the image to local disk.

POST /thumbnails/ai/:sessionId/upscale-for-download
Body: { index: 1-4 }
→ { url, publicId }   (Cloudinary URL)

The skill then HTTP-GETs that URL and writes the binary to disk. The default
target is ~/Downloads/cesto-thumbnail-<sessionId>-q<index>.<ext>; override
with --output <path>.

This is independent of the "Select-as-final" flow: downloading does NOT
commit the image as the basket cover. To do that, run ai_thumbnail_select.py
on the same quadrant afterwards (the backend reuses the upscaled image, so no
second Midjourney upscale is fired).

Usage:
  python3 ai_thumbnail_download.py --session-id <id> --index <1-4>
  python3 ai_thumbnail_download.py --session-id <id> --index 2 --output ~/Pictures/cover.png

Output:
  {
    "url":      "https://res.cloudinary.com/...",
    "publicId": "thumbnails/...",
    "savedTo":  "/Users/you/Downloads/cesto-thumbnail-abc123-q2.png",
    "bytes":    184227
  }
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.dont_write_bytecode = True

from _store import read_session, ACCESS_KEY

BASE_URL = "https://backend.cesto.co"


def _ext_from_url(url):
    """Best-effort extension parse from a Cloudinary URL."""
    path = urllib.parse.urlparse(url).path
    _, dot, ext = path.rpartition(".")
    if dot and 1 <= len(ext) <= 5 and ext.isalnum():
        return ext.lower()
    return "png"


def main():
    args = sys.argv[1:]
    session_id = None
    index = None
    output = None
    i = 0
    while i < len(args):
        if args[i] == "--session-id" and i + 1 < len(args):
            session_id = args[i + 1]; i += 2
        elif args[i] == "--index" and i + 1 < len(args):
            try:
                index = int(args[i + 1])
            except ValueError:
                index = None
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output = os.path.expanduser(args[i + 1]); i += 2
        else:
            i += 1

    if not session_id:
        print(json.dumps({"error": True, "message": "Missing --session-id"}))
        sys.exit(1)
    if index not in (1, 2, 3, 4):
        print(json.dumps({"error": True, "message": "--index must be 1, 2, 3, or 4"}))
        sys.exit(1)

    session = read_session()
    if session is None:
        print(json.dumps({"error": True, "message": "No valid session found. Please log in first."}))
        sys.exit(1)
    token = session[ACCESS_KEY]

    # Trigger upscale-for-download. Backend caches per-quadrant so a follow-up
    # Select on the same quadrant won't re-fire the Midjourney upscale.
    body = json.dumps({"index": index}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/thumbnails/ai/{session_id}/upscale-for-download",
        data=body,
        method="POST",
    )
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    try:
        resp = urllib.request.urlopen(req, timeout=120)
        api_data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        try:
            err = json.loads(body_text)
        except Exception:
            err = {"message": body_text}
        print(json.dumps({"error": True, "status": e.code, **err}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}))
        sys.exit(1)

    image_url = api_data.get("url")
    if not image_url:
        print(json.dumps({"error": True, "message": "Backend did not return a url", "response": api_data}))
        sys.exit(1)

    # Resolve the save path.
    if output:
        target = output
        target_dir = os.path.dirname(target) or "."
        os.makedirs(target_dir, exist_ok=True)
    else:
        downloads_dir = os.path.expanduser("~/Downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        ext = _ext_from_url(image_url)
        target = os.path.join(
            downloads_dir,
            f"cesto-thumbnail-{session_id}-q{index}.{ext}",
        )

    # Fetch and write the image. Cloudinary URLs are unauthenticated GET.
    try:
        with urllib.request.urlopen(image_url, timeout=60) as img_resp:
            raw = img_resp.read()
        with open(target, "wb") as fh:
            fh.write(raw)
    except Exception as e:
        print(json.dumps({"error": True, "message": f"Failed to download image: {e}", "url": image_url}))
        sys.exit(1)

    print(json.dumps({
        "url": image_url,
        "publicId": api_data.get("publicId"),
        "savedTo": target,
        "bytes": len(raw),
    }))


if __name__ == "__main__":
    main()
