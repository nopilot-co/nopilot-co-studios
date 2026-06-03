# nopilot-co-utilities

A Claude Code plugin marketplace for small, **brand-agnostic utilities** — the bits that support the [studios](https://github.com/nopilot-co/nopilot-co-studios) and general day-to-day workflows but aren't creative-production studios themselves.

Each utility is a **self-contained plugin** in its own top-level directory, with a **standalone CLI** that runs without Claude Code. They are maintained together in this one marketplace and installed together by the root `./install.sh` — but each can also be installed on its own.

| Plugin | Standalone CLI | What it does |
|---|---|---|
| **youtube-transcript** | `yt-transcript` | Extract a YouTube video's transcript to a `.txt`. |

## Skills

### youtube-transcript
Extract a YouTube video's transcript to a plain-text `.txt`.

- **Fast path:** fetches existing captions (auto-generated or human) via `youtube-transcript-api` — no API key, no OAuth, no audio download.
- **Fallback (`--fallback`):** downloads the audio with `yt-dlp` and transcribes locally with `faster-whisper` when a video has no captions.

Trigger it by asking naturally (*"get me the transcript of `<url>` as a txt"*), via the standalone CLI, or by invoking the script directly:

```bash
yt-transcript "https://www.youtube.com/watch?v=ID" --out transcript.txt          # after install.sh
python3 youtube-transcript/scripts/extract.py "https://www.youtube.com/watch?v=ID" --out transcript.txt  # from a checkout
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

The quickest path — clone and run the root installer. It registers the marketplace,
installs every utility plugin, and sets up each standalone CLI (deps + a command on
your PATH):

```bash
git clone https://github.com/nopilot-co/nopilot-co-utilities.git
cd nopilot-co-utilities
./install.sh
```

Or install just the Claude Code plugin (no standalone CLI):

```bash
claude plugin marketplace add nopilot-co/nopilot-co-utilities
claude plugin install youtube-transcript@nopilot-co-utilities
```

Or set up only one utility's standalone CLI from a checkout:

```bash
./youtube-transcript/install.sh        # installs deps + the `yt-transcript` command
# YT_TRANSCRIPT_FALLBACK=1 ./youtube-transcript/install.sh   # also install Whisper-fallback deps
```

Python deps (`youtube-transcript-api`, and for the fallback `yt-dlp` + `faster-whisper`) also auto-install on first use of the plugin skill; see each utility's `requirements.txt`. `yt-dlp` must be on PATH for the fallback (`pip install yt-dlp` or `brew install yt-dlp`).

### Updating

```bash
claude plugin marketplace update nopilot-co-utilities          # refresh the marketplace clone
claude plugin update youtube-transcript@nopilot-co-utilities    # re-copy into the installed cache
```

> **Version bump required.** `claude plugin update` compares the `version` in a plugin's `.claude-plugin/plugin.json` (and its marketplace entry), **not** file contents — so a change to `extract.py` or a skill won't be picked up unless the version is bumped. Bump both the plugin manifest and its `marketplace.json` entry on every shippable change, then run the two commands above and restart Claude Code.

## Layout

The repo root is the **marketplace** (a catalog only). Each utility is a
self-contained plugin in its own top-level directory — its own manifest, skill,
standalone CLI, and installer — mirroring the
[nopilot-co-studios](https://github.com/nopilot-co/nopilot-co-studios) structure.

```
.claude-plugin/
  marketplace.json            # marketplace catalog — lists each utility plugin + its source
install.sh                    # registers marketplace + installs every plugin & CLI
youtube-transcript/           # a utility plugin (source: ./youtube-transcript)
  .claude-plugin/
    plugin.json               # the plugin manifest
  install.sh                  # installs deps + the standalone `yt-transcript` CLI
  skills/
    youtube-transcript/
      SKILL.md                # model-invoked skill; calls scripts/extract.py via $CLAUDE_PLUGIN_ROOT
  scripts/
    extract.py                # the CLI (also runnable standalone)
  requirements.txt
LICENSE                       # MIT
```

To add another utility, create `<name>/.claude-plugin/plugin.json` (plus its
`skills/`, `scripts/`, and `install.sh`), add an entry to `marketplace.json` with
`"source": "./<name>"`, and append the name to the `PLUGINS` array in `install.sh`.

## License

MIT — see [LICENSE](LICENSE).
