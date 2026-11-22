"""Public Instagram Reel retrieval with independent open-source fallbacks.

Only public URLs; no credential bypass. Exits nonzero when no playable video was obtained.
"""
import argparse
import json
import pathlib
import subprocess
import sys
from urllib.parse import urlparse

def canonical_url(raw):
    p = urlparse(raw)
    parts = [x for x in p.path.split("/") if x]
    if (p.scheme != "https" or p.hostname not in ("instagram.com", "www.instagram.com")
            or len(parts) != 2 or parts[0] not in ("reel", "p")
            or not all(c.isalnum() or c in "_-" for c in parts[1])):
        raise ValueError("Only public Instagram post and Reel HTTPS URLs are supported")
    return "https://www.instagram.com/" + "/".join(parts) + "/"

def retrieve(url, output):
    output = pathlib.Path(output)
    output.mkdir(parents=True, exist_ok=True)
    attempts = []
    commands = [
        ("parth-dl", ["parth-dl", "-P", str(output), url]),
        ("yt-dlp", ["yt-dlp", "--no-playlist", "--no-progress", "--max-filesize", "250M",
                    "-o", str(output / "%(id)s.%(ext)s"), url]),
        ("instaloader", ["instaloader", "--no-profile-pic", "--no-metadata-json",
                         "--no-captions", "--dirname-pattern", str(output),
                         "--", url]),
    ]
    for name, cmd in commands:
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            videos = [x for x in output.rglob("*") if x.is_file()
                      and x.suffix.lower() in (".mp4", ".mov", ".mkv")
                      and x.stat().st_size > 0]
            attempts.append({"method": name, "exit_code": p.returncode,
                             "video_found": bool(videos)})
            if videos:
                return {"status": "SUCCESS", "method": name, "attempts": attempts}
        except (OSError, subprocess.TimeoutExpired) as exc:
            attempts.append({"method": name, "error_type": type(exc).__name__})
    return {"status": "FAILED", "attempts": attempts}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--output", default="osint-output")
    args = parser.parse_args()
    try:
        url = canonical_url(args.url)
    except ValueError as exc:
        parser.error(str(exc))
    result = retrieve(url, args.output)
    out = pathlib.Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    (out / "retrieval.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "SUCCESS" else 1

if __name__ == "__main__":
    sys.exit(main())
