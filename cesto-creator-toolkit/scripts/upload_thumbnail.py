#!/usr/bin/env python3
"""
Upload a thumbnail image for a basket.

Usage:
  python3 upload_thumbnail.py --file /path/to/image.png
  python3 upload_thumbnail.py --url https://example.com/image.png

Output:
  {"url": "https://res.cloudinary.com/..."}
"""

import sys
sys.dont_write_bytecode = True
import json, os, tempfile, urllib.request, uuid
from _store import read_session, ACCESS_KEY

BASE_URL = "https://dev.backend.cesto.co"


def _download_image(url):
    """Download image from URL to temp file. Returns path."""
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "CestoCreatorToolkit/1.0")
        resp = urllib.request.urlopen(req, timeout=30)
        content_type = resp.headers.get("Content-Type", "image/png")
        ext = ".png"
        if "jpeg" in content_type or "jpg" in content_type:
            ext = ".jpg"
        elif "webp" in content_type:
            ext = ".webp"
        elif "gif" in content_type:
            ext = ".gif"

        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        tmp.write(resp.read())
        tmp.close()
        return tmp.name
    except Exception as e:
        return None


def _multipart_upload(file_path, token):
    """Upload file using multipart/form-data."""
    boundary = uuid.uuid4().hex
    filename = os.path.basename(file_path)

    # Detect content type
    ext = os.path.splitext(filename)[1].lower()
    content_types = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".gif": "image/gif", ".svg": "image/svg+xml",
    }
    ct = content_types.get(ext, "application/octet-stream")

    with open(file_path, "rb") as f:
        file_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {ct}\r\n\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"{BASE_URL}/labs/upload-thumbnail",
        data=body,
        method="POST",
    )
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    resp = urllib.request.urlopen(req, timeout=30)
    return json.loads(resp.read().decode())


def main():
    args = sys.argv[1:]
    file_path = None
    image_url = None
    i = 0
    while i < len(args):
        if args[i] == "--file" and i + 1 < len(args):
            file_path = args[i + 1]
            i += 2
        elif args[i] == "--url" and i + 1 < len(args):
            image_url = args[i + 1]
            i += 2
        else:
            i += 1

    if not file_path and not image_url:
        print(json.dumps({"error": True, "message": "Provide --file <path> or --url <url>"}))
        sys.exit(1)

    _session = read_session()
    if _session is None:
        print(json.dumps({"error": True, "message": "No valid session found. Please log in first."}))
        sys.exit(1)

    token = _session[ACCESS_KEY]
    tmp_file = None

    try:
        if image_url:
            file_path = _download_image(image_url)
            if file_path is None:
                print(json.dumps({"error": True, "message": "Failed to download image from URL"}))
                sys.exit(1)
            tmp_file = file_path

        if not os.path.exists(file_path):
            print(json.dumps({"error": True, "message": f"File not found: {file_path}"}))
            sys.exit(1)

        result = _multipart_upload(file_path, token)
        print(json.dumps(result))

    except urllib.error.HTTPError as e:
        print(json.dumps({"error": True, "status": e.code, "message": e.read().decode()}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}))
        sys.exit(1)
    finally:
        if tmp_file and os.path.exists(tmp_file):
            os.unlink(tmp_file)


if __name__ == "__main__":
    main()
