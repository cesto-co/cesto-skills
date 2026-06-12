# AI Thumbnail Sub-Flow (Midjourney / Gemini)

Open this file when the creator picks "Generate with AI" as their cover image during
Flow A (create) or Flow B (edit cover). The backend powers this via `/thumbnails/ai/*`;
full endpoint details in [`api-reference.md` §16](api-reference.md#16-ai-thumbnail-builder--thumbnailsai).

The whole flow: pick a provider → pre-fill a prompt the user can edit → start a 2×2
grid generation → poll until ready → show the 4 previews → user either "uses" one
(commits as basket cover) or "downloads" one (saves locally) or asks to "regenerate".

---

## Step 1 — Pick provider

> "Midjourney or Gemini? Midjourney is more stylized and artistic (good for thematic /
> illustrative covers, ~30-90s). Gemini is cleaner and more realistic (good for
> product-style covers, faster)."

## Step 2 — Generate a starter prompt locally (optional but recommended)

Note: `GET /thumbnails/ai/prompt-template` does NOT exist on the backend. The
starter prompt is generated client-side by `ai_thumbnail_prompt.py` — no network
call required. The `grid` endpoint accepts any client-supplied prompt.

```bash
python3 <skill-path>/scripts/ai_thumbnail_prompt.py \
  --provider <midjourney|gemini> \
  --title "{Title}" \
  --description "{Description}" 2>/dev/null
```

Show the returned `prompt` and ask:

> "Want to use this as-is, tweak it, or write your own?"

The user-edited prompt is what we send to the grid endpoint verbatim. Midjourney
appends its fixed flag suffix server-side — the user never has to think about it.

## Step 3 — Start the grid

```bash
python3 <skill-path>/scripts/ai_thumbnail_grid.py \
  --title "{Title}" \
  --description "{Description}" \
  --provider <midjourney|gemini> \
  --prompt "<final user prompt>" 2>/dev/null
```

Capture `response.sessionId`. Tell the user:

> "Generating 4 options — this can take 30-90 seconds for Midjourney, less for Gemini.
> Sit tight."

## Step 4 — Wait for the grid

```bash
python3 <skill-path>/scripts/ai_thumbnail_session.py --session-id <sessionId> --wait 2>/dev/null
```

Polls every 5s, ≤3 min ceiling, emits a progress line to stderr every 15s. When it
exits cleanly, the response has:

- `gridStatus: "ready"`
- `previews: [{ index: 1, url, downloadUrl? }, …]` — 4 entries
- `provider: "midjourney" | "gemini"` — the backend that actually produced them
- `fellBack: boolean` — `true` if the primary provider failed and the backend swapped

If `fellBack: true`, mention it to the user:

> "Heads up — Midjourney was unavailable so Gemini produced these instead."

If the script exits non-zero with an `error` field, surface the message and offer
regenerate.

## Step 5 — Show the previews

Render as a numbered table. Don't try to embed the images inline — URLs work everywhere
and the user can click them in their terminal to view in a browser.

```
Here are your 4 options:

| # | Preview                                  |
|---|------------------------------------------|
| 1 | https://res.cloudinary.com/…preview1.png |
| 2 | https://res.cloudinary.com/…preview2.png |
| 3 | https://res.cloudinary.com/…preview3.png |
| 4 | https://res.cloudinary.com/…preview4.png |

Tell me: "use 2" to set it as the cover, "download 3" to save it locally, or
"regenerate" to try a new prompt.
```

## Step 6 — Handle the pick

### Branch A: "use N" — select as final cover

```bash
python3 <skill-path>/scripts/ai_thumbnail_select.py --session-id <sessionId> --index N 2>/dev/null
python3 <skill-path>/scripts/ai_thumbnail_session.py \
  --session-id <sessionId> --wait --wait-for upscale 2>/dev/null
```

The second call polls until `upscaleStatus: "ready"`. Read `finalUrl` from the
response. Use that URL as `product.logoUrl` in the Flow A Step 10 payload (or the
Flow B partial update). Do **not** set `aiGenerateThumbnail` alongside a `logoUrl` —
they're mutually exclusive.

### Branch B: "download N" — save locally

```bash
# Default: saves to ~/Downloads/cesto-thumbnail-<sessionId>-q<N>.<ext>
python3 <skill-path>/scripts/ai_thumbnail_download.py --session-id <sessionId> --index N 2>/dev/null

# Custom path:
python3 <skill-path>/scripts/ai_thumbnail_download.py \
  --session-id <sessionId> --index N --output ~/Pictures/cover.png 2>/dev/null
```

Response: `{ url, publicId, savedTo, bytes }`. Tell the user the saved path so they
can move/rename it.

After downloading, the user can still pick "use N" on the same quadrant — the backend
caches the upscale so the second click doesn't re-fire a Midjourney upscale.

### Branch C: "regenerate"

Loop back to **Step 1** (different provider) or **Step 2** (different prompt, same
provider). A fresh `POST /grid` creates a new sessionId; the previous session is
harmless and expires server-side.

## Step 7 — Confirm before proceeding

Once the user has a `finalUrl` they're happy with, confirm:

> "Using this cover: {finalUrl}. Ready to publish the basket?"

Then go back to whichever flow called this sub-flow (Flow A Step 10 or Flow B Step 6).

---

## Quick reference — script cheat sheet

| Step | Script | Purpose |
|---|---|---|
| 2 | `ai_thumbnail_prompt.py` | Generate a starter prompt locally (client-side, no backend call). |
| 3 | `ai_thumbnail_grid.py` | Kick off the 2×2 grid. Returns `sessionId`. |
| 4 | `ai_thumbnail_session.py --wait` | Poll until `gridStatus="ready"`. |
| 6A.i | `ai_thumbnail_select.py` | Pick the final quadrant. |
| 6A.ii | `ai_thumbnail_session.py --wait --wait-for upscale` | Poll until `upscaleStatus="ready"`, read `finalUrl`. |
| 6B | `ai_thumbnail_download.py` | Save a quadrant to disk without committing it as the cover. |

## Failure cases

- **Grid fails (`gridStatus: "failed"`)** — the session view has an `error`. Tell the
  user, offer regenerate. Common cause: the underlying provider rejected the prompt
  (e.g. NSFW filter, length).
- **Timeout (>3 min)** — Midjourney is overloaded. Tell the user, offer regenerate
  (may automatically fall back to Gemini next time).
- **`fellBack: true`** — informational, not an error. Mention it so the user knows
  they're seeing Gemini output even though they asked for Midjourney (or vice versa).
- **403** — caller lost CREATOR/ADMIN role since auth. Re-run `session_status.py`.
