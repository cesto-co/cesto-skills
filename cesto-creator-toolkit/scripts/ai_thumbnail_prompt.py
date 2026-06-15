#!/usr/bin/env python3
"""
Build a default AI-thumbnail starter prompt locally (no backend call).

The GET /thumbnails/ai/prompt-template endpoint does NOT exist on the backend —
the thumbnails controller only exposes grid/upscale/session endpoints. This
script generates the starter prompt client-side instead, which is functionally
equivalent: the grid endpoint accepts any user-supplied prompt, and a
server-suggested starter prompt is entirely optional.

Different prose per provider:
  - midjourney: title-focused, concise, art-direction style descriptors.
  - gemini:     weaves the description into the prose for richer context.

Usage:
  python3 ai_thumbnail_prompt.py --provider midjourney --title "Football Glory"
  python3 ai_thumbnail_prompt.py --provider gemini --title "Football Glory" --description "..."

Output:
  { "prompt": "..." }   — the suggested prompt; user can edit before sending to grid.
"""

import sys
sys.dont_write_bytecode = True
import json


def _midjourney_prompt(title: str) -> str:
    return (
        f"Crypto finance basket cover art for '{title}', "
        "digital illustration, vibrant gradient background, "
        "abstract blockchain network nodes, glowing accent lines, "
        "professional fintech aesthetic, clean composition, "
        "wide aspect ratio banner, no text, no letters"
    )


def _gemini_prompt(title: str, description: str | None) -> str:
    base = (
        f"Create a cover image for a crypto investment basket titled '{title}'. "
    )
    if description:
        base += (
            f"The basket is described as: {description}. "
        )
    base += (
        "Style: modern fintech illustration with abstract blockchain or market chart "
        "motifs, vibrant but professional color palette, suitable as a product cover. "
        "No text or letters in the image."
    )
    return base


def main():
    args = sys.argv[1:]
    provider = title = description = None
    i = 0
    while i < len(args):
        if args[i] == "--provider" and i + 1 < len(args):
            provider = args[i + 1]; i += 2
        elif args[i] == "--title" and i + 1 < len(args):
            title = args[i + 1]; i += 2
        elif args[i] == "--description" and i + 1 < len(args):
            description = args[i + 1]; i += 2
        else:
            i += 1

    if not provider or provider not in ("midjourney", "gemini"):
        print(json.dumps({"error": True, "message": "Missing or invalid --provider (midjourney|gemini)"}))
        sys.exit(1)
    if not title:
        print(json.dumps({"error": True, "message": "Missing --title"}))
        sys.exit(1)

    if provider == "midjourney":
        prompt = _midjourney_prompt(title)
    else:
        prompt = _gemini_prompt(title, description)

    print(json.dumps({"prompt": prompt}))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as _e:
        import json, sys
        print(json.dumps({"error": True, "message": f"Unexpected error: {_e}"}))
        sys.exit(1)
