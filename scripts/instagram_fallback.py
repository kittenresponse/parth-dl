"""Retrieve public Instagram Reels; never accept an HTML page as video."""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlparse

MIN_BYTES = 50 * 1024

def canonical_url(raw):
    parsed = urlparse(raw)
    parts = [part for part in parsed.path.split("/") if part]
    if (parsed.scheme != "https" or parsed.hostname not in ("instagram.com", "www.instagram.com")
            or len(parts) != 2 or parts[0] not in ("reel", "p")
            or not re.fullmatch(r"[A-Za-z0-9_-]+", parts[1])):
        raise ValueError("Only public Instagram post/Reel HTTPS URLs are supported")
    return "https://www.instagram.com/" + "/".join(parts) + "/"

def valid_mp4(path):
    try:
        if pathlib.Path(path).suffix.lower() != ".mp4" or pathlib.Path(path).stat().st_size < MIN_BYTES:
            return False
        with open(path, "rb") as stream:
            return b"ftyp" in stream.read(32)
    except OSError:
        return False

def valid_videos(directory):
    return sorted((p for p in pathlib.Path(directory).rglob("*.mp4") if valid_mp4(p)),
                  key=lambda p: str(p))

def error_summary(stderr):
    # Never include URL query strings, cookies, tokens, or arbitrary server responses in artifacts.
    text = stderr.lower()
    for marker in ("http error 429", "http error 403", "http error 401",
                   "login required", "login_required", "authentication required",
                   "not found", "private", "timed out"):
        if marker in text:
            return marker
    return "downloader error; inspect GitHub step logs for details"

def retrieve(url, output, cookies_text=None):
    output = pathlib.Path(output)
    output.mkdir(parents=True, exist_ok=True)
    attempts = []
    shortcode = urlparse(url).path.strip("/").split("/")[-1]
    # Never reuse a stale video from an earlier request.
    for old in output.rglob("*.mp4"):
        old.unlink()
    with tempfile.TemporaryDirectory(prefix="percept-ig-") as temp:
        cookie_file = None
        if cookies_text:
            cookie_file = pathlib.Path(temp) / "cookies.txt"
            cookie_file.write_text(cookies_text, encoding="utf-8")
            cookie_file.chmod(0o600)
        commands = [
            ("parth-dl", ["parth-dl", "-P", str(output), url]),
            ("yt-dlp", ["yt-dlp", "--no-playlist", "--no-progress",
                        "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
                        "--merge-output-format", "mp4",
                        "--max-filesize", "250M", "-o", str(output / "%(id)s.%(ext)s")]
                       + (["--cookies", str(cookie_file)] if cookie_file else []) + [url]),
            ("instaloader", ["instaloader", "--no-pictures", "--no-metadata-json",
                             "--no-compress-json", "--dirname-pattern", str(output),
                             "--", "-" + shortcode]),
        ]
        for name, command in commands:
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=180)
                files = valid_videos(output)
                attempts.append({"method": name, "exit_code": result.returncode,
                                 "valid_video": bool(files),
                                 "error": error_summary(result.stderr) if result.returncode else None})
                if files:
                    return {"status": "SUCCESS", "method": name,
                            "video_file": str(files[0]), "attempts": attempts}
            except (OSError, subprocess.TimeoutExpired) as exc:
                attempts.append({"method": name, "error": type(exc).__name__})
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
    output = pathlib.Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    result = retrieve(url, output, os.environ.get("IG_COOKIES_TXT"))
    (output / "retrieval.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    if result["status"] != "SUCCESS":
        sys.exit(1)

if __name__ == "__main__":
    main()
