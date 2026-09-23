# I Love Marketing podcast transcriber

A single Python script that downloads every episode of the
[I Love Marketing](https://ilovemarketing.com/podcasts/) podcast (Joe Polish and
Dean Jackson) and transcribes each one to text on your own Mac.

This repository contains only the script. It does not contain any audio or any
transcript. The podcast content belongs to its creators; run the script to make
your own copy for personal use.

## What it does

1. Reads the show's public Libsyn podcast feed. The website itself sits behind a
   web application firewall that blocks scripts, so the feed is the reliable source.
2. Downloads each episode as an MP3 file.
3. Transcribes each episode locally with
   [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) and
   the `whisper-large-v3-turbo` model. No application programming interface key and
   no cloud service is needed.
4. Writes a plain text transcript and a subtitle file (`.srt`, with timestamps) for
   each episode.

## Requirements

- A Mac with Apple silicon (M1 or later). mlx-whisper runs on Apple silicon only.
- [uv](https://docs.astral.sh/uv/). The script declares its own dependencies, so
  `uv run` installs them on the first run.
- About 25 gigabytes of free disk space for the full audio archive (about 510
  episodes). The transcripts take about 70 megabytes.

## Usage

```bash
uv run podcast.py                  # download and transcribe every episode
uv run podcast.py --limit 3        # only the 3 newest episodes
uv run podcast.py --download-only  # download audio, skip transcription
uv run podcast.py --delete-audio   # delete each MP3 after its transcript is written
uv run podcast.py --out /path/dir  # write somewhere other than ./data
uv run podcast.py --model <repo>   # use a different Hugging Face mlx-whisper model
```

Re-running is safe. The script skips every episode that already has a transcript,
and it downloads to a `.part` file first, so an interrupted download never looks
finished.

If one episode fails, the script continues with the rest and lists the failures at
the end. It exits with status 1 when at least one episode failed.

## Output

```
data/
  audio/
    0001_The_One_Where_We_Start_At_The_Beginning_....mp3
    ...
  transcripts/
    0001_The_One_Where_We_Start_At_The_Beginning_....txt
    0001_The_One_Where_We_Start_At_The_Beginning_....srt
    ...
```

Episodes are numbered from the oldest (`0001`) to the newest, so the file names stay
the same when new episodes are published. The number is the position in the feed,
not the episode number in the title.

Each `.txt` file starts with three header lines (title, publish date, audio URL),
then a blank line, then the transcript with one segment per line.

## Performance

On an Apple M5 Pro, the full archive took about 8 hours, or about 1 minute per
episode on average. Newer episodes are longer (up to about 95 minutes) and take
longer to transcribe.

## Known issues

- **Episode 61 (Eben Pagan) has a broken link in the feed.** The feed points to
  `ILoveMarketing60.mp3` on Libsyn, which returns HTTP 404. The original file is
  still online at `https://s3.amazonaws.com/ilovemarketing/I+Love+Marketing+60.mp3`
  (found through the Wayback Machine copy of the 2012 episode page). Download it by
  hand to `data/audio/0062_Episode_061The_one_with_Eben_Pagan.mp3`, then run the
  script again; it transcribes audio that is already present.
- **Whisper can invent text in silence.** The last line of a transcript is
  sometimes a short phrase that is not in the audio, because the model produces
  text for the silence at the end of an episode.
- **Memory use.** The large model needs several gigabytes of memory. Close other
  heavy applications if the process is stopped for low memory, then run the script
  again to continue.
