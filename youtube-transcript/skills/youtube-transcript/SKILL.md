---
name: youtube-transcript
description: Extract the transcript of a YouTube video to a plain-text .txt file. Use when the user gives a YouTube URL or video ID and wants the transcript, captions, subtitles, or a text version of what was said. Handles videos that already have captions (fast path) and falls back to local Whisper audio transcription when they don't.
---

# YouTube Transcript Extractor

Extract a YouTube video's transcript to a `.txt` file.

## Inputs
- A YouTube URL (`https://www.youtube.com/watch?v=ID`, `https://youtu.be/ID`, or a Shorts/clip URL) **or** a bare 11-character video ID.
- Optional: target language code(s) (default `en`), output path (default `transcript.txt` in the cwd).

## Procedure

### 1. Fast path — existing captions
Run the bundled script. It accepts a URL or ID, extracts the ID itself, and writes plain text:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/extract.py" "<url-or-id>" --out transcript.txt --lang en
```

`$CLAUDE_PLUGIN_ROOT` is set by Claude Code to this plugin's root. The script auto-installs `youtube-transcript-api` if missing. On success it prints the output path and word count — report those to the user and offer the file.

### 2. Fallback — no captions
If step 1 exits code **2** printing `NO_CAPTIONS`, the video has no captions and must be transcribed from audio. This is built into the script behind the `--fallback` flag.

**Confirm with the user first** — it downloads the audio (via `yt-dlp`) and, on first use, a Whisper model (hundreds of MB), then runs CPU transcription (minutes for a long video). Once confirmed, re-run with `--fallback`:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/extract.py" "<url-or-id>" --out transcript.txt --fallback --whisper-model base
```

- Requires `yt-dlp` on PATH (`pip install yt-dlp` or `brew install yt-dlp`); `faster-whisper` auto-installs on first run.
- `--whisper-model` sizes: `tiny|base|small|medium|large-v3|turbo`. `base` is a good speed/quality default; use `small`/`medium` for better accuracy at more time.
- `--keep-audio` leaves the downloaded mp3 in the cwd (default: deleted from a temp dir).
- For a cloud alternative (OpenAI Whisper / Deepgram / AssemblyAI), download audio with `yt-dlp -x --audio-format mp3` and send it to the user's configured API — only if they have a key and prefer it over local.

## Notes
- Use `--lang "de,en"` to try languages in priority order.
- Use `--paragraph` to collapse caption lines into continuous prose instead of one line per caption.
- The YouTube Data API `captions.download` endpoint is intentionally **not** used — it needs OAuth and video ownership for most tracks.
