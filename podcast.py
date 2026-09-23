#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["mlx-whisper"]
# ///
"""Download every episode of the I Love Marketing podcast and transcribe it.

The website (ilovemarketing.com/podcasts) sits behind a WAF that blocks scripts,
so this reads the show's public Libsyn RSS feed instead.

Usage:
    uv run podcast.py                  # download + transcribe everything
    uv run podcast.py --limit 3        # only the 3 newest episodes
    uv run podcast.py --download-only  # skip transcription
    uv run podcast.py --delete-audio   # remove each mp3 after its transcript is written

Re-running is safe: finished downloads and transcripts are skipped.
"""

import argparse
import re
import shutil
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

FEED_URL = "https://rss.libsyn.com/shows/54677/destinations/200948.xml"
USER_AGENT = "Mozilla/5.0 (podcast-archiver)"


def fetch(url: str):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=60)


def slugify(text: str, max_len: int = 120) -> str:
    text = re.sub(r"[^\w\s-]", "", text).strip()
    return re.sub(r"[\s_-]+", "_", text)[:max_len].strip("_")


def load_episodes() -> list[dict]:
    """Return episodes newest first, numbered oldest = 1 so names stay stable as new ones arrive."""
    with fetch(FEED_URL) as resp:
        root = ET.fromstring(resp.read())
    items = [item for item in root.findall("./channel/item") if item.find("enclosure") is not None]
    episodes = []
    for index, item in enumerate(reversed(items), start=1):
        title = item.findtext("title", "").strip()
        episodes.append(
            {
                "title": title,
                "date": item.findtext("pubDate", ""),
                "url": item.find("enclosure").get("url"),
                "stem": f"{index:04d}_{slugify(title)}",
            }
        )
    return list(reversed(episodes))


def download(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    with fetch(url) as resp, open(tmp, "wb") as out:
        shutil.copyfileobj(resp, out, length=1 << 20)
    tmp.rename(dest)


def srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def transcribe(audio: Path, txt: Path, srt: Path, model: str, episode: dict) -> None:
    import mlx_whisper

    segments = mlx_whisper.transcribe(str(audio), path_or_hf_repo=model, language="en")["segments"]

    header = f"{episode['title']}\n{episode['date']}\n{episode['url']}\n\n"
    body = "\n".join(seg["text"].strip() for seg in segments)
    txt.write_text(header + body + "\n", encoding="utf-8")

    srt.write_text(
        "\n".join(
            f"{i}\n{srt_time(seg['start'])} --> {srt_time(seg['end'])}\n{seg['text'].strip()}\n"
            for i, seg in enumerate(segments, start=1)
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "data")
    parser.add_argument("--limit", type=int, help="only process the N newest episodes")
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--delete-audio", action="store_true")
    parser.add_argument("--model", default="mlx-community/whisper-large-v3-turbo")
    args = parser.parse_args()

    audio_dir = args.out / "audio"
    text_dir = args.out / "transcripts"
    audio_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)

    episodes = load_episodes()
    if args.limit:
        episodes = episodes[: args.limit]
    print(f"{len(episodes)} episodes to process -> {args.out}")

    failures = []
    for n, ep in enumerate(episodes, start=1):
        audio = audio_dir / f"{ep['stem']}.mp3"
        txt = text_dir / f"{ep['stem']}.txt"
        srt = text_dir / f"{ep['stem']}.srt"
        prefix = f"[{n}/{len(episodes)}] {ep['stem']}"
        try:
            if txt.exists():
                print(f"{prefix}: transcript exists, skip")
                continue
            if not audio.exists():
                print(f"{prefix}: downloading", flush=True)
                download(ep["url"], audio)
            if args.download_only:
                continue
            print(f"{prefix}: transcribing", flush=True)
            transcribe(audio, txt, srt, args.model, ep)
            if args.delete_audio:
                audio.unlink()
        except Exception as exc:  # keep going; report at the end
            print(f"{prefix}: FAILED: {exc}", file=sys.stderr)
            failures.append(ep["stem"])

    print(f"done, {len(failures)} failures")
    for stem in failures:
        print(f"  {stem}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
