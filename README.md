# nopilot-co-utilities

A Claude Code plugin marketplace for small, **brand-agnostic utility skills** — the bits that support the [studios](https://github.com/nopilot-co/nopilot-co-studios) and general day-to-day workflows but aren't creative-production studios themselves.

| Plugin | What it does |
|---|---|
| **utilities** | General-purpose utility skills. Currently: **youtube-transcript**. |

## Skills

### youtube-transcript
Extract a YouTube video's transcript to a plain-text `.txt`.

- **Fast path:** fetches existing captions (auto-generated or human) via `youtube-transcript-api` — no API key, no OAuth, no audio download.
- **Fallback (`--fallback`):** downloads the audio with `yt-dlp` and transcribes locally with `faster-whisper` when a video has no captions.

Trigger it by asking naturally (*"get me the transcript of `<url>` as a txt"*) or invoke the script directly:

```bash
python3 scripts/extract.py "https://www.youtube.com/watch?v=ID" --out transcript.txt
```

| Flag | Default | Description |
|------|---------|-------------|
| `--out` | `transcript.txt` | Output file path |
| `--lang` | `en` | Comma-separated language priority, e.g. `de,en` |
| `--paragraph` | off | Collapse caption lines into continuous prose |
| `--fallback` | off | If no captions, download audio and transcribe with faster-whisper |
| `--whisper-model` | `base` | `tiny`\|`base`\|`small`\|`medium`\|`large-v3`\|`turbo` |
| `--keep-audio` | off | Keep the downloaded mp3 instead of using a temp dir |

Exit codes: `0` success · `2` no captions (re-run with `--fallback`) · `3` error.

## Install

```bash
# 1. Register the marketplace
claude plugin marketplace add nopilot-co/nopilot-co-utilities

# 2. Install the plugin (skills)
claude plugin install utilities@nopilot-co-utilities
```

### Updating

```bash
claude plugin marketplace update nopilot-co-utilities   # refresh the marketplace clone
claude plugin update utilities@nopilot-co-utilities      # re-copy into the installed cache
```

> **Version bump required.** `claude plugin update` compares the `version` in `.claude-plugin/plugin.json` (and the marketplace entry), **not** file contents — so a change to `extract.py` or a skill won't be picked up unless the version is bumped. Bump both manifests on every shippable change, then run the two commands above and restart Claude Code to load the new version.

Python deps (`youtube-transcript-api`, and for the fallback `yt-dlp` + `faster-whisper`) auto-install on first use; see `requirements.txt`. `yt-dlp` must be on PATH for the fallback (`pip install yt-dlp` or `brew install yt-dlp`).

## Layout

```
.claude-plugin/
  marketplace.json    # marketplace manifest (lists the `utilities` plugin)
  plugin.json         # the `utilities` plugin manifest
skills/
  youtube-transcript/
    SKILL.md          # model-invoked skill; calls scripts/extract.py via $CLAUDE_PLUGIN_ROOT
scripts/
  extract.py          # the CLI (also runnable standalone)
requirements.txt
LICENSE               # MIT
```

## License

MIT — see [LICENSE](LICENSE).
