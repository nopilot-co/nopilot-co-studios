#!/usr/bin/env python3
# Part of the nopilot-co-utilities Claude Code plugin (utilities:youtube-transcript).
# Invoked by skills/youtube-transcript/SKILL.md via $CLAUDE_PLUGIN_ROOT/scripts/extract.py.
# Also runnable standalone: python3 scripts/extract.py <url-or-id>
"""Extract a YouTube transcript to a plain-text file.

Fast path: fetch existing captions via youtube-transcript-api.
Fallback (opt-in, --fallback): download audio with yt-dlp and transcribe
locally with faster-whisper when no captions exist.

Usage:
    extract.py <url-or-id> [--out transcript.txt] [--lang en] [--paragraph]
                           [--fallback] [--whisper-model base] [--keep-audio]

Exit codes:
    0  success
    2  no captions available AND fallback not requested (caller may re-run
       with --fallback after confirming with the user)
    3  other error
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile


def extract_video_id(s: str) -> str:
    """Accept a full URL or a bare ID and return the 11-char video ID."""
    s = s.strip()
    if re.fullmatch(r"[0-9A-Za-z_-]{11}", s):
        return s
    m = re.search(r"(?:v=|/v/|youtu\.be/|/embed/|/shorts/|/clip/)([0-9A-Za-z_-]{11})", s)
    if m:
        return m.group(1)
    raise ValueError(f"Could not extract a video ID from: {s!r}")


def pip_install(pkg: str):
    print(f"Installing {pkg} ...", file=sys.stderr)
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", pkg], check=True)


def fetch_captions(video_id: str, langs, paragraph: bool):
    """Return transcript text, or None if no captions exist."""
    try:
        import youtube_transcript_api  # noqa: F401
    except ImportError:
        pip_install("youtube-transcript-api")
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
    from youtube_transcript_api.formatters import TextFormatter

    api = YouTubeTranscriptApi()
    try:
        transcript = api.fetch(video_id, languages=langs)
    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    if paragraph:
        return " ".join(snippet.text for snippet in transcript)
    return TextFormatter().format_transcript(transcript)


def whisper_fallback(video_id: str, model_size: str, keep_audio: bool) -> str:
    """Download audio with yt-dlp and transcribe with faster-whisper."""
    if not shutil.which("yt-dlp"):
        raise RuntimeError(
            "yt-dlp not found. Install it (pip install yt-dlp, or brew install yt-dlp) "
            "to use the --fallback audio-transcription path."
        )
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        pip_install("faster-whisper")
    from faster_whisper import WhisperModel

    url = f"https://www.youtube.com/watch?v={video_id}"
    workdir = "." if keep_audio else tempfile.mkdtemp(prefix="yt_audio_")
    audio_path = os.path.join(workdir, f"{video_id}.mp3")
    out_tmpl = os.path.join(workdir, f"{video_id}.%(ext)s")

    print(f"No captions — downloading audio for {video_id} ...", file=sys.stderr)
    subprocess.run(
        ["yt-dlp", "-x", "--audio-format", "mp3", "-o", out_tmpl, url],
        check=True,
    )

    print(f"Transcribing with faster-whisper ({model_size}, cpu/int8) ...", file=sys.stderr)
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio_path, beam_size=5)
    print(f"Detected language '{info.language}' "
          f"(p={info.language_probability:.2f}, {info.duration:.0f}s audio)", file=sys.stderr)

    text = " ".join(seg.text.strip() for seg in segments)

    if not keep_audio:
        shutil.rmtree(workdir, ignore_errors=True)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="YouTube URL or 11-char video ID")
    ap.add_argument("--out", default="transcript.txt")
    ap.add_argument("--lang", default="en", help="comma-separated language priority, e.g. 'de,en'")
    ap.add_argument("--paragraph", action="store_true",
                    help="collapse caption lines into continuous prose")
    ap.add_argument("--fallback", action="store_true",
                    help="if no captions, download audio and transcribe with faster-whisper")
    ap.add_argument("--whisper-model", default="base",
                    help="faster-whisper size: tiny|base|small|medium|large-v3|turbo (default base)")
    ap.add_argument("--keep-audio", action="store_true",
                    help="keep the downloaded mp3 in the cwd instead of a temp dir")
    args = ap.parse_args()

    try:
        video_id = extract_video_id(args.source)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 3

    langs = [x.strip() for x in args.lang.split(",") if x.strip()]

    try:
        text = fetch_captions(video_id, langs, args.paragraph)
        source = "captions"
        if text is None:
            if not args.fallback:
                print("NO_CAPTIONS", file=sys.stderr)
                return 2
            text = whisper_fallback(video_id, args.whisper_model, args.keep_audio)
            source = f"whisper:{args.whisper_model}"
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(text)

    words = len(text.split())
    print(f"OK: wrote {args.out} ({words} words, video {video_id}, via {source})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
