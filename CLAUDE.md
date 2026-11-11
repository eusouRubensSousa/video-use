# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`video-use` is a **Claude Code skill**, not an application. The deliverables are:

- [SKILL.md](SKILL.md) — the prose runbook Claude reads during a video-editing session. This is the primary product. Behavioral rules for editing live here, not in code.
- [helpers/](helpers/) — Python scripts the skill invokes (transcription, packing, timeline visualization, color grade, render). Helpers are imported into a session via `python helpers/<name>.py` — there are no console scripts.
- [install.md](install.md) — first-time install runbook (separate from daily usage in SKILL.md).
- [skills/manim-video/](skills/manim-video/) — vendored sub-skill for Manim animations. Read its own SKILL.md before building a Manim slot.

When the skill is "run," Claude is symlinked into the user's agent skills dir (`~/.claude/skills/video-use/`), the user `cd`s into a footage folder, and Claude executes the SKILL.md workflow against files in that external `<videos_dir>`. **All session outputs go to `<videos_dir>/edit/`, never inside this repo.**

## Working in this repo (vs. running the skill)

Most edits here are to SKILL.md prose or to a helper script. Two things follow:

1. **SKILL.md changes are behavioral changes.** A line in SKILL.md is an instruction Claude follows during real edits. Treat prose edits with the same care as code — the "Hard Rules" section in particular encodes silent-failure conditions (subtitles last, per-segment extract, 30ms fades, PTS shift, output-timeline SRT offsets, word-boundary cuts). Don't soften or reorder them without understanding the failure mode each prevents.
2. **Helpers are called from a session, not from tests.** There is no test suite. The verification path is: edit a helper → run it against a real video in a scratch `<videos_dir>/edit/` → check the output by eye and via `ffprobe`. Don't add fake test fixtures; use a real short clip.

## Pipeline (what the helpers do together)

```
transcribe_batch.py  →  pack_transcripts.py  →  (LLM picks cuts → edl.json)  →  render.py  →  final.mp4
                                                                                  │
                                                                          uses grade.py + builds master.srt
```

`timeline_view.py` is the on-demand visual drill-down — called at decision points (and in the self-eval loop on the rendered output), never as a scan.

## Render pipeline invariants ([helpers/render.py](helpers/render.py))

These are load-bearing in the helper, not just SKILL.md guidance:

- `extract_all_segments` → `concat_segments` → `build_final_composite`. Per-segment extract + lossless `-c copy` concat is the only path; do not collapse it into a single filtergraph (would double-encode every segment when overlays are added).
- `build_final_composite` chains overlays first, then applies the `subtitles` filter LAST. Reordering hides captions behind overlays.
- Each overlay gets `setpts=PTS-STARTPTS+T/TB` so its frame 0 lands at the overlay window start. Without this you see the middle of the animation during the window.
- Per-segment extract bakes in 30ms `afade` in/out (`extract_segment`). Don't move fades to the concat step — concat is `-c copy`.
- `build_master_srt` computes output times as `word.start - segment_start + segment_offset`. Source-timeline times will misalign after concat.
- HDR sources (HLG/PQ, common on iPhone) get the `TONEMAP_CHAIN` prepended via `is_hdr_source`. Skipping this keeps HDR transfer metadata on 8-bit output and looks blown out on social uploads.
- Portrait sources (`is_portrait_source`) scale by height, not width, to preserve orientation.
- Final pass runs two-pass `loudnorm` to -14 LUFS / -1 dBTP / LRA 11 (social-platform target). `--no-loudnorm` skips it; `--draft` drops to one-pass for speed.
- `SUB_FORCE_STYLE` uses `MarginV=90` because TikTok/Reels/Shorts UI covers the bottom ~25–30% of vertical frames. Don't drop below ~75 without a specific reason — the comment in [helpers/render.py](helpers/render.py) explains why libass scales relative to PlayResY=288.

## Transcription invariants ([helpers/transcribe.py](helpers/transcribe.py))

- ElevenLabs Scribe with `timestamps_granularity=word`, `diarize=true`, `tag_audio_events=true`, verbatim. Never SRT/phrase mode (loses sub-second gaps), never normalized fillers (loses editorial signal).
- Cached per source — `transcripts/<stem>.json` exists ⇒ skip. Re-transcription is opt-in only.
- API key resolution order: repo-root `.env` → cwd `.env` → `ELEVENLABS_API_KEY` env var. Write keys to repo `.env` only, never to the user's `<videos_dir>`.

## Common commands

```bash
# Install / refresh deps (one of these)
uv sync
pip install -e .

# Run a helper directly (from repo root or anywhere)
python helpers/transcribe.py <video>
python helpers/transcribe_batch.py <videos_dir>          # 4-worker parallel
python helpers/pack_transcripts.py --edit-dir <edit_dir>
python helpers/timeline_view.py <video> <start> <end>
python helpers/grade.py <input> -o <output>              # auto mode
python helpers/render.py <edl.json> -o final.mp4 --build-subtitles
python helpers/render.py <edl.json> -o preview.mp4 --preview
```

There is no lint/test/build step. `ffmpeg` and `ffprobe` are hard runtime requirements; `yt-dlp`, Node (HyperFrames/Remotion), and `manim` are lazy per-feature.

## Edits that need extra care

- **Reordering anything in `build_final_composite`** — the overlay-then-subtitles ordering is Hard Rule 1.
- **Touching the EDL schema** — see the example in SKILL.md "EDL format". `render.py` reads `sources`, `ranges` (`source`/`start`/`end`), `grade` (preset name | raw filter | `"auto"`), `overlays` (`file`/`start_in_output`/`duration`), `subtitles`. Schema changes need to ripple to SKILL.md's editor sub-agent brief.
- **Adding new helpers** — they're invoked as `python helpers/<name>.py` from a session. Keep them runnable standalone (no package imports across helpers beyond the existing `from grade import ...` pattern in `render.py`, which works because both live in `helpers/`).
- **Vendored Manim skill** — [skills/manim-video/](skills/manim-video/) has its own SKILL.md and reference docs. When changing how video-use spawns Manim slots, update both files.
